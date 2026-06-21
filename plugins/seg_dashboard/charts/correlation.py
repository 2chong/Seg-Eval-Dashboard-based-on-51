"""
plugins/seg_dashboard/charts/correlation.py
─────────────────────────────────────────────
속성–메트릭 Pearson 상관계수 heatmap.

필요 데이터 (precompute_panel_stats.py 가 생성):
  stats["correlation"] = {
      "fields":   ["field_a", "field_b", ...],   # 수치형 속성 목록
      "metrics":  ["recall", "f1", "precision"],
      "matrix":   [[r, r, r], ...],              # shape: (n_fields, n_metrics)
  }

stats["correlation"] 키가 없으면 placeholder 메시지를 표시하므로,
구 panel_stats.json 에서도 패널이 crash 나지 않는다.
"""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure
from .metric import _metric_label

_PLACEHOLDER = (
    "Correlation data not yet computed.<br>"
    "Re-run precompute_panel_stats.py to generate this chart."
)


class CorrelationChart(BaseChart):
    """속성–메트릭 상관계수 heatmap (-1 ~ +1, RdBu colorscale)."""

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        corr = stats.get("correlation")
        if not corr:
            return _empty_figure(_PLACEHOLDER)

        fields = corr["fields"]
        metrics = corr["metrics"]
        matrix = np.array(corr["matrix"])

        if matrix.size == 0:
            return _empty_figure("Not enough data for correlation")

        # 셀 텍스트: 소수점 둘째자리 상관계수 표시
        text = [[f"{v:.2f}" for v in row] for row in matrix.tolist()]

        trace = {
            "type": "heatmap",
            "z": matrix.tolist(),
            "x": [_metric_label(m) for m in metrics],
            "y": fields,
            "colorscale": "RdBu",
            "zmin": -1,
            "zmax": 1,
            "showscale": True,
            "text": text,
            "texttemplate": "%{text}",
            "hovertemplate": (
                "Field: <b>%{y}</b><br>"
                "Metric: <b>%{x}</b><br>"
                "Corr: %{z:.3f}<extra></extra>"
            ),
        }

        n_samples = corr.get("n_samples", "?")
        layout = {
            "title": {"text": f"Attribute–Metric Correlation  (n={n_samples})"},
            "xaxis": {"title": "Metric"},
            "yaxis": {"title": "Attribute", "autorange": "reversed"},
            "height": max(280, 100 + 45 * len(fields)),
            "margin": {"t": 50, "b": 80},
        }

        return {"data": [trace], "layout": layout}
