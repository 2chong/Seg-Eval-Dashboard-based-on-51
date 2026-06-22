# 세그멘테이션 대시보드 — 아키텍처 가이드

`seg_dashboard` 플러그인의 설계 철학과 확장 규칙을 정의한다.
새 기능을 추가할 때 이 규칙을 따르면 코드를 읽는 누구든 최소한의 파일 수정으로 이해하고 확장할 수 있다.

---

## 1. 핵심 원칙

1. **렌더 시점에 무거운 연산 없음.**
   마스크·픽셀 연산, 모델 추론, 평가 집계는 전부 `tools/precompute_panel_stats.py` 에서 처리한다.
   패널은 `data/panel_stats.json` 만 읽는다. 패널 렌더 함수 안에 픽셀 루프가 있으면 잘못된 설계다.

2. **records(단일 테이블)를 기본 데이터 소스로.**
   per-sample 통합 테이블(`records`: 행 1개 = 샘플 1개의 속성 + 메트릭)이 분포·상관·추이 차트와
   데이터 표의 **유일한** 소스다. JSON 형태의 pandas DataFrame 으로 생각하면 된다.
   **픽셀 전용 예외** — records 에서 파생 불가능, FiftyOne `report()` 필요:
   `confusion_matrix`, `per_class`, `per_class_by_value`.
   그 외의 사전집계 블록은 존재해서는 안 된다. (`fields` — 구 배포판 캐시 — 는 제거됨)

3. **attribute 와 metric 을 항상 구분.**
   - `attribute` = 예측과 무관하게 이미지 자체에서 결정되는 속성 (e.g. `time`, `complexity`).
     **attribute 만** `generate_attrs.py` 가 생성하고, `sample_attrs.json` 에 저장하며,
     FO Dataset sample 필드로 부착해 App 사이드바 **"Sample Attributes"** 그룹에 표시한다.
   - `metric` = 예측·평가에서 나오는 값, 실험마다 다름 (e.g. `recall`, `f1`, `biou`).
     `dataset_builder.py` 는 `kind=="metric"` 항목을 attrs 부착 루프에서 제외한다.
     대신 `pipeline/evaluation.py` 가 FiftyOne `evaluate_segmentations` 후 `fiftyone_eval` 메트릭을
     `{metric}_{exp}` 필드로, `dataset_builder.attach_derived_metric_fields()` 가 `derived`·`mask`
     메트릭(f1, f2, biou)을 같은 방식으로 부착한다.
     모든 메트릭은 App 사이드바 **"Metrics · {model}"** 그룹(실험당 1개)에 표시된다.
   - 테스트: "예측 마스크를 교체하면 값이 바뀌는가?" → 예 = metric, 아니오 = attribute.

4. **하드코딩 없음.** 클래스 목록, 필드 이름, 메트릭 이름, 실험 이름, 데이터셋 키 모두
   stats/config 에서 동적으로 읽는다.

5. **데이터 없음 → 플레이스홀더, 크래시 없음.** stats 에 키가 없으면 예외를 던지지 말고
   메시지를 표시한다. 오래된 stats 파일이 패널을 망가뜨려선 안 된다.

6. **`fiftyone.yml` 에는 ASCII 문자만.** Windows(cp949)에서 FiftyOne YAML 파서는 em-dash,
   원문자, 한국어 등 비-ASCII 문자 앞에서 조용히 실패한다 — 플러그인이 App `+` 메뉴에서
   사라지고 아무 오류 메시지도 없다. `fiftyone.yml` 은 반드시 ASCII 전용으로 유지한다.

---

## 2. 계층 구조

```
데이터 레이어  precompute_panel_stats.py  ->  panel_stats.json (columns / records 스키마)
      |  (읽기 전용)
stats.py       load_stats(dataset?) + list_datasets / list_experiments / get_records
               / get_columns / list_metrics / list_attributes / get_experiment_stats
      |
charts/        BaseChart 서브클래스 — Plotly {"data","layout"} dict 반환만.
               FiftyOne import 없음 (numpy 전용). 오프라인 단위 테스트 가능.
               registry.py: @register_chart(role) 데코레이터 + chart_for(role, col_type) 디스패치.
               _common.py : _COLORS 팔레트 단일 소스.
      |
sections/      PanelSection 서브클래스 — UI 위젯(드롭다운/슬라이더) + 차트 그룹화.
               field_section.py : 선언형 FieldSection (field+chart 조합을 6개 파라미터로 선언).
               multi_select.py  : MultiSelectSection (FiftyOne chips 선택기) + 공용 헬퍼.
      |
framework/     BasePanel — 상태 관리 + 섹션 루프 + 콜백 라우팅.
               widgets.py      : add_dropdown / add_bins_slider / resolve_col_type 헬퍼.
               multi_select.py : MultiSelectMixin (chips 멀티셀렉트를 자동 콜백으로 부여).
      |
panels/        5개 구체 패널 — PANEL_NAME, PANEL_LABEL, SECTIONS 선언만.
```

**의존성은 위에서 아래로만 흐른다.** 하위 계층이 상위 계층을 import 해서는 안 된다.
차트는 FiftyOne 을 import 하지 않는다 — App 없이도 차트 단위 테스트가 가능해야 한다.

---

## 3. 기능 추가 레시피

각 작업은 **최소한의 파일**만 수정하도록 설계됐다.

`make run` 은 `config.py` 변경을 자동 감지하고 App 시작 전에
`generate_attrs` / `precompute_panel_stats` 를 다시 실행한다.
패널·차트·섹션 코드만 변경하는 경우 데이터 재빌드가 필요 없다.

| 추가 항목 | 해야 할 일 | 리빌드 |
|-----------|-----------|--------|
| **새 차트** | `charts/<name>.py` 에 BaseChart 서브클래스 + `@register_chart(role)` 데코레이터 → `charts/__init__.py` 에 1줄 import | 없음 — `make run` |
| **새 섹션 (선언형)** | 패널의 SECTIONS 리스트에 `FieldSection(container=..., dist_role=..., ...)` 추가. 새 파일 불필요 | 없음 — `make run` |
| **새 섹션 (커스텀)** | `sections/<name>.py` 에 PanelSection 서브클래스 → `sections/__init__.py` 에 1줄 import, 패널 SECTIONS 에 추가 | 없음 — `make run` |
| **섹션 구분 헤더** | SECTIONS 리스트에 `SectionLabel("[Overview/Interactive/Selection] ...")` 추가. 새 파일 불필요 | 없음 — `make run` |
| **멀티셀렉트 선택기** | 패널이 `MultiSelectMixin` 을 상속하고 `MULTI_SELECTS` 선언, SECTIONS 에 `MultiSelectSection(key, items_fn, ...)` 추가 | 없음 — `make run` |
| **새 패널** | `panels/<name>.py` 에 BasePanel 서브클래스 → `panels/__init__.py` + `seg_dashboard/__init__.py` + `fiftyone.yml` 에 각 1줄 등록 | 없음 — `make run` |
| **새 속성** (예: weather) | `PANEL_COLUMN_META` 에 `kind:"attribute"` + `generate` 키 항목 추가, `ATTRIBUTE_GROUPS` 의 해당 그룹에 키 추가. `generate_attrs.py` 가 자동 인식 — 추가 코드 없음 | `make run` (config 변경 자동 감지) |
| **새 메트릭** (예: IoU) | `PANEL_COLUMN_META` 에 `kind:"metric"` + `compute` 키 항목 추가. `precompute_panel_stats.py` 가 `_metric_specs()` 로 자동 인식. 새 source 전략은 `_MASK_FNS` 또는 `_DERIVED_FNS` 에 함수 1개 추가 | `make run` (config 변경 자동 감지) |
| **새 실험** (새 모델) | `config._EXPERIMENT_LABELS` 에 키 추가 + `run_inference.py` 의 `MODEL_LOADERS` 에 로더 추가 (불일치 시 시작 시 자동 경고). 추론 먼저 실행 | `make inference` → `make run` |
| **새 데이터셋** | `config.DATASETS` 에 항목 추가(`"attributes": "<group>"`) + `Makefile` 의 `DATASETS` 변수에 키 추가. 전체 파이프라인 실행. 패널 Dataset 드롭다운은 `panel_stats.json` 존재 여부로 자동 발견 | `make pipeline DS=<name>` |

> 규칙: **기존 파일의 `if/elif` 체인이 늘어나야 한다면 설계를 재검토한다.**
> 이상적 패턴: "새 파일 1개 + 등록 1줄."

---

## 4. 컴포넌트 계약 (인터페이스)

### BaseChart
```python
class BaseChart:
    field_types: tuple = ()    # 지원하는 col_type ("categorical" / "numerical")
    def build_figure(self, stats, field=None, params=None) -> dict:
        # 항상 {"data": [...], "layout": {...}} 반환.
        # 데이터 없음 → _empty_figure(msg) 반환, 절대 raise 하지 않음.
```

차트 등록 — `charts/registry.py`:
```python
from .registry import register_chart, chart_for

@register_chart("distribution")   # role 이름으로 등록
class MyDistChart(BaseChart):
    field_types = ("numerical",)
    def build_figure(self, stats, field=None, params=None) -> dict: ...

# 섹션에서 사용:
ChartClass = chart_for("distribution", "numerical")  # 등록된 클래스 반환
```

비-디스패치 차트(Confusion Matrix, Correlation Heatmap, 표, Grouped Bar 등)는
role/field_types 없이 `charts/__init__.py` 에서 직접 import 해 사용한다.

### PanelSection
```python
class PanelSection(ABC):
    def render(self, panel, stats, state, callbacks=None) -> None:
        # 패널에 위젯/차트를 추가. 반환값 없음.
        # state     : 현재 패널 상태 dict.
        # callbacks : {"dataset":fn, "field":fn, "bins":fn, "metric":fn, ...
        #              **panel._extra_callbacks()}  ← 패널별 키 포함
```

### FieldSection
```python
FieldSection(
    container="attr_sec",     # types.Object 컨테이너 이름 (상태 키 네임스페이스)
    dist_role="distribution", # 분포 차트 role (None이면 분포 차트 없음)
    metric_role="metric",     # 메트릭 차트 role (None이면 메트릭 차트 없음)
    kind_filter="attribute",  # 드롭다운에 표시할 kind ("attribute"|"metric"|None=전체)
    show_bins=True,           # bins 슬라이더 표시 여부 (기본 True)
    label="...",              # 섹션 제목
)
# 상태 키: container.field, container.bins, container.metric (점 표기 네임스페이스)
```

언제 `FieldSection` 을 쓰지 않는가:
- 복수 데이터셋/실험의 records 를 직접 조합할 때 (DatasetCompareSection, AttrMetricCompareSection)
- 표·heatmap 처럼 field_types 디스패치가 없는 차트
- 6개 파라미터로 표현되지 않는 특수 로직

### MultiSelectMixin + MultiSelectSection
```python
# 패널 선언
class MyPanel(MultiSelectMixin, BasePanel):  # MRO: Mixin 이 BasePanel 보다 앞
    MULTI_SELECTS = [("selected_experiments", experiment_items)]
    STATE_DEFAULTS = {**BasePanel.STATE_DEFAULTS, "selected_experiments": None}

# 섹션 선언
MultiSelectSection(
    "selected_experiments",          # 상태 키
    experiment_items,                # items_fn(stats) -> list[str]
    label="Experiments",
    labels_fn=experiment_labels,     # items_fn(stats) -> list[str] (표시 이름)
)
```

`MultiSelectMixin` 제공 기능:
- `on_load` / `on_change_dataset` 에서 super() 체이닝으로 전체 선택 자동 초기화.
- `_make_cb(key, items_fn)` → `_BoundCb` 생성, `__getattr__` 로 hot-reload 안전 콜백.
- `_extra_callbacks()` 에 자동으로 포함됨 → 패널에서 별도 등록 불필요.

### BasePanel
```python
class BasePanel(foo.Panel):
    SECTIONS: list[PanelSection]   # 서브클래스에서 선언
    STATE_DEFAULTS: dict           # 상태 스키마 (set_state 키 전부 여기 선언)
    # on_load / render / 콜백 라우팅은 BasePanel 제공.
    # 서브클래스는 PANEL_NAME, PANEL_LABEL, SECTIONS 만 선언.
    # 추가 상태 키 + 콜백 등록:
    #   1. STATE_DEFAULTS = {**BasePanel.STATE_DEFAULTS, "new_key": default}
    #   2. def on_change_new_key(self, ctx): ...
    #   3. def _extra_callbacks(self) -> dict: return {"new_key": self.on_change_new_key}
```

### SectionLabel
```python
SectionLabel("[Overview] 속성 요약  |  전체 데이터, 실험 무관")
SectionLabel("[Interactive] 메트릭 분포  |  Field / Metric / Bins 선택")
SectionLabel("[Selection] Experiments  |  아래 차트의 표시 실험 제어")
# 컨벤션 접두어:
#   [Overview]    — 드롭다운/슬라이더 선택과 무관한 차트
#   [Interactive] — 선택에 반응하는 차트
#   [Selection]   — 아래 섹션을 제어하는 UI 컨트롤(chips/드롭다운)
# 패널 내 레이블 텍스트가 중복되면 위젯 ID 충돌 → 고유하게 유지한다.
```

### _BoundCb
```python
# _BoundCb 는 FiftyOne 직렬화 요구사항(value.__self__.uri, value.__name__)을
# 충족시키는 래퍼다. 클로저는 AttributeError 를 일으키지만 _BoundCb 는 이를 해결한다.
# MultiSelectMixin 이 내부적으로 사용하므로 일반적으로 직접 사용할 필요 없다.
```

### widgets.py 헬퍼
```python
from ..framework.widgets import add_dropdown, add_bins_slider, resolve_col_type

# 드롭다운 한 줄 추가 (types.Dropdown + add_choice 루프 + .enum() 을 대체)
add_dropdown(grp, "metric", metrics, label="Metric",
             default=metric, on_change=cb.get("metric"), labels=_metric_label)

# bins 슬라이더 한 줄 추가
add_bins_slider(grp, "bins", value=bins, on_change=cb.get("bins"))

# col_type 판별 (columns 메타 우선, 없으면 records 값 타입 추론)
col_type = resolve_col_type(field, columns, records)  # "categorical"|"numerical"|None
```

---

## 5. 데이터 스키마 규칙 (panel_stats.json)

```jsonc
{
  "meta": {
    "dataset":            str,                   // "seg-eval-<name>"
    "num_samples":        int,                   // 샘플 수
    "classes":            [str],                 // 클래스 이름 목록
    "generated_at":       str,                   // ISO 8601 UTC
    "experiments":        [str],                 // experiment 이름 목록
    "default_experiment": str,
    "experiment_labels":  {exp: label}
  },
  "columns": {                                   // 모든 차트와 Schema 패널이 이 값을 구동
    "<col>": {
      "kind":        "attribute"|"metric",
      "type":        "categorical"|"numerical",
      "description": str,
      "values":      [str],                      // categorical 전용
      "range":       [lo, hi]                    // numerical 전용 (선택)
      // generate/compute 키는 여기 포함되지 않음 (_DISPLAY_KEYS 에서 제외)
    }
  },
  "experiments": {
    "<exp>": {
      "confusion_matrix":   {"classes":[str], "matrix":[[int]]},  // 픽셀 전용
      "per_class":          {"<cls>": {"recall":f, "f1":f, "precision":f}},  // 픽셀 전용
      "per_class_by_value": {                    // 픽셀 전용 (categorical 속성별 per-class 메트릭)
        "<field>": {
          "<value>": {"per_class": {"<cls>": {"recall":f, "f1":f, "precision":f}}}
        }
      },
      "records": [                               // 단일 기본 소스 (속성 + 전체 메트릭)
        {"image_path":str, "time":str, "complexity":f, "recall":f, "f1":f, ...}
      ],
      "correlation": {"fields":[], "metrics":[], "matrix":[[]], "n_samples":int}
    }
  }
}
```

- **`records`** — **단일 기본 소스**. 분포·상관·추이 차트 전부가 런타임에 이 테이블에서 계산된다.
  속성 값은 `generate_attrs.py` 가, 메트릭 값은 `precompute_panel_stats.py` 의 `compute` 레지스트리가 채운다.
- **`columns`** — `config.PANEL_COLUMN_META` 의 표시 메타데이터. 직접 편집 금지; `PANEL_COLUMN_META` 편집.
  `generate`/`compute` 키는 기록 시 제외된다 (`_DISPLAY_KEYS = {kind, type, description, values, range, unit}`).
- **픽셀 전용 블록** (`confusion_matrix`, `per_class`, `per_class_by_value`) — FiftyOne `report()` 필요,
  records 에서 파생 불가. 그 외 stat 블록은 존재해서는 안 된다.
- **`per_class_by_value` 중첩 구조**: `{field → {value → {per_class → {cls → {recall,f1,precision}}}}}`.
  `per_class` 키가 한 단계 더 있음에 주의.

---

## 6. 패널 레이아웃

| 패널 | 성격 | 상태 키 | 주요 섹션 |
|------|------|----------|----------|
| (1) Data Analysis | 속성만 (실험 무관) | `selected_datasets` (MultiSelectMixin), `attr_sec.*` | Dataset 셀렉터, **[Overview]** 속성 요약, **[Interactive]** 분포 히스토그램, **[Selection]** Datasets chips, 데이터셋 분포 비교 |
| (2) Evaluation | 메트릭, 실험별 | `metric_dist.dist_metric`, `metric_dist.dist_bins` | Dataset 셀렉터, 실험 드롭다운, **[Interactive]** 메트릭 분포 히스토그램, **[Overview]** Confusion Matrix |
| (3) Combined | 속성 × 메트릭 | `attr_sec.*` | Dataset 셀렉터, 실험 드롭다운, **[Interactive]** 메트릭 breakdown, **[Overview]** 상관 heatmap |
| (4) Experiment | 실험 간 비교 | `selected_experiments` (MultiSelectMixin), `attr_cmp.cmp_field/cmp_metric/cmp_bins` | Dataset 셀렉터, **[Selection]** Experiments chips, **[Overview]** per-class 그룹 막대, **[Interactive]** 속성×메트릭 교차 실험 선/막대 |
| (5) Schema & Table | 메타데이터 | ─ | Dataset 셀렉터, **[Overview]** 컬럼 스키마 표, 실험 드롭다운, **[Interactive]** records 표 |

SectionLabel 컨벤션: `[Overview]` = 선택 무관, `[Interactive]` = 선택에 반응, `[Selection]` = 아래 제어.

**Dataset 셀렉터**는 전 패널 공통 (App 그리드와 독립).
**단일 실험 드롭다운**은 패널②③⑤에 있다. 패널①④는 `MultiSelectMixin` 으로 멀티셀렉트(chips).

패널④ 주의: **[Overview] Overall** 막대는 per-sample records 값의 평균(샘플 macro average)이고,
per-class 막대는 픽셀 레벨 `report()` 에서 온다. 같은 y축을 공유하지만 집계 방식이 다름 — 의도된 설계.

### 멀티 데이터셋 설계
- `config.DATASETS` 레지스트리: 항목마다 `data_dir`, zoo 다운로드 파라미터, 시드.
- 각 데이터셋은 자체 `data_dir/` 에 `manifest.json`, `sample_attrs.json`, `panel_stats.json`,
  마스크 하위 디렉터리를 가진다. 데이터셋은 디스크에서 완전히 격리된다.
- 기본 제공 데이터셋 디렉터리: `data/`(Set A, seed 51), `data_coco_b/`(Set B, seed 7), `data_coco_c/`(Set C, seed 99).
- 새 데이터셋 전체 파이프라인: `make pipeline DS=<name>`.
- 패널 Dataset 드롭다운은 `panel_stats.json` 이 실제로 있는 데이터셋만 나열한다.
  데이터셋 전환은 패널 통계만 변경한다 — App 그리드는 `main.py` 가 로드한 데이터셋 유지. 두 선택은 **독립적**.

### FiftyOne 데이터셋 생명주기
- `run_inference.py` 가 zoo 원본(`coco-val-voc-50`)을 GT 마스크 추출용으로 로드한 뒤 추론 완료 후
  FiftyOne DB 에서 삭제한다. 디스크 파일은 zoo 캐시에 남으므로 재실행 시 재다운로드 없음.
- `dataset_builder.build` 가 `persistent=True` 로 `seg-eval-<name>` 을 생성한다.
  평가 결과(`seg_eval_<exp>`)는 FiftyOne DB 에 데이터셋과 함께 저장된다.
- 이후 `main.py` 실행 시 `dataset_builder.build` 가 캐시를 감지 → 재빌드·재평가 건너뜀.
- `main.py` 는 `config.py` mtime 을 `sample_attrs.json` 과 비교해 자동 동기화한다.
  **`make run` 하나로 속성·메트릭 config 변경이 자동 반영된다.**
- 시작 시 정리: 오래된 `seg-eval-*` 와 잔여 zoo 데이터셋을 삭제해 App 에 예상한 데이터셋만 표시한다.
- 강제 재빌드: `make rebuild DS=<name>`

---

## 7. 안티패턴 (하지 말 것)

- 패널 렌더 함수 안에서 마스크·픽셀 연산 → `precompute_panel_stats.py` 로 이동.
- 차트 안에 클래스 이름·메트릭 이름 하드코딩 → stats/columns 에서 동적으로 읽을 것.
- 하나의 `panel.py` 가 계속 길어지는 구조 → sections 과 panels 로 분리.
- 차트에서 FiftyOne import → 차트는 numpy 전용 (FiftyOne 의존성은 sections 이상에서 처리).
- attribute 와 metric 을 동일하게 취급 → 항상 `columns.kind` 로 구분.
- `sample_attrs` / `generate_attrs` 경로로 metric 부착 시도 → `dataset_builder.py` 가 `kind=="metric"` 을 attrs 루프에서 제외. 메트릭은 `evaluation.py` 와 `attach_derived_metric_fields()` 가 `{metric}_{exp}` 필드로 사이드바 "Metrics · {model}" 그룹에 따로 부착한다.
- `fiftyone.yml` 에 비-ASCII 문자 → ASCII 전용 유지 (원칙 6 참고).
- `stats["fields"]` 직접 접근 → `fields` 블록은 제거됨. `get_records(stats, exp)` 사용.
- `generate_attrs.py` 에 속성 이름 하드코딩 → 모든 속성 정의는 `PANEL_COLUMN_META` 에 (`generate` 키 포함). `generate_attrs.py` 는 데이터 주도여야 한다.
- 렌더 시점에 속성 계산 → 속성은 `generate_attrs.py` 가 1회 생성해 `sample_attrs.json` 에 저장. 패널은 `panel_stats.json` 만 읽는다.
- `_build_all_datasets` 루프 바깥에서 `configure_sidebar()` 호출 → 루프 안에서 `activate_dataset()` 가 활성화된 동안 호출해야 데이터셋별 올바른 사이드바 레이아웃을 적용한다.
- `SUPPORTED_METRICS` 상수에 메트릭 이름 하드코딩 → `list_metrics(stats)` 사용. `config.py` 만 편집하면 드롭다운이 자동 동기화된다.
- `STATE_DEFAULTS` 에 추가한 상태 키를 `_extra_callbacks()` 에 미등록 → `on_change` 핸들러 없는 위젯은 상태 업데이트를 조용히 실패한다.
- `if col_type == "categorical": CatChart() else: NumChart()` 분기 → `chart_for(role, col_type)()` 사용.
- `types.Dropdown` + `add_choice` 루프 + `.enum()` 수동 작성 → `add_dropdown()` 헬퍼 사용 (`framework/widgets.py`).
- 새 차트 파일에서 `_COLORS` 팔레트 중복 정의 → `charts/_common.py` 에서 import.
- 체크박스 + `_make_exp_sel_callback` 패턴으로 실험 선택 → `MultiSelectMixin` + `MultiSelectSection` (chips) 로 대체.

---

## 8. 속성 규칙 그룹 + 데이터셋 연결

속성은 세 레이어를 거쳐 전파된다:

```
PANEL_COLUMN_META          — 규칙 라이브러리: 모든 속성의 generate 스펙
       |
ATTRIBUTE_GROUPS           — 명명된 프리셋: {"basic": [...], "full": [...], ...}
                             basic=[time,complexity], full=[time,complexity,count,brightness,density]
       |
DATASETS[name]["attributes"]  — 각 데이터셋이 그룹 이름을 선택 (현재 전부 "full")
       |
config.dataset_attribute_keys(name)  — 그룹 → 검증된 키 목록으로 변환
       |
generate_attrs.py          — 해당 데이터셋에 대한 키만 생성
       |
sample_attrs.json / dataset 필드 / panel_stats columns  — 자동 전파
```

데이터셋별 다른 속성 사용: `ATTRIBUTE_GROUPS` 에 항목 추가·수정 후 `DATASETS` 항목의
`"attributes": "<group>"` 을 변경. 다른 코드 수정 없음.

### 사이드바 자동 구성

**동일 속성 그룹 → 동일 사이드바 레이아웃, 자동으로.**

`pipeline/app.py` 의 `configure_sidebar(dataset)` 는 실제 schema 필드와
`config.EXPERIMENTS` 로 사이드바 그룹을 동적 구성한다 — 필드 이름 하드코딩 없음.
`main.py` 의 `_build_all_datasets` 루프 안에서 각 데이터셋의 `activate_dataset()` 가 활성화된 채 호출된다.

생성되는 그룹:
- `tags` / `metadata` (FiftyOne 기본)
- `Labels` — `ground_truth` + `predictions_{exp}` 필드
- `Sample Attributes` — `PANEL_COLUMN_META` 의 `kind=="attribute"` 이면서 schema 에 존재하는 필드
- `Metrics · {exp_label}` (실험당 1개) — `f.endswith(f"_{exp_name}")` 이고 수치형인 필드
  (e.g. `recall_lraspp_mv3`, `f1_lraspp_mv3`, `biou_lraspp_mv3`)

현재 `media_fields` 는 별도 설정하지 않는다 (기본값 사용). 커스텀 미디어 필드 설정이 필요하다면
`configure_sidebar()` 가 확장 포인트다.

### 알려진 제한: 전역 활성화 모델

`config.activate_dataset(name)` 은 모듈 레벨 전역 변수(`DATA_DIR`, `EXPERIMENTS` 등)를 변경한다.
`main.py` 가 한 프로세스에서 여러 데이터셋을 처리하므로, **모든 per-dataset 작업은 해당 데이터셋의
전역 변수가 활성화된 루프 안에서 실행해야 한다.** 루프 바깥에서 config 전역 변수를 읽는 단계를
추가하면 마지막으로 활성화된 데이터셋의 값을 조용히 사용한다.

---

## 9. PANEL_COLUMN_META — 속성·메트릭 스키마

`config.PANEL_COLUMN_META` 는 대시보드에 나타나는 모든 컬럼의 **규칙 라이브러리**다.
속성은 `ATTRIBUTE_GROUPS` 에도 등록해 어느 데이터셋에 쓸지 제어한다 (§8 참고).

### 속성 항목 구조
```python
"<field_name>": {
    "kind":        "attribute",
    "type":        "categorical" | "numerical",
    "description": str,                    # Schema 패널에 표시
    "values":      [str, ...],             # categorical 전용 — 생성에도 사용
    "range":       [lo, hi],               # numerical 전용  — 생성에도 사용
    "generate":    {                       # generate_attrs.py 제어
        "method":    "choice" | "float" | "int",
        "round":     int,                  # float 전용 (소수 자릿수, 기본 3)
        "null_prob": float,                # 선택. 지정 확률로 None(JSON null) 반환.
                                           # 예: 0.2 → 20% 샘플에서 null, 나머지 정상 생성.
                                           # 미지정 → 항상 정상 값 생성 (기본 동작).
    },
}
```

`generate.method` 규칙:
| method | 공식 | 추가 키 |
|--------|------|---------|
| `"choice"` | `rng.choice(values)` | — |
| `"float"` | `round(rng.uniform(*range), round)` | `round` (기본 3) |
| `"int"` | `rng.randint(*range)` | — |

`null_prob` 처리 순서: method 분기 **전에** RNG 를 1회 소비해 확률적으로 None 반환.
예시: `density` — `{"method": "float", "round": 3, "null_prob": 0.2}`.

**시드 격리**: 속성마다 `f"{ATTR_SEED}:{field}"` 로 독립 RNG 사용. 새 속성 추가가 기존 값에 영향 없음.

`generate` 키는 `panel_stats.json` 기록 시 제외된다 (`_DISPLAY_KEYS` 범위 밖).

### 메트릭 항목 구조
```python
"<field_name>": {
    "kind":        "metric",
    "type":        "numerical",
    "description": str,
    "range":       [lo, hi],               # 선택, 표시 힌트용
    "compute":     {                       # precompute_panel_stats.py 제어
        "source": "fiftyone_eval"          # FiftyOne 평가 결과에서 읽기
               | "mask"                   # 원시 마스크 파일에서 직접 계산
               | "derived",               # 이미 records 에 있는 다른 메트릭에서 파생
        "field":  str,                     # fiftyone_eval 전용 — FO eval 필드 이름
        "fn":     str,                     # mask/derived 전용 — _MASK_FNS/_DERIVED_FNS 키
        "deps":   [str, ...],              # derived 전용 — 이미 계산된 메트릭 이름 목록
                                           # (순서대로 fn 에 위치 인수로 전달)
        "params": dict,                    # mask 전용 — fn 에 전달할 추가 kwargs
    },
}
```

**compute source 전략**:
| source | 계산 위치 | 디스패치 dict |
|--------|-----------|--------------|
| `fiftyone_eval` | FiftyOne `evaluate_segmentations` 결과, `{field}_{exp}` 필드에서 읽기 | n/a (직접 필드 읽기) |
| `mask` | `_MASK_FNS[fn](manifest, exp, **params)` | `_MASK_FNS` |
| `derived` | `_DERIVED_FNS[fn](p, r, ...)` per sample | `_DERIVED_FNS` |

**compute 실행 순서**: `fiftyone_eval` → `mask` → `derived`. `deps` 는 fn 에 전달되는 순서와 일치해야 한다.

새 source 또는 fn: 해당 dispatch dict 에 항목 1개 추가. `if/elif` 체인 불필요.

`compute` 키는 `panel_stats.json` 기록 시 제외된다.

### config.py 변경 → make run (자동 동기화)

`main.py` 는 매 시작 시 `config.py` mtime 을 `sample_attrs.json` mtime 과 비교한다.
`config.py` 편집(새 속성·메트릭·실험 레이블)이 있으면 App 시작 전에 attrs/stats 를 자동 재생성한다.
**별도 make 명령 불필요.**

| config.py 변경 | 명령 |
|----------------|------|
| 새/수정 속성 | `make run` (자동 동기화) |
| 새/수정 메트릭 | `make run` (자동 동기화) |
| 새 실험 레이블 | 추론 완료 후 `make run` (자동 동기화) |
| 새 실험(모델) | 먼저 `make inference`, 이후 `make run` |
| 새 데이터셋 | `config.DATASETS` + `Makefile DATASETS` 추가 후 `make pipeline DS=<name>` |
