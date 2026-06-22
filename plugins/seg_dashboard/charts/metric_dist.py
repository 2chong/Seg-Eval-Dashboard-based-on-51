"""plugins/seg_dashboard/charts/metric_dist.py — Metric Distribution Histogram."""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure
from .metric import _metric_label
from .registry import register_chart


@register_chart("metric_dist")
class MetricDistributionChart(BaseChart):
    """선택된 메트릭의 샘플 분포 히스토그램 (records 기반).

    x축: 메트릭 값 구간 (0.0–1.0 고정 범위)
    y축: 해당 구간의 샘플 수 (count 고정)

    params:
      records : list[dict] — get_records() 결과
      metric  : str        — 표시할 메트릭 이름
      bins    : int        — 구간 수 (기본 10)
    """

    field_types = ("numerical",)

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params  = params or {}
        records = params.get("records", [])
        metric  = params.get("metric", "recall")
        bins    = max(2, int(params.get("bins", 10)))

        if not records:
            return _empty_figure("Records not available.<br>Re-run precompute_panel_stats.py.")

        values = [float(r[metric]) for r in records if r.get(metric) is not None]
        if not values:
            return _empty_figure(f"No data for metric '{metric}'")

        arr = np.array(values)
        counts, bin_edges = np.histogram(arr, bins=bins, range=(0.0, 1.0))

        x_labels = [
            f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}"
            for i in range(len(bin_edges) - 1)
        ]

        label = _metric_label(metric)
        trace = {
            "type":          "bar",
            "x":             x_labels,
            "y":             counts.tolist(),
            "name":          label,
            "marker":        {"color": "steelblue"},
            "hovertemplate": f"{label}: %{{x}}<br>Count: %{{y}}<extra></extra>",
        }
        layout = {
            "title":  {"text": f"{label} Score Distribution"},
            "xaxis":  {"title": f"{label} score", "tickangle": 45},
            "yaxis":  {"title": "Sample count"},
            "height": 300,
            "margin": {"t": 50, "b": 100},
        }
        return {"data": [trace], "layout": layout}
