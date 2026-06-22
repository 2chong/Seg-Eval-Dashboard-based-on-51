"""
tools/generate_attrs.py
───────────────────────
1회성 스크립트: 샘플별 **intrinsic attribute** 를 계산해 data/sample_attrs.json 에 저장한다.

intrinsic attribute = 예측·평가와 무관하게 이미지 자체에서 결정되는 속성.
어떤 속성을 생성할지는 두 단계 규칙으로 결정된다:
  1. PANEL_COLUMN_META (규칙 라이브러리) — kind="attribute" + generate 키 있는 항목 전체.
  2. ATTRIBUTE_GROUPS + 각 데이터셋 "attributes" 키 (그룹 선택) — 데이터셋마다 쓸 속성을 지정.
  config.dataset_attribute_keys() 가 이 두 단계를 합쳐 최종 키 목록을 반환한다.

generate.method 별 생성 규칙:
  "choice"  → rng.choice(meta["values"])
  "float"   → rng.uniform(*meta["range"]), round(…, generate["round"])
  "int"     → rng.randint(*meta["range"])

metric (biou, recall 등 예측 의존 값) 은 이 스크립트의 대상이 아님:
  precompute_panel_stats.py 가 experiment 별로 계산한다.

Run once (after run_inference.py):
    python tools/generate_attrs.py [--dataset <name>]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config

_p = argparse.ArgumentParser(add_help=False)
_p.add_argument("--dataset", default=None)
config.activate_dataset(_p.parse_known_args()[0].dataset)

import seg_utils


def _generate_value(meta: dict, rng: random.Random):
    """PANEL_COLUMN_META 한 항목의 generate 스펙에 따라 값을 생성한다.

    null_prob 지정 시 해당 확률로 None(JSON null) 을 반환한다.
    """
    gen    = meta.get("generate", {})
    method = gen.get("method")

    if gen.get("null_prob", 0.0) > 0.0 and rng.random() < gen["null_prob"]:
        return None

    if method == "choice":
        return rng.choice(meta["values"])

    if method == "float":
        lo, hi = meta.get("range", [0.0, 1.0])
        return round(rng.uniform(lo, hi), gen.get("round", 3))

    if method == "int":
        lo, hi = meta.get("range", [0, 50])
        return rng.randint(int(lo), int(hi))

    return None


def _attr_schema() -> dict[str, dict]:
    """이 데이터셋에 부착할 attribute 항목만 반환한다.

    config.dataset_attribute_keys() 가 데이터셋 그룹을 해석하고,
    그 키 중 generate 키가 있는 항목만 생성 대상이다.
    """
    active_keys = set(config.dataset_attribute_keys(config.ACTIVE_DATASET))
    return {
        key: meta
        for key, meta in config.PANEL_COLUMN_META.items()
        if meta.get("kind") == "attribute" and "generate" in meta and key in active_keys
    }


def compute_random_attrs(
    manifest: list[dict],
    base_seed: int,
) -> dict[str, dict]:
    """PANEL_COLUMN_META 의 attribute 스키마를 읽어 샘플별 속성값을 생성한다.

    각 속성은 독립된 RNG (seed="{base_seed}:{field}") 를 사용한다.
    새 속성을 추가해도 기존 속성의 생성값이 변하지 않는다.
    """
    schema = _attr_schema()
    rngs   = {field: random.Random(f"{base_seed}:{field}") for field in schema}

    updates: dict[str, dict] = {}
    for entry in manifest:
        updates[entry["image_path"]] = {
            field: _generate_value(meta, rngs[field])
            for field, meta in schema.items()
        }

    return updates


def main() -> None:
    print("=" * 65)
    print("  Sample Attribute Generation  (intrinsic attributes only)")
    print("=" * 65)

    if not config.MANIFEST_PATH.exists():
        sys.exit(
            f"Manifest not found: {config.MANIFEST_PATH}\n"
            "Please run  python tools/run_inference.py  first."
        )

    schema   = _attr_schema()
    print(f"Attribute schema: {list(schema.keys())}  (from PANEL_COLUMN_META)")

    manifest = seg_utils.load_manifest(config.MANIFEST_PATH)
    print(f"Manifest loaded:  {len(manifest)} entries")

    updates = compute_random_attrs(manifest, config.ATTR_SEED)

    # 속성별 요약 출력
    print()
    for field, meta in schema.items():
        all_vals = [v[field] for v in updates.values()]
        null_count = sum(1 for v in all_vals if v is None)
        vals = [v for v in all_vals if v is not None]
        null_suffix = f"  (null: {null_count}/{len(all_vals)})" if null_count else ""
        if not vals:
            print(f"  {field:<12}: all null{null_suffix}")
            continue
        if meta["type"] == "categorical":
            from collections import Counter
            dist = Counter(vals)
            print(f"  {field:<12}: {dict(dist)}{null_suffix}")
        else:
            print(
                f"  {field:<12}: min={min(vals)}, max={max(vals)}, "
                f"mean={sum(vals)/len(vals):.3f}{null_suffix}"
            )

    print(
        "\n  NOTE: biou / recall / precision / f1 / f2 are prediction-dependent metrics\n"
        "        and are NOT computed here — see precompute_panel_stats.py."
    )

    # 전체 덮어쓰기: 스키마에 없는 속성(삭제된 속성)이 파일에 남지 않도록 한다.
    config.ATTRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.ATTRS_PATH, "w", encoding="utf-8") as fh:
        json.dump(updates, fh, indent=2, ensure_ascii=False)
    print(f"\nAttrs saved → {config.ATTRS_PATH}  ({len(updates)} entries)")
    print("Done. Next step → python tools/precompute_panel_stats.py")


if __name__ == "__main__":
    main()
