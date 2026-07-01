"""
plugins/seg_dashboard/sections/spatial.py
───────────────────────────────────────────
공간 분석 섹션 2종.

SpatialFieldSection
  - color-by 필드 드롭다운 (numerical 속성 + 메트릭)
  - 격자 히트맵 (GridHeatmapChart)
  - 지리 산점도 (GeoScatterChart)
  - spatial 블록 없으면 placeholder 표시 (graceful degradation)

MoransISection
  - Moran's I 가로 막대 차트 (MoransIChart)
  - 선택 UI 없이 전체 필드 한눈에 표시
  - spatial 블록 없으면 placeholder 표시

렌더 패턴: AttrMetricCompareSection 과 동일.
  - 드롭다운·차트 모두 grp.plot()/grp.enum() 으로 컨테이너 안에 배치
  - 컨테이너 이름 "spatial_sec" — state 키 "spatial_sec.field" 와 일치
  - panel.define_property("spatial_sec", grp) 로 최종 등록
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None  # type: ignore[assignment]

from .base import PanelSection
from ..charts import GridHeatmapChart, GeoScatterChart, MoransIChart
from ..charts.base import _empty_figure
from ..framework.widgets import add_dropdown
from ..stats import get_records, get_spatial_stats, get_columns, list_attributes, list_metrics

_CONTAINER = "spatial_sec"

_NO_SPATIAL_MSG = (
    "Spatial data not available.<br>"
    "manifest.json 에 patch_id / geo 블록이 있는 데이터셋에서만 표시됩니다.<br>"
    "Re-run: make regen-stats DS=&lt;dataset&gt;"
)


class SpatialFieldSection(PanelSection):
    """격자 히트맵 + 지리 산점도 — color-by 필드 드롭다운 포함.

    state 키: "spatial_sec.field" (컨테이너 "spatial_sec" 안의 "field")
    """

    def render(
        self,
        panel,
        stats: dict,
        state: dict,
        callbacks: dict | None = None,
    ) -> None:
        if types is None:
            return

        callbacks = callbacks or {}
        experiment = state.get("experiment")

        spatial = get_spatial_stats(stats, experiment)
        records = get_records(stats, experiment)
        columns = get_columns(stats)

        # color-by 후보: numerical 속성 + 메트릭
        attr_fields  = list_attributes(stats)
        metric_fields = list_metrics(stats)
        numerical_fields = [
            f for f in [*metric_fields, *attr_fields]
            if columns.get(f, {}).get("type") == "numerical"
        ]

        grp = types.Object()

        # ── 좌표 없는 데이터셋 → placeholder (crash 없음) ─────────────────────
        if not spatial or not spatial.get("has_geo"):
            fig = _empty_figure(_NO_SPATIAL_MSG)
            grp.plot("spatial_no_data", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Spatial Distribution",
                view=types.ObjectView(),
            )
            return

        # ── color-by 드롭다운 ─────────────────────────────────────────────────
        current_field = state.get(f"{_CONTAINER}.field") or (
            numerical_fields[0] if numerical_fields else None
        )
        if current_field not in numerical_fields and numerical_fields:
            current_field = numerical_fields[0]

        if numerical_fields:
            # 컨테이너 안에서 상대 키 "field" 사용 → state 경로: "spatial_sec.field"
            add_dropdown(
                grp, "field",
                numerical_fields,
                label="Color-by Field (metric / attribute)",
                default=current_field,
                on_change=callbacks.get("spatial_field"),
            )

        params = {"spatial": spatial, "records": records}

        # ── 격자 히트맵 ───────────────────────────────────────────────────────
        grid_fig = GridHeatmapChart().build_figure(
            stats, field=current_field, params=params
        )
        grp.plot("grid_heatmap", data=grid_fig["data"], layout=grid_fig["layout"])

        # ── 지리 산점도 ───────────────────────────────────────────────────────
        scatter_fig = GeoScatterChart().build_figure(
            stats, field=current_field, params=params
        )
        grp.plot("geo_scatter", data=scatter_fig["data"], layout=scatter_fig["layout"])

        panel.define_property(
            _CONTAINER, grp,
            label="Spatial Distribution",
            view=types.ObjectView(),
        )


class MoransISection(PanelSection):
    """Moran's I 공간자기상관 지수 막대 차트 섹션.

    선택 없이 전체 필드를 한눈에 표시한다.
    spatial 블록 없으면 placeholder (graceful degradation).
    """

    def render(
        self,
        panel,
        stats: dict,
        state: dict,
        callbacks: dict | None = None,
    ) -> None:
        experiment = state.get("experiment")
        spatial = get_spatial_stats(stats, experiment)

        params = {"spatial": spatial}
        fig = MoransIChart().build_figure(stats, params=params)
        panel.plot("morans_i_chart", data=fig["data"], layout=fig["layout"])
