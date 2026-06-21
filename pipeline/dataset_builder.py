"""
pipeline/dataset_builder.py
───────────────────────────
역할: manifest + sample_attrs → fo.Dataset 구축

manifest 스키마 v2:
  {image_path, gt_mask_path, predictions: {exp_name: pred_mask_path}}

  하위호환 (v1):
  {image_path, gt_mask_path, pred_mask_path}
  → predictions = {DEFAULT_EXPERIMENT: pred_mask_path} 로 자동 변환

FiftyOne 필드:
  ground_truth            — GT 시맨틱 마스크
  predictions             — DEFAULT_EXPERIMENT 예측 마스크 (App 기본 오버레이)
  predictions_<exp>       — 각 experiment 예측 마스크 (App 비교용)
  <attr_name>             — sample_attrs.json 에서 로드한 속성 필드
"""

from __future__ import annotations

from pathlib import Path

import config

try:
    import fiftyone as fo
except ImportError as exc:
    import sys
    sys.exit(f"FiftyOne not installed.\nError: {exc}")


def _normalize_predictions(entry: dict) -> dict[str, str]:
    """manifest v1 / v2 모두에서 {exp_name: pred_path} dict 를 반환한다."""
    # v2 스키마
    if "predictions" in entry and isinstance(entry["predictions"], dict):
        return entry["predictions"]
    # v1 스키마 (pred_mask_path 단일 키)
    if "pred_mask_path" in entry:
        return {config.DEFAULT_EXPERIMENT: entry["pred_mask_path"]}
    return {}


def _is_cached(name: str) -> bool:
    """기존 FiftyOne 데이터셋을 재사용할 수 있는지 확인한다.

    조건: 데이터셋이 존재하고, 샘플이 있으며,
    config.EXPERIMENTS 의 모든 experiment 평가 결과가 저장돼 있어야 한다.
    """
    if not fo.dataset_exists(name):
        return False
    ds = fo.load_dataset(name)
    if len(ds) == 0:
        return False
    expected = {f"seg_eval_{exp}" for exp in config.EXPERIMENTS}
    return expected.issubset(set(ds.list_evaluations()))


def build(
    manifest: list[dict],
    attrs: dict[str, dict] | None = None,
    force_rebuild: bool = False,
) -> fo.Dataset:
    """manifest 와 (선택적) sample_attrs 로부터 FiftyOne 데이터셋을 반환한다.

    force_rebuild=False (기본값) 이면 평가 결과가 캐시된 경우 기존 데이터셋을 재사용한다.
    precompute_panel_stats.py 는 항상 force_rebuild=True 로 호출한다.
    """
    name = config.EVAL_DATASET_NAME

    if not force_rebuild and _is_cached(name):
        cached = fo.load_dataset(name)
        print(f"Dataset '{name}' loaded from cache  ({len(cached)} samples).")
        return cached

    if fo.dataset_exists(name):
        fo.delete_dataset(name)

    dataset = fo.Dataset(name=name, persistent=True)
    samples: list[fo.Sample] = []
    missing = 0

    for entry in manifest:
        gt_path = Path(entry["gt_mask_path"])
        preds   = _normalize_predictions(entry)

        if not gt_path.exists() or not preds:
            missing += 1
            continue

        # 최소 하나의 pred mask 가 존재해야 포함
        valid_preds = {
            exp: p for exp, p in preds.items() if Path(p).exists()
        }
        if not valid_preds:
            missing += 1
            continue

        sample = fo.Sample(filepath=entry["image_path"])
        sample["ground_truth"] = fo.Segmentation(mask_path=str(gt_path))

        # 기본 predictions 필드 (App 오버레이 기본값)
        default_pred = valid_preds.get(config.DEFAULT_EXPERIMENT)
        if default_pred is None:
            default_pred = next(iter(valid_preds.values()))
        sample["predictions"] = fo.Segmentation(mask_path=default_pred)

        # 각 experiment 별 predictions_<exp> 필드
        for exp, pred_path in valid_preds.items():
            sample[f"predictions_{exp}"] = fo.Segmentation(mask_path=pred_path)

        # 속성 필드 부착 — attribute kind로 등록된 컬럼만 sample 필드로 붙인다.
        # metric(biou 등)은 panel_stats.json에만 존재하며 절대 sample 필드가 되지 않는다.
        if attrs is not None:
            sample_attrs = attrs.get(entry["image_path"])
            if sample_attrs is not None:
                for key, value in sample_attrs.items():
                    col_kind = config.PANEL_COLUMN_META.get(key, {}).get("kind")
                    if col_kind == "attribute":
                        sample[key] = value
                    elif col_kind is None:
                        # 메타 미등록 키는 보수적으로 부착 (하위호환)
                        sample[key] = value
                    # col_kind == "metric" 이면 조용히 무시

        if len(samples) == 0:
            print("\n[Sample preview]")
            print(sample)

        samples.append(sample)

    if missing:
        print(
            f"  ⚠  {missing} manifest entr{'y' if missing == 1 else 'ies'} skipped "
            "(mask file not found or no predictions)."
        )

    dataset.add_samples(samples)
    dataset.compute_metadata()

    n_attrs  = sum(1 for s in samples if attrs and attrs.get(s.filepath))
    attr_keys = sorted({k for v in (attrs or {}).values() for k in v}) or []
    note_str  = f", {n_attrs} with attrs {attr_keys}" if attr_keys else " (no attrs)"
    exps      = [e for e in config.EXPERIMENTS if any(
        f"predictions_{e}" in s.field_names for s in samples[:1]
    )]
    print(
        f"Dataset ready: '{config.EVAL_DATASET_NAME}'  "
        f"({len(dataset)} samples{note_str}, experiments={exps})"
    )
    return dataset
