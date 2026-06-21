"""
tools/fix_mask_sizes.py
────────────────────────
이미 저장된 예측 마스크의 크기를 GT 마스크 크기에 맞게 수정한다.
모델 재추론 없이 PNG 파일만 읽고 쓰므로 수 초 내에 완료된다.

Run once (after run_inference.py, before main.py):
    python tools/fix_mask_sizes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image

import config
import seg_utils


def main() -> None:
    if not config.MANIFEST_PATH.exists():
        sys.exit(f"Manifest not found: {config.MANIFEST_PATH}")

    manifest = seg_utils.load_manifest(config.MANIFEST_PATH)
    fixed = 0

    for entry in manifest:
        gt_path   = Path(entry["gt_mask_path"])
        pred_path = Path(entry["pred_mask_path"])
        if not gt_path.exists() or not pred_path.exists():
            continue

        gt_mask   = seg_utils.load_mask(gt_path)
        pred_mask = seg_utils.load_mask(pred_path)

        if pred_mask.shape == gt_mask.shape:
            continue

        pred_fixed = np.array(
            Image.fromarray(pred_mask).resize(
                (gt_mask.shape[1], gt_mask.shape[0]), Image.NEAREST
            )
        )
        seg_utils.save_mask(pred_fixed, pred_path)
        fixed += 1

    print(f"Fixed {fixed} / {len(manifest)} prediction masks.")


if __name__ == "__main__":
    main()
