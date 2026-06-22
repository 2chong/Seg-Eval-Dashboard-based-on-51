# Attribute 추가 예시 — `brightness`

> **참고**: `brightness` 는 현재 코드베이스에 이미 존재한다 (`config.py`의 `PANEL_COLUMN_META` 와 `ATTRIBUTE_GROUPS["full"]`).
> 이 문서는 그 추가 과정을 단계별로 재현한 **튜토리얼**이다.

`brightness` (0~1 float, 랜덤 생성) 속성을 `full` 그룹에 추가하는 과정을 단계별로 기록한다.

---

## 0. 변경한 파일

**단 하나**: `config.py`

나머지 파일(`generate_attrs.py`, `precompute_panel_stats.py`, 패널 코드)은
**전혀 손대지 않는다.** 이것이 이 아키텍처의 핵심이다.

---

## 1. `PANEL_COLUMN_META` 에 항목 추가 (`config.py`)

### 변경 전

```python
PANEL_COLUMN_META: dict[str, dict] = {
    "time":       { ... },
    "complexity": { ... },
    "count":      { ... },
    # metrics ...
}
```

### 변경 후

```python
PANEL_COLUMN_META: dict[str, dict] = {
    "time":       { ... },
    "complexity": { ... },
    "count":      { ... },
    "brightness": {                                          # ← 추가
        "kind":        "attribute",
        "type":        "numerical",
        "description": "Image brightness score (randomly generated, 0-1)",
        "range":       [0.0, 1.0],
        "generate":    {"method": "float", "round": 3},
    },
    # metrics ...
}
```

### 각 필드의 역할

| 키 | 값 | 설명 |
|---|---|---|
| `kind` | `"attribute"` | 예측과 무관한 데이터 고유 속성. `"metric"`이면 FiftyOne 샘플 필드가 되지 않는다. |
| `type` | `"numerical"` | 차트 타입 결정. `"categorical"` / `"numerical"` 두 가지. |
| `description` | 문자열 | Schema 패널에 표시되는 설명. |
| `range` | `[0.0, 1.0]` | 생성 범위(최솟값, 최댓값). `type="numerical"` 필수. |
| `generate.method` | `"float"` | `rng.uniform(lo, hi)` 호출. `"choice"` / `"float"` / `"int"` 세 가지. |
| `generate.round` | `3` | 소수점 자릿수. `method="float"` 전용. |

> `generate` 키는 `generate_attrs.py` 내부 전용이다.
> `precompute_panel_stats.py`가 `panel_stats.json["columns"]`에 쓸 때
> `_DISPLAY_KEYS = {"kind","type","description","values","range","unit"}` 에 없는 키는 모두 제거되므로
> 출력 파일에는 포함되지 않는다.

---

## 2. `ATTRIBUTE_GROUPS["full"]` 에 키 추가 (`config.py`)

### 변경 전

```python
ATTRIBUTE_GROUPS: dict[str, list[str]] = {
    "basic": ["time", "complexity"],
    "full":  ["time", "complexity", "count"],
}
```

### 변경 후

```python
ATTRIBUTE_GROUPS: dict[str, list[str]] = {
    "basic": ["time", "complexity"],
    "full":  ["time", "complexity", "count", "brightness"],  # ← brightness 추가
}
```

`ATTRIBUTE_GROUPS`는 단순한 키 목록(프리셋)이다.
`PANEL_COLUMN_META`가 "규칙 라이브러리"라면, `ATTRIBUTE_GROUPS`는 "이 데이터셋에 쓸 항목 목록"이다.

각 데이터셋은 `DATASETS[name]["attributes"]`로 그룹명을 지정한다:

```python
DATASETS: dict[str, dict] = {
    "coco-val-voc-50":  { ..., "attributes": "full" },
    "coco-val-voc-50b": { ..., "attributes": "full" },
    "coco-val-voc-50c": { ..., "attributes": "full" },
}
```

세 데이터셋 모두 `"full"` 그룹을 쓰므로 `brightness`가 전부에 자동 반영된다.

---

## 3. 이후 코드는 왜 건드리지 않아도 되는가

### 3-1. `generate_attrs.py` — 데이터 기반 동작

`_attr_schema()` 함수가 config를 읽어 "이 데이터셋에 쓸 attribute" 목록을 스스로 조립한다:

```python
# tools/generate_attrs.py

def _attr_schema() -> dict[str, dict]:
    active_keys = set(config.dataset_attribute_keys(config.ACTIVE_DATASET))
    # PANEL_COLUMN_META 중 kind=="attribute" + generate 키 있음 + 이 데이터셋 그룹에 속함
    return {
        key: meta
        for key, meta in config.PANEL_COLUMN_META.items()
        if meta.get("kind") == "attribute" and "generate" in meta and key in active_keys
    }
```

`dataset_attribute_keys()` 는 `DATASETS[name]["attributes"]` → `ATTRIBUTE_GROUPS[group]` 순서로 해석해
검증된 키 목록을 돌려준다. `brightness`를 `full` 그룹에 넣으면 여기서 자동으로 잡힌다.

값 생성은 `_generate_value()`가 `generate.method` 에 따라 분기한다:

```python
def _generate_value(meta: dict, rng: random.Random):
    gen    = meta.get("generate", {})
    method = gen.get("method")

    # null_prob 지정 시 method 분기 전에 RNG를 1회 소비해 None 반환 여부 결정
    if gen.get("null_prob", 0.0) > 0.0 and rng.random() < gen["null_prob"]:
        return None

    if method == "choice":
        return rng.choice(meta["values"])

    if method == "float":                              # ← brightness가 여기로
        lo, hi = meta.get("range", [0.0, 1.0])
        return round(rng.uniform(lo, hi), gen.get("round", 3))

    if method == "int":
        lo, hi = meta.get("range", [0, 50])
        return rng.randint(int(lo), int(hi))
```

`brightness`의 `generate.method = "float"`, `range = [0.0, 1.0]`, `round = 3` 이므로
`round(rng.uniform(0.0, 1.0), 3)` 이 호출된다. 별도 코드 분기 불필요.

### 3-2. 시드 격리 — 기존 속성값 불변

각 속성은 **독립된 RNG** 를 사용한다:

```python
def compute_random_attrs(manifest, base_seed):
    schema = _attr_schema()
    rngs = {field: random.Random(f"{base_seed}:{field}") for field in schema}
    #                                    ↑
    #  "51:time", "51:complexity", "51:count", "51:brightness"
    #  각각 별개의 RNG — 새 속성 추가가 기존 값에 영향 없음
```

`brightness`용 RNG는 `"51:brightness"` 로 시드된다.
`time`, `complexity`, `count`는 원래 시드 그대로이므로 값이 전혀 바뀌지 않는다.

### 3-3. `precompute_panel_stats.py` — columns 메타와 records 자동 반영

**columns 메타** — `PANEL_COLUMN_META`에서 display key만 추출해 그대로 쓴다:

```python
# tools/precompute_panel_stats.py

_DISPLAY_KEYS = {"kind", "type", "description", "values", "range", "unit"}

for name in attr_field_names:          # FiftyOne 스키마에서 감지된 attribute 필드 목록
    if name in config.PANEL_COLUMN_META:
        columns_meta[name] = {
            k: v for k, v in config.PANEL_COLUMN_META[name].items()
            if k in _DISPLAY_KEYS      # generate 키는 여기서 자동 제거됨
        }
```

`attr_field_names`는 `dataset.get_field_schema()`에서 실제 FiftyOne 샘플 필드를 읽어 만든다.
`generate_attrs.py`가 `brightness`를 생성하고 `dataset_builder.py`가 샘플 필드로 등록했다면
`attr_field_names`에 자동으로 포함된다.

**records** — `_build_records()` 가 각 샘플에서 `attr_fields`를 순회해 값을 읽는다:

```python
for sample in dataset.iter_samples():
    record: dict = {"image_path": sample.filepath}

    for f in attr_fields:              # attr_field_names 에서 온 목록
        record[f] = sample.get_field(f)  # ← brightness 값이 여기서 읽힌다

    # ... 이후 metric 계산
    records.append(record)
```

결과적으로 모든 `records` 행에 `brightness` 컬럼이 자동 포함된다.

**상관계수(correlation)** — `_correlation_stats()` 가 수치형 속성을 동적으로 찾는다:

```python
numerical_attrs = [
    f for f in attr_fields
    if isinstance(schema.get(f), (fo.FloatField, fo.IntField))  # brightness → FloatField
]
```

`brightness`가 수치형이므로 자동으로 상관계수 계산 대상이 된다.

---

## 4. 재생성 커맨드

```bash
# 두 데이터셋 모두 attrs + stats 재생성
make regen-attr-all

# 특정 데이터셋만
make regen-attr DS=coco-val-voc-50
```

내부적으로 각 데이터셋에 대해 아래 두 스크립트를 순서대로 실행한다:

```
python tools/generate_attrs.py --dataset <name>
python tools/precompute_panel_stats.py --dataset <name>
```

---

## 5. 실행 결과 확인

`generate_attrs.py` 출력:

```
Attribute schema: ['time', 'complexity', 'count', 'brightness']  (from PANEL_COLUMN_META)
Manifest loaded:  50 entries

  time        : {'day': 29, 'night': 21}
  complexity  : min=0.015, max=0.893, mean=0.463
  count       : min=0, max=49, mean=24.060
  brightness  : min=0.027, max=0.996, mean=0.549   ← 새로 추가됨
```

`precompute_panel_stats.py` 출력 (records 행 요약):

```
records: 50 rows, keys=['image_path', 'time', 'complexity', 'count', 'brightness',
                         'density', 'recall', 'precision', 'f1', 'biou', 'f2']
                                            ↑
                                        brightness 포함
```

`panel_stats.json["columns"]` 최종 내용 (generate 키 없음):

```json
"brightness": {
  "kind":        "attribute",
  "type":        "numerical",
  "description": "Image brightness score (randomly generated, 0-1)",
  "range":       [0.0, 1.0]
}
```

---

## 6. 전체 데이터 흐름 요약

```
config.py
  PANEL_COLUMN_META["brightness"] = { kind, type, range, generate }
  ATTRIBUTE_GROUPS["full"] += ["brightness"]
       │
       ▼
generate_attrs.py
  _attr_schema()          ← PANEL_COLUMN_META + ATTRIBUTE_GROUPS 교차
  _generate_value()       ← generate.method="float" → rng.uniform(0,1)
  시드: random.Random("51:brightness")  ← 기존 속성과 독립
       │
       ▼ 저장
  data/sample_attrs.json
  {"path/img.jpg": {"time":"day", "complexity":0.527, "count":6, "brightness":0.027}, ...}
       │
       ▼
precompute_panel_stats.py
  dataset_builder.build()  ← sample_attrs.json 을 FiftyOne 샘플 필드로 등록
  attr_field_names         ← FiftyOne 스키마에서 brightness 감지
  columns_meta             ← PANEL_COLUMN_META에서 generate 키 제거 후 복사
  _build_records()         ← 샘플별 brightness 값 + 메트릭을 한 행으로
  _correlation_stats()     ← brightness(numerical) × 모든 메트릭 Pearson 상관계수
       │
       ▼ 저장
  data/panel_stats.json
    columns["brightness"]  → Schema 패널 표시
    experiments[*].records → 분포·상관·데이터 테이블 자동 반영
```

---

## 7. 다른 타입으로 추가하려면

### categorical (`"choice"`)

```python
"weather": {
    "kind":        "attribute",
    "type":        "categorical",
    "description": "Weather condition",
    "values":      ["clear", "cloudy", "rainy"],
    "generate":    {"method": "choice"},
}
```

`generate.method = "choice"` → `rng.choice(meta["values"])` 호출.
`range` 대신 `values`를 사용한다.

### integer (`"int"`)

```python
"object_count": {
    "kind":        "attribute",
    "type":        "numerical",
    "description": "Number of annotated objects",
    "range":       [0, 100],
    "generate":    {"method": "int"},
}
```

`generate.method = "int"` → `rng.randint(lo, hi)` 호출.
`round` 키는 필요 없다.

### None 생성 허용 (`null_prob`) — `density` 사례

일부 샘플에서 값이 없는 속성(어노테이션 미존재 등)이 필요할 때 `null_prob`을 사용한다:

```python
"density": {
    "kind":        "attribute",
    "type":        "numerical",
    "description": "Mask density: foreground pixel ratio (0-1). null if annotation absent.",
    "range":       [0.0, 1.0],
    "generate":    {"method": "float", "round": 3, "null_prob": 0.2},
}
```

`null_prob: 0.2` → 약 20%의 샘플에서 `None`(JSON `null`)을 반환, 나머지 80%는 정상 float 생성.
처리 순서: method 분기 **전에** RNG를 1회 소비해 확률 결정 → 기존 속성의 시드 시퀀스에 영향 없음.
`panel_stats.json` 의 records 에서 `None` 값으로 직접 저장된다.
상관계수 계산 시 `None`이 아닌 쌍만 사용한다 (`r.get(fname) is not None` 조건).

---

## 8. 체크리스트

새 attribute를 추가할 때 확인할 사항:

- [ ] `PANEL_COLUMN_META`에 항목 추가 (`kind`, `type`, `description`, `range`/`values`, `generate`)
- [ ] `ATTRIBUTE_GROUPS[그룹명]`에 키 추가
- [ ] `make regen-attr-all` 실행
- [ ] `generate_attrs.py` 출력에서 새 속성 통계 확인
- [ ] `precompute_panel_stats.py` 출력의 `records: keys=` 에서 새 키 확인
- [ ] App 재시작 후 Schema 패널·분포 차트·상관 히트맵에 반영 여부 확인
