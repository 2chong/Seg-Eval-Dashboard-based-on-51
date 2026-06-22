"""plugins/seg_dashboard/charts/cross_exp_metric.py
Cross-experiment attribute x metric comparison charts.

속성값(또는 구간)별 평균 메트릭을 실험별로 겹쳐 보여준다.

  categorical attribute -> grouped bar  (x=속성값, y=mean metric, trace=experiment)
  numerical attribute   -> multi-line   (x=bin center, y=mean metric, line=experiment)

params:
  all_records      : dict[str, list[dict]]  — {exp_key: records}
  metric           : str
  experiment_labels: dict[str, str]          — {exp_key: 표시 이름}
  bins             : int  (numerical 전용, 기본 10)
"""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure
from .metric import _metric_label
from .registry import register_chart
from ._common import _COLORS


@register_chart("cross_exp")
class CrossExpCategoricalChart(BaseChart):
    """categorical 속성 × 메트릭 실험별 grouped bar chart."""

    field_types = ("categorical",)

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params      = params or {}
        all_records = params.get("all_records", {})
        metric      = params.get("metric", "recall")
        exp_labels  = params.get("experiment_labels", {})

        if not all_records or not field:
            return _empty_figure("No data available")

        all_values: set[str] = set()
        for records in all_records.values():
            for r in records:
                v = r.get(field)
                if v is not None:
                    all_values.add(str(v))

        if not all_values:
            return _empty_figure(f"No data: {field} × {metric}")

        x_labels = sorted(all_values)
        label    = _metric_label(metric)
        traces   = []

        for i, (exp, records) in enumerate(all_records.items()):
            groups: dict[str, list[float]] = {}
            for r in records:
                v = r.get(field)
                m = r.get(metric)
                if v is not None and m is not None:
                    groups.setdefault(str(v), []).append(float(m))

            y = [
                float(np.mean(groups[x])) if x in groups else 0.0
                for x in x_labels
            ]
            traces.append({
                "type":          "bar",
                "name":          exp_labels.get(exp, exp),
                "x":             x_labels,
                "y":             y,
                "marker":        {"color": _COLORS[i % len(_COLORS)]},
                "hovertemplate": (
                    f"{field}: %{{x}}<br>"
                    f"Mean {label}: %{{y:.3f}}<extra></extra>"
                ),
            })

        layout = {
            "title":   {"text": f"Mean {label} by {field}  —  Experiment Comparison"},
            "xaxis":   {"title": field},
            "yaxis":   {"title": f"Mean {label}", "range": [0, 1]},
            "barmode": "group",
            "height":  340,
            "margin":  {"t": 50, "b": 80},
            "legend":  {"title": {"text": "Experiment"}},
        }
        return {"data": traces, "layout": layout}


@register_chart("cross_exp")
class CrossExpNumericalChart(BaseChart):
    """numerical 속성 구간 × 메트릭 실험별 multi-line chart."""

    field_types = ("numerical",)

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params      = params or {}
        all_records = params.get("all_records", {})
        metric      = params.get("metric", "recall")
        bins        = max(2, int(params.get("bins", 10)))
        exp_labels  = params.get("experiment_labels", {})

        if not all_records or not field:
            return _empty_figure("No data available")

        # 모든 실험의 필드 값을 합쳐 공유 bin_edges 계산
        all_field_vals: list[float] = [
            float(r[field])
            for records in all_records.values()
            for r in records
            if r.get(field) is not None
        ]
        if not all_field_vals:
            return _empty_figure(f"No data: {field} × {metric}")

        _, bin_edges = np.histogram(np.array(all_field_vals), bins=bins)

        label  = _metric_label(metric)
        traces = []

        for i, (exp, records) in enumerate(all_records.items()):
            pairs = [
                (float(r[field]), float(r[metric]))
                for r in records
                if r.get(field) is not None and r.get(metric) is not None
            ]
            if not pairs:
                continue

            fvals = np.array([p[0] for p in pairs])
            mvals = np.array([p[1] for p in pairs])

            centers: list[float] = []
            means:   list[float] = []
            counts:  list[int]   = []

            for j in range(len(bin_edges) - 1):
                lo, hi  = bin_edges[j], bin_edges[j + 1]
                is_last = j == len(bin_edges) - 2
                mask    = (fvals >= lo) & (fvals <= hi if is_last else fvals < hi)
                n = int(mask.sum())
                if n > 0:
                    centers.append(float((lo + hi) / 2))
                    means.append(float(mvals[mask].mean()))
                    counts.append(n)

            if not centers:
                continue

            traces.append({
                "type":  "scatter",
                "mode":  "lines+markers",
                "name":  exp_labels.get(exp, exp),
                "x":     centers,
                "y":     means,
                "text":  [f"n={c}" for c in counts],
                "hovertemplate": (
                    f"{field}: %{{x:.3f}}<br>"
                    f"Mean {label}: %{{y:.3f}}<br>"
                    "Samples: %{text}<extra></extra>"
                ),
                "line":   {"shape": "spline", "color": _COLORS[i % len(_COLORS)]},
                "marker": {"size": 8},
            })

        if not traces:
            return _empty_figure(f"No data: {field} × {metric}")

        layout = {
            "title":  {
                "text": f"Mean {label} by {field}  —  Experiment Comparison  (bins={bins})"
            },
            "xaxis":  {"title": field},
            "yaxis":  {"title": f"Mean {label}", "range": [0, 1]},
            "height": 340,
            "margin": {"t": 50},
            "legend": {"title": {"text": "Experiment"}},
        }
        return {"data": traces, "layout": layout}
