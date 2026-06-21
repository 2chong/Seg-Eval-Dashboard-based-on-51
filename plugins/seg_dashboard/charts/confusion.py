"""plugins/seg_dashboard/charts/confusion.py — Confusion Matrix Heatmap."""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure


class ConfusionMatrixChart(BaseChart):
    """Confusion matrix heatmap (log pixel count scale).

    행(y) = Ground Truth, 열(x) = Predicted.
    로그 스케일로 background 픽셀 지배를 줄여 소수 클래스 패턴도 식별 가능.
    """

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        cm_data = stats.get("confusion_matrix")
        if not cm_data:
            return _empty_figure("Confusion matrix data not found")

        classes = cm_data["classes"]
        matrix = np.array(cm_data["matrix"], dtype=float)
        log_matrix = np.log1p(matrix).tolist()

        trace = {
            "type": "heatmap",
            "z": log_matrix,
            "x": classes,
            "y": classes,
            "colorscale": "Blues",
            "showscale": True,
            "hovertemplate": (
                "GT: <b>%{y}</b><br>"
                "Pred: <b>%{x}</b><br>"
                "pixels: %{customdata:,}<extra></extra>"
            ),
            "customdata": matrix.tolist(),
        }

        layout = {
            "title": {"text": "Confusion Matrix  (log pixel count)"},
            "xaxis": {"title": "Predicted", "tickangle": 45},
            "yaxis": {"title": "Ground Truth", "autorange": "reversed"},
            "height": 420,
            "margin": {"t": 50, "b": 120},
        }

        return {"data": [trace], "layout": layout}
