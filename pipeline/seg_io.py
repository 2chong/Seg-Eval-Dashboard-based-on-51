"""
pipeline/seg_io.py
──────────────────
Lightweight I/O helpers shared across tools/ and pipeline/.

  Mask PNG  : save_mask / load_mask
  Manifest  : save_manifest / load_manifest
  Attrs     : load_attrs
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


# ── Mask I/O ──────────────────────────────────────────────────────────────────

def save_mask(mask_array: np.ndarray, path: str | Path) -> None:
    """Save a 2-D integer mask as a grayscale PNG.

    Pixel values are class indices (uint8, 0-255). Parent directories are
    created automatically.

    Args:
        mask_array: H x W numpy array, dtype will be cast to uint8.
        path:       Destination file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask_array.astype(np.uint8), mode="L").save(str(path))


def load_mask(path: str | Path) -> np.ndarray:
    """Load a grayscale PNG and return it as a uint8 numpy array (H x W)."""
    return np.array(Image.open(path), dtype=np.uint8)


# ── Manifest I/O ─────────────────────────────────────────────────────────────

def save_manifest(entries: list[dict], path: str | Path) -> None:
    """Persist a list of manifest entry dicts as JSON.

    Each entry contains at minimum ``image_path``, ``gt_mask_path``, and
    ``predictions`` keys written by ``oneoff/build_manifest.py``.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)
    print(f"Manifest saved -> {path}  ({len(entries)} entries)")


def load_manifest(path: str | Path) -> list[dict]:
    """Load and return manifest entries from JSON."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── Sample Attributes I/O ────────────────────────────────────────────────────
# sample_attrs.json: {image_path: {attr_name: value, ...}}
# tools/generate_attrs.py 가 계산해 저장 -> pipeline/dataset_builder.py 가 로드.

def load_attrs(path: str | Path) -> dict[str, dict]:
    """Load sample_attrs.json. Returns empty dict if file does not exist."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
