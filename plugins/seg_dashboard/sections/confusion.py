"""plugins/seg_dashboard/sections/confusion.py — Confusion Matrix Section."""

from __future__ import annotations

from .base import PanelSection
from ..charts import ConfusionMatrixChart
from ..stats import get_experiment_stats


class ConfusionMatrixSection(PanelSection):
    """항상 표시되는 Confusion Matrix heatmap.

    v2 스키마에서는 experiment 별 CM 을 읽는다.
    v1 스키마(구)에서는 최상위 confusion_matrix 를 읽는다 (하위호환).
    """

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        exp_stats = get_experiment_stats(stats, state.get("experiment"))
        fig = ConfusionMatrixChart().build_figure(exp_stats)
        panel.plot("cm_figure", data=fig["data"], layout=fig["layout"])
