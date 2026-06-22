# 패널 편집 예시

`ARCHITECTURE.md`(동일 `docs/` 폴더)의 아키텍처 제약을 기준으로 패널 확장 작업을
단계별로 기록한다. 향후 추가 시 레시피로 활용한다.

아래의 모든 파일 경로는 프로젝트 루트(`D:/projects/`) 기준이다.

---

## 아키텍처 준수 검증

### 핵심 원칙 (ARCHITECTURE.md §1)

| 원칙 | 상태 | 근거 |
|------|------|------|
| 1. 렌더 시점에 무거운 연산 없음 | PASS | 모든 새 차트가 precomputed `records` JSON 소비. 마스크 루프 없음. |
| 2. `records` 단일 기본 소스 | PASS | 모든 새 섹션이 `get_records()` 호출. 새 사전집계 블록 없음. |
| 3. `attribute` / `metric` 구분 | PASS | `list_attributes()` / `list_metrics()` 사용. 혼합 없음. |
| 4. 하드코딩 없음 | PASS | 필드·메트릭·데이터셋·실험 이름 모두 동적 읽기. |
| 5. 데이터 없음 → 플레이스홀더 | PASS | 모든 섹션·차트에 `_empty_figure()` 가드 존재. |
| 6. `fiftyone.yml` ASCII 전용 | PASS | `fiftyone.yml` 미변경. |

### 계층 구조 (ARCHITECTURE.md §2)

```
stats.py          load_stats / get_records / list_* 헬퍼  ← 변경 없음
     |
charts/           charts/metric_dist.py          numpy 전용  ✓
                  charts/cross_exp_metric.py     numpy 전용  ✓
                  charts/dataset_compare.py      numpy 전용  ✓
     |
sections/         sections/metric_dist.py          FiftyOne types 사용  ✓
                  sections/attr_metric_compare.py  FiftyOne types 사용  ✓
                  sections/dataset_compare.py      FiftyOne types 사용  ✓
                  sections/multi_select.py         FiftyOne types 사용  ✓
     |
framework/        framework/base_panel.py          _extra_callbacks() 훅
                  framework/multi_select.py        MultiSelectMixin (chips 자동 콜백)
                  framework/widgets.py             add_dropdown / add_bins_slider / resolve_col_type
     |
panels/           panels/evaluation.py   +STATE_DEFAULTS + extra cbs
                  panels/experiment.py   MultiSelectMixin + AttrMetricCompareSection
                  panels/data_analysis.py MultiSelectMixin + DatasetCompareSection
```

---

## 프레임워크 변경 1: `_extra_callbacks()`

`BasePanel.render()` 는 기본 콜백 5개(`dataset`, `field`, `bins`, `metric`, `experiment`)를
제공한다. 새 상태 키가 필요할 때 `_extra_callbacks()` 를 오버라이드해 추가한다:

```python
# framework/base_panel.py
def _extra_callbacks(self) -> dict:
    """서브클래스에서 추가 상태 키 콜백을 등록한다."""
    return {}

# render() 내부:
callbacks = {
    "dataset": ..., "field": ..., "bins": ...,
    "metric": ..., "experiment": ...,
    **self._extra_callbacks(),   # ← 패널별 추가 키 병합
}
```

`if/elif` 체인 없이 확장 가능.

## 프레임워크 변경 2: `_BoundCb`

FiftyOne 직렬화 요구사항: `on_change` 콜백이 `value.__self__.uri` 와 `value.__name__` 속성을
갖는 바운드 메서드여야 한다. 일반 클로저는 `AttributeError: 'function' object has no attribute '__self__'`
를 일으킨다.

`_BoundCb` 는 클로저를 바운드 메서드처럼 보이게 래핑한다:

```python
class _BoundCb:
    def __init__(self, operator, method_name, fn):
        self.__self__ = operator     # FiftyOne 이 operator.uri 를 여기서 읽음
        self.__name__ = method_name  # dispatch 키
        self._fn      = fn
        setattr(operator, method_name, self)  # FiftyOne dispatch 를 위해 등록

    def __call__(self, ctx):
        return self._fn(ctx)
```

`MultiSelectMixin` 이 내부적으로 사용하므로 일반적으로 직접 사용할 필요 없다.

## 프레임워크 변경 3: `MultiSelectMixin` (핵심)

여러 실험 또는 여러 데이터셋을 동시에 선택하는 compact chips 위젯을 자동으로 처리한다.
이전의 per-experiment 체크박스 패턴(`ExperimentSelectSection`, `exp_sel_<exp>` bool,
`_make_exp_sel_callback` 클로저)을 완전히 대체한다.

```python
class MultiSelectMixin:
    MULTI_SELECTS: list = []   # [(state_key, items_fn(stats) -> list[str]), ...]

    def on_load(self, ctx):
        super().on_load(ctx)     # BasePanel.on_load 체이닝
        self._reset_multi(ctx)   # 전체 선택으로 초기화

    def on_change_dataset(self, ctx):
        super().on_change_dataset(ctx)
        self._reset_multi(ctx)

    def _make_cb(self, key, items_fn) -> _BoundCb:
        def _cb(ctx): ...        # 빈 선택 → 전체 선택으로 자동 복구
        return _BoundCb(self, f"on_change_{key}", _cb)

    def __getattr__(self, name): ...  # hot-reload 안전: on_change_<key> 즉시 생성

    def _extra_callbacks(self) -> dict:
        extra = dict(super()._extra_callbacks())
        for key, items_fn in self.MULTI_SELECTS:
            extra[key] = self._make_cb(key, items_fn)
        return extra
```

---

## 예시 1 — Evaluation 패널: 메트릭 분포 히스토그램

**목표**: 샘플별 메트릭 점수가 어떻게 분포하는지 히스토그램으로 표시
(x = 점수 구간, y = 샘플 수, 실험 선택 고정).

### 수정한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `charts/metric_dist.py` | 신규 `MetricDistributionChart` |
| `charts/__init__.py` | +1줄 import |
| `sections/metric_dist.py` | 신규 `MetricDistributionSection` |
| `sections/__init__.py` | +1줄 import |
| `panels/evaluation.py` | +STATE_DEFAULTS, +on_change_*, +_extra_callbacks, +섹션 |

### 왜 새 상태 키가 필요한가

`dist_metric` / `dist_bins` 를 독립 키로 두어 히스토그램 드롭다운·슬라이더가
다른 섹션의 `metric` / `bins` 와 간섭하지 않도록 한다.
컨테이너 이름 `metric_dist` 로 네임스페이스를 분리한다.

### 단계별 구현

**Step 1 — 차트 작성** (`charts/metric_dist.py`):

```python
class MetricDistributionChart(BaseChart):
    field_types = ("numerical",)

    def build_figure(self, stats, field=None, params=None) -> dict:
        records = params.get("records", [])
        metric  = params.get("metric", "recall")
        bins    = max(2, int(params.get("bins", 10)))
        if not records:
            return _empty_figure("Records not available.")
        values = [float(r[metric]) for r in records if r.get(metric) is not None]
        counts, bin_edges = np.histogram(np.array(values), bins=bins, range=(0.0, 1.0))
        ...
        return {"data": [trace], "layout": layout}
```

규칙: 항상 `{"data": [...], "layout": {...}}` 반환. FiftyOne import 없음. 오프라인 테스트 가능.

**Step 2 — 섹션 작성** (`sections/metric_dist.py`):

컨테이너 `"metric_dist"` 를 사용해 상태 키를 네임스페이스로 묶는다:

```python
class MetricDistributionSection(PanelSection):
    def render(self, panel, stats, state, callbacks=None):
        records = get_records(stats, state.get("experiment"))
        grp = panel.obj("metric_dist", label="Metric Distribution", view=types.ObjectView())
        add_dropdown(grp, "dist_metric", metrics, label="Metric",
                     default=metric, on_change=callbacks.get("metric_dist.dist_metric"))
        add_bins_slider(grp, "dist_bins", value=bins,
                        on_change=callbacks.get("metric_dist.dist_bins"))
        fig = MetricDistributionChart().build_figure(stats, params={...})
        grp.plot("figure", data=fig["data"], layout=fig["layout"])
```

**Step 3 — 패널 업데이트** (`panels/evaluation.py`):

```python
class EvaluationPanel(BasePanel):
    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "metric_dist.dist_metric": "",
        "metric_dist.dist_bins":   10,
    }
    SECTIONS = [..., MetricDistributionSection(), ...]

    def on_change_dist_metric(self, ctx):
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("metric_dist.dist_metric", v)

    def on_change_dist_bins(self, ctx):
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("metric_dist.dist_bins", max(2, int(v)))

    def _extra_callbacks(self):
        return {
            "metric_dist.dist_metric": self.on_change_dist_metric,
            "metric_dist.dist_bins":   self.on_change_dist_bins,
        }
```

상태 키가 `metric_dist.dist_metric` (점 표기) 이고 콜백 dict 키도 동일해야 FiftyOne 이 매핑한다.

---

## 예시 2 — Experiment 패널: 속성 × 메트릭 교차 실험 비교

**목표**: 속성 + 메트릭 선택 → 속성 값별 메트릭 평균을 실험당 하나의 선/막대로 비교.

### 수정한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `charts/cross_exp_metric.py` | 신규 `CrossExpCategoricalChart`, `CrossExpNumericalChart` |
| `charts/__init__.py` | +2줄 import |
| `sections/attr_metric_compare.py` | 신규 `AttrMetricCompareSection` |
| `sections/__init__.py` | +1줄 import |
| `panels/experiment.py` | +STATE_DEFAULTS, +콜백, +섹션 |

### 설계 결정

- **컨테이너 `attr_cmp`**: 상태 키 `attr_cmp.cmp_field`, `attr_cmp.cmp_metric`, `attr_cmp.cmp_bins`.
  `ExperimentCompareSection` 의 `metric` 드롭다운과 간섭하지 않도록 독립 네임스페이스 사용.
- **공유 bin edges**: `CrossExpNumericalChart` 가 전 실험의 field 값을 합쳐 bin edges 를 계산.
  모든 선이 동일한 x축 구간을 사용.

```python
# panels/experiment.py
class ExperimentPanel(MultiSelectMixin, BasePanel):
    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "attr_cmp.cmp_field":   None,
        "attr_cmp.cmp_metric":  "",
        "attr_cmp.cmp_bins":    10,
        "selected_experiments": None,
    }

    def on_change_cmp_field(self, ctx): ...   # attr_cmp.cmp_field 업데이트
    def on_change_cmp_metric(self, ctx): ...  # attr_cmp.cmp_metric 업데이트
    def on_change_cmp_bins(self, ctx): ...    # attr_cmp.cmp_bins 업데이트

    def _extra_callbacks(self):
        extra = dict(super()._extra_callbacks())  # MultiSelectMixin 콜백 포함
        extra.update({
            "attr_cmp.cmp_field":  self.on_change_cmp_field,
            "attr_cmp.cmp_metric": self.on_change_cmp_metric,
            "attr_cmp.cmp_bins":   self.on_change_cmp_bins,
        })
        return extra
```

---

## 예시 3 — Data Analysis 패널: 데이터셋 분포 비교

**목표**: 빌드된 전 데이터셋의 속성 분포를 하나의 차트에 오버레이.
y축을 비율(proportion)로 정규화해 크기가 다른 데이터셋을 공정하게 비교.

### 수정한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `charts/dataset_compare.py` | 신규 `DatasetCompareCategoricalChart`, `DatasetCompareNumericalChart` |
| `charts/__init__.py` | +2줄 import |
| `sections/dataset_compare.py` | 신규 `DatasetCompareSection` |
| `sections/__init__.py` | +1줄 import |
| `panels/data_analysis.py` | SECTIONS 에 +1 섹션 |

**새 상태 키 없음. 프레임워크 변경 없음.**

`DatasetCompareSection` 은 `FieldSection(container="attr_sec")` 이 관리하는
`attr_sec.field` 와 `attr_sec.bins` 를 재사용한다.
사용자가 필드를 바꾸면 비교 차트도 자동으로 그 필드로 업데이트된다.

단일 데이터셋 graceful degradation: 빌드된 데이터셋이 1개뿐이면 섹션이 조용히 반환하고
패널은 정상 동작한다.

---

## 예시 4 — Experiment 패널: 실험 멀티셀렉트 (chips)

**목표**: 사용자가 비교 차트에 포함할 실험을 chips 로 선택.
이전의 체크박스 패턴(`ExperimentSelectSection`, `exp_sel_<exp>` bool,
`_make_exp_sel_callback`)을 `MultiSelectMixin` 으로 완전 교체.

### 수정한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `sections/multi_select.py` | 신규 `MultiSelectSection` + `experiment_items` / `experiment_labels` 헬퍼 |
| `sections/__init__.py` | +1줄 import |
| `framework/multi_select.py` | 신규 `MultiSelectMixin` |
| `framework/__init__.py` | +1줄 import |
| `panels/experiment.py` | `MultiSelectMixin` 상속, `MULTI_SELECTS`, `MultiSelectSection` 추가 |
| `sections/experiment_compare.py` | `state.get("selected_experiments")` 로 필터 |
| `sections/attr_metric_compare.py` | 동일 |

### 이전 패턴 vs 현재 패턴

**이전 (체크박스):**
```python
# experiment.py — 이제 존재하지 않는 패턴
class ExperimentPanel(BasePanel):
    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "exp_sel_lraspp_mv3":    True,
        "exp_sel_deeplabv3_mv3": True,
        "exp_sel_fcn_r50":       True,
        "selected_experiments":  None,
    }

    def _make_exp_sel_callback(self, exp):
        def _cb(ctx):
            v = ctx.params.get("value")
            ctx.panel.set_state(f"exp_sel_{exp}", v)
            # 모든 체크박스 재집계 → selected_experiments
            ...
        return _BoundCb(self, f"on_change_exp_sel_{exp}", _cb)
```

**현재 (MultiSelectMixin + chips):**
```python
class ExperimentPanel(MultiSelectMixin, BasePanel):
    MULTI_SELECTS = [("selected_experiments", experiment_items)]
    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "attr_cmp.cmp_field":   None,
        "attr_cmp.cmp_metric":  "",
        "attr_cmp.cmp_bins":    10,
        "selected_experiments": None,   # None → on_load 시 전체 선택으로 초기화
    }

    SECTIONS = [
        DatasetSelectorSection(),
        SectionLabel("[Selection] Experiments to include in comparison charts"),
        MultiSelectSection(
            "selected_experiments",
            experiment_items,
            label="Experiments",
            labels_fn=experiment_labels,
        ),
        SectionLabel("[Overview] Per-Class Metric Comparison  |  selected experiments"),
        ExperimentCompareSection(),
        AttrMetricCompareSection(),
    ]
```

`MultiSelectMixin` 이 자동으로 처리하는 것:
- `on_load` / `on_change_dataset` 에서 전체 선택으로 초기화
- 빈 선택 → 전체 선택으로 자동 복구
- `_extra_callbacks()` 에 `selected_experiments` 콜백 자동 포함

### 섹션에서의 소비

```python
# sections/experiment_compare.py
def render(self, panel, stats, state, callbacks=None):
    all_exps = list_experiments(stats)
    selected = set(state.get("selected_experiments") or all_exps)
    experiments = [e for e in all_exps if e in selected] or all_exps
    # ↑ None (첫 렌더, on_load 전) 또는 빈 선택 → 전체 실험 사용
```

---

## 예시 5 — 전 패널: SectionLabel UI 구분자

**목표**: "Overview"(선택 무관)와 "Interactive"(선택에 반응) 섹션을 시각으로 구분.
미래 작성자가 코드베이스 전체를 읽지 않아도 따를 수 있는 확장 가능 규칙 제정.

### 수정한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `sections/section_label.py` | 신규 `SectionLabel` |
| `sections/__init__.py` | +1줄 import |
| `panels/*.py` 전부 | `SectionLabel(...)` 를 SECTIONS 에 삽입 |

**새 상태 키 없음. 콜백 없음. 프레임워크 변경 없음.**

### SectionLabel 설계

```python
class SectionLabel(PanelSection):
    def __init__(self, text: str) -> None:
        self._text = text

    def render(self, panel, stats, state, callbacks=None) -> None:
        safe_id = "_lbl_" + "".join(c if c.isalnum() else "_" for c in self._text)[:36]
        panel.md(f"**{self._text}**", name=safe_id)
```

`panel.md()` 사용 — `LabelValueView` 는 "No value provided" 를 보이므로 사용하지 않는다.
상태 키 없음, 콜백 없음 — SECTIONS 에 추가하는 것 외에 다른 코드 수정 불필요.

### 컨테이너 그루핑 (완전 독립 상태 키)

**완전히 독립적인** 상태 키(다른 섹션과 공유하지 않음)는 `panel.obj()` 컨테이너로 묶는다:

```python
# MetricDistributionSection.render() 내부
grp = panel.obj("metric_dist", label="Metric Distribution", view=types.ObjectView())
grp.enum("dist_metric", ...)   # 상태 키: "metric_dist.dist_metric"
grp.int("dist_bins",   ...)    # 상태 키: "metric_dist.dist_bins"
grp.plot("figure",     ...)
```

컨테이너 내부 키는 `컨테이너명.키명` 으로 자동 접두어가 붙는다.
`STATE_DEFAULTS` 와 콜백 dict 에서도 같은 점 표기 키를 사용해야 한다:

```python
STATE_DEFAULTS = {"metric_dist.dist_metric": "", "metric_dist.dist_bins": 10}

def _extra_callbacks(self):
    return {
        "metric_dist.dist_metric": self.on_change_dist_metric,
        "metric_dist.dist_bins":   self.on_change_dist_bins,
    }
```

**공유** 상태 키(`field`, `bins`, `metric`, `experiment`)는 평탄하게 유지한다.
여러 섹션이 같은 키를 읽기 때문이다. `SectionLabel()` 로 시각적으로 구분한다.

### 컨벤션

```
[Overview]    — 드롭다운/슬라이더 선택과 무관한 차트
[Interactive] — 선택에 반응하는 차트, | 뒤에 어떤 선택인지 명시
[Selection]   — 아래 섹션을 제어하는 UI 컨트롤 (chips/드롭다운)
```

---

## 예시 6 — Data Analysis 패널: 데이터셋 멀티셀렉트

**목표**: 데이터셋 분포 비교 차트에 포함할 데이터셋을 chips 로 선택.
Experiment 패널의 `MultiSelectMixin` 패턴을 Data Analysis 에도 적용.

### 수정한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `sections/multi_select.py` | `dataset_items` / `dataset_labels` 헬퍼 추가 |
| `panels/data_analysis.py` | `MultiSelectMixin` 상속, `MULTI_SELECTS`, `MultiSelectSection` |
| `sections/dataset_compare.py` | `state.get("selected_datasets")` 로 필터 |

### 구현

```python
class DataAnalysisPanel(MultiSelectMixin, BasePanel):
    MULTI_SELECTS = [("selected_datasets", dataset_items)]

    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "selected_datasets": None,
        # attr_sec.* 는 FieldSection + BasePanel 이 관리
    }

    SECTIONS = [
        DatasetSelectorSection(),
        SectionLabel("[Overview] Attribute Summary  |  all attributes, experiment-independent"),
        AttributeSummarySection(kind_filter="attribute"),
        SectionLabel("[Interactive] Attribute Distribution  |  Field / Bins selection"),
        FieldSection(
            container="attr_sec",
            dist_role="distribution",
            metric_role=None,
            kind_filter="attribute",
            label="Attribute Distribution",
        ),
        SectionLabel("[Selection] Datasets  |  controls which datasets appear in the comparison below"),
        MultiSelectSection(
            "selected_datasets",
            dataset_items,
            label="Datasets",
            labels_fn=dataset_labels,
        ),
        DatasetCompareSection(),
    ]
```

Experiment 패턴과의 유일한 차이: `MULTI_SELECTS` 의 상태 키와 items_fn 만 다르다.

---

## Decision Guide: 새 상태 키가 필요한가?

| 상황 | 사용할 키 | 비고 |
|------|----------|------|
| 속성 필드 선택 | `attr_sec.field` (FieldSection) | 공유; `on_change_field` 가 `attr_sec.bins` 리셋 |
| 히스토그램 bin 수 | `attr_sec.bins` (FieldSection) | 공유 |
| 주 메트릭 선택 | `attr_sec.metric` (FieldSection) | 같은 패널 내 섹션과 공유 |
| 실험 선택 (단일) | `experiment` | 패널 내 공유, ExperimentSelectorSection 관리 |
| **독립 메트릭 드롭다운** | 새 컨테이너 키 e.g. `metric_dist.dist_metric` | 같은 패널에 메트릭 드롭다운이 2개 있을 때 |
| **독립 bins** | 새 컨테이너 키 e.g. `metric_dist.dist_bins` | 공유 bins 와 독립적이어야 할 때 |
| **멀티 실험 선택** | `selected_experiments` (list) | `MultiSelectMixin` + `MultiSelectSection` 사용 |
| **멀티 데이터셋 선택** | `selected_datasets` (list) | 동일 패턴 |

### FieldSection 선언형 패턴

field+chart 조합 섹션은 `FieldSection` 선언으로 새 파일 없이 추가할 수 있다:

```python
# SECTIONS 리스트에 선언만 추가
FieldSection(
    container="attr_sec",       # types.Object 이름 (상태 키 네임스페이스)
    dist_role="distribution",   # 분포 차트 role — chart_for("distribution", col_type)
    metric_role="metric",       # 메트릭 차트 role
    kind_filter="attribute",    # 드롭다운에 표시할 kind
    label="Attribute Distribution",
)
# 자동 생성 상태 키: attr_sec.field, attr_sec.bins, attr_sec.metric
# 자동 생성 콜백: BasePanel.on_change_field, on_change_bins, on_change_metric
```

`FieldSection` 을 사용하지 않고 커스텀 `PanelSection` 을 쓸 때:
- 복수 데이터셋/실험의 records 를 직접 조합하는 경우
- 표·heatmap 처럼 col_type 디스패치 없는 차트
- 6개 파라미터로 표현되지 않는 특수 로직

### 새 상태 키 등록 4단계

1. 패널의 `STATE_DEFAULTS` 에 키와 기본값 추가
2. `on_change_<key>(self, ctx)` 메서드 추가
3. `_extra_callbacks()` 에 `{"<key>": self.on_change_<key>}` 추가
4. 섹션에서 `state.get("<key>")` 로 읽고, `callbacks.get("<key>")` 를 위젯에 전달

---

## 리빌드 요구사항

네 가지 변경 모두 stats 재빌드 또는 추론 재실행이 필요 없다.
모든 새 차트는 기존 `panel_stats.json` 의 `records` 를 소비한다.

| 변경 | 리빌드 |
|------|--------|
| `records` 를 읽는 새 차트 / 섹션 / 패널 | 없음 — `make run` |
| `config.py` 의 새 속성 | `make run` (자동 동기화) |
| `config.py` 의 새 메트릭 | `make run` (자동 동기화) |
| 새 실험 (추론 필요) | `make inference` → `make run` |
| 새 데이터셋 | `make pipeline DS=<name>` |
