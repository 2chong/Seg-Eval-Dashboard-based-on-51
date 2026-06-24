# 건물 패치 평가 대시보드

항공 이미지 기반 건물 세그멘테이션 예측 마스크를 GT SHP와 비교·평가하는 FiftyOne 대시보드.

서울 9개 자치구 2022년 데이터셋, 기하 20종·방사 4종 = 24종 속성, 이진 마스크(건물=1/배경=0) 평가를 지원한다.

---

## 무엇을 하는 프로젝트인가

- 건물 예측 마스크를 GT와 비교해 Recall/Precision/F1/IoU 등을 계산
- Confusion Matrix, 메트릭 분포 히스토그램 시각화
- 기하(건물 면적·군집·복잡도)·방사(밝기·식생·그림자) 속성과 메트릭의 교차 분석
- 여러 모델(experiment)을 나란히 비교하는 패널

모든 시각화는 FiftyOne App 안의 5개 패널에서 인터랙티브하게 탐색할 수 있다.

---

## 실행

환경을 한 번 만들어두면 이후에는 `make run` 하나로 끝난다.

```bash
# 최초 1회 — 환경 설정
conda env create -f environment.yml
conda activate fiftyone-seg-eval

# 이후 매 실행
make run
```

브라우저에서 http://localhost:5151 을 열고, 우상단 `+` 버튼으로 원하는 패널을 추가하면 된다.

데이터셋을 바꾸고 싶으면:

```bash
make run DS=seocho_2022
make run DS=gangseo_2022
```

---

## 5개 패널

| 패널 | 내용 |
|------|------|
| (1) Data Analysis | 속성 요약 및 분포 차트. 여러 데이터셋을 함께 선택해 분포를 비교할 수 있다. |
| (2) Evaluation | 메트릭 요약(mean/min/max), 분포 히스토그램, Confusion Matrix. |
| (3) Combined | 속성 × 메트릭 교차 분석과 상관 heatmap. |
| (4) Experiment | 여러 모델을 chips로 선택해 per-class 메트릭과 속성별 추이를 나란히 비교. |
| (5) Schema & Table | 컬럼 스키마 전체와 per-sample 표. |

---

## 확장하기

새 데이터셋, 모델, 속성, 메트릭을 추가하는 방법은 아래 문서를 참고한다.

- [docs/EXTENDING.md](docs/EXTENDING.md) — 단계별 확장 가이드
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 설계 원칙과 계층 구조

---

## 환경

`conda env create -f environment.yml` 로 설치된다. 전체 패키지 목록은 `environment.yml` 참고.

---

## 프로젝트 구조

```
.
+-- main.py                          # 진입점
+-- config.py                        # 데이터셋/실험/속성/메트릭 레지스트리
+-- Makefile
+-- pipeline/
|   +-- seg_io.py                    # 마스크·manifest·attrs I/O
|   +-- dataset_builder.py           # manifest -> fo.Dataset
|   +-- evaluation.py                # 평가 실행 + 메트릭 필드 부착
|   +-- app.py                       # App 실행 + 사이드바 설정
|   +-- attributes/
|       +-- geometric.py             # 기하 속성 20종 계산
|       +-- radiometric.py           # 방사 속성 4종 계산
+-- tools/
|   +-- generate_attrs.py            # 속성 계산
|   +-- precompute_panel_stats.py    # 패널 통계 집계
+-- plugins/
|   +-- seg_dashboard/               # FiftyOne 패널 플러그인 (5개 패널)
|       +-- charts/                  # Plotly 차트 빌더
|       +-- sections/                # 패널 UI 섹션
|       +-- panels/                  # 5개 패널 선언
|       +-- framework/               # BasePanel, MultiSelectMixin, 위젯 헬퍼
|       +-- stats.py                 # panel_stats.json 로더
+-- data_building/
|   +-- <region_year>/
|       +-- manifest.json, sample_attrs.json, panel_stats.json
|       +-- masks/ground_truth/, masks/predictions/
```
