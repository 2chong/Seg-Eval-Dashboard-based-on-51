# EXTENDING — 확장 교본

이 문서는 자신의 데이터셋·모델·속성·메트릭으로 이 프로젝트를 이식할 때의 레시피다.

---

## 핵심 철학: 한 곳에 선언 → 전 계층 자동 동기화

이 프로젝트의 목표는 **"기억해서 매번 맞추는"** 것이 아니라
**"한 곳에 선언하면 자동으로 따라오는"** 틀이다.

| 선언 위치 | 자동으로 따라오는 것 |
|-----------|---------------------|
| `config.PANEL_COLUMN_META` (attribute) | 생성 로직, sample 필드 부착, 사이드바, 패널 드롭다운, 스키마 표, 분포 차트, 상관 heatmap |
| `config.PANEL_COLUMN_META` (metric + compute) | 패널 드롭다운, records 컬럼, 상관 heatmap, schema 표 |
| `config.ATTRIBUTE_GROUPS` | 데이터셋별 속성 집합, 사이드바 그룹, 패널 필터 |
| `config.DATASETS` | 데이터셋 드롭다운, Makefile 루프, 경로 관리 |
| `config._EXPERIMENT_LABELS` | 실험 드롭다운, 비교 패널, panel_stats 저장 |

---

## 주의: 전역 활성 모델의 한계

`config.activate_dataset(name)`은 **전역 변수를 변이**한다.
`main.py`는 한 프로세스에서 여러 데이터셋을 처리하므로,
**데이터셋별 작업은 반드시 해당 데이터셋이 활성인 구간(`activate_dataset` 직후)에서 수행해야 한다.**
그렇지 않으면 경로·실험 설정이 엉뚱한 데이터셋을 가리킨다.
현재 `main.py`의 `_build_all_datasets` 루프가 이 규칙을 따른다.

---

## 레시피 1: 새 속성 추가

**건드리는 파일: `config.py` 1곳**

```python
# config.PANEL_COLUMN_META 에 추가
"weather": {
    "kind":        "attribute",
    "type":        "categorical",
    "description": "촬영 날씨",
    "values":      ["sunny", "cloudy", "rainy"],
    "generate":    {"method": "choice"},
}

# config.ATTRIBUTE_GROUPS 의 원하는 그룹에 키 추가
"full": ["time", "complexity", "count", "weather"],
```

자동으로 따라오는 것:
- `generate_attrs.py` — weather 컬럼 자동 생성
- FiftyOne sample 필드 부착 (사이드바에 자동 등장)
- 패널 드롭다운, 분포 차트, 상관 heatmap
- `panel_stats.json`의 `columns` 항목

재생성 명령:
```bash
make regen-attr-all
```

**새 generate method 가 필요한 경우 (예: "gaussian")**:
- `tools/generate_attrs.py`의 `_generate_value()` 에 분기 추가 (1곳만)

---

## 레시피 2: 속성 그룹 관리

**건드리는 파일: `config.py` 1곳**

```python
# 새 그룹 정의
ATTRIBUTE_GROUPS = {
    "basic":  ["time", "complexity"],
    "full":   ["time", "complexity", "count"],
    "custom": ["time", "weather", "scene_type"],   # 추가
}

# 데이터셋이 그룹 참조
DATASETS = {
    "my-dataset": {
        ...
        "attributes": "custom",   # 이 한 줄만 바꾸면 속성 집합 전체 전환
    }
}
```

같은 그룹을 가진 데이터셋은 사이드바 그룹 구성도 자동으로 동일해진다.

---

## 레시피 3: 새 데이터셋 추가

**건드리는 파일: `config.py` 1곳 + `Makefile`의 `DATASETS` 변수**

```python
# config.DATASETS 에 추가
"my-dataset": {
    "label":       "My Custom Dataset",
    "data_dir":    ROOT_DIR / "data_my",
    "zoo_name":    "coco-2017",          # 또는 None (자체 데이터면 run_inference 커스터마이즈)
    "split":       "validation",
    "classes":     None,
    "num_samples": 200,
    "seed":        42,
    "attr_seed":   42,
    "attributes":  "full",
}
```

```makefile
# Makefile 상단 DATASETS 변수에 추가
DATASETS = coco-val-voc-50 coco-val-voc-50b my-dataset
```

이후 `make pipeline DS=my-dataset` 으로 전체 파이프라인 실행.

**자체 데이터셋(비-COCO)인 경우**:
- `tools/run_inference.py`의 `load_zoo_subset`을 자신의 데이터 로더로 교체
- `manifest.json` 스키마는 동일하게 유지:
  ```json
  {"image_path": "...", "gt_mask_path": "...", "predictions": {"exp_name": "..."}}
  ```

---

## 레시피 4: 새 평가 메트릭 추가

**건드리는 파일: `config.py` 1곳 + (새 source일 때만) `precompute_panel_stats.py` 1곳**

### 기존 source 재사용 (FiftyOne eval 필드)

FiftyOne `evaluate_segmentations`가 이미 계산하는 값이라면:

```python
# config.PANEL_COLUMN_META 에 추가
"iou": {
    "kind":        "metric",
    "type":        "numerical",
    "description": "Mean IoU per sample",
    "range":       [0.0, 1.0],
    "compute":     {"source": "fiftyone_eval", "field": "iou"},
}
```

### 새 source — 마스크에서 직접 계산

```python
# config.PANEL_COLUMN_META 에 추가
"hausdorff": {
    "kind":    "metric",
    "type":    "numerical",
    "description": "Hausdorff distance (픽셀)",
    "compute": {"source": "mask", "fn": "hausdorff", "params": {"percentile": 95}},
}
```

`precompute_panel_stats.py`에 추가 (1곳):

```python
def _compute_hausdorff(manifest, exp_name, percentile=95):
    # 구현
    return {image_path: value, ...}

_MASK_FNS["hausdorff"] = _compute_hausdorff
```

### 새 source — derived (다른 메트릭에서 파생)

```python
# config 에 추가
"f_beta": {
    "kind":    "metric",
    "type":    "numerical",
    "description": "F-beta score (beta=0.5)",
    "compute": {"source": "derived", "fn": "f_beta"},
}
```

`precompute_panel_stats.py`에 추가 (1곳):

```python
def _f_beta(precision, recall, beta=0.5):
    if precision is None or recall is None:
        return None
    denom = beta**2 * precision + recall
    return float((1 + beta**2) * precision * recall / denom) if denom > 0 else 0.0

_DERIVED_FNS["f_beta"] = _f_beta
```

`config.py`의 compute 스펙에 `deps` 키 추가 (인수 순서 선언):

```python
"f_beta": {
    "compute": {"source": "derived", "fn": "f_beta", "deps": ["precision", "recall"]},
}
```

`deps` 목록의 순서대로 이미 계산된 값이 함수 인수로 전달된다.
새 derived fn을 추가해도 `_build_records` 코드를 수정할 필요가 없다.

재생성 명령:
```bash
make regen-stats-all
```

자동으로 따라오는 것:
- 패널의 메트릭 드롭다운 (list_metrics() 가 동적 읽기)
- Schema 표
- records 컬럼
- 상관 heatmap

**한계**: per-class 메트릭은 FiftyOne `report()`가 반환하는 recall/precision/f1만 지원.
새 메트릭이 per-class로 필요하다면 `_per_class_overall`에 직접 계산 로직 추가 필요.

---

## 레시피 5: 새 실험(모델) 추가

**건드리는 파일: `config.py` + `tools/run_inference.py`**

```python
# config._EXPERIMENT_LABELS 에 추가
_EXPERIMENT_LABELS = {
    "lraspp_mv3":    "LRASPP MobileNetV3-Large",
    "deeplabv3_mv3": "DeepLabV3 MobileNetV3-Large",
    "my_model":      "My Custom Model",              # 추가
}
```

```python
# run_inference.py 에 로더 추가
def _load_my_model():
    from my_package import MyModel
    model = MyModel.load_pretrained()
    return model, my_preprocess_transform

MODEL_LOADERS["my_model"] = _load_my_model
```

실행:
```bash
make inference
make regen-stats-all
```

자동으로 따라오는 것:
- 실험 드롭다운, Experiment 비교 패널
- panel_stats.json에 새 exp 블록

> `run_inference.py` 실행 시 config.EXPERIMENTS와 MODEL_LOADERS의 불일치를 자동 경고한다.

---

## 레시피 6: 새 분석 차트 추가

**건드리는 파일: 신규 파일 1개 + `charts/__init__.py` 1줄**

```python
# plugins/seg_dashboard/charts/my_chart.py
from .base import BaseChart, _empty_figure

class MyChart(BaseChart):
    field_types = ("numerical",)   # 지원 타입 선언

    def build_figure(self, stats, field=None, params=None):
        records = (params or {}).get("records", [])
        # ... Plotly figure 생성 ...
        return {"data": [...], "layout": {...}}
```

```python
# charts/__init__.py 에 한 줄 추가
from .my_chart import MyChart
```

규칙:
- `build_figure`는 항상 `{"data": [...], "layout": {...}}` 반환
- FiftyOne import 금지 (차트는 numpy 전용)
- 데이터 없으면 `_empty_figure(msg)` 반환 (크래시 금지)

---

## 레시피 7: 새 패널 섹션 추가

**건드리는 파일: 신규 파일 1개 + `sections/__init__.py` 1줄 + 원하는 패널 SECTIONS 리스트**

```python
# plugins/seg_dashboard/sections/my_section.py
from .base import PanelSection

class MySection(PanelSection):
    def render(self, panel, stats, state, callbacks=None):
        records = get_records(stats, state.get("experiment"))
        # ... FiftyOne panel 위젯/차트 추가 ...
```

```python
# sections/__init__.py 에 한 줄 추가
from .my_section import MySection
```

```python
# panels/combined.py (또는 원하는 패널) SECTIONS 에 추가
SECTIONS = [
    DatasetSelectorSection(),
    ExperimentSelectorSection(),
    MetricBreakdownSection(),
    MySection(),          # 추가 — 다른 섹션 코드 수정 불필요
    CorrelationSection(),
]
```

---

## 레시피 8: 새 패널 추가

**건드리는 파일: 신규 파일 1개 + `panels/__init__.py` 1줄 + `seg_dashboard/__init__.py` 1줄 + `fiftyone.yml` 1줄**

```python
# plugins/seg_dashboard/panels/my_panel.py
from ..framework import BasePanel
from ..sections import DatasetSelectorSection, MySection

class MyPanel(BasePanel):
    PANEL_NAME  = "seg_my_panel"     # fiftyone.yml 과 일치해야 함 (ASCII only)
    PANEL_LABEL = "(6) My Panel"     # App '+' 메뉴에 표시

    SECTIONS = [
        DatasetSelectorSection(),
        MySection(),
    ]
```

`panels/__init__.py`, `seg_dashboard/__init__.py`(register 추가), `fiftyone.yml`(panels 항목 추가)에 각 1줄씩.

> `fiftyone.yml`은 **ASCII 문자만** 허용. 한글·이모지 등 비ASCII 문자가 들어가면
> FiftyOne이 플러그인을 조용히 무시한다 (오류 메시지 없음).

---

## 레시피 9: 사이드바·그리드 커스터마이즈

사이드바는 `pipeline/app.py`의 `configure_sidebar(dataset)` 함수가 담당한다.
이 함수는 `main.py`의 `_build_all_datasets` 루프에서 **각 데이터셋이 활성인 구간**에 호출되므로,
**같은 속성그룹을 가진 데이터셋은 자동으로 같은 사이드바 구성**을 갖는다.

사이드바 그룹 구조를 바꾸려면 `configure_sidebar`만 수정하면 된다.
그룹은 스키마(실제 필드)와 `config.EXPERIMENTS`(현재 활성 데이터셋 기준)에서 동적 생성된다 —
하드코딩된 필드명 없음.

그리드(App 썸네일 표시 필드) 커스터마이즈도 같은 함수에서 `dataset.app_config.media_fields`를
설정하는 방식으로 확장 가능하다.
