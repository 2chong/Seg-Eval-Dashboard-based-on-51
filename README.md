# 건물 패치 평가 대시보드

항공 이미지 기반 건물 세그멘테이션 **예측 마스크**를 GT SHP 와 비교·평가하는 FiftyOne 대시보드.

서울 9개 자치구 2022년 데이터셋, 기하 20종·방사 4종 = 24종 속성, 이진 마스크(건물=1/배경=0) 평가를 지원한다.

---

## 이 프로젝트가 하는 일

- 건물 예측 마스크(pred SHP → 래스터)를 GT 마스크와 비교·평가
- Confusion Matrix, per-class Recall/Precision/F1/IoU 시각화
- 기하(건물 면적·군집·복잡도)·방사(밝기·식생·그림자) 속성과 메트릭의 교차 분석
- **여러 모델(experiment)을 나란히 비교**하는 패널

모든 시각화는 FiftyOne App 안의 **5개 패널**에서 인터랙티브하게 볼 수 있다.

---

## 빠른 시작

```bash
# 환경 설정 (최초 1회)
conda env create -f environment.yml
conda activate fiftyone-seg-eval

# 1. 최초: 패치 PNG·마스크 생성 + 속성 계산 + 통계 집계
make pipeline                                  # 기본 데이터셋 (jungrang_2022)
make pipeline DS=seocho_2022                   # 추가 데이터셋

# 2. 이후: App 실행 (config.py 변경 자동 감지)
make run
# 브라우저 -> http://localhost:5151 -> 우상단 '+' -> 패널 선택
```

다른 데이터셋으로 전환:
```bash
make run DS=seocho_2022
make run DS=gangseo_2022
```

---

## 5개 패널

| 패널 | 목적 |
|------|------|
| (1) Data Analysis | 속성 요약 + 분포 차트 + **Datasets 멀티셀렉트**로 데이터셋 간 분포 비교 (예측 무관) |
| (2) Evaluation | 메트릭 분포 히스토그램 + Confusion Matrix (experiment 별) |
| (3) Combined | 속성 × 메트릭 교차분석 + 상관 heatmap |
| (4) Experiment | **Experiments 멀티셀렉트(chips)**로 실험 선택 + per-class 메트릭 비교 + 속성별 메트릭 추이 비교 |
| (5) Schema & Table | 컬럼 스키마 + per-sample 표 |

---

## 내 데이터셋/모델/속성으로 바꾸기

→ **[EXTENDING.md](EXTENDING.md)** 참고

설계 원칙과 계층 구조 상세:

→ **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** 참고

---

## Makefile 명령

**평상시에는 `make run` 하나로 충분합니다.**
`main.py`가 시작 시 `config.py` 변경을 감지해 attrs/stats를 자동으로 재생성하고 App을 실행합니다.

| 명령 | 언제 사용 |
|------|-----------|
| `make pipeline` | **최초 1회** — 패치 PNG·마스크 생성 + 속성 계산 + 통계 집계 (기본 DS) |
| `make pipeline DS=<name>` | 특정 데이터셋 최초 준비 |
| `make run` | **매 실행** — App 시작 (config 변경 시 자동 sync 포함) |
| `make run DS=<name>` | 특정 데이터셋으로 App 실행 |
| `make manifest DS=<name>` | 새 실험(pred SHP 추가) 후 — manifest·마스크만 재생성 |
| `make rebuild` | FiftyOne DB 캐시 문제 시 — 강제 재빌드 |
| `make regen-attr-all` | config.py 에서 속성 변경 후 전 데이터셋 재생성 |
| `make regen-stats-all` | config.py 에서 메트릭/실험 변경 후 전 데이터셋 통계 재집계 |
| `make clean-all` | data 디렉터리 전체 삭제 (마스크·이미지 포함) |

---

## 환경

| 라이브러리 | 용도 |
|-----------|------|
| Python 3.10 | 런타임 |
| fiftyone >= 0.23 | 데이터셋 관리 + App + 플러그인 |
| rasterio, geopandas, shapely, pyproj | 공간 데이터 처리 (TIF windowed read, SHP 래스터화) |
| scipy | binary_erosion (마스크 형태 연산) |
| Pillow >= 10.0, numpy >= 1.24 | 마스크 I/O, 배열 연산 |
| matplotlib | 사전 집계 시 보조 시각화 |
| tqdm | 진행률 표시 |
| kaleido | Plotly 정적 이미지 내보내기 |

## 프로젝트 구조

```
.
+-- main.py                          # 오케스트레이터
+-- config.py                        # 데이터셋/실험/속성/메트릭 레지스트리 (단일 선언 지점)
+-- seg_utils.py                     # 마스크 I/O, manifest, BIoU
+-- Makefile                         # 파이프라인 자동화
+-- pipeline/
|   +-- dataset_builder.py           # manifest -> fo.Dataset
|   +-- evaluation.py                # evaluate_segmentations + {metric}_{exp} 필드 rename
|   +-- app.py                       # fo.launch_app + 사이드바 설정
+-- tools/
|   +-- build_manifest.py            # 패치 PNG + GT/Pred 마스크 + manifest.json 생성
|   +-- generate_attrs.py            # 속성 생성 (config 기반 자동)
|   +-- precompute_panel_stats.py    # 패널 통계 집계 (메트릭 레지스트리 기반)
+-- plugins/
|   +-- seg_dashboard/               # FiftyOne 패널 플러그인 (5개 패널)
|       +-- charts/                  # Plotly 차트 빌더 (FiftyOne import 없음)
|       |   +-- registry.py          # @register_chart 데코레이터 + chart_for() 디스패치
|       |   +-- _common.py           # _COLORS 팔레트 단일 소스
|       +-- sections/                # 패널 UI 섹션
|       |   +-- field_section.py     # 선언형 FieldSection (field+chart 조합)
|       |   +-- multi_select.py      # MultiSelectSection (chips 선택기) + 공용 헬퍼
|       +-- panels/                  # 5개 구체 패널 선언
|       +-- framework/               # BasePanel (상태관리/렌더/콜백)
|       |   +-- widgets.py           # add_dropdown / add_bins_slider / resolve_col_type
|       |   +-- multi_select.py      # MultiSelectMixin (자동 콜백 생성)
|       +-- stats.py                 # panel_stats.json 로더 + 헬퍼
+-- data/                            # Set A (자동 생성, git 제외)
|   +-- manifest.json, sample_attrs.json, panel_stats.json
|   +-- masks/ground_truth/, masks/predictions/
+-- data_coco_b/                     # Set B (동일 구조)
+-- data_coco_c/                     # Set C (동일 구조)
```
