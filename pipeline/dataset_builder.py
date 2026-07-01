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
    pred 필드가 실제로 존재하는 experiment 의 평가 결과가 모두 저장돼 있어야 한다.
    pred_shp 미존재 experiment 는 검사에서 제외한다.
    """
    if not fo.dataset_exists(name):
        return False
    ds = fo.load_dataset(name)
    if len(ds) == 0:
        return False
    schema = ds.get_field_schema()
    available = {exp for exp in config.EXPERIMENTS if f"predictions_{exp}" in schema}
    if not available:
        return False
    return available.issubset(set(ds.list_evaluations()))


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

        # 각 experiment 별 predictions_<exp> 필드
        for exp, pred_path in valid_preds.items():
            sample[f"predictions_{exp}"] = fo.Segmentation(mask_path=pred_path)

        # 속성 필드 부착 — attribute kind 로 등록된 컬럼만 sample 필드로 붙인다.
        # metric(biou 등)은 이 경로에서는 붙이지 않는다.
        # (metric 은 evaluation.run() 과 attach_derived_metric_fields() 가 담당한다.)
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

                # scene_type 이 "only_background" 면 FiftyOne sample 태그도 부착.
                # 사이드바 "Tags" 그룹에서 체크박스 한 번으로 배경만 패치를 필터링할 수 있다.
                # 속성 필드(scene_type)와 독립적으로 양쪽 다 부착한다.
                scene = sample_attrs.get("scene_type")
                if scene == "only_background":
                    sample.tags.append("only_background")
                elif scene == "has_building":
                    sample.tags.append("has_building")

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


def attach_derived_metric_fields(dataset: fo.Dataset, stats: dict) -> None:
    """panel_stats.json 의 derived/mask 메트릭을 {metric}_{exp} sample 필드로 부착한다.

    사이드바 배치 기준은 compute.source 가 아니라 kind 다.
      attribute → "Sample Attributes" 그룹 (build() 에서 처리)
      metric    → "Metrics · {model}" 그룹  (이 함수 + evaluation.run() 이 처리)

    fiftyone_eval 메트릭(accuracy/recall/precision)은 evaluation.run() 이 이미 붙이므로
    여기서는 source != "fiftyone_eval" 인 메트릭(f1/f2/biou 등)만 담당한다.
    메트릭 목록은 config.PANEL_COLUMN_META 에서 동적으로 읽어 하드코딩 없이 동작한다.

    캐시 적중 최적화: {metric}_{exp} 필드가 이미 schema 에 존재하는 experiment 는
    샘플 순회 없이 건너뛴다. persistent 데이터셋이라 DB 에 이미 저장돼 있음.

    Args:
        dataset: 대상 FiftyOne 데이터셋 (evaluation.run() 이 완료된 상태).
        stats:   panel_stats.json 의 파싱 결과 dict.
    """
    non_fo = [
        m for m, spec in config.PANEL_COLUMN_META.items()
        if spec.get("kind") == "metric"
        and spec.get("compute", {}).get("source") != "fiftyone_eval"
    ]
    if not non_fo or not stats:
        return

    schema = dataset.get_field_schema()
    experiments = stats.get("experiments", {})
    attached_any = False

    for exp_name in config.EXPERIMENTS:
        # 이미 모든 derived 메트릭 필드가 schema 에 있으면 재부착 불필요
        already_present = all(f"{m}_{exp_name}" in schema for m in non_fo)
        if already_present:
            continue

        records = experiments.get(exp_name, {}).get("records", [])
        if not records:
            print(f"  [attach_metrics] '{exp_name}': records 없음 → 건너뜀.")
            continue

        rec_by_path = {r["image_path"]: r for r in records}
        count = 0
        for sample in dataset.iter_samples(autosave=True):
            rec = rec_by_path.get(sample.filepath)
            if not rec:
                continue
            for m in non_fo:
                val = rec.get(m)
                if val is not None:
                    sample[f"{m}_{exp_name}"] = float(val)
                    count += 1
        if count:
            attached_any = True
            print(
                f"  [attach_metrics] '{exp_name}': {non_fo} → "
                f"{len(records)} 샘플에 부착 완료."
            )

    if attached_any:
        print(f"  → 사이드바에 {non_fo} 메트릭이 표시됩니다.")
