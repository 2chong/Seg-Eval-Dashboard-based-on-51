"""
plugins/seg_dashboard/charts/summary.py
─────────────────────────────────────────
속성 요약 테이블: attribute 필드의 통계 + 설명을 한눈에.

데이터 소스:
  - stats["columns"] 의 description (v2 스키마)
  - records 에서 min/max/mean/std/mode 계산
"""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure


class AttributeSummaryChart(BaseChart):
    """모든 속성 필드의 요약을 Plotly table 로 반환."""

    field_types = ("categorical", "numerical")

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params  = params or {}
        records = params.get("records", [])
        columns = stats.get("columns", {})

        # attribute 컬럼만 추출
        attr_cols = [
            name for name, meta in columns.items()
            if meta.get("kind") == "attribute"
        ]
        if not attr_cols and records:
            # columns 메타 없으면 records 키에서 추론 (하위호환)
            metric_hint = {k for k, v in columns.items() if v.get("kind") == "metric"}
            attr_cols = [
                k for k in records[0].keys()
                if k != "image_path" and k not in metric_hint
            ]

        if not attr_cols:
            return _empty_figure("No attribute fields found")

        headers = ["Field", "Type", "Description", "Values / Range", "Mean / Mode", "N"]
        rows: list[list] = []

        for fname in attr_cols:
            col_meta = columns.get(fname, {})
            ftype    = col_meta.get("type", "—")
            desc     = col_meta.get("description", "—")

            # records 에서 통계 계산
            if records:
                vals = [r.get(fname) for r in records if r.get(fname) is not None]
            else:
                vals = []

            if ftype == "numerical" or (
                ftype == "—" and vals and isinstance(vals[0], (int, float))
            ):
                ftype = "numerical"
                if vals:
                    arr = np.array([float(v) for v in vals])
                    val_range = f"{arr.min():.3f} - {arr.max():.3f}"
                    mean_val  = f"{arr.mean():.3f}  (sigma={arr.std():.3f})"
                    n = len(vals)
                else:
                    r = col_meta.get("range")
                    val_range = f"{r[0]} - {r[1]}" if r else "-"
                    mean_val  = "-"
                    n = 0

            elif ftype == "categorical" or (ftype == "—" and vals):
                ftype = "categorical"
                if vals:
                    dist: dict[str, int] = {}
                    for v in vals:
                        dist[str(v)] = dist.get(str(v), 0) + 1
                    unique_vals = list(dist.keys())
                    val_range   = ", ".join(str(v) for v in unique_vals[:5])
                    if len(unique_vals) > 5:
                        val_range += f"  ... (+{len(unique_vals) - 5})"
                    mode     = max(dist, key=dist.get)
                    mean_val = f"mode: {mode}"
                    n        = sum(dist.values())
                else:
                    vlist = col_meta.get("values") or []
                    val_range = ", ".join(str(v) for v in vlist)
                    mean_val  = "-"
                    n         = 0
            else:
                val_range = "-"
                mean_val  = "-"
                n         = 0

            rows.append([fname, ftype, desc, val_range, mean_val, n])

        if not rows:
            return _empty_figure("No attribute data available")

        cols = list(zip(*rows))   # transpose rows -> columns for Plotly table

        trace = {
            "type": "table",
            "header": {
                "values": headers,
                "fill":   {"color": "#4a7fc1"},
                "font":   {"color": "white", "size": 12},
                "align":  "left",
                "height": 32,
            },
            "cells": {
                "values": list(cols),
                "fill": {
                    "color": [
                        ["#f0f4fa" if i % 2 == 0 else "white" for i in range(len(rows))]
                    ] * len(headers)
                },
                "align": "left",
                "font":  {"size": 11},
                "height": 28,
            },
        }
        layout = {
            "title":  {"text": "Attribute Summary"},
            "height": max(200, 80 + 32 * len(rows)),
            "margin": {"t": 50, "b": 20, "l": 10, "r": 10},
        }
        return {"data": [trace], "layout": layout}
