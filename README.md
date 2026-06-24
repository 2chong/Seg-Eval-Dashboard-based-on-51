# Building Seg-Eval Dashboard

FiftyOne 기반 건물 segmentation 평가 대시보드.

---

## Getting Started

```bash
conda env create -f environment.yml
conda activate fiftyone-seg-eval
make run
```

http://localhost:5151 에서 App 실행. 우상단 `+` 버튼으로 패널 추가.

---

## Panels

| Panel | |
|---|---|
| **(1) Data Analysis** | 1) 속성 분포 시각화<br>2) 데이터셋 간 분포 비교 |
| **(2) Evaluation** | 1) 전체 패치 metrics 평균<br>2) Metrics distribution histogram<br>3) Confusion Matrix |
| **(3) Combined** | 1) 속성 x metrics 교차 분석<br>2) Correlation heatmap |
| **(4) Experiment** | 1) 모델별 per-class metrics 비교<br>2) 속성별 metrics 추이 비교 |
| **(5) Schema & Table** | 1) Column schema<br>2) Per-sample 표 |

---

## Extending

- [docs/EXTENDING.md](docs/EXTENDING.md) — 데이터셋, 모델, 속성, metrics 추가 가이드
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 설계 원칙과 계층 구조

---

## Structure

```
.
+-- main.py
+-- config.py                        # 데이터셋/실험/속성/metrics 레지스트리
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
