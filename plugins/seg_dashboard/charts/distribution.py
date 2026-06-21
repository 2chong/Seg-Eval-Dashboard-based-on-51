"""plugins/seg_dashboard/charts/distribution.py — Attribute Distribution Chart."""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure


class AttributeDistributionChart(BaseChart):
    """속성 분포 차트 (records 기반).

    categorical -> bar chart (값별 샘플 수)
    numerical   -> histogram (bins 파라미터로 구간 수 조절)

    params:
      records   : list[dict] -- get_records() 결과
      field     : str        -- 표시할 속성 이름 (build_figure field 인수와 동일)
      bins      : int        -- numerical 구간 수 (기본 10)
    """

    field_types = ("categorical", "numerical")

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params  = params or {}
        records = params.get("records", [])
        bins    = max(2, int(params.get("bins", 10)))

        if not records:
            return _empty_figure("Records not available")
        if not field:
            return _empty_figure("No field selected")

        # 필드 타입 판별: columns 메타 우선, 없으면 값 타입 추론
        columns  = stats.get("columns", {})
        col_type = columns.get(field, {}).get("type")
        if col_type is None:
            sample_val = next((r.get(field) for r in records if r.get(field) is not None), None)
            if sample_val is None:
                return _empty_figure(f"No data for field '{field}'")
            col_type = "numerical" if isinstance(sample_val, (int, float)) else "categorical"

        if col_type == "categorical":
            return self._categorical(field, records)
        if col_type == "numerical":
            return self._numerical(field, records, bins)
        return _empty_figure(f"Unknown field type: {col_type}")

    def _categorical(self, field: str, records: list[dict]) -> dict:
        dist: dict[str, int] = {}
        for r in records:
            val = r.get(field)
            if val is not None:
                dist[str(val)] = dist.get(str(val), 0) + 1

        if not dist:
            return _empty_figure(f"No data for '{field}'")

        labels = list(dist.keys())
        counts = [dist[k] for k in labels]

        trace = {
            "type":   "bar",
            "x":      labels,
            "y":      counts,
            "name":   field,
            "marker": {"color": "steelblue"},
        }
        layout = {
            "title":  {"text": f"Distribution: {field}"},
            "xaxis":  {"title": field},
            "yaxis":  {"title": "Sample count"},
            "height": 280,
            "margin": {"t": 50},
        }
        return {"data": [trace], "layout": layout}

    def _numerical(self, field: str, records: list[dict], bins: int) -> dict:
        values = [float(r[field]) for r in records if r.get(field) is not None]
        if not values:
            return _empty_figure(f"No samples for field '{field}'")

        arr = np.array(values)
        counts, bin_edges = np.histogram(arr, bins=bins)
        x_labels = [
            f"{bin_edges[i]:.3f}-{bin_edges[i+1]:.3f}"
            for i in range(len(bin_edges) - 1)
        ]

        trace = {
            "type":   "bar",
            "x":      x_labels,
            "y":      counts.tolist(),
            "name":   field,
            "marker": {"color": "steelblue"},
        }
        layout = {
            "title":  {"text": f"Distribution: {field}"},
            "xaxis":  {"title": field, "tickangle": 45},
            "yaxis":  {"title": "Sample count"},
            "height": 280,
            "margin": {"t": 50, "b": 100},
        }
        return {"data": [trace], "layout": layout}
