"""
seg_utils.py
────────────
Lightweight helpers for mask PNG I/O, manifest management, and tags I/O.
Shared between tools/* (1회성 준비 스크립트) and pipeline/* (분석 단계).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion


# ── Mask I/O ──────────────────────────────────────────────────────────────────

def save_mask(mask_array: np.ndarray, path: str | Path) -> None:
    """Save a 2-D integer mask as a grayscale PNG.

    Pixel values are class indices (uint8, 0–255).  Parent directories are
    created automatically.

    Args:
        mask_array: H×W numpy array, dtype will be cast to uint8.
        path:       Destination file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask_array.astype(np.uint8), mode="L").save(str(path))


def load_mask(path: str | Path) -> np.ndarray:
    """Load a grayscale PNG and return it as a uint8 numpy array (H×W)."""
    return np.array(Image.open(path), dtype=np.uint8)


# ── Manifest I/O ─────────────────────────────────────────────────────────────

def save_manifest(entries: list[dict], path: str | Path) -> None:
    """Persist a list of ``{image_path, gt_mask_path, pred_mask_path}`` dicts.

    This file is the only coupling between ``tools/run_inference.py`` and
    ``main.py`` — no FiftyOne zoo database access is needed after inference.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)
    print(f"Manifest saved → {path}  ({len(entries)} entries)")


def load_manifest(path: str | Path) -> list[dict]:
    """Load and return manifest entries from JSON."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── Sample Attributes I/O ────────────────────────────────────────────────────
# sample_attrs.json 형태: {image_path: {attr_name: value, ...}}
# tools/* 가 각자 담당 속성을 계산해 머지 저장 → pipeline/dataset_builder.py 가 로드.

def load_attrs(path: str | Path) -> dict[str, dict]:
    """Load sample_attrs.json. Returns empty dict if file does not exist."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def merge_attrs(path: str | Path, updates: dict[str, dict]) -> None:
    """Merge ``updates`` into sample_attrs.json and save.

    For each image_path key, new attribute keys are added and existing ones are
    overwritten.  Other attributes already in the file are left untouched.
    """
    path = Path(path)
    attrs = load_attrs(path)
    for image_path, new_vals in updates.items():
        attrs.setdefault(image_path, {}).update(new_vals)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(attrs, fh, indent=2, ensure_ascii=False)
    print(f"Attrs saved → {path}  ({len(attrs)} entries)")


# ── Boundary IoU ──────────────────────────────────────────────────────────────

def _boundary(binary_mask: np.ndarray, dilation_ratio: float) -> np.ndarray:
    """Return boundary pixels: region within `dilation_ratio` of the mask edge.

    The boundary width d is set to dilation_ratio × (shorter image side),
    clamped to at least 1 pixel.  Uses erosion so the boundary stays inside
    the original mask.
    """
    d = max(1, int(round(dilation_ratio * min(binary_mask.shape))))
    struct = np.ones((2 * d + 1, 2 * d + 1), dtype=bool)
    eroded = binary_erosion(binary_mask, structure=struct, border_value=0)
    # boundary = original mask minus its eroded interior
    return binary_mask & ~eroded


def compute_biou(
    gt_mask: np.ndarray,
    pred_mask: np.ndarray,
    classes: list[int],
    dilation_ratio: float = 0.02,
) -> dict[int, float]:
    """Compute Boundary IoU per class.

    Args:
        gt_mask:        H×W uint8 ground-truth mask (class indices).
        pred_mask:      H×W uint8 prediction mask (class indices).
        classes:        Class indices to evaluate (e.g. list(range(21))).
        dilation_ratio: Boundary width as fraction of the shorter image side.

    Returns:
        ``{class_idx: biou}`` — only classes present in GT or prediction are
        included.  An all-zero pair in both masks is skipped to avoid inflating
        scores with absent classes.
    """
    # pred_mask 크기가 다르면 gt_mask 크기로 맞춤 (nearest-neighbor, 클래스 인덱스 보존)
    if pred_mask.shape != gt_mask.shape:
        pred_mask = np.array(
            Image.fromarray(pred_mask).resize(
                (gt_mask.shape[1], gt_mask.shape[0]), Image.NEAREST
            )
        )

    scores: dict[int, float] = {}
    for c in classes:
        gt_c   = (gt_mask   == c)
        pred_c = (pred_mask == c)

        # skip classes absent from both GT and prediction
        if not gt_c.any() and not pred_c.any():
            continue

        b_gt   = _boundary(gt_c,   dilation_ratio)
        b_pred = _boundary(pred_c, dilation_ratio)

        intersection = int((b_gt & b_pred).sum())
        union        = int((b_gt | b_pred).sum())

        scores[c] = intersection / union if union > 0 else 1.0

    return scores
