"""plugins/seg_dashboard/sections/metric_summary.py
Overall metrics summary table — Evaluation panel 상단 고정.

records 기반으로 선택된 experiment 의 per-sample 메트릭 평균을 Plotly table 로 표시한다.
"""

from __future__ import annotations

import numpy as np

from .base import PanelSection
from ..stats import get_records, list_metrics

_LABELS: dict[str, str] = {
    "precision": "Precision",
    "recall":    "Recall",
    "f1":        "F1",
    "f2":        "F2",
    "iou":       "IoU",
    "accuracy":  "Accuracy",
}
_ORDER = ["precision", "recall", "f1", "f2", "iou", "accuracy"]


class MetricSummarySection(PanelSection):
    """선택된 experiment 의 per-sample 메트릭 평균 테이블."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        records     = get_records(stats, state.get("experiment"))
        all_metrics = list_metrics(stats)

        if not all_metrics or not records:
            return

        ordered   = [m for m in _ORDER if m in all_metrics]
        remaining = sorted(m for m in all_metrics if m not in ordered)
        metrics   = ordered + remaining

        rows: list[tuple[str, float]] = []
        for m in metrics:
            vals = [r[m] for r in records if r.get(m) is not None]
            if not vals:
                continue
            rows.append((m, float(np.mean(vals))))

        if not rows:
            return

        n            = len(records)
        metric_names = [_LABELS.get(m, m.capitalize()) for m, _ in rows]
        means        = [f"{mean:.4f}" for _, mean in rows]

        stripe = ["#f0f4f8" if i % 2 == 0 else "white" for i in range(len(rows))]
        fig = {
            "data": [{
                "type":   "table",
                "header": {
                    "values": ["Metric", "Mean"],
                    "fill":   {"color": "#2c3e50"},
                    "font":   {"color": "white", "size": 13},
                    "align":  "center",
                    "height": 32,
                },
                "cells": {
                    "values": [metric_names, means],
                    "fill":   {"color": [stripe] * 2},
                    "align":  ["left", "center"],
                    "height": 28,
                },
            }],
            "layout": {
                "title":  {"text": f"Overall Metrics  (n = {n:,} patches)"},
                "height": 80 + 28 * len(rows),
                "margin": {"t": 40, "b": 10, "l": 10, "r": 10},
            },
        }
        panel.plot("metric_summary_table", data=fig["data"], layout=fig["layout"])
