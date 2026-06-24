"""plugins/seg_dashboard/charts/dataset_compare.py
Dataset cross-comparison distribution charts.

선택된 속성(field)의 분포를 모든 데이터셋에 걸쳐 비교해 보여준다.
데이터셋마다 샘플 수가 다를 수 있으므로 y축을 비율(proportion)로 정규화한다.

  categorical -> grouped bar         (x=속성값, y=proportion, trace=dataset)
  numerical   -> line+marker curves  (x=bin 중심값, y=proportion, trace=dataset)

params:
  all_records    : dict[str, list[dict]]  — {dataset_key: records}
  dataset_labels : dict[str, str]         — {dataset_key: 표시 이름}
  bins           : int  (numerical 전용, 기본 10)
"""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure
from .registry import register_chart
from ._common import _COLORS


@register_chart("dataset_compare")
class DatasetCompareCategoricalChart(BaseChart):
    """categorical 속성 값별 비율 grouped bar — 데이터셋 비교."""

    field_types = ("categorical",)

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params         = params or {}
        all_records    = params.get("all_records", {})
        dataset_labels = params.get("dataset_labels", {})

        if not all_records or not field:
            return _empty_figure("No data available")

        all_values: set[str] = set()
        for records in all_records.values():
            for r in records:
                v = r.get(field)
                if v is not None:
                    all_values.add(str(v))

        if not all_values:
            return _empty_figure(f"No data for field '{field}'")

        x_labels = sorted(all_values)
        traces   = []

        for i, (ds_key, records) in enumerate(all_records.items()):
            counts: dict[str, int] = {}
            for r in records:
                v = r.get(field)
                if v is not None:
                    counts[str(v)] = counts.get(str(v), 0) + 1

            total = sum(counts.values()) or 1
            y     = [counts.get(x, 0) / total for x in x_labels]
            ds_label = dataset_labels.get(ds_key, ds_key)
            hover = [
                f"<b>{ds_label}</b><br>"
                f"{field}: {x}<br>"
                f"Proportion: {counts.get(x, 0) / total:.1%}<br>"
                f"Count: {counts.get(x, 0)}"
                for x in x_labels
            ]
            traces.append({
                "type":          "bar",
                "name":          dataset_labels.get(ds_key, ds_key),
                "x":             x_labels,
                "y":             y,
                "marker":        {"color": _COLORS[i % len(_COLORS)]},
                "text":          hover,
                "hovertemplate": "%{text}<extra></extra>",
            })

        exp_label = params.get("experiment_label")
        title = f"Distribution Comparison: {field}"
        if exp_label:
            title += f"  [{exp_label}]"
        layout = {
            "title":   {"text": title},
            "xaxis":   {"title": field},
            "yaxis":   {"title": "Proportion", "tickformat": ".0%"},
            "barmode": "group",
            "height":  320,
            "margin":  {"t": 50, "b": 60},
            "legend":  {"title": {"text": "Dataset"}},
        }
        return {"data": traces, "layout": layout}


@register_chart("dataset_compare")
class DatasetCompareNumericalChart(BaseChart):
    """numerical 속성 구간별 비율 line curve — 데이터셋 비교.

    막대 대신 라인+마커 곡선을 사용해 여러 데이터셋이 겹치지 않게 한다.
    x축은 bin 중심값(numeric), hover 텍스트에 bin 구간 표시.
    """

    field_types = ("numerical",)

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params         = params or {}
        all_records    = params.get("all_records", {})
        dataset_labels = params.get("dataset_labels", {})
        bins           = max(2, int(params.get("bins", 10)))

        if not all_records or not field:
            return _empty_figure("No data available")

        # 공유 bin_edges — 모든 데이터셋 값을 합쳐 전체 범위 결정
        all_vals: list[float] = [
            float(r[field])
            for records in all_records.values()
            for r in records
            if r.get(field) is not None
        ]
        if not all_vals:
            return _empty_figure(f"No data for field '{field}'")

        _, bin_edges = np.histogram(np.array(all_vals), bins=bins)
        # bin 중심값 (x축 numeric) + bin 구간 문자열 (hover용)
        centers  = [
            float((bin_edges[j] + bin_edges[j + 1]) / 2)
            for j in range(len(bin_edges) - 1)
        ]
        x_labels = [
            f"{bin_edges[j]:.3f}-{bin_edges[j + 1]:.3f}"
            for j in range(len(bin_edges) - 1)
        ]

        traces = []
        for i, (ds_key, records) in enumerate(all_records.items()):
            values = [float(r[field]) for r in records if r.get(field) is not None]
            if not values:
                continue

            counts, _ = np.histogram(np.array(values), bins=bin_edges)
            total      = len(values) or 1
            y          = (counts / total).tolist()
            ds_label   = dataset_labels.get(ds_key, ds_key)
            hover      = [
                f"<b>{ds_label}</b><br>"
                f"{field}: {x_labels[j]}<br>"
                f"Proportion: {y[j]:.1%}<br>"
                f"Count: {counts[j]}"
                for j in range(len(x_labels))
            ]
            traces.append({
                "type":          "scatter",
                "mode":          "lines+markers",
                "name":          dataset_labels.get(ds_key, ds_key),
                "x":             centers,
                "y":             y,
                "line":          {"shape": "spline", "color": _COLORS[i % len(_COLORS)]},
                "marker":        {"size": 6},
                "text":          hover,
                "hovertemplate": "%{text}<extra></extra>",
            })

        if not traces:
            return _empty_figure(f"No data for field '{field}'")

        exp_label = params.get("experiment_label")
        title = f"Distribution Comparison: {field}  (bins={bins})"
        if exp_label:
            title += f"  [{exp_label}]"
        layout = {
            "title":  {"text": title},
            "xaxis":  {"title": field},
            "yaxis":  {"title": "Proportion", "tickformat": ".0%"},
            "height": 320,
            "margin": {"t": 50, "b": 60},
            "legend": {"title": {"text": "Dataset"}},
        }
        return {"data": traces, "layout": layout}
