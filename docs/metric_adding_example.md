# Metric 추가 예시 — `f2`

> **참고**: `f2` 는 현재 코드베이스에 이미 존재한다 (`config.py`의 `PANEL_COLUMN_META` + `precompute_panel_stats.py`의 `_f2_from_pr`).
> 이 문서는 그 추가 과정을 단계별로 재현한 **튜토리얼**이다.

`f2` (F-beta score, β=2 — recall을 precision보다 2배 가중) 메트릭을 추가하는 과정을 단계별로 기록한다.

---

## 0. Metric vs Attribute: 무엇이 다른가

| 구분 | Attribute | Metric |
|------|-----------|--------|
| 정의 | 예측과 무관한 데이터 고유 속성 | 예측/평가 결과에서 나온 값 |
| 예 | `time`, `complexity`, `brightness` | `recall`, `f1`, `biou`, `f2` |
| 실험별 차이 | 없음 (이미지 자체의 속성) | 있음 (모델마다 다른 값) |
| FiftyOne 샘플 필드 | **O** `sample_attrs` 경로로 부착, 사이드바 "Sample Attributes" 그룹 | **O** `{metric}_{exp}` 형태로 실험별 부착, 사이드바 "Metrics · {model}" 그룹 |
| 생성 시점 | `generate_attrs.py` | `precompute_panel_stats.py` |

테스트: "예측 마스크를 교체하면 이 값이 바뀌는가?" → 바뀌면 metric, 안 바뀌면 attribute.

---

## 1. Metric의 세 가지 compute source

`config.PANEL_COLUMN_META` 에서 `kind="metric"` 항목은 반드시 `compute` 키를 가진다.
`compute.source` 가 어떻게 계산할지를 결정한다.

| source | 계산 위치 | 디스패치 | 기존 예 |
|--------|-----------|----------|---------|
| `fiftyone_eval` | FiftyOne `evaluate_segmentations()` 결과 필드 직접 읽기 | 없음 (필드명만 지정) | `recall`, `precision` |
| `derived` | 이미 계산된 다른 메트릭 값들로 파생 | `_DERIVED_FNS[fn]` | `f1` |
| `mask` | GT/예측 마스크 파일로 직접 계산 | `_MASK_FNS[fn]` | `biou` |

새 메트릭 추가 시 파일 터치 수:

- **기존 fn 재사용** (같은 source, 같은 fn): `config.py` 1개만
- **새 fn (기존 source)**: `config.py` + `precompute_panel_stats.py` 에 함수 1개
- **새 source**: `config.py` + `precompute_panel_stats.py` 에 source 전략 1개

`f2` 는 "새 fn, 기존 source(`derived`)" — **2파일** 터치.

---

## 2. 변경한 파일

| 파일 | 변경 내용 |
|------|-----------|
| `config.py` | `PANEL_COLUMN_META` 에 `f2` 항목 추가 |
| `tools/precompute_panel_stats.py` | `_f2_from_pr` 함수 추가 + `_DERIVED_FNS` 에 등록 |

나머지 파일(`generate_attrs.py`, 패널 코드, `stats.py`)은 전혀 건드리지 않는다.

---

## 3. `config.py` — `PANEL_COLUMN_META` 에 항목 추가

### 변경 전

```python
PANEL_COLUMN_META: dict[str, dict] = {
    # ... attributes ...
    "recall":    { ... },
    "precision": { ... },
    "f1":        { ... },
    "biou":      { ... },
}
```

### 변경 후

```python
PANEL_COLUMN_META: dict[str, dict] = {
    # ... attributes ...
    "recall":    { ... },
    "precision": { ... },
    "f1":        { ... },
    "biou":      { ... },
    "f2": {                                                          # ← 추가
        "kind":        "metric",
        "type":        "numerical",
        "description": "Per-sample F2 score (beta=2, weights recall over precision)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "derived", "fn": "f2", "deps": ["precision", "recall"]},
    },
}
```

### 각 필드의 역할

| 키 | 값 | 설명 |
|---|---|---|
| `kind` | `"metric"` | 예측 의존 값. `sample_attrs` 경로로는 부착되지 않는다. 대신 `evaluation.py` 와 `attach_derived_metric_fields()` 가 `{metric}_{exp}` 필드로 부착해 사이드바 "Metrics · {model}" 그룹에 표시한다. |
| `type` | `"numerical"` | 차트 타입 결정. 메트릭은 항상 `"numerical"`. |
| `description` | 문자열 | Schema 패널 표시용. |
| `range` | `[0.0, 1.0]` | 표시 힌트용 (선택). |
| `compute.source` | `"derived"` | 이미 계산된 다른 메트릭에서 파생. |
| `compute.fn` | `"f2"` | `_DERIVED_FNS` 에서 찾을 함수 이름. |
| `compute.deps` | `["precision", "recall"]` | 함수에 순서대로 전달할 의존 메트릭 이름 목록. |

> `compute` 키는 `generate` 키와 마찬가지로 `panel_stats.json` 에 포함되지 않는다.
> `precompute_panel_stats.py` 의 `_DISPLAY_KEYS` 필터가 제거한다.

---

## 4. `precompute_panel_stats.py` — 함수 추가 + 디스패치 등록

### 변경 전

```python
def _f1_from_pr(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    return float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0


_DERIVED_FNS: dict[str, callable] = {
    "f1": _f1_from_pr,
}
```

### 변경 후

```python
def _f1_from_pr(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    return float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0


def _f2_from_pr(p: float | None, r: float | None) -> float | None:   # ← 추가
    # F_beta (beta=2): (1 + 4) * P * R / (4 * P + R)
    if p is None or r is None:
        return None
    denom = 4 * p + r
    return float(5 * p * r / denom) if denom > 0 else 0.0


_DERIVED_FNS: dict[str, callable] = {
    "f1": _f1_from_pr,
    "f2": _f2_from_pr,   # ← 등록
}
```

### F2 공식

$$F_\beta = \frac{(1 + \beta^2) \cdot P \cdot R}{\beta^2 \cdot P + R}$$

β=2 대입:

$$F_2 = \frac{5 \cdot P \cdot R}{4P + R}$$

β=1이면 F1과 동일. β>1이면 recall을 더 중시. β=2이면 recall 실수(false negative)를
precision 실수(false positive)보다 2배 더 나쁘게 본다.

### 함수 시그니처 규칙 (`derived` source)

```python
# compute.deps 에 선언한 순서대로 positional args 로 전달된다.
# "deps": ["precision", "recall"] → fn(precision_val, recall_val)
def _f2_from_pr(p: float | None, r: float | None) -> float | None:
    ...
```

`_build_records()` 의 derived 처리 루프가 이 규칙을 강제한다:

```python
# precompute_panel_stats.py — _build_records() 내부

for mname, spec in derived_metrics.items():
    fn_name = spec["compute"]["fn"]
    fn = _DERIVED_FNS.get(fn_name)           # "f2" → _f2_from_pr
    if fn is None:
        computed[mname] = None
        continue
    deps = spec["compute"].get("deps", [])   # ["precision", "recall"]
    args = [computed.get(dep) for dep in deps]  # [p_val, r_val]
    computed[mname] = fn(*args)              # _f2_from_pr(p_val, r_val)
```

`deps` 에 선언한 메트릭이 먼저 계산되어 있어야 한다.
compute 순서는 `fiftyone_eval → mask → derived` 로 고정되어 있으므로
`precision`, `recall`(`fiftyone_eval`) 은 항상 `f2`(`derived`) 보다 먼저 계산된다.

---

## 5. 왜 다른 파일을 건드리지 않아도 되는가

### 5-1. 메트릭 자동 감지 (`_metric_specs`)

`precompute_panel_stats.py` 는 어떤 메트릭을 계산할지를
`config.PANEL_COLUMN_META` 에서 **런타임에 동적으로** 읽는다:

```python
def _metric_specs() -> dict[str, dict]:
    return {
        name: meta
        for name, meta in config.PANEL_COLUMN_META.items()
        if meta.get("kind") == "metric" and "compute" in meta
    }
```

`f2` 를 `PANEL_COLUMN_META` 에 추가하면 이 dict 에 자동으로 포함된다.
`precompute_panel_stats.py` 의 메인 로직은 이 dict 을 순회하므로
하드코딩된 `"f2"` 문자열은 `_DERIVED_FNS` 등록 외에 어디에도 없다.

실행 로그에서 확인 가능:
```
Metric specs: ['recall', 'precision', 'f1', 'biou', 'f2']  (from PANEL_COLUMN_META)
```

### 5-2. records 에 자동 포함

`_build_records()` 가 `metric_specs` 전체를 순회해 records 행을 만들기 때문에
`f2` 가 `metric_specs` 에 들어가는 순간 모든 records 행에 자동으로 포함된다:

```
records: 50 rows, keys=[..., 'f1', 'f2']
```

### 5-3. 패널 드롭다운 자동 반영 (`list_metrics`)

패널 코드의 메트릭 드롭다운은 `stats.list_metrics(stats)` 를 호출해
`panel_stats.json["columns"]` 에서 `kind=="metric"` 항목을 동적으로 조회한다.
`f2` 가 `columns` 에 기록되는 순간 모든 패널의 드롭다운에 자동으로 나타난다.

```python
# plugins/seg_dashboard/stats.py (예시)
def list_metrics(stats: dict) -> list[str]:
    return [
        col for col, meta in stats.get("columns", {}).items()
        if meta.get("kind") == "metric"
    ]
```

하드코딩 없이 `config.py` 등록 → `columns` 기록 → 드롭다운 반영 이 자동으로 이어진다.

### 5-4. correlation 에 자동 포함

`_correlation_stats()` 는 records 의 실제 키에서 메트릭을 동적으로 산출한다:

```python
all_keys = set(records[0].keys())
metric_keys = [
    k for k in all_keys
    if k not in ("image_path", *attr_fields)    # 속성·경로 제외하면 전부 메트릭
]
```

`f2` 가 records 에 들어가면 자동으로 correlation 계산 대상이 된다.

---

## 6. 재생성 커맨드

속성(attribute) 변경 없이 메트릭만 변경했으므로 `regen-stats-all` 을 사용한다.
(`regen-attr-all` 은 `generate_attrs.py` 까지 다시 돌리는데 여기선 불필요하다.)

```bash
make regen-stats-all
```

내부 실행:
```
python tools/precompute_panel_stats.py --dataset building-jungrang-2022
python tools/precompute_panel_stats.py --dataset building-seocho-2022
python tools/precompute_panel_stats.py --dataset building-youngdeungpo-2022
```

`generate_attrs.py` 는 실행하지 않는다 — `sample_attrs.json` 은 그대로 재사용된다.

---

## 7. 실행 결과 확인

```
Metric specs: ['recall', 'precision', 'f1', 'biou', 'f2']  (from PANEL_COLUMN_META)

records: 50 rows, keys=['image_path', 'time', 'complexity', 'count', 'brightness',
                         'density', 'recall', 'precision', 'f1', 'biou', 'f2']
                                                                            ↑
                                                                        f2 포함

columns: ['time', 'complexity', 'count', 'brightness', 'density', 'recall', 'precision', 'f1', 'biou', 'f2']
```

`panel_stats.json["columns"]["f2"]` 최종 내용 (`compute` 키 없음):

```json
"f2": {
  "kind":        "metric",
  "type":        "numerical",
  "description": "Per-sample F2 score (beta=2, weights recall over precision)",
  "range":       [0.0, 1.0]
}
```

### F1 vs F2 비교 (같은 샘플)

F2 는 recall 가중이므로 recall이 precision보다 낮은 샘플에서 F2 < F1,
recall이 precision보다 높은 샘플에서 F2 > F1 이 된다.

| P | R | F1 | F2 |
|---|---|----|----|
| 0.8 | 0.4 | 0.533 | 0.455 | ← recall 낮음 → F2 더 낮음 |
| 0.4 | 0.8 | 0.533 | 0.667 | ← recall 높음 → F2 더 높음 |
| 0.6 | 0.6 | 0.600 | 0.600 | ← P=R → F1=F2 |

---

## 8. 세 가지 source 패턴 비교

### Pattern A — `fiftyone_eval` (config 1개만)

FiftyOne `evaluate_segmentations()` 가 `{exp}_{field}` 로 생성한 샘플 필드를
`evaluation.py` 가 `{field}_{exp}` 로 rename 한 뒤, 그 값을 읽는다.
추가 함수 불필요.

```python
# config.py 만 변경
"recall": {
    "kind":    "metric",
    "type":    "numerical",
    "description": "...",
    "compute": {"source": "fiftyone_eval", "field": "recall"},
    #                                               ↑
    #  rename 후 recall_{exp} 샘플 필드에서 읽는다 (예: recall_segformer_init)
}
```

`_build_records()` 의 처리:
```python
for mname, spec in fo_eval_metrics.items():
    # evaluation.py 가 {exp}_{field} → {field}_{exp} 로 rename 한 필드를 읽음
    fo_field = f"{spec['compute']['field']}_{exp_name}"
    computed[mname] = _get_scalar(sample, fo_field)
```

### Pattern B — `derived` (config + 함수 1개) ← 이번 예시

이미 계산된 메트릭 값들을 조합해 새 값을 만든다.

```python
# config.py
"f2": {
    "compute": {"source": "derived", "fn": "f2", "deps": ["precision", "recall"]},
}

# precompute_panel_stats.py
def _f2_from_pr(p, r): ...

_DERIVED_FNS = {"f1": ..., "f2": _f2_from_pr}
```

`_build_records()` 의 처리:
```python
for mname, spec in derived_metrics.items():
    fn  = _DERIVED_FNS[spec["compute"]["fn"]]
    args = [computed[dep] for dep in spec["compute"]["deps"]]
    computed[mname] = fn(*args)
```

**주의**: `deps` 에 적은 메트릭이 이미 `computed` 에 있어야 한다.
`fiftyone_eval → mask → derived` 순서로 처리되므로
`precision`, `recall` 같은 `fiftyone_eval` 메트릭은 항상 먼저 계산된다.

### Pattern C — `mask` (config + 함수 1개)

GT 마스크와 예측 마스크 파일을 직접 읽어 픽셀 레벨 계산을 한다.
FiftyOne evaluation 과 무관한 별도 집계가 필요할 때 사용한다.

```python
# config.py
"biou": {
    "compute": {"source": "mask", "fn": "biou", "params": {"dilation_ratio": 0.02}},
}

# precompute_panel_stats.py
def _compute_biou_for_exp(manifest, exp_name, dilation_ratio=0.02):
    # manifest 에서 GT/예측 마스크 경로를 읽어 per-sample 값 계산
    # 반환: {image_path: float | None}
    ...

_MASK_FNS = {"biou": _compute_biou_for_exp}
```

`_build_records()` 의 처리 (사전 계산 후 lookup):
```python
# 사전 계산 (exp 루프 내)
for mname, spec in metric_specs.items():
    if spec["compute"]["source"] == "mask":
        fn = _MASK_FNS[spec["compute"]["fn"]]
        params = spec["compute"].get("params", {})
        precomputed[fn_name] = fn(manifest, exp_name, **params)

# records 빌드 시 lookup
for mname, spec in mask_metrics.items():
    fn_name = spec["compute"]["fn"]
    computed[mname] = precomputed[fn_name].get(sample.filepath)
```

---

## 9. 전체 데이터 흐름 요약

```
config.py
  PANEL_COLUMN_META["f2"] = {
      kind="metric", compute={source="derived", fn="f2", deps=["precision","recall"]}
  }
       │
       ▼
precompute_panel_stats.py
  _metric_specs()         ← PANEL_COLUMN_META 에서 f2 자동 감지
       │
       ▼ per-experiment 루프
  evaluate_segmentations()  ← precision, recall (fiftyone_eval source 먼저)
  _compute_biou_for_exp()   ← biou (mask source)
  _f2_from_pr(p, r)         ← f2 = 5PR/(4P+R) (derived: DERIVED_FNS["f2"])
  _build_records()          ← 한 행에 attrs + 모든 메트릭 (f2 포함)
  _correlation_stats()      ← f2 포함 자동 상관계수
       │
       ▼ 저장
  data/panel_stats.json
    columns["f2"]            → Schema 패널 표시 (compute 키 없음)
    experiments[*].records   → 분포·상관·데이터 테이블 자동 반영
    experiments[*].correlation → f2 × attributes 상관계수 자동 포함
```

---

## 10. 체크리스트

새 metric을 추가할 때:

- [ ] `PANEL_COLUMN_META` 에 항목 추가 (`kind="metric"`, `type`, `description`, `compute`)
- [ ] source 에 따라 추가 작업:
  - `fiftyone_eval`: FO eval 필드명 확인 후 `compute.field` 에 기재 (함수 불필요)
  - `derived`: `_DERIVED_FNS` 에 함수 1개 추가 / `deps` 순서 ↔ 함수 인수 순서 일치 확인
  - `mask`: `_MASK_FNS` 에 `(manifest, exp_name, **params) → {path: float}` 함수 1개 추가
- [ ] `make regen-stats-all` 실행 (`generate_attrs.py` 는 불필요)
- [ ] 출력의 `Metric specs:` 줄에 새 메트릭 이름 있는지 확인
- [ ] 출력의 `records: keys=` 줄에 새 메트릭 컬럼 있는지 확인
- [ ] App 재시작 후 메트릭 드롭다운에 새 이름 표시 여부 확인
