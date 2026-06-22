"""
pipeline/evaluation.py
───────────────────────
역할: 등록된 모든 experiment 에 대해 픽셀 레벨 segmentation 평가 실행.

  run(dataset)          → {exp_name: SegmentationResults} 반환
  print_report(results) → 콘솔에 per-class 표 출력

evaluate_segmentations() 가 생성하는 {exp}_{metric} 필드를 실행 직후
{metric}_{exp} 형태로 rename 한다 (configure_sidebar 의 endswith("_{exp}") 패턴에 맞추기 위함).

최종 sample 필드 이름:
  accuracy_{exp}   — 샘플별 픽셀 정확도  (예: accuracy_lraspp_mv3)
  recall_{exp}     — per-sample recall
  precision_{exp}  — per-sample precision
"""

from __future__ import annotations

import config

try:
    import fiftyone as fo
except ImportError as exc:
    import sys
    sys.exit(f"FiftyOne not installed.\nError: {exc}")

# FiftyOne이 eval_key=exp_name 으로 생성하는 per-sample 스칼라 필드 목록.
# evaluate_segmentations 직후 {exp}_{metric} → {metric}_{exp} 로 리네임한다.
# configure_sidebar 가 f.endswith(f"_{exp_name}") 패턴으로 검색하기 때문.
_FO_EVAL_SCALARS = ("accuracy", "recall", "precision")


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
        eval_key   = exp_name

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

    # FO가 {exp}_{metric} 순으로 필드를 생성하므로 {metric}_{exp} 로 리네임.
    # configure_sidebar 의 f.endswith(f"_{exp_name}") 패턴과 일치시키기 위함.
    schema = dataset.get_field_schema()
    for exp_name in config.EXPERIMENTS:
        for m in _FO_EVAL_SCALARS:
            old_name, new_name = f"{exp_name}_{m}", f"{m}_{exp_name}"
            if old_name in schema:
                dataset.rename_sample_field(old_name, new_name)
                print(f"  [rename] {old_name} → {new_name}")

    return all_results


def print_report(results: dict[str, object]) -> None:
    """experiment 별 per-class precision / recall 를 콘솔에 표로 출력한다."""
    for exp_name, res in results.items():
        print()
        print("=" * 70)
        print(f"  Per-Class Evaluation Report — {exp_name}")
        print("=" * 70)
        res.print_report()
