"""plugins/seg_dashboard/sections/correlation.py — Correlation Section."""

from __future__ import annotations

from .base import PanelSection
from ..charts import CorrelationChart
from ..stats import get_experiment_stats


class CorrelationSection(PanelSection):
    """속성–메트릭 Pearson 상관계수 heatmap.

    v2 스키마: experiment 별 correlation 블록을 읽는다.
    stats 에 'correlation' 키가 없으면 placeholder 를 표시하므로
    구 stats 파일에서도 패널이 crash 나지 않는다.
    """

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        exp_stats = get_experiment_stats(stats, state.get("experiment"))
        fig = CorrelationChart().build_figure(exp_stats)
        panel.plot("corr_figure", data=fig["data"], layout=fig["layout"])
