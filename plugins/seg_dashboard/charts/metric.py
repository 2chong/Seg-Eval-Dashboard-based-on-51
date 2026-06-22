"""
plugins/seg_dashboard/charts/metric.py
────────────────────────────────────────
속성별 per-class / 구간별 성능 메트릭 차트.

메트릭 목록은 stats["columns"] (kind=="metric") 에서 동적으로 읽는다.
SUPPORTED_METRICS 상수는 제거됐다 -- 메트릭 추가 시 config.py 만 편집하면 된다.

데이터 소스 (모두 records 기반):
  categorical → records 의 (field_value, metric) 쌍 평균
  numerical   → records 의 (field_value, metric) 쌍을 bins 로 분할 후 평균
"""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure
from .registry import register_chart


def _metric_label(metric: str) -> str:
    return metric.upper() if metric == "f1" else metric.capitalize()


# ─────────────────────────────────────────────────────────────────────────────
# Categorical
# ─────────────────────────────────────────────────────────────────────────────

@register_chart("metric")
class CategoricalMetricChart(BaseChart):
    """categorical 속성 값별 평균 메트릭 bar chart (records 기반).

    예: bd_small_ratio 구간별 / vegetation_ratio 값별 mean recall(또는 다른 메트릭).
    """

    field_types = ("categorical",)

    def build_figure(
        self,
        stats: dict,
        field: str,
        params: dict | None = None,
    ) -> dict:
        params  = params or {}
        metric  = params.get("metric", "recall")
        records = params.get("records", [])

        if not records:
            return _empty_figure("Records not available")

        if field is None:
            return _empty_figure("No field selected")

        groups: dict[str, list[float]] = {}
        for r in records:
            val = r.get(field)
            m   = r.get(metric)
            if val is not None and m is not None:
                groups.setdefault(str(val), []).append(float(m))

        if not groups:
            return _empty_figure(f"No data: {field} × {metric}")

        label = _metric_label(metric)
        traces = [{
            "type": "bar",
            "x": list(groups.keys()),
            "y": [float(np.mean(v)) for v in groups.values()],
            "marker": {"color": "steelblue"},
        }]
        layout = {
            "title": {"text": f"Mean {label} by {field}"},
            "xaxis": {"title": field},
            "yaxis": {"title": f"Mean {label}", "range": [0, 1]},
            "height": 320,
            "margin": {"t": 50},
        }
        return {"data": traces, "layout": layout}


# ─────────────────────────────────────────────────────────────────────────────
# Numerical
# ─────────────────────────────────────────────────────────────────────────────

@register_chart("metric")
class NumericalMetricChart(BaseChart):
    """numerical 속성 구간별 mean 메트릭 추이 line chart (records 기반).

    bins 파라미터 변경만으로 재binning — 런타임 마스크 연산 없음.
    """

    field_types = ("numerical",)

    def build_figure(
        self,
        stats: dict,
        field: str,
        params: dict | None = None,
    ) -> dict:
        params  = params or {}
        metric  = params.get("metric", "recall")
        bins    = max(2, int(params.get("bins", 10)))
        records = params.get("records", [])

        if not records:
            return _empty_figure("Records not available")

        if field is None:
            return _empty_figure("No field selected")

        pairs = [
            (float(r[field]), float(r[metric]))
            for r in records
            if r.get(field) is not None and r.get(metric) is not None
        ]
        if not pairs:
            return _empty_figure(f"No data: {field} × {metric}")

        values = np.array([p[0] for p in pairs])
        mvals  = np.array([p[1] for p in pairs])
        _, bin_edges = np.histogram(values, bins=bins)

        bin_centers: list[float] = []
        bin_means:   list[float] = []
        bin_counts:  list[int]   = []

        for i in range(len(bin_edges) - 1):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            mask = (
                (values >= lo)
                & (values <= hi if i == len(bin_edges) - 2 else values < hi)
            )
            n = int(mask.sum())
            if n > 0:
                bin_centers.append(float((lo + hi) / 2))
                bin_means.append(float(mvals[mask].mean()))
                bin_counts.append(n)

        label = _metric_label(metric)
        trace = {
            "type":  "scatter",
            "mode":  "lines+markers",
            "x":     bin_centers,
            "y":     bin_means,
            "name":  f"Mean {label}",
            "text":  [f"n={c}" for c in bin_counts],
            "hovertemplate": (
                f"{field}: %{{x:.3f}}<br>"
                f"Mean {label}: %{{y:.3f}}<br>"
                "Samples: %{text}<extra></extra>"
            ),
            "line":   {"shape": "spline", "color": "steelblue"},
            "marker": {"size": 8},
        }
        layout = {
            "title": {"text": f"Mean {label} by {field}  (bins={bins})"},
            "xaxis": {"title": field},
            "yaxis": {"title": f"Mean {label}", "range": [0, 1]},
            "height": 300,
            "margin": {"t": 50},
        }
        return {"data": [trace], "layout": layout}


# ── 하위호환 별칭 ──────────────────────────────────────────────────────────────
CategoricalRecallChart = CategoricalMetricChart
NumericalRecallChart   = NumericalMetricChart
