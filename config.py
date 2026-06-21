"""
config.py
---------
Shared constants for the FiftyOne Semantic Segmentation Evaluation demo.

Datasets  : COCO-2017 validation subset (VOC-overlapping classes)
            새 데이터셋 추가 -> DATASETS 레지스트리에 항목 추가
Models    : LRASPP MobileNetV3-Large  (기본)
            DeepLabV3 MobileNetV3-Large (비교용)

실행 시 데이터셋 선택 (기본값: DEFAULT_DATASET):
    python main.py --dataset coco-val-voc-50b
"""

import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.resolve()

# ── Attribute rule groups ─────────────────────────────────────────────────────
# PANEL_COLUMN_META 의 attribute 항목들이 규칙 라이브러리.
# 그룹(preset)은 그 라이브러리에서 사용할 키 목록을 명명한 것.
# 각 데이터셋은 "attributes" 키로 그룹명을 참조한다.
ATTRIBUTE_GROUPS: dict[str, list[str]] = {
    "basic": ["time", "complexity"],
    "full":  ["time", "complexity", "count"],
}
DEFAULT_ATTRIBUTE_GROUP = "full"


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
# data_dir    : 이미지·마스크·manifest·attrs·panel_stats 가 저장될 루트
# zoo_name    : fiftyone.zoo.load_zoo_dataset() 의 dataset 이름
# split       : zoo dataset split (COCO: "validation")
# classes     : 다운로드할 클래스 목록. None -> COCO_CLASSES 사용
# num_samples : 최대 샘플 수
# seed        : zoo 다운로드 shuffle seed (다른 seed = 다른 이미지셋)
# attr_seed   : generate_attrs.py 의 랜덤 속성 생성 시드
# attributes  : ATTRIBUTE_GROUPS 의 그룹명 — 이 데이터셋에 부착할 속성 집합
DATASETS: dict[str, dict] = {
    "coco-val-voc-50": {
        "label":       "COCO Val 50 - Set A (seed 51)",
        "data_dir":    ROOT_DIR / "data",
        "zoo_name":    "coco-2017",
        "split":       "validation",
        "classes":     None,   # None -> COCO_CLASSES
        "num_samples": 50,
        "seed":        51,
        "attr_seed":   51,
        "attributes":  "full",
    },
    "coco-val-voc-50b": {
        "label":       "COCO Val 50 - Set B (seed 7)",
        "data_dir":    ROOT_DIR / "data_coco_b",
        "zoo_name":    "coco-2017",
        "split":       "validation",
        "classes":     None,
        "num_samples": 50,
        "seed":        7,
        "attr_seed":   7,
        "attributes":  "full",
    },
    # 새 데이터셋 추가 예시:
    # "my-dataset": {
    #     "label":       "My Dataset",
    #     "data_dir":    ROOT_DIR / "data_my",
    #     "zoo_name":    "coco-2017",
    #     "split":       "validation",
    #     "classes":     None,
    #     "num_samples": 100,
    #     "seed":        42,
    #     "attr_seed":   42,
    #     "attributes":  "full",
    # },
}
DEFAULT_DATASET = "coco-val-voc-50"

# ── Experiment 레지스트리 ─────────────────────────────────────────────────────
# 새 모델(experiment)을 추가할 때 여기에만 등록하면 된다.
# pred_dir 은 activate_dataset() 이 활성 DATA_DIR 기준으로 채워 준다.
# label : App/패널 표시 이름
_EXPERIMENT_LABELS: dict[str, str] = {
    "lraspp_mv3":    "LRASPP MobileNetV3-Large",
    "deeplabv3_mv3": "DeepLabV3 MobileNetV3-Large",
}
DEFAULT_EXPERIMENT = "lraspp_mv3"

# EXPERIMENTS 는 activate_dataset() 이 채운다 — import 시점에 직접 정의하지 않는다.
EXPERIMENTS: dict[str, dict] = {}


# ── 활성 데이터셋 선택 ─────────────────────────────────────────────────────────
# main.py / tools 스크립트에서 --dataset 인수로 오버라이드 가능.
# config.activate_dataset("name") 으로 언제든지 전환할 수 있다.
def activate_dataset(name: str | None = None) -> None:
    """활성 데이터셋을 전환하고 모든 경로 상수·EXPERIMENTS 를 업데이트한다."""
    global ACTIVE_DATASET, DATA_DIR, GT_MASK_DIR, MANIFEST_PATH, ATTRS_PATH
    global PANEL_STATS_PATH, DATASET_NAME, EVAL_DATASET_NAME
    global NUM_SAMPLES, SPLIT, SEED, ATTR_SEED
    global EXPERIMENTS, PRED_MASK_DIR

    name = name or DEFAULT_DATASET
    if name not in DATASETS:
        print(f"[config] Unknown dataset '{name}'. Using '{DEFAULT_DATASET}'.", file=sys.stderr)
        name = DEFAULT_DATASET

    cfg = DATASETS[name]
    ACTIVE_DATASET    = name
    DATA_DIR          = cfg["data_dir"]
    GT_MASK_DIR       = DATA_DIR / "masks" / "ground_truth"
    MANIFEST_PATH     = DATA_DIR / "manifest.json"
    ATTRS_PATH        = DATA_DIR / "sample_attrs.json"
    PANEL_STATS_PATH  = DATA_DIR / "panel_stats.json"
    DATASET_NAME      = name
    EVAL_DATASET_NAME = f"seg-eval-{name}"
    NUM_SAMPLES       = cfg["num_samples"]
    SPLIT             = cfg["split"]
    SEED              = cfg["seed"]
    ATTR_SEED         = cfg.get("attr_seed", cfg["seed"])

    # EXPERIMENTS: pred_dir 을 활성 DATA_DIR 기준으로 재계산
    EXPERIMENTS = {
        exp_name: {
            "label":    label,
            "pred_dir": DATA_DIR / "masks" / "predictions" / exp_name,
        }
        for exp_name, label in _EXPERIMENT_LABELS.items()
    }
    # 하위호환 별칭
    PRED_MASK_DIR = EXPERIMENTS[DEFAULT_EXPERIMENT]["pred_dir"]


# 모듈 import 시 기본 데이터셋으로 초기화
activate_dataset(DEFAULT_DATASET)

# ── Sample attribute constants ────────────────────────────────────────────────
INFERENCE_MAX_SIZE = 640

# ── VOC-21 label space ────────────────────────────────────────────────────────
VOC_CLASSES = [
    "background",   # 0
    "aeroplane",    # 1
    "bicycle",      # 2
    "bird",         # 3
    "boat",         # 4
    "bottle",       # 5
    "bus",          # 6
    "car",          # 7
    "cat",          # 8
    "chair",        # 9
    "cow",          # 10
    "diningtable",  # 11
    "dog",          # 12
    "horse",        # 13
    "motorbike",    # 14
    "person",       # 15
    "pottedplant",  # 16
    "sheep",        # 17
    "sofa",         # 18
    "train",        # 19
    "tvmonitor",    # 20
]

MASK_TARGETS: dict[int, str] = {i: name for i, name in enumerate(VOC_CLASSES)}
LABEL_TO_IDX: dict[str, int] = {name: i for i, name in enumerate(VOC_CLASSES)}

# ── Plugin path (dataset 무관) ────────────────────────────────────────────────
PLUGINS_DIR = ROOT_DIR / "plugins"

PANEL_EXCLUDE_FIELDS: frozenset = frozenset({
    "id", "filepath", "tags", "metadata",
    "ground_truth", "predictions",
})

# Column metadata for panel display.
# precompute_panel_stats.py 가 이 내용을 panel_stats.json["columns"] 에 포함시킨다.
# 새 속성/메트릭 추가 시 여기에 등록 -> Schema 패널·차트에 자동 반영된다.
#
# kind="attribute" : 데이터 고유 속성, experiment 무관.
#                    fo.Dataset sample 필드로 부착된다 (사이드바 primitive).
# kind="metric"    : 예측·평가에서 나온 값, experiment 마다 다름.
#                    panel_stats.json 에만 존재하며 절대 sample 필드가 되지 않는다.
PANEL_COLUMN_META: dict[str, dict] = {
    # ── attributes ────────────────────────────────────────────────────────────
    # generate.method:
    #   "choice" → rng.choice(values)
    #   "float"  → rng.uniform(*range), rounded to generate.round decimals
    #   "int"    → rng.randint(*range)  (stored as integer)
    "time": {
        "kind":        "attribute",
        "type":        "categorical",
        "description": "Shooting time of day (day / night)",
        "values":      ["day", "night"],
        "generate":    {"method": "choice"},
    },
    "complexity": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "Scene complexity score (randomly generated, 0-1)",
        "range":       [0.0, 1.0],
        "generate":    {"method": "float", "round": 3},
    },
    "count": {
        "kind":        "attribute",
        "type":        "numerical",
        "description": "Random object count (integer, 0-50)",
        "range":       [0, 50],
        "generate":    {"method": "int"},
    },
    # ── metrics ───────────────────────────────────────────────────────────────
    # compute.source 는 3가지 일반 전략:
    #   "fiftyone_eval" → seg_eval_{exp}_{field} 샘플 필드에서 읽기
    #   "derived"       → 다른 메트릭에서 파생 (fn 으로 함수 지정)
    #   "mask"          → 마스크 파일에서 직접 계산 (fn 으로 함수 지정, 사전 계산됨)
    #
    # 새 메트릭 추가:
    #   - 기존 source 재사용: config 한 항목만 추가
    #   - 새 source: config 항목 + tools/precompute_panel_stats.py 에 계산 함수 1개 추가
    # compute 키는 generate 처럼 panel_stats.json 에 포함되지 않는다 (_DISPLAY_KEYS 에서 제외됨).
    "recall": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "Per-sample macro recall (evaluate_segmentations)",
        "compute":     {"source": "fiftyone_eval", "field": "recall"},
    },
    "precision": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "Per-sample macro precision",
        "compute":     {"source": "fiftyone_eval", "field": "precision"},
    },
    "f1": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "Per-sample macro F1 (= 2*P*R / (P+R))",
        "compute":     {"source": "derived", "fn": "f1", "deps": ["precision", "recall"]},
    },
    "biou": {
        "kind":        "metric",
        "type":        "numerical",
        "description": "Boundary IoU (boundary accuracy, dilation_ratio=0.02)",
        "range":       [0.0, 1.0],
        "compute":     {"source": "mask", "fn": "biou", "params": {"dilation_ratio": 0.02}},
    },
}

# ── COCO class names ──────────────────────────────────────────────────────────
COCO_CLASSES: list[str] = [
    "airplane", "bicycle", "bird", "boat", "bottle",
    "bus", "car", "cat", "chair", "cow",
    "dining table", "dog", "horse", "motorcycle", "person",
    "potted plant", "sheep", "couch", "train", "tv",
]

COCO_TO_VOC: dict[str, str] = {
    "airplane":     "aeroplane",
    "motorcycle":   "motorbike",
    "couch":        "sofa",
    "tv":           "tvmonitor",
    "potted plant": "pottedplant",
    "dining table": "diningtable",
}
