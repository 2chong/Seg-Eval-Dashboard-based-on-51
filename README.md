# FiftyOne 시맨틱 세그멘테이션 평가 대시보드

COCO 데이터셋 기반 **데모이자 확장 교본**. 자신의 데이터셋·모델·속성으로 그대로 이식해 쓸 수 있도록 설계됐다.

---

## 이 프로젝트가 하는 일

- 시맨틱 세그멘테이션 **예측 마스크**를 GT 마스크와 비교·평가
- 픽셀 레벨 Confusion Matrix, per-class Recall/Precision/F1, Boundary IoU 시각화
- 속성(time, complexity 등)과 메트릭의 교차 분석 (상관·분포·구간별 평균)
- **여러 모델(experiment)을 나란히 비교**하는 패널

모든 시각화는 FiftyOne App 안의 **5개 패널**에서 인터랙티브하게 볼 수 있다.

---

## 빠른 시작 (COCO 데모)

```bash
# 환경 설정 (최초 1회)
conda env create -f environment.yml
conda activate fiftyone-seg-eval

# 1. 최초: 추론 + 속성 생성 + 통계 집계
make pipeline

# 2. 이후: App 실행
make run
# 브라우저 -> http://localhost:5151 -> 우상단 '+' -> 패널 선택
```

두 번째 데이터셋:
```bash
make pipeline DS=coco-val-voc-50b
make run DS=coco-val-voc-50b
```

---

## 5개 패널

| 패널 | 목적 |
|------|------|
| (1) Data Analysis | 속성 요약 + 분포 차트 (예측 무관) |
| (2) Evaluation | Confusion Matrix (experiment 별) |
| (3) Combined | 속성 x 메트릭 교차분석 + 상관 heatmap |
| (4) Experiment | 모델 간 per-class 메트릭 비교 |
| (5) Schema & Table | 컬럼 스키마 + per-sample 표 |

---

## 내 데이터셋/모델/속성으로 바꾸기

→ **[EXTENDING.md](EXTENDING.md)** 참고

설계 원칙과 계층 구조 상세:

→ **[ARCHITECTURE.md](plugins/seg_dashboard/ARCHITECTURE.md)** 참고

---

## 주요 Makefile 명령

| 명령 | 설명 |
|------|------|
| `make pipeline` | 최초 실행 (inference -> attrs -> stats) |
| `make run` | App 실행 |
| `make sync` | config 변경 후 attrs+stats 재생성 |
| `make sync-all` | 모든 데이터셋 sync |
| `make regen-attr-all` | 속성 추가 후 전체 재생성 |
| `make regen-stats-all` | 메트릭/실험 추가 후 통계 재생성 |
| `make rebuild` | FiftyOne DB 캐시 삭제 후 재실행 |

---

## 환경

| 라이브러리 | 용도 |
|-----------|------|
| Python 3.10 | 런타임 |
| PyTorch + torchvision | 모델 추론 (CPU) |
| fiftyone >= 0.23 | 데이터셋 관리 + App + 플러그인 |
| scipy | Boundary IoU (binary_erosion) |
| Pillow, numpy | 마스크 I/O, 배열 연산 |

## 프로젝트 구조

```
.
+-- main.py                          # 오케스트레이터
+-- config.py                        # 데이터셋/실험/속성/메트릭 레지스트리 (단일 선언 지점)
+-- seg_utils.py                     # 마스크 I/O, manifest, BIoU
+-- Makefile                         # 파이프라인 자동화
+-- pipeline/
|   +-- dataset_builder.py           # manifest -> fo.Dataset
|   +-- evaluation.py                # evaluate_segmentations
|   +-- app.py                       # fo.launch_app + 사이드바 설정
+-- tools/
|   +-- run_inference.py             # 모델 추론 + manifest 생성
|   +-- generate_attrs.py            # 속성 생성 (config 기반 자동)
|   +-- precompute_panel_stats.py    # 패널 통계 집계 (메트릭 레지스트리 기반)
+-- plugins/
|   +-- seg_dashboard/               # FiftyOne 패널 플러그인 (5개 패널)
|       +-- charts/                  # Plotly 차트 빌더 (FiftyOne import 없음)
|       +-- sections/                # 패널 UI 섹션
|       +-- panels/                  # 5개 구체 패널 선언
|       +-- framework/               # BasePanel (상태관리/렌더/콜백)
|       +-- stats.py                 # panel_stats.json 로더 + 헬퍼
+-- data/                            # (자동 생성, git 제외)
    +-- manifest.json, sample_attrs.json, panel_stats.json
    +-- masks/ground_truth/, masks/predictions/
```
