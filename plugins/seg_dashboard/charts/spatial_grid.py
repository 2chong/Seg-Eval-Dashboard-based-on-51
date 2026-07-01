"""
plugins/seg_dashboard/charts/spatial_grid.py
─────────────────────────────────────────────
격자 히트맵 차트 — 패치 격자 (row x col) 위에 선택 필드 평균값을 색으로 표시.

비-디스패치 차트 (EXTENDING 레시피 6-B).
  - FiftyOne import 금지 (numpy 전용)
  - {"data": [...], "layout": {...}} 반환
  - 데이터 없으면 _empty_figure(msg) 반환
"""

from __future__ import annotations

import numpy as np

from .base import BaseChart, _empty_figure

_PLACEHOLDER = (
    "Spatial data not available.<br>"
    "manifest.json 에 patch_id / geo 블록이 있는 데이터셋에서만 표시됩니다.<br>"
    "Re-run make regen-stats to generate spatial block."
)


class GridHeatmapChart(BaseChart):
    """패치 격자 (row x col) 히트맵.

    points: [{"image_path","row","col","lon","lat"}]  — spatial 블록
    records: [{"image_path", field: value, ...}]     — records 단일 소스

    두 리스트를 image_path 로 join 해 z-매트릭스를 채운다.
    값이 없는 셀은 NaN (회색).
    """

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params = params or {}
        spatial = params.get("spatial", {})
        records = params.get("records", [])

        if not spatial or not spatial.get("has_geo"):
            return _empty_figure(_PLACEHOLDER)
        if not field:
            return _empty_figure("color-by 필드를 선택하세요.")

        points = spatial.get("points", [])
        if not points:
            return _empty_figure("points 데이터가 없습니다.")

        # records 를 path 로 인덱싱
        rec_by_path = {r["image_path"]: r for r in records}

        # 격자 범위 결정
        rows = [p["row"] for p in points]
        cols = [p["col"] for p in points]
        row_min, row_max = min(rows), max(rows)
        col_min, col_max = min(cols), max(cols)
        n_rows = row_max - row_min + 1
        n_cols = col_max - col_min + 1

        z = np.full((n_rows, n_cols), float("nan"))
        patch_ids: list[list[str]] = [[""] * n_cols for _ in range(n_rows)]

        for pt in points:
            rec = rec_by_path.get(pt["image_path"], {})
            val = rec.get(field)
            if val is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            r = pt["row"] - row_min
            c = pt["col"] - col_min
            z[r][c] = v
            patch_ids[r][c] = pt["image_path"].split("/")[-1]  # 파일명만

        if np.all(np.isnan(z)):
            return _empty_figure(f"'{field}' 값이 없습니다.")

        # y 축: row 번호 (위→아래 = 작은 row→큰 row)
        y_labels = [str(row_min + i) for i in range(n_rows)]
        x_labels = [str(col_min + j) for j in range(n_cols)]

        trace = {
            "type": "heatmap",
            "z": z.tolist(),
            "x": x_labels,
            "y": y_labels,
            "colorscale": "RdYlGn",
            "showscale": True,
            "hovertemplate": (
                "row: <b>%{y}</b>  col: <b>%{x}</b><br>"
                f"{field}: <b>%{{z:.4f}}</b>"
                "<extra></extra>"
            ),
            "connectgaps": False,
        }

        layout = {
            "title": {"text": f"Grid Heatmap — {field}"},
            "xaxis": {"title": "col", "type": "category"},
            "yaxis": {"title": "row", "type": "category", "autorange": "reversed"},
            "height": max(300, 60 + 20 * n_rows),
            "margin": {"t": 50, "b": 60, "l": 60},
        }

        return {"data": [trace], "layout": layout}
