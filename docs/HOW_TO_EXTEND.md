# 확장 가이드 — 데이터셋·Experiment·속성·메트릭·패널·차트 추가하기

이 프로젝트는 **한 곳에 선언하면 파이프라인·사이드바·차트·상관분석에 자동으로 전파**되도록 설계됐다.  
이 문서는 그 확장성을 실제로 활용하는 방법을 **복붙 가능한 레시피** 형태로 정리한다.

---

## 설계 철학 (1분 이해)

```
config.py 의 4개 레지스트리
  DATASETS               → 어떤 지역/연도 데이터를 쓸 것인가
  _EXPERIMENT_LABELS     → 어떤 모델(실험)을 비교할 것인가
  ATTRIBUTE_GROUPS       → 어떤 속성 집합을 계산할 것인가
  PANEL_COLUMN_META      → 각 속성/메트릭의 정의·범위·계산 방법
        │
        │ 자동 전파
        ▼
  경로 상수 (DATA_DIR, MANIFEST_PATH, ...)
  사이드바 필드 그룹
  드롭다운 목록
  패널 차트
  상관분석 대상
```

**속성 vs 메트릭 판별 한 줄**: "예측 마스크를 바꾸면 이 값도 바뀌는가?"
- No → **attribute** (`kind: "attribute"`, experiment 무관, 1회 계산)
- Yes → **metric** (`kind: "metric"`, experiment마다 다른 값)

**실행 명령은 항상 `make`로.** `python` / `conda` 직접 실행 금지.

---

## 빠른 참조

| 추가 대상 | 고칠 파일 | 재실행 명령 |
|---|---|---|
| 데이터셋 | `config.py` → `DATASETS` | `make pipeline DS=<name>` (최초) → `make run` |
| Experiment | `config.py` → `_EXPERIMENT_LABELS` | 추론 후 `make manifest-all` → `make run` |
| 속성 (attribute) | `pipeline/attributes/*.py` + `config.py` × 2곳 | `make regen-attr` |
| 메트릭 (metric) | `config.py` + (필요 시) `precompute_panel_stats.py` | `make regen-stats` |
| 패널 (panel) | `plugins/seg_dashboard/` 4곳 | `make run` |
| 차트 (chart) | `plugins/seg_dashboard/charts/` 2곳 | `make run` |

---

## 1. 데이터셋 추가

**고칠 곳: `config.py` `DATASETS` 딕셔너리 1곳** (필요 시 `DEFAULT_DATASET`도)

### 1-1. `config.py` — `DATASETS` 항목 추가

```python
# config.py
DATASETS: dict[str, dict] = {
    # ... 기존 항목들 ...

    # ↓ 새 항목 추가
    "dobong_2023": {
        "label":      "도봉구 2023",                          # App/패널 표시 이름
        "data_dir":   ROOT_DIR / "data_building" / "dobong_2023",  # JSON 저장 루트
        "region":     "dobong",                               # 경로 파생에 사용
        "year":       2023,                                   # 경로 파생에 사용
        "attributes": "all",                                  # ATTRIBUTE_GROUPS 키
    },
}
```

`attributes` 값은 반드시 `ATTRIBUTE_GROUPS`에 있는 키여야 한다 (`"geometric"`, `"radiometric"`, `"all"`).  
기본 데이터셋으로 쓰려면 `DEFAULT_DATASET = "dobong_2023"` 도 변경한다.

> **자동 파생되는 경로들** (`activate_dataset()` 이 채움):
> - `DATA_DIR` → `data_building/dobong_2023/`
> - `MANIFEST_PATH` → `data_building/dobong_2023/manifest.json`
> - `ATTRS_PATH` → `data_building/dobong_2023/sample_attrs.json`
> - `PANEL_STATS_PATH` → `data_building/dobong_2023/panel_stats.json`
> - `SOURCE_DB_PATH` → `source_data/experiments/dobong/2023/patches.sqlite`
>
> 따라서 원본 `patches.sqlite` 가 위 경로에 존재해야 한다.

### 1-2. Makefile — 새 데이터셋을 `DATASETS` 목록에 추가 (선택)

`make sync-all` / `make regen-attr-all` 등 `-all` 타겟에 포함시키려면:

```makefile
# Makefile 상단 DATASETS 변수에 추가
DATASETS = seocho_2022 gangseo_2022 junggu_2022 \
           jungrang_2022 mapo_2022 songpa_2022 \
           suseo_2022 yangcheon_2022 youngdeungpo_2022 \
           dobong_2023   # ← 추가
```

### 1-3. 재실행

```bash
# 최초 파이프라인 (manifest → attrs → stats 순서)
make pipeline DS=dobong_2023

# 이후 일상 실행
make run DS=dobong_2023
```

---

## 2. Experiment(모델) 추가

**고칠 곳: `config.py` `_EXPERIMENT_LABELS` 딕셔너리 1곳** (필요 시 `DEFAULT_EXPERIMENT`도)

### 2-1. `config.py` — `_EXPERIMENT_LABELS` 항목 추가

```python
# config.py
_EXPERIMENT_LABELS: dict[str, str] = {
    "segformer_init": "SegFormer 초기 모델",
    "mobile_unet":    "WHU Building UNet++ (EfficientNet-B4)",

    # ↓ 새 항목 추가
    "segformer_v2":   "SegFormer 파인튜닝 v2",   # key = exp_id, value = 표시 라벨
}
```

> **자동 파생**: `activate_dataset()` 이 `EXPERIMENTS[exp]["pred_dir"]` 를 채운다.
> ```
> source_data/data/pred_shp/<region>/<year>/segformer_v2/
> ```
> 추론 스크립트 실행 후 pred SHP 를 이 경로에 두면 된다.
>
> **메트릭 정의는 수정 불필요** — 기존 `precision`, `recall`, `f1` 등이  
> `{metric}_{exp}` 형태(예: `precision_segformer_v2`)로 자동 생성된다.

### 2-2. 재실행

```bash
# 1) 추론 스크립트 실행 → pred SHP 생성 (프로젝트 외부 작업)

# 2) manifest 갱신 (새 predictions 경로 포함)
make manifest-all

# 3) manifest 변경 자동 감지 → precompute 재실행 → App 시작
make run
```

새 experiment 가 FiftyOne 에서 평가되지 않은 경우, FiftyOne 캐시를 지우고 재빌드한다:

```bash
make rebuild DS=jungrang_2022   # DS 별로 실행 필요
```

---

## 3. 속성(attribute) 추가

**고칠 곳 3군데**:
1. `pipeline/attributes/geometric.py` 또는 `radiometric.py` — 계산 함수
2. `config.py` `PANEL_COLUMN_META` — 정의 등록
3. `config.py` `ATTRIBUTE_GROUPS` — 그룹 목록 갱신

### 3-1. 계산 함수 구현

**기하 속성**이면 `pipeline/attributes/geometric.py` 수정:

```python
# pipeline/attributes/geometric.py

# 1) 개별 계산 함수 추가
def building_perimeter_mean(buildings: gpd.GeoDataFrame) -> float:
    """건물 폴리곤 평균 둘레 (m)."""
    if buildings.empty:
        return 0.0
    return float(buildings.geometry.length.mean())


# 2) 통합 함수 compute_geometric() 의 return dict 에 새 키 추가
def compute_geometric(...) -> dict:
    ...
    return {
        "bd_s":              building_count(buildings),
        # ... 기존 키들 ...
        "bd_perimeter_mean": building_perimeter_mean(buildings),  # ← 추가
    }
```

**방사 속성**이면 `pipeline/attributes/radiometric.py` 의 `compute_radiometric()` 또는  
`compute_shadow_ratio()` / `compute_vegetation_ratio()` 패턴을 따라 새 함수를 추가한다.

### 3-2. `config.py` — `PANEL_COLUMN_META` 항목 추가

```python
# config.py  →  PANEL_COLUMN_META 딕셔너리 안에 추가
"bd_perimeter_mean": {
    "kind":        "attribute",
    "type":        "numerical",
    "description": "건물 폴리곤 평균 둘레 (m)",
    "range":       [0, None],          # [최솟값, 최댓값], 상한 미정은 None
    "compute":     {
        "source": "geometric",         # "geometric" 또는 "radiometric"
        "field":  "bd_perimeter_mean", # compute_geometric() 반환 dict 의 키
    },
},
```

### 3-3. `config.py` — `ATTRIBUTE_GROUPS` 갱신

```python
# config.py  →  ATTRIBUTE_GROUPS

ATTRIBUTE_GROUPS: dict[str, list[str]] = {
    "geometric": [
        "bd_s", "bd_portion", ...,
        "bd_perimeter_mean",   # ← 추가
    ],
    "radiometric": [...],
    "all": [
        "bd_s", "bd_portion", ...,
        "bd_perimeter_mean",   # ← "geometric" 과 "all" 양쪽에 추가 (수동 합집합)
        "brightness_mean", ...,
    ],
}
```

> **주의**: `all` 은 `geometric` + `radiometric` 의 수동 합집합이다.  
> 새 속성 추가 시 해당 그룹과 `all` 양쪽을 갱신해야 한다.

### 3-4. 재실행

```bash
# 기본 데이터셋만
make regen-attr

# 모든 데이터셋 한번에
make regen-attr-all
```

> `make run` 의 auto-sync 는 **파일 mtime** 만 감지한다.  
> 속성 compute 코드·config 변경 후에는 반드시 `make regen-attr` 를 명시적으로 실행한다.

---

## 4. 메트릭(metric) 추가

**compute.source 에 따라 고칠 곳이 다르다:**

| source | 의미 | 고칠 파일 |
|---|---|---|
| `fiftyone_eval` | FiftyOne `evaluate_segmentations` scalar | `config.py` 만 |
| `derived` | 다른 메트릭에서 수식으로 파생 | `config.py` + `precompute_panel_stats.py` |
| `mask` | 마스크 파일 직접 계산 (커스텀) | `config.py` + `precompute_panel_stats.py` |

### 패턴 A — `fiftyone_eval` (FiftyOne 기본 평가 지표)

`config.py` 만 수정하면 된다:

```python
# config.py  →  PANEL_COLUMN_META
"my_fo_metric": {
    "kind":        "metric",
    "type":        "numerical",
    "description": "FiftyOne 평가에서 나오는 지표",
    "range":       [0.0, 1.0],
    "compute":     {"source": "fiftyone_eval", "field": "my_fo_metric"},
},
```

### 패턴 B — `derived` (기존 메트릭에서 수식 파생)

**Step 1**: `precompute_panel_stats.py` — 계산 함수 정의 + `_DERIVED_FNS` 등록

```python
# tools/precompute_panel_stats.py

def _f2_from_pr(p, r):
    """F_beta (beta=2): (1+4)*P*R / (4*P + R)"""
    if p is None or r is None:
        return None
    denom = 4 * p + r
    return float(5 * p * r / denom) if denom > 0 else 0.0

_DERIVED_FNS: dict[str, callable] = {
    "f1":  _f1_from_pr,
    "iou": _iou_from_pr,
    "f2":  _f2_from_pr,   # ← 새 함수 등록
}
```

**Step 2**: `config.py` — `PANEL_COLUMN_META` 항목 추가

```python
# config.py  →  PANEL_COLUMN_META
"f2": {
    "kind":        "metric",
    "type":        "numerical",
    "description": "F2 점수 — recall 가중 F-score",
    "range":       [0.0, 1.0],
    "compute":     {
        "source": "derived",
        "fn":     "f2",                     # _DERIVED_FNS 의 키와 일치
        "deps":   ["precision", "recall"],  # 인수 순서가 함수 파라미터 순서
    },
},
```

> `deps` 순서 = 함수의 인수 순서.  
> `_f2_from_pr(p, r)` 이면 `"deps": ["precision", "recall"]`.

### 패턴 C — `mask` (완전 커스텀 마스크 계산)

**Step 1**: `precompute_panel_stats.py` — `_MASK_FNS` 에 함수 등록

```python
# tools/precompute_panel_stats.py

def _my_mask_metric(manifest: list, exp_name: str, **params) -> dict[str, float | None]:
    """이미지 경로 → 값 매핑을 반환."""
    results = {}
    for entry in manifest:
        img_path = entry["image_path"]
        # ... 마스크 로딩 및 계산 ...
        results[img_path] = computed_value
    return results

_MASK_FNS: dict[str, callable] = {
    "my_mask_metric": _my_mask_metric,   # ← 등록
}
```

**Step 2**: `config.py` — `PANEL_COLUMN_META` 항목 추가

```python
"my_mask_metric": {
    "kind":        "metric",
    "type":        "numerical",
    "description": "커스텀 마스크 기반 지표",
    "range":       [0.0, 1.0],
    "compute":     {"source": "mask", "fn": "my_mask_metric"},
},
```

### 재실행

```bash
# 기본 데이터셋만 (--force 로 staleness 무시)
make regen-stats

# 모든 데이터셋
make regen-stats-all
```

> `make run` 의 auto-sync 는 manifest/attrs mtime 변경만 감지한다.  
> 메트릭 정의 변경 후에는 반드시 `make regen-stats` 를 명시적으로 실행한다.

---

## 5. 패널(panel) 추가

**고칠 곳 4군데**:

| 순서 | 파일 | 할 일 |
|---|---|---|
| 1 | `plugins/seg_dashboard/panels/<name>.py` | BasePanel 서브클래스 작성 |
| 2 | `plugins/seg_dashboard/panels/__init__.py` | import + `__all__` 추가 |
| 3 | `plugins/seg_dashboard/__init__.py` | `register()` 루프에 추가 |
| 4 | `plugins/seg_dashboard/fiftyone.yml` | `panels:` 목록에 `PANEL_NAME` 추가 |

### 5-1. 패널 파일 작성 (`panels/my_panel.py`)

```python
# plugins/seg_dashboard/panels/my_panel.py
from ..framework.base_panel import BasePanel
from ..sections.field_section import FieldSection
# (필요한 섹션 import)

class MyPanel(BasePanel):
    PANEL_NAME  = "seg_my_panel"   # fiftyone.yml panels: 의 항목과 정확히 일치해야 함
    PANEL_LABEL = "My Panel"       # App '+' 메뉴에 표시되는 이름
    SECTIONS    = [
        FieldSection(
            title="속성 분포",
            role="distribution",   # chart registry 의 role
        ),
    ]
```

`BasePanel` 이 상태 관리·렌더 루프·콜백 라우팅을 자동으로 처리한다.  
`SECTIONS` 에 나열한 섹션들을 순서대로 렌더링한다.

기존 패널 참조 예시:

| 패널 클래스 | PANEL_NAME | 참고 패턴 |
|---|---|---|
| `DataAnalysisPanel` | `seg_data_analysis` | MultiSelectMixin + FieldSection |
| `EvaluationPanel` | `seg_evaluation` | metric_dist + ConfusionMatrix |
| `CombinedPanel` | `seg_combined` | FieldSection(metric) + Correlation |
| `ExperimentPanel` | `seg_experiment` | MultiSelectMixin + 다중 콜백 |
| `SchemaPanel` | `seg_schema` | 표(Schema/Records) |

### 5-2. `panels/__init__.py` 에 import 추가

```python
# plugins/seg_dashboard/panels/__init__.py
from .data_analysis import DataAnalysisPanel
# ... 기존 import ...
from .my_panel import MyPanel          # ← 추가

__all__ = [
    "DataAnalysisPanel",
    # ...
    "MyPanel",                          # ← 추가
]
```

### 5-3. `seg_dashboard/__init__.py` 에 register 추가

```python
# plugins/seg_dashboard/__init__.py
from .panels import (
    DataAnalysisPanel,
    # ...
    MyPanel,           # ← 추가
)

def register(p):
    for cls in (
        DataAnalysisPanel,
        # ...
        MyPanel,       # ← 추가
    ):
        p.register(cls)
```

### 5-4. `fiftyone.yml` 에 `PANEL_NAME` 추가

```yaml
# plugins/seg_dashboard/fiftyone.yml
name: seg_dashboard
version: "2.0.0"
description: "Multi-panel segmentation evaluation dashboard (...)"
panels:
  - seg_data_analysis
  - seg_evaluation
  - seg_combined
  - seg_experiment
  - seg_schema
  - seg_my_panel      # ← 추가 (MyPanel.PANEL_NAME 과 정확히 일치)
```

> **경고**: `fiftyone.yml` 은 **ASCII 문자만** 허용한다.  
> 한글·이모지·em-dash 등 비ASCII 가 들어가면 FiftyOne 이 **오류 없이 조용히** 플러그인 전체를 무시한다.  
> `description` 값도 yml 본문이므로 비ASCII 삽입 시 같은 문제가 발생한다.

### 재실행

```bash
make run
```

---

## 6. 차트(chart) 추가

**고칠 곳 2군데**:

| 순서 | 파일 | 할 일 |
|---|---|---|
| 1 | `plugins/seg_dashboard/charts/<name>.py` | BaseChart 서브클래스 작성 |
| 2 | `plugins/seg_dashboard/charts/__init__.py` | import + `__all__` 추가 (데코레이터 실행 트리거) |

### 6-1. 차트 파일 작성

**디스패치 차트** (role + col_type 조합으로 자동 선택되는 경우):

```python
# plugins/seg_dashboard/charts/my_chart.py
from .base import BaseChart, _empty_figure
from .registry import register_chart
from ._common import _COLORS   # 공유 색상 팔레트

@register_chart("my_role")          # role 이름 지정
class MyNumericalChart(BaseChart):
    field_types = ("numerical",)    # "categorical", "numerical", 또는 둘 다

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        data = stats.get("records", [])
        if not data:
            return _empty_figure("데이터 없음")   # 빈 데이터 방어 필수

        # Plotly figure dict 직접 반환
        return {
            "data": [{"type": "histogram", "x": [r[field] for r in data if field in r]}],
            "layout": {"title": field},
        }
```

**비-디스패치 차트** (표, heatmap 등 고정 용도):

```python
# @register_chart 없이 직접 구현
class MyTableChart(BaseChart):
    def build_figure(self, stats, field=None, params=None) -> dict:
        ...
```

> **차트 작성 규칙**:
> - **FiftyOne import 금지** — 차트 코드는 numpy/Plotly 전용. `import fiftyone` 은 이 레이어에서 불허.
> - **빈 데이터 방어 필수** — 데이터가 없을 때 반드시 `_empty_figure("...")` 를 반환.
> - **색상은 `_common._COLORS`** — 팔레트 단일 소스. 임의 색상 하드코딩 금지.
> - `build_figure()` 는 항상 `{"data": [...], "layout": {...}}` dict 반환.

현재 등록된 role 목록:

| role | 매핑 클래스 |
|---|---|
| `distribution` | `AttributeDistributionChart` (categorical + numerical) |
| `metric` | `CategoricalMetricChart` / `NumericalMetricChart` |
| `cross_exp` | `CrossExpCategoricalChart` / `CrossExpNumericalChart` |
| `dataset_compare` | `DatasetCompareCategoricalChart` / `DatasetCompareNumericalChart` |
| `metric_dist` | `MetricDistributionChart` (numerical) |

### 6-2. `charts/__init__.py` 에 import 추가

```python
# plugins/seg_dashboard/charts/__init__.py
# ... 기존 import ...
from .my_chart import MyNumericalChart   # ← 추가 (이 import 가 @register_chart 실행)

__all__ = [
    # ...
    "MyNumericalChart",   # ← 추가
]
```

> `@register_chart` 데코레이터는 **클래스 정의 시점**에 실행된다.  
> `charts/__init__.py` 를 통해 import 해야 레지스트리에 실제로 등록된다.  
> 등록 전에 `chart_for("my_role", "numerical")` 를 호출하면 `KeyError` 가 발생한다.

섹션에서 새 차트를 사용하는 방법:

```python
# sections 코드에서
from ..charts import chart_for
fig = chart_for("my_role", col_type)().build_figure(stats, field=field_name)
```

### 재실행

```bash
make run
```

---

## 부록 A: 공통 함정

### `activate_dataset()` 는 모듈 전역을 변경한다

`config.activate_dataset(name)` 은 `DATA_DIR`, `REGION`, `YEAR`, `EXPERIMENTS` 등 모듈 전역을 덮어쓴다.  
`main.py:_build_all_datasets()` 처럼 **반드시 원래 상태로 복원하는 루프 구조**를 써야 한다:

```python
original_active = config.ACTIVE_DATASET
for ds_key in config.DATASETS:
    config.activate_dataset(ds_key)
    # ... 작업 ...
config.activate_dataset(original_active)  # 반드시 복원
```

데이터셋별 작업을 직접 파이썬으로 짤 때 이 패턴을 따르지 않으면  
마지막으로 호출된 데이터셋 기준으로 전역이 남아 다른 코드가 오동작한다.

### `ATTRIBUTE_GROUPS["all"]` 은 수동 합집합이다

```python
ATTRIBUTE_GROUPS = {
    "geometric": ["bd_s", ..., "bd_perimeter_mean"],
    "radiometric": ["brightness_mean", ...],
    "all": [
        "bd_s", ..., "bd_perimeter_mean",   # geometric 목록 복사
        "brightness_mean", ...,             # radiometric 목록 복사
    ],
}
```

새 속성을 추가할 때 해당 그룹(`geometric` 또는 `radiometric`)과 `all` **양쪽에** 키를 넣어야 한다.  
`all` 에 빠지면 `dataset_attribute_keys()` 가 그 키를 반환하지 않아 계산에서 제외된다.

### `make run` 의 auto-sync 한계

`make run` 은 **파일 mtime** 만 감지한다:

| 변경 내용 | `make run` 자동 감지? | 필요한 명령 |
|---|---|---|
| `sample_attrs.json` 없음 | O — `generate_attrs` + `precompute` 자동 실행 | — |
| manifest 가 panel_stats 보다 새로움 | O — `precompute` 자동 실행 | — |
| attrs 가 panel_stats 보다 새로움 | O — `precompute` 자동 실행 | — |
| 속성 compute 코드 / config 변경 | X | `make regen-attr` |
| 메트릭 정의 변경 | X | `make regen-stats` |

### `fiftyone.yml` ASCII 전용

FiftyOne 은 `fiftyone.yml` 파싱 실패 시 **오류 메시지 없이** 플러그인을 조용히 무시한다.  
패널이 App 에서 보이지 않을 때 가장 먼저 `fiftyone.yml` 의 비ASCII 문자를 확인한다.

---

## 부록 B: 심화 참조

| 문서 | 내용 |
|---|---|
| `docs/EXTENDING.md` | 10개 레시피 전체 (섹션 구조, 멀티셀렉트, 사이드바 그룹 등) |
| `docs/panel_editing_example.md` | 기존 패널 수정 6가지 실제 예시 (상태키 네임스페이스 포함) |
| `docs/metric_adding_example.md` | F2 추가 완전 튜토리얼 (per-class 한계 포함) |
| `docs/ARCHITECTURE.md` | 6대 설계 원칙 (렌더시 연산 금지, records 단일소스 등) |
