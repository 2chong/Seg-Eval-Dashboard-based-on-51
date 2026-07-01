"""
plugins/seg_dashboard/panels/spatial.py
─────────────────────────────────────────
(6) Spatial Panel

Purpose: 패치의 공간 위치 기반 분포 + 공간자기상관 분석.
         "모델이 특정 지역에서 집중적으로 실패하는가?"
         "건물 밀도 같은 속성이 공간적으로 군집하는가?"

Shows:   Dataset selector + Experiment selector
         + Spatial Distribution (격자 히트맵 + 지리 산점도) — color-by field
         + Moran's I (공간자기상관 지수 막대 차트)

manifest.json 에 geo/patch_id 가 없는 데이터셋은 placeholder 표시 (graceful degradation).
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import (
    DatasetSelectorSection,
    ExperimentSelectorSection,
    SpatialFieldSection,
    MoransISection,
    SectionLabel,
)
from ..stats import get_spatial_stats, list_metrics, list_attributes, get_columns


class SpatialPanel(BasePanel):
    PANEL_NAME  = "seg_6_spatial"
    PANEL_LABEL = "(6) Spatial"

    # spatial_sec.field: color-by 드롭다운 상태 키
    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "spatial_sec.field": "",
    }

    SECTIONS = [
        DatasetSelectorSection(),
        ExperimentSelectorSection(),
        SectionLabel(
            "[Spatial] Grid Heatmap & Geo Scatter  |  color-by field"
        ),
        SpatialFieldSection(),
        SectionLabel(
            "[Index] Moran's I — Spatial Autocorrelation"
        ),
        MoransISection(),
    ]

    def on_load(self, ctx) -> None:
        """BasePanel.on_load 에 spatial_sec.field 초기화를 추가한다."""
        super().on_load(ctx)

        # spatial_sec.field: 첫 번째 메트릭으로 초기화
        dataset = ctx.panel.get_state("dataset")
        from ..stats import load_stats
        stats = load_stats(dataset)
        if not stats:
            return

        spatial_field = ctx.panel.get_state("spatial_sec.field")
        if not spatial_field:
            metrics = list_metrics(stats)
            columns = get_columns(stats)
            attrs = list_attributes(stats)
            numerical_fields = [
                f for f in [*metrics, *attrs]
                if columns.get(f, {}).get("type") == "numerical"
            ]
            if numerical_fields:
                ctx.panel.set_state("spatial_sec.field", numerical_fields[0])

    def on_change_dataset(self, ctx) -> None:
        """BasePanel 의 콜백을 오버라이드해 spatial_sec.field 도 초기화."""
        super().on_change_dataset(ctx)
        v = ctx.params.get("value")
        if v is None:
            return
        from ..stats import load_stats
        stats = load_stats(v)
        if not stats:
            return
        metrics = list_metrics(stats)
        columns = get_columns(stats)
        attrs = list_attributes(stats)
        numerical_fields = [
            f for f in [*metrics, *attrs]
            if columns.get(f, {}).get("type") == "numerical"
        ]
        if numerical_fields:
            ctx.panel.set_state("spatial_sec.field", numerical_fields[0])

    def on_change_spatial_field(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("spatial_sec.field", v)

    def _extra_callbacks(self) -> dict:
        return {"spatial_field": self.on_change_spatial_field}
