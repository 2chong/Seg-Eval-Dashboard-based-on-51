"""
pipeline/evaluation.py
───────────────────────
역할: 등록된 모든 experiment 에 대해 픽셀 레벨 segmentation 평가 실행.

  run(dataset)          → {exp_name: SegmentationResults} 반환
  print_report(results) → 콘솔에 per-class 표 출력

evaluate_segmentations() 는 각 샘플에 아래 scalar 필드를 기록한다:
  seg_eval_<exp>_accuracy   — 샘플별 픽셀 정확도
  seg_eval_<exp>_recall     — per-sample recall (또는 DictField)
  seg_eval_<exp>_precision  — per-sample precision
"""

from __future__ import annotations

import config

try:
    import fiftyone as fo
except ImportError as exc:
    import sys
    sys.exit(f"FiftyOne not installed.\nError: {exc}")


def run(dataset: fo.Dataset) -> dict[str, object]:
    """등록된 모든 experiment 의 segmentation 평가를 실행하고 결과 dict 를 반환한다.

    데이터셋에 이미 seg_eval_<exp> 평가 결과가 저장돼 있으면 재실행하지 않고
    캐시된 결과를 로드한다. (같은 데이터셋·같은 모델의 평가 결과는 항상 동일하다.)

    Returns:
        {exp_name: SegmentationResults}
    """
    print("\nChecking evaluation cache …")
    existing_evals = dataset.list_evaluations()
    all_results: dict[str, object] = {}
    schema = dataset.get_field_schema()

    for exp_name in config.EXPERIMENTS:
        pred_field = f"predictions_{exp_name}"
        eval_key   = f"seg_eval_{exp_name}"

        if pred_field not in schema:
            print(f"  ⚠  '{pred_field}' 필드 없음 → '{exp_name}' 평가 건너뜀")
            continue

        if eval_key in existing_evals:
            print(f"  [{exp_name}] 캐시 로드 ('{eval_key}') …")
            all_results[exp_name] = dataset.load_evaluation_results(eval_key)
            print(f"  ✓ '{exp_name}' loaded from cache.")
            continue

        print(f"  [{exp_name}] predictions='{pred_field}', eval_key='{eval_key}' …")
        results = dataset.evaluate_segmentations(
            pred_field,
            gt_field="ground_truth",
            eval_key=eval_key,
            mask_targets=config.MASK_TARGETS,
        )
        all_results[exp_name] = results
        print(f"  ✓ '{exp_name}' evaluation complete.")

    if not all_results:
        print(
            "  ⚠  No experiments evaluated."
            "  Run python tools/run_inference.py first."
        )

    print("Evaluation done.")
    return all_results


def print_report(results: dict[str, object]) -> None:
    """experiment 별 per-class precision / recall 를 콘솔에 표로 출력한다."""
    for exp_name, res in results.items():
        print()
        print("=" * 70)
        print(f"  Per-Class Evaluation Report — {exp_name}")
        print("=" * 70)
        res.print_report()
