"""
plugins/seg_dashboard/charts/grouped_metric.py
────────────────────────────────────────────────
GroupedMetricChart: experiment 간 per-class 메트릭 grouped bar.

params:
  experiments      : list[str]           — experiment 이름 목록
  exp_per_class    : dict[str, dict]     — {exp: {cls: score}}
  metric           : str                 — 표시 메트릭 이름
  experiment_labels: dict[str, str]      — {exp: 표시 이름} (선택)
  overall_key      : str                 — 전체 평균 카테고리 키 (선택, 맨 앞에 고정)
"""

from __future__ import annotations

from .base import BaseChart, _empty_figure


class GroupedMetricChart(BaseChart):
    """Experiment 별 per-class 메트릭 grouped bar chart."""

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params = params or {}
        experiments   = params.get("experiments", [])
        exp_per_class = params.get("exp_per_class", {})
        metric        = params.get("metric", "recall")
        exp_labels    = params.get("experiment_labels", {})
        overall_key   = params.get("overall_key")

        if not experiments or not exp_per_class:
            return _empty_figure("No experiment data available")

        # 유효 클래스 = 어떤 experiment 에서든 값이 있는 클래스
        all_classes: set[str] = set()
        for cls_data in exp_per_class.values():
            all_classes |= set(cls_data.keys())
        # Overall 은 맨 앞에 고정, 나머지는 알파벳 정렬
        if overall_key and overall_key in all_classes:
            classes = [overall_key] + sorted(all_classes - {overall_key})
        else:
            classes = sorted(all_classes)

        metric_label = metric.upper() if metric == "f1" else metric.capitalize()

        traces = []
        for exp in experiments:
            cls_data = exp_per_class.get(exp, {})
            y = [float(cls_data.get(cls, 0.0)) for cls in classes]
            traces.append({
                "type": "bar",
                "name": exp_labels.get(exp, exp),
                "x": classes,
                "y": y,
            })

        layout = {
            "title":   {"text": f"Per-Class {metric_label} — Experiment Comparison"},
            "xaxis":   {"title": "Class", "tickangle": 45},
            "yaxis":   {"title": metric_label, "range": [0, 1]},
            "barmode": "group",
            "height":  400,
            "margin":  {"t": 50, "b": 140},
            "legend":  {"title": {"text": "Experiment"}},
        }

        return {"data": traces, "layout": layout}
