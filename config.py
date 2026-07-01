"""
config.py
---------
건물 패치 평가 대시보드 공유 상수.

데이터셋 : 건물 패치 PNG + GT/Pred 이진 마스크 (건물=1, 배경=0)
속성     : 기하 20종 / 방사 4종 / 장면 1종 = 25종  (VLM 3종 미구현 — 추후 port-attribute 로 추가)
실험     : pred SHP → 이진 마스크 래스터화 → FiftyOne 평가

새 데이터셋 추가 → DATASETS 레지스트리에 항목 추가.
새 실험(모델) 추가 → _EXPERIMENT_LABELS 에 항목 추가.
"""

import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.resolve()

# 원본 입력 데이터 루트 (patches.sqlite · pred_shp · aerial_image)
SOURCE_DIR = ROOT_DIR / "source_data"

# ── Attribute rule groups ─────────────────────────────────────────────────────
# PANEL_COLUMN_META 의 attribute 항목들이 규칙 라이브러리.
# 그룹(preset)은 그 라이브러리에서 사용할 키 목록을 명명한 것.
# 각 데이터셋은 "attributes" 키로 그룹명을 참조한다.
ATTRIBUTE_GROUPS: dict[str, list[str]] = {
    "geometric": [
        "bd_s", "bd_portion", "bg_portion", "bd_avg_area",
        "bd_area_min", "bd_area_max", "bd_gap", "bd_gap_min",
        "bd_adj_density", "bd_completeness", "bd_completeness_a",
        "bd_fi", "bd_cv", "bd_cluster_ratio", "bd_boundary_complexity",
        "bd_elongation_mean", "bd_orientation_entropy",
        "bd_small_ratio", "bd_middle_ratio", "bd_big_ratio",
        "scene_type",
    ],
    "radiometric": [
        "brightness_mean", "brightness_std",
        "shadow_area_ratio", "vegetation_ratio",
    ],
    "all": [
        "bd_s", "bd_portion", "bg_portion", "bd_avg_area",
        "bd_area_min", "bd_area_max", "bd_gap", "bd_gap_min",
        "bd_adj_density", "bd_completeness", "bd_completeness_a",
        "bd_fi", "bd_cv", "bd_cluster_ratio", "bd_boundary_complexity",
        "bd_elongation_mean", "bd_orientation_entropy",
        "bd_small_ratio", "bd_middle_ratio", "bd_big_ratio",
        "brightness_mean", "brightness_std",
        "shadow_area_ratio", "vegetation_ratio",
        "scene_type",
    ],
}
DEFAULT_ATTRIBUTE_GROUP = "all"


def dataset_attribute_keys(name: str | None = None) -> list[str]:
    """주어진 데이터셋의 attribute 키 목록을 반환한다.

    DATASETS[name]["attributes"] 에 등록된 그룹명을 ATTRIBUTE_GROUPS 에서 조회.
    그룹 미지정 → DEFAULT_ATTRIBUTE_GROUP 사용.
    각 키가 PANEL_COLUMN_META 의 attribute 인지 검증 후 반환.
    """
    ds_name = name or DEFAULT_DATASET
    cfg = DATASETS.get(ds_name, {})
    group_name = cfg.get("attributes", DEFAULT_ATTRIBUTE_GROUP)
    if group_name not in ATTRIBUTE_GROUPS:
        print(
            f"[config] Unknown attribute group '{group_name}' for dataset '{ds_name}'. "
            f"Falling back to '{DEFAULT_ATTRIBUTE_GROUP}'.",
            file=sys.stderr,
        )
        group_name = DEFAULT_ATTRIBUTE_GROUP
    keys = ATTRIBUTE_GROUPS[group_name]
    valid = []
    for k in keys:
        meta = PANEL_COLUMN_META.get(k, {})
        if meta.get("kind") == "attribute":
            valid.append(k)
        else:
            print(
                f"[config] Attribute group '{group_name}' references '{k}' which is not "
                f"a registered attribute in PANEL_COLUMN_META — skipping.",
                file=sys.stderr,
            )
    return valid


# ── Dataset 레지스트리 ────────────────────────────────────────────────────────
# 새 데이터셋을 추가할 때 여기에만 등록하면 된다.
#
# data_dir     : manifest.json · sample_attrs.json · panel_stats.json 저장 루트
# region       : 지역 식별자 (SOURCE_DIR/experiments/{region}/{year}/patches.sqlite 경로에 사용)
# year         : 연도 (정수)
# attributes   : ATTRIBUTE_GROUPS 의 그룹명
DATASETS: dict[str, dict] = {
    "seocho_2022": {
        "label":      "서초구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "seocho_2022",
        "region":     "seocho",
        "year":       2022,
        "attributes": "all",
    },
    "gangseo_2022": {
        "label":      "강서구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "gangseo_2022",
        "region":     "gangseo",
        "year":       2022,
        "attributes": "all",
    },
    "junggu_2022": {
        "label":      "중구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "junggu_2022",
        "region":     "junggu",
        "year":       2022,
        "attributes": "all",
    },
    "jungrang_2022": {
        "label":      "중랑구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "jungrang_2022",
        "region":     "jungrang",
        "year":       2022,
        "attributes": "all",
    },
    "mapo_2022": {
        "label":      "마포구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "mapo_2022",
        "region":     "mapo",
        "year":       2022,
        "attributes": "all",
    },
    "songpa_2022": {
        "label":      "송파구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "songpa_2022",
        "region":     "songpa",
        "year":       2022,
        "attributes": "all",
    },
    "suseo_2022": {
        "label":      "수서 2022",
        "data_dir":   ROOT_DIR / "data_building" / "suseo_2022",
        "region":     "suseo",
        "year":       2022,
        "attributes": "all",
    },
    "yangcheon_2022": {
        "label":      "양천구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "yangcheon_2022",
        "region":     "yangcheon",
        "year":       2022,
        "attributes": "all",
    },
    "youngdeungpo_2022": {
        "label":      "영등포구 2022",
        "data_dir":   ROOT_DIR / "data_building" / "youngdeungpo_2022",
        "region":     "youngdeungpo",
        "year":       2022,
        "attributes": "all",
    },
}
DEFAULT_DATASET = "suseo_2022"

# ── Experiment 레지스트리 ─────────────────────────────────────────────────────
# 새 모델(experiment)을 추가할 때 여기에만 등록하면 된다.
# pred_dir 은 activate_dataset() 이 SOURCE_DIR/data/pred_shp/{region}/{year}/{exp} 로 채운다.
# label : App/패널 표시 이름
_EXPERIMENT_LABELS: dict[str, str] = {
    "segformer_init": "SegFormer 초기 모델",
    "mobile_unet":    "WHU Building UNet++ (EfficientNet-B4)",  # oneoff/infer_mobile_unet.py 로 생성
}
DEFAULT_EXPERIMENT = "segformer_init"

# EXPERIMENTS 는 activate_dataset() 이 채운다 — import 시점에 직접 정의하지 않는다.
EXPERIMENTS: dict[str, dict] = {}


# ── 활성 데이터셋 선택 ─────────────────────────────────────────────────────────
def activate_dataset(name: str | None = None) -> None:
    """활성 데이터셋을 전환하고 모든 경로 상수·EXPERIMENTS 를 업데이트한다."""
    global ACTIVE_DATASET, DATA_DIR, MANIFEST_PATH, ATTRS_PATH
    global PANEL_STATS_PATH, DATASET_NAME, EVAL_DATASET_NAME
    global REGION, YEAR, SOURCE_DB_PATH
    global EXPERIMENTS

    name = name or DEFAULT_DATASET
    if name not in DATASETS:
        print(f"[config] Unknown dataset '{name}'. Using '{DEFAULT_DATASET}'.", file=sys.stderr)
        name = DEFAULT_DATASET

    cfg = DATASETS[name]
    ACTIVE_DATASET    = name
    DATA_DIR          = cfg["data_dir"]
    MANIFEST_PATH     = DATA_DIR / "manifest.json"
    ATTRS_PATH        = DATA_DIR / "sample_attrs.json"
    PANEL_STATS_PATH  = DATA_DIR / "panel_stats.json"
    DATASET_NAME      = name
    EVAL_DATASET_NAME = name
    REGION            = cfg["region"]
    YEAR              = cfg["year"]
    # patches.sqlite 경로 — generate_attrs.py 가 속성을 읽는 원본 DB
    SOURCE_DB_PATH    = (
        SOURCE_DIR / "experiments" / REGION / str(YEAR) / "patches.sqlite"
    )

    # EXPERIMENTS: pred_dir 을 SOURCE_DIR 기준으로 채운다
    EXPERIMENTS = {
        exp_name: {
            "label":    label,
            "pred_dir": SOURCE_DIR / "data" / "pred_shp" / REGION / str(YEAR) / exp_name,
        }
        for exp_name, label in _EXPERIMENT_LABELS.items()
    }


# 모듈 import 시 기본 데이터셋으로 초기화
activate_dataset(DEFAULT_DATASET)

# ── Binary segmentation label space ───────────────────────────────────────────
MASK_TARGETS: dict[int, str] = {0: "background", 1: "building"}

# ── Plugin path (dataset 무관) ────────────────────────────────────────────────
PLUGINS_DIR = ROOT_DIR / "plugins"

PANEL_EXCLUDE_FIELDS: frozenset = frozenset({
    "id", "filepath", "tags", "metadata",
    "gt", "ground_truth",
    "patch_id", "region", "year",
})

# Column metadata for panel display.
# precompute_panel_stats.py 가 이 내용을 panel_stats.json["columns"] 에 포함시킨다.
# 새 속성/메트릭 추가 시 여기에 등록 → Schema 패널·차트에 자동 반영된다.
#
# kind="attribute" : 데이터 고유 속성, experiment 무관.
#                    patches.sqlite 에서 읽어 FO sample 필드로 부착한다.
# kind="metric"    : 예측·평가에서 나온 값, experiment 마다 다름.
#                    evaluation.run() 과 attach_derived_metric_fields() 가
#                    {metric}_{exp} 필드로 부착해 사이드바 "Metrics · {model}" 그룹에 표시.
#
# attribute compute.source:
#   "geometric"   → GT SHP + patch geometry → pipeline/attributes/geometric.py
#   "radiometric" → TIF windowed read       → pipeline/attributes/radiometric.py
#
# metric compute.source:
#   "fiftyone_eval" → {field}_{exp} 샘플 필드에서 읽기
#                     (evaluation.run() 이 FO evaluate_segmentations 후 rename)
#   "derived"       → 다른 메트릭에서 파생 (fn 으로 함수 지정)
PANEL_COLUMN_META: dict[str, dict] = {

    # ── 기하 속성 20종 ──────────────────────────────────────────────────────
    # source="geometric": pipeline/attributes/geometric.py compute_geometric() 호출
    "bd_s": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "패치 내 건물 폴리곤 개수",
        "range":       [0, None],
        "compute":     {"source": "geometric", "field": "bd_s"},
    },
    "bd_portion": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "패치 면적 대비 건물 총 면적 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_portion"},
    },
    "bg_portion": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "배경 면적 비율 = 1 − bd_portion (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bg_portion"},
    },
    "bd_avg_area": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "패치 내 건물 평균 교차 면적 (m²)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_avg_area"},
    },
    "bd_area_min": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "패치 내 최소 건물 면적 (m²)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_area_min"},
    },
    "bd_area_max": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "패치 내 최대 건물 면적 (m²)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_area_max"},
    },
    "bd_gap": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "인접 건물 쌍 간 평균 최근접 거리 (m)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_gap"},
    },
    "bd_gap_min": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "건물 쌍 간 최소 최근접 거리 (m)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_gap_min"},
    },
    "bd_adj_density": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "일정 거리 이내 인접 건물이 있는 건물 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_adj_density"},
    },
    "bd_completeness": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "패치 경계와 교차하지 않는 온전한 건물의 수 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_completeness"},
    },
    "bd_completeness_a": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "온전한 건물의 면적 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_completeness_a"},
    },
    "bd_fi": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "Simpson 다양성 지수 기반 건물 크기 분산 — 조각화 지수 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_fi"},
    },
    "bd_cv": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "건물 폴리곤 평균 볼록도 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_cv"},
    },
    "bd_cluster_ratio": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "군집 건물 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_cluster_ratio"},
    },
    "bd_boundary_complexity": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "경계선 단위 길이당 방향 변화량 (rad/m)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_boundary_complexity"},
    },
    "bd_elongation_mean": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "MBR 장축/단축 비율 — 평균 세장비 (≥1)",
        "range":       [1.0, None],
        "compute":     {"source": "geometric", "field": "bd_elongation_mean"},
    },
    "bd_orientation_entropy": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "건물 주축 방향의 Shannon entropy (bits)",
        "range":       [0.0, None],
        "compute":     {"source": "geometric", "field": "bd_orientation_entropy"},
    },
    "bd_small_ratio": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "전체 면적 < 100m² 건물 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_small_ratio"},
    },
    "bd_middle_ratio": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "100m² ≤ 면적 < 500m² 건물 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_middle_ratio"},
    },
    "bd_big_ratio": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "면적 ≥ 500m² 건물 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "geometric", "field": "bd_big_ratio"},
    },

    # ── 방사 속성 4종 ──────────────────────────────────────────────────────
    # source="radiometric": pipeline/attributes/radiometric.py 호출
    "brightness_mean": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "RGB → luminance 픽셀 평균 (0~255)",
        "range":       [0.0, 255.0],
        "compute":     {"source": "radiometric", "field": "brightness_mean"},
    },
    "brightness_std": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "RGB → luminance 픽셀 표준편차 (0~255)",
        "range":       [0.0, 255.0],
        "compute":     {"source": "radiometric", "field": "brightness_std"},
    },
    "shadow_area_ratio": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "HSV + 청색비 기반 그림자 픽셀 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "radiometric", "field": "shadow_area_ratio"},
    },
    "vegetation_ratio": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "ExG(Excess Green) 기반 식생 픽셀 비율 (0~1)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "radiometric", "field": "vegetation_ratio"},
    },

    # ── 장면 속성 1종 ──────────────────────────────────────────────────────
    # source="gt_mask": GT 마스크 building(1) 픽셀 유무로 판정
    "scene_type": {
        "kind":        "attribute",
        "type":        "categorical",
        "description": "GT 마스크 건물 픽셀 유무 — only_background / has_building",
        "values":      ["only_background", "has_building"],
        "compute":     {"source": "gt_mask", "field": "scene_type"},
    },

    # ── metrics ───────────────────────────────────────────────────────────────
    # fiftyone_eval: FiftyOne evaluate_segmentations 가 생성하는 per-sample 필드.
    #   evaluation.run() 이 {exp}_{field} → {field}_{exp} 로 rename 후
    #   panel_stats / 사이드바에서 {field}_{exp} 로 접근한다.
    "precision": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "건물 픽셀 정밀도 (FiftyOne evaluate_segmentations)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "fiftyone_eval", "field": "precision"},
    },
    "recall": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "건물 픽셀 재현율",
        "range":       [0.0, 1.0],
        "compute":     {"source": "fiftyone_eval", "field": "recall"},
    },
    "accuracy": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "전체 픽셀 정확도",
        "range":       [0.0, 1.0],
        "compute":     {"source": "fiftyone_eval", "field": "accuracy"},
    },
    "f1": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "건물 F1 점수 (2PR / (P+R))",
        "range":       [0.0, 1.0],
        "compute":     {"source": "derived", "fn": "f1", "deps": ["precision", "recall"]},
    },
    "iou": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "건물 픽셀 IoU — Jaccard 지수 (PR / (P+R−PR))",
        "range":       [0.0, 1.0],
        "compute":     {"source": "derived", "fn": "iou", "deps": ["precision", "recall"]},
    },
}

# ── 공간 좌표 출처 선언 ──────────────────────────────────────────────────────
# manifest entry 에서 격자 좌표 + 경위도를 추출하는 규칙의 단일 진실 소스.
# 이 키들이 manifest 에 없는 데이터셋은 spatial 블록이 생성되지 않고
# Spatial 패널이 placeholder 를 표시한다 (graceful degradation).
#
# 새 좌표 스키마의 데이터셋을 추가할 때 이 dict 만 수정하면 된다.
SPATIAL_META: dict = {
    "patch_id_key":        "patch_id",          # manifest entry 의 격자 ID 키
    "patch_id_regex":      r"r(\d+)_c(\d+)",    # r{row}_c{col} 파싱 정규식
    "geo_key":             "geo",               # entry["geo"] 서브딕셔너리 키
    "lon_field":           "centroid_lon",      # entry["geo"]["centroid_lon"]
    "lat_field":           "centroid_lat",      # entry["geo"]["centroid_lat"]
    "adjacency":           "queen",             # Moran's I 격자 가중치 (queen = 8근방)
    "morans_permutations": 199,                 # 순열검정 반복 횟수
}
