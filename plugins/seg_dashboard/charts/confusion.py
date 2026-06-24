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

        x_labels = [f"Pred: {c}" for c in classes]
        y_labels = [f"GT: {c}"   for c in classes]
        cell_text = [[f"{int(v):,}" for v in row] for row in matrix.tolist()]

        trace = {
            "type": "heatmap",
            "z": log_matrix,
            "x": x_labels,
            "y": y_labels,
            "colorscale": "Blues",
            "showscale": True,
            "text": cell_text,
            "texttemplate": "%{text}",
            "textfont": {"size": 12, "color": "black"},
            "hovertemplate": (
                "<b>%{y}</b><br>"
                "<b>%{x}</b><br>"
                "pixels: %{customdata:,}<extra></extra>"
            ),
            "customdata": matrix.tolist(),
        }

        layout = {
            "title": {"text": "Confusion Matrix  (pixel count)"},
            "xaxis": {"title": "Predicted", "tickangle": 0},
            "yaxis": {"title": "Ground Truth", "autorange": "reversed"},
            "height": 420,
            "margin": {"t": 50, "b": 80},
        }

        return {"data": [trace], "layout": layout}
