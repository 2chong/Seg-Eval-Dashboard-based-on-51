"""
plugins/seg_dashboard/sections/experiment_compare.py
──────────────────────────────────────────────────────
ExperimentCompareSection: experiment 간 메트릭 비교 grouped bar.

메트릭 목록은 stats["columns"] (kind=="metric") 에서 동적으로 읽는다.
SUPPORTED_METRICS 상수를 사용하지 않는다.
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..charts import GroupedMetricChart
from ..charts.base import _empty_figure
from ..charts.metric import _metric_label
from ..stats import list_experiments, get_experiment_stats, list_metrics


class ExperimentCompareSection(PanelSection):
    """Experiment 간 overall 및 per-class 메트릭 grouped bar chart.

    메트릭 드롭다운: per_class 데이터에 실제로 존재하는 메트릭만 표시한다.
    실험 목록: stats 에 등록된 모든 experiment 를 비교한다.
    """

    def _available_metrics(self, stats: dict, experiments: list[str]) -> list[str]:
        """per_class 에 값이 있는 메트릭 키 목록. 없으면 columns kind=metric 전체."""
        for exp in experiments:
            per_class = get_experiment_stats(stats, exp).get("per_class", {})
            if per_class:
                sample = next(iter(per_class.values()), {})
                found = [m for m in sample if sample.get(m) is not None]
                if found:
                    return found
        return list_metrics(stats)

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks   = callbacks or {}
        experiments = list_experiments(stats)

        if len(experiments) < 2:
            fig = _empty_figure(
                "Experiment comparison requires 2+ experiments.<br>"
                "Run tools/run_inference.py with multiple models,<br>"
                "then re-run precompute_panel_stats.py."
            )
            panel.plot("exp_compare_figure", data=fig["data"], layout=fig["layout"])
            return

        # ── 메트릭 드롭다운 ───────────────────────────────────────────────────
        available = self._available_metrics(stats, experiments)
        metric    = state.get("metric", available[0] if available else "recall")
        if metric not in available:
            metric = available[0] if available else "recall"

        mc = types.Dropdown(label="Metric")
        for m in available:
            mc.add_choice(m, label=_metric_label(m))
        panel.enum(
            "metric",
            mc.values(),
            view=mc,
            default=metric,
            on_change=callbacks.get("metric"),
        )

        # ── per-experiment per-class 데이터 수집 ─────────────────────────────
        _OVERALL_KEY = "Overall"
        exp_per_class: dict[str, dict[str, float]] = {}
        for exp in experiments:
            exp_stats = get_experiment_stats(stats, exp)
            per_class = exp_stats.get("per_class", {})
            if per_class:
                cls_scores = {
                    cls: float(data.get(metric) or 0.0)
                    for cls, data in per_class.items()
                    if data.get(metric) is not None
                }
                # Overall = records 의 metric 평균 (sample-level)
                records = exp_stats.get("records", [])
                vals = [float(r[metric]) for r in records if r.get(metric) is not None]
                if vals:
                    cls_scores[_OVERALL_KEY] = round(sum(vals) / len(vals), 6)
                exp_per_class[exp] = cls_scores

        if not exp_per_class:
            fig = _empty_figure("per_class data not found.<br>Re-run precompute_panel_stats.py.")
            panel.plot("exp_compare_figure", data=fig["data"], layout=fig["layout"])
            return

        meta_labels = stats.get("meta", {}).get("experiment_labels", {})
        fig = GroupedMetricChart().build_figure(
            stats,
            params={
                "experiments":       experiments,
                "exp_per_class":     exp_per_class,
                "metric":            metric,
                "experiment_labels": meta_labels,
                "overall_key":       _OVERALL_KEY,
            },
        )
        panel.plot("exp_compare_figure", data=fig["data"], layout=fig["layout"])
