"""plugins/seg_dashboard/sections/metric_dist.py — Metric Distribution Section.

Private state keys (prefixed with container name "metric_dist"):
  metric_dist.dist_metric  -- selected metric
  metric_dist.dist_bins    -- histogram bin count
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..charts import MetricDistributionChart
from ..charts.base import _empty_figure
from ..framework.widgets import add_dropdown, add_bins_slider
from ..charts.metric import _metric_label
from ..stats import get_records, list_metrics

_PLACEHOLDER = (
    "Records data not yet available.<br>"
    "Re-run precompute_panel_stats.py to generate this chart."
)

# Container name -- all private state keys are prefixed with this
_CONTAINER = "metric_dist"


class MetricDistributionSection(PanelSection):
    """메트릭 점수 분포 히스토그램.

    x축: 메트릭 점수 구간 / y축: 샘플 수 (count 고정).
    컨트롤과 차트는 같은 ObjectView 컨테이너 안에 묶인다.
    """

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks = callbacks or {}
        records   = get_records(stats, state.get("experiment"))

        # panel.obj() 는 Property 를 반환하므로 직접 Object 를 생성한다.
        grp = types.Object()

        if not records:
            fig = _empty_figure(_PLACEHOLDER)
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Metric Distribution",
                view=types.ObjectView(),
            )
            return

        all_metrics = list_metrics(stats)
        available   = [m for m in all_metrics if m in records[0]] if all_metrics else []
        if not available:
            fig = _empty_figure("No metrics in records.<br>Re-run precompute_panel_stats.py.")
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Metric Distribution",
                view=types.ObjectView(),
            )
            return

        metric = state.get(f"{_CONTAINER}.dist_metric") or ""
        if metric not in available:
            metric = available[0]

        add_dropdown(
            grp, "dist_metric", available,
            label="Metric", default=metric,
            on_change=callbacks.get(f"{_CONTAINER}.dist_metric"),
            labels=_metric_label,
        )

        bins = max(2, int(state.get(f"{_CONTAINER}.dist_bins", 10)))
        add_bins_slider(
            grp, "dist_bins", value=bins,
            on_change=callbacks.get(f"{_CONTAINER}.dist_bins"),
        )

        fig = MetricDistributionChart().build_figure(
            stats,
            params={"records": records, "metric": metric, "bins": bins},
        )
        grp.plot("figure", data=fig["data"], layout=fig["layout"])

        panel.define_property(
            _CONTAINER, grp,
            label="Metric Distribution",
            view=types.ObjectView(),
        )
