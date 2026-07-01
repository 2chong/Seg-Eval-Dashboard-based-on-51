"""
plugins/seg_dashboard/charts/spatial_scatter.py
─────────────────────────────────────────────────
지리 산점도 차트 — centroid_lon/lat 를 x/y 로, 선택 필드 값을 marker color 로 표시.

커스텀 Plotly 직접 개발 (FiftyOne 네이티브 Map 미사용).
  - mapbox 토큰 / 인터넷 불필요, 완전 오프라인 동작.
  - 비-디스패치 차트 (EXTENDING 레시피 6-B).
  - FiftyOne import 금지 (numpy 전용).
  - {"data": [...], "layout": {...}} 반환.
  - 데이터 없으면 _empty_figure(msg) 반환.
"""

from __future__ import annotations

from .base import BaseChart, _empty_figure

_PLACEHOLDER = (
    "Spatial data not available.<br>"
    "manifest.json 에 patch_id / geo 블록이 있는 데이터셋에서만 표시됩니다.<br>"
    "Re-run make regen-stats to generate spatial block."
)


class GeoScatterChart(BaseChart):
    """경위도 산점도 (lon=x, lat=y, color=선택 필드값).

    points: [{"image_path","row","col","lon","lat"}]  — spatial 블록
    records: [{"image_path", field: value, ...}]     — records 단일 소스

    두 리스트를 image_path 로 join 한다.
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

        rec_by_path = {r["image_path"]: r for r in records}

        lons, lats, colors, hover_texts = [], [], [], []
        for pt in points:
            rec = rec_by_path.get(pt["image_path"], {})
            val = rec.get(field)
            if val is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            lons.append(pt["lon"])
            lats.append(pt["lat"])
            colors.append(v)
            patch_name = pt["image_path"].split("/")[-1]
            hover_texts.append(
                f"patch: {patch_name}<br>"
                f"lon: {pt['lon']:.6f}  lat: {pt['lat']:.6f}<br>"
                f"{field}: {v:.4f}"
            )

        if not lons:
            return _empty_figure(f"'{field}' 값이 없습니다.")

        trace = {
            "type": "scattergl",
            "mode": "markers",
            "x": lons,
            "y": lats,
            "text": hover_texts,
            "hovertemplate": "%{text}<extra></extra>",
            "marker": {
                "color": colors,
                "colorscale": "RdYlGn",
                "showscale": True,
                "colorbar": {"title": field},
                "size": 8,
                "opacity": 0.8,
                "line": {"width": 0.5, "color": "rgba(0,0,0,0.3)"},
            },
        }

        lon_range = [min(lons) - 0.001, max(lons) + 0.001]
        lat_range = [min(lats) - 0.001, max(lats) + 0.001]

        layout = {
            "title": {"text": f"Geo Scatter — {field}"},
            "xaxis": {
                "title": "Longitude",
                "range": lon_range,
                "constrain": "domain",
            },
            "yaxis": {
                "title": "Latitude",
                "range": lat_range,
                "scaleanchor": "x",   # 등축 비율 유지
                "scaleratio": 1,
            },
            "height": 450,
            "margin": {"t": 50, "b": 60, "l": 70, "r": 20},
        }

        return {"data": [trace], "layout": layout}
