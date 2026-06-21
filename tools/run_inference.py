"""
tools/run_inference.py
──────────────────────
One-shot script: 모든 등록된 experiment(모델) 에 대해 예측 마스크를 생성하고
data/manifest.json 을 갱신한다.

새 모델을 추가하려면:
  1. config.EXPERIMENTS 에 이름·pred_dir 등록
  2. MODEL_LOADERS 딕셔너리에 로더 함수 추가
  3. 이 스크립트를 재실행

Steps:
  1. COCO-2017 validation subset 다운로드 (또는 재사용)
  2. GT 마스크 래스터라이즈
  3. EXPERIMENTS 에 등록된 각 모델 → 추론 → 마스크 저장
  4. manifest.json 갱신

Run:
    python tools/run_inference.py [--dataset <name>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import torch
from PIL import Image

import config

_p = argparse.ArgumentParser(add_help=False)
_p.add_argument("--dataset", default=None)
config.activate_dataset(_p.parse_known_args()[0].dataset)

import seg_utils

try:
    import fiftyone as fo
    import fiftyone.utils.labels as foul
    import fiftyone.zoo as foz
except ImportError as exc:
    sys.exit(f"FiftyOne not installed.\nError: {exc}")


# ── 모델 로더 레지스트리 ─────────────────────────────────────────────────────
# 새 모델 추가: 아래 dict 에 함수 하나 추가하면 됨.
# 반환: (model, preprocess_transform)

def _load_lraspp_mv3():
    from torchvision.models.segmentation import (
        LRASPP_MobileNet_V3_Large_Weights,
        lraspp_mobilenet_v3_large,
    )
    weights = LRASPP_MobileNet_V3_Large_Weights.COCO_WITH_VOC_LABELS_V1
    model   = lraspp_mobilenet_v3_large(weights=weights)
    model.eval()
    return model, weights.transforms()


def _load_deeplabv3_mv3():
    from torchvision.models.segmentation import (
        DeepLabV3_MobileNet_V3_Large_Weights,
        deeplabv3_mobilenet_v3_large,
    )
    weights = DeepLabV3_MobileNet_V3_Large_Weights.COCO_WITH_VOC_LABELS_V1
    model   = deeplabv3_mobilenet_v3_large(weights=weights)
    model.eval()
    return model, weights.transforms()


MODEL_LOADERS: dict[str, callable] = {
    "lraspp_mv3":    _load_lraspp_mv3,
    "deeplabv3_mv3": _load_deeplabv3_mv3,
}

# 새 모델 추가 체크리스트:
#   1. config._EXPERIMENT_LABELS 에 이름·라벨 추가
#   2. 위 MODEL_LOADERS 에 로더 함수 추가
#   두 곳이 일치하지 않으면 아래 검증에서 경고가 출력된다.
def _validate_model_loaders() -> None:
    """config.EXPERIMENTS 와 MODEL_LOADERS 의 키 집합이 일치하는지 검증한다."""
    exp_keys    = set(config.EXPERIMENTS.keys())
    loader_keys = set(MODEL_LOADERS.keys())
    missing_loaders = exp_keys - loader_keys
    orphan_loaders  = loader_keys - exp_keys
    if missing_loaders:
        print(
            f"\n  [WARNING] config.EXPERIMENTS 에 등록됐지만 MODEL_LOADERS 에 없는 실험:\n"
            f"    {missing_loaders}\n"
            f"  run_inference.py 의 MODEL_LOADERS 에 로더 함수를 추가하세요.\n"
        )
    if orphan_loaders:
        print(
            f"\n  [WARNING] MODEL_LOADERS 에 있지만 config.EXPERIMENTS 에 없는 실험:\n"
            f"    {orphan_loaders}\n"
            f"  config._EXPERIMENT_LABELS 에 추가하거나 MODEL_LOADERS 에서 제거하세요.\n"
        )


# ── Step 1 — zoo dataset 로드 (DATASETS 레지스트리 기반) ─────────────────────

def load_zoo_subset() -> fo.Dataset:
    """활성 데이터셋 설정(config.DATASETS[ACTIVE_DATASET])으로 zoo 데이터를 로드한다."""
    if fo.dataset_exists(config.DATASET_NAME):
        print(f"Reusing existing FiftyOne dataset '{config.DATASET_NAME}' …")
        return fo.load_dataset(config.DATASET_NAME)

    ds_cfg   = config.DATASETS[config.ACTIVE_DATASET]
    zoo_name = ds_cfg.get("zoo_name", "coco-2017")
    split    = ds_cfg.get("split", "validation")
    classes  = ds_cfg.get("classes") or config.COCO_CLASSES
    n        = ds_cfg.get("num_samples", config.NUM_SAMPLES)
    seed     = ds_cfg.get("seed", config.SEED)

    print(f"Downloading '{zoo_name}' ({split}, {n} samples, seed={seed}) …")
    dataset = foz.load_zoo_dataset(
        zoo_name,
        split=split,
        label_types=["segmentations"],
        classes=classes,
        max_samples=n,
        dataset_name=config.DATASET_NAME,
        shuffle=True,
        seed=seed,
    )
    dataset.persistent = True
    return dataset


# 하위호환 별칭
load_coco_subset = load_zoo_subset


# ── Step 2 — 라벨 이름 매핑 ──────────────────────────────────────────────────

def remap_labels(dataset: fo.Dataset) -> None:
    mapping = config.COCO_TO_VOC
    changed = 0
    for sample in dataset.iter_samples(progress=True, autosave=True):
        if sample.ground_truth is None:
            continue
        for det in sample.ground_truth.detections:
            if det.label in mapping:
                det.label = mapping[det.label]
                changed += 1
    print(f"  Renamed {changed} detection label(s).")


# ── Step 3 — GT 마스크 래스터라이즈 ──────────────────────────────────────────

def build_gt_masks(dataset: fo.Dataset) -> None:
    config.GT_MASK_DIR.mkdir(parents=True, exist_ok=True)
    print("Rasterising GT instance masks → semantic PNGs …")
    foul.objects_to_segmentations(
        dataset,
        in_field="ground_truth",
        out_field="gt_seg",
        output_dir=str(config.GT_MASK_DIR),
        mask_targets=config.MASK_TARGETS,
        overwrite=True,
    )
    dataset.save()
    print(f"  GT masks → {config.GT_MASK_DIR}")


# ── Step 4 — 단일 이미지 추론 ────────────────────────────────────────────────

def infer_one(filepath: str, model: torch.nn.Module, preprocess) -> np.ndarray:
    """이미지 하나에 대해 예측 마스크(uint8 H×W)를 반환한다."""
    img    = Image.open(filepath).convert("RGB")
    orig_w, orig_h = img.size

    scale = min(config.INFERENCE_MAX_SIZE / max(orig_w, orig_h), 1.0)
    img_inf = img.resize((max(int(orig_w * scale), 1), max(int(orig_h * scale), 1)), Image.BILINEAR) if scale < 1.0 else img

    tensor = preprocess(img_inf).unsqueeze(0)
    with torch.no_grad():
        output = model(tensor)["out"]
    pred = output.argmax(dim=1).squeeze(0).byte().numpy()

    if pred.shape != (orig_h, orig_w):
        pred = np.array(Image.fromarray(pred).resize((orig_w, orig_h), Image.NEAREST))

    return pred


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("  FiftyOne Seg-Eval — Inference Pipeline (multi-experiment)")
    print("=" * 65)

    _validate_model_loaders()

    dataset = load_zoo_subset()
    print(f"Dataset: {len(dataset)} samples.")
    dataset.compute_metadata(overwrite=False)
    remap_labels(dataset)
    build_gt_masks(dataset)

    # GT mask 경로 수집
    gt_paths: dict[str, str] = {}
    for sample in dataset.iter_samples():
        gt_field = sample.get_field("gt_seg")
        if gt_field and gt_field.mask_path and Path(gt_field.mask_path).exists():
            gt_paths[sample.filepath] = gt_field.mask_path

    # manifest: {image_path, gt_mask_path, predictions: {exp: path}}
    manifest: dict[str, dict] = {
        fp: {"image_path": fp, "gt_mask_path": gp, "predictions": {}}
        for fp, gp in gt_paths.items()
    }

    # 각 experiment(모델) 순환
    for exp_name, exp_cfg in config.EXPERIMENTS.items():
        loader = MODEL_LOADERS.get(exp_name)
        if loader is None:
            print(f"\n  ⚠  No loader for '{exp_name}' — skipping.")
            continue

        print(f"\n[{exp_name}] Loading model: {exp_cfg['label']} …")
        try:
            model, preprocess = loader()
        except Exception as exc:
            print(f"  ⚠  Failed to load model for '{exp_name}': {exc}  — skipping.")
            continue

        pred_dir: Path = exp_cfg["pred_dir"]
        pred_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Running inference on {len(gt_paths)} samples (CPU) …")
        skipped = 0
        for i, (filepath, _) in enumerate(gt_paths.items(), 1):
            try:
                pred_mask = infer_one(filepath, model, preprocess)
            except Exception as exc:
                print(f"  ⚠  [{i}] {Path(filepath).name}: {exc}")
                skipped += 1
                continue

            pred_filename  = Path(filepath).stem + "_pred.png"
            pred_mask_path = pred_dir / pred_filename
            seg_utils.save_mask(pred_mask, pred_mask_path)
            manifest[filepath]["predictions"][exp_name] = str(pred_mask_path)

            if i % 10 == 0 or i == len(gt_paths):
                print(f"  {i}/{len(gt_paths)} done", end="\r")
        print()

        if skipped:
            print(f"  ⚠  {skipped} sample(s) skipped.")
        print(f"  ✓ '{exp_name}': {len(gt_paths) - skipped} masks → {pred_dir}")

        del model  # 메모리 해제

    # manifest 저장 (list 형태)
    entries = list(manifest.values())
    seg_utils.save_manifest(entries, config.MANIFEST_PATH)

    # zoo 데이터셋을 FiftyOne DB에서 제거한다.
    # 디스크 파일(~/fiftyone/zoo/...)은 그대로 보존되므로 재실행 시 재다운로드 없음.
    if fo.dataset_exists(config.DATASET_NAME):
        fo.delete_dataset(config.DATASET_NAME)
        print(f"  [cleanup] Zoo dataset '{config.DATASET_NAME}' removed from FiftyOne DB.")

    print()
    print("=" * 65)
    print("✓ Inference complete.")
    print(f"  Experiments : {list(config.EXPERIMENTS.keys())}")
    print(f"  Manifest    : {config.MANIFEST_PATH}  ({len(entries)} entries)")
    print()
    print("Next steps:")
    print("  python tools/generate_attrs.py")
    print("  python tools/precompute_panel_stats.py")
    print("  python main.py")
    print("=" * 65)


if __name__ == "__main__":
    main()
