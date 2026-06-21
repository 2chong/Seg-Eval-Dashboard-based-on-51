"""
plugins/seg_dashboard/charts/table.py
───────────────────────────────────────
범용 Plotly table 차트 빌더.

RecordsTableChart  — per-sample 통합 표 (행=샘플, 열=속성+메트릭)
SchemaTableChart   — 컬럼 설명표 (kind / type / description / range)
"""

from __future__ import annotations

from .base import BaseChart, _empty_figure

def _ordered_columns(records: list[dict], columns: dict) -> list[str]:
    """records 의 키를 kind 순서로 정렬한다.

    순서: image_path → attribute(알파벳) → metric(알파벳) → 기타
    columns 메타가 없어도 image_path 는 항상 맨 앞.
    하드코딩된 열 이름 없음 — columns 메타(kind)에서 자동 파생.
    """
    all_keys = list(records[0].keys()) if records else []
    attrs   = sorted(k for k in all_keys if columns.get(k, {}).get("kind") == "attribute")
    metrics = sorted(k for k in all_keys if columns.get(k, {}).get("kind") == "metric")
    others  = sorted(
        k for k in all_keys
        if k != "image_path" and k not in attrs and k not in metrics
    )
    ordered = ["image_path"] if "image_path" in all_keys else []
    ordered += attrs + metrics + others
    return ordered


# ─────────────────────────────────────────────────────────────────────────────
# Records Table
# ─────────────────────────────────────────────────────────────────────────────

class RecordsTableChart(BaseChart):
    """per-sample 통합 테이블 (pandas DataFrame 스타일).

    params:
      records : list[dict]  — get_records() 결과
      columns : dict        — get_columns() 결과 (컬럼 메타, 선택)
    """

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params  = params or {}
        records = params.get("records", [])
        columns = params.get("columns", {})

        if not records:
            return _empty_figure(
                "Records table not yet available.<br>"
                "Re-run precompute_panel_stats.py to generate this view."
            )

        # 컬럼 순서: image_path → attribute → metric → 기타 (kind 기반, 하드코딩 없음)
        ordered = _ordered_columns(records, columns)

        # 헤더: kind 가 있으면 "[A]" 또는 "[M]" 접두사
        def header(col: str) -> str:
            kind = columns.get(col, {}).get("kind", "")
            prefix = {"attribute": "[A] ", "metric": "[M] "}.get(kind, "")
            return prefix + col

        headers = [header(c) for c in ordered]

        # 셀 데이터 (컬럼별 리스트)
        cell_values = []
        for col in ordered:
            col_vals = []
            for r in records:
                v = r.get(col)
                if isinstance(v, float):
                    col_vals.append(f"{v:.4f}")
                elif v is None:
                    col_vals.append("—")
                else:
                    col_vals.append(str(v))
            cell_values.append(col_vals)

        # 행 색상: attribute 컬럼은 파란 계열, metric 은 초록 계열, 나머지 흰색
        def header_color(col: str) -> str:
            kind = columns.get(col, {}).get("kind", "")
            return {"attribute": "#4a7fc1", "metric": "#3a9e6e"}.get(kind, "#555")

        header_colors = [header_color(c) for c in ordered]

        trace = {
            "type": "table",
            "header": {
                "values": headers,
                "fill":   {"color": header_colors},
                "font":   {"color": "white", "size": 11},
                "align":  "left",
                "height": 30,
            },
            "cells": {
                "values": cell_values,
                "fill":   {"color": "white"},
                "align":  "left",
                "font":   {"size": 10},
                "height": 24,
            },
        }

        n = len(records)
        layout = {
            "title":  {"text": f"Sample Records  (n={n})  [A]=attribute  [M]=metric"},
            "height": min(800, 100 + 26 * n),
            "margin": {"t": 50, "b": 20, "l": 10, "r": 10},
        }

        return {"data": [trace], "layout": layout}


# ─────────────────────────────────────────────────────────────────────────────
# Schema Table
# ─────────────────────────────────────────────────────────────────────────────

class SchemaTableChart(BaseChart):
    """컬럼 메타데이터 설명표 — stats["columns"] 에서 읽는다."""

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        columns = stats.get("columns", {})
        if not columns:
            return _empty_figure(
                "Schema (columns) data not yet available.<br>"
                "Re-run precompute_panel_stats.py to generate this table."
            )
        return self._from_columns(columns)

    def _from_columns(self, columns: dict) -> dict:
        rows = []
        for name, meta in columns.items():
            kind  = meta.get("kind", "—")
            ctype = meta.get("type", "—")
            desc  = meta.get("description", "—")

            if ctype == "categorical":
                rng = ", ".join(str(v) for v in (meta.get("values") or []))
            elif ctype == "numerical":
                r = meta.get("range")
                rng = f"{r[0]} – {r[1]}" if r else "—"
            else:
                rng = "—"

            unit = meta.get("unit", "")
            rows.append([name, kind, ctype, desc, rng, unit])

        return self._render_table(
            rows,
            headers=["Name", "Kind", "Type", "Description", "Values / Range", "Unit"],
        )

    @staticmethod
    def _render_table(rows: list[list], headers: list[str]) -> dict:
        if not rows:
            return _empty_figure("No schema data available")

        cols = list(zip(*rows))
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
                "fill":   {
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
            "title":  {"text": "Column Schema"},
            "height": max(200, 80 + 32 * len(rows)),
            "margin": {"t": 50, "b": 20, "l": 10, "r": 10},
        }
        return {"data": [trace], "layout": layout}
