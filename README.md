# 건물 패치 평가 대시보드

FiftyOne 기반 건물 세그멘테이션 평가 대시보드.

---

## 실행

```bash
conda env create -f environment.yml
conda activate fiftyone-seg-eval
make run
```

http://localhost:5151 에서 App이 열리면 우상단 `+` 버튼으로 패널을 추가한다.

---

## 패널

| 패널 | 내용 |
|------|------|
| (1) Data Analysis | 속성 분포 탐색. 여러 데이터셋을 함께 선택해 비교 가능. |
| (2) Evaluation | 메트릭 요약, 분포 히스토그램, Confusion Matrix. |
| (3) Combined | 속성 × 메트릭 교차 분석 및 상관 heatmap. |
| (4) Experiment | 여러 모델을 선택해 per-class 메트릭과 속성별 추이 비교. |
| (5) Schema & Table | 컬럼 스키마 전체와 per-sample 표. |

---

## 확장

- [docs/EXTENDING.md](docs/EXTENDING.md) — 새 데이터셋·모델·속성·메트릭 추가 가이드
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 설계 원칙과 계층 구조

---

## 구조

```
.
+-- main.py
+-- config.py                        # 데이터셋/실험/속성/메트릭 레지스트리
+-- Makefile
+-- pipeline/
|   +-- seg_io.py
|   +-- dataset_builder.py
|   +-- evaluation.py
|   +-- app.py
|   +-- attributes/
|       +-- geometric.py
|       +-- radiometric.py
+-- tools/
|   +-- generate_attrs.py
|   +-- precompute_panel_stats.py
+-- plugins/
|   +-- seg_dashboard/
|       +-- charts/
|       +-- sections/
|       +-- panels/
|       +-- framework/
|       +-- stats.py
+-- data_building/
    +-- <region_year>/
        +-- manifest.json, sample_attrs.json, panel_stats.json
        +-- masks/ground_truth/, masks/predictions/
```
