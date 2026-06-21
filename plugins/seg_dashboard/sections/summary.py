"""plugins/seg_dashboard/sections/summary.py -- Attribute Summary Section."""

from __future__ import annotations

from .base import PanelSection
from ..charts import AttributeSummaryChart
from ..stats import get_records, get_columns


class AttributeSummarySection(PanelSection):
    """전체 속성 필드의 통계 + 설명을 하나의 테이블로 표시.

    데이터 소스: records (단일 소스) + columns 메타의 description.
    kind_filter: "attribute" 로 설정하면 attribute 종류 필드만 표시.
    """

    def __init__(self, kind_filter: str | None = "attribute") -> None:
        self.kind_filter = kind_filter

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        experiment = state.get("experiment")
        records    = get_records(stats, experiment)
        columns    = get_columns(stats)

        # kind_filter 적용 — columns 메타에서 파생
        if self.kind_filter is not None and columns:
            filtered_cols = {
                k: v for k, v in columns.items()
                if v.get("kind") == self.kind_filter
            }
        else:
            filtered_cols = columns

        # AttributeSummaryChart 에 records + 필터된 columns 전달
        fig = AttributeSummaryChart().build_figure(
            {**stats, "columns": filtered_cols},
            params={"records": records},
        )
        panel.plot("summary_table", data=fig["data"], layout=fig["layout"])
