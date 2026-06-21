"""
plugins/seg_dashboard/sections/records_table.py
─────────────────────────────────────────────────
RecordsTableSection: per-sample 통합 테이블 (pandas 같은 뷰).

데이터 요구사항:
  stats["experiments"][exp]["records"] 배열이 있어야 한다 (Phase B+).
"""

from __future__ import annotations

from .base import PanelSection
from ..charts.table import RecordsTableChart
from ..stats import get_records

_PLACEHOLDER = (
    "Records table not yet available.<br>"
    "Re-run precompute_panel_stats.py to generate this view."
)


class RecordsTableSection(PanelSection):
    """per-sample 통합 표. 행=샘플, 열=속성+메트릭."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        records = get_records(stats, state.get("experiment"))
        columns = stats.get("columns", {})
        fig = RecordsTableChart().build_figure(
            stats,
            params={"records": records, "columns": columns},
        )
        panel.plot("records_table", data=fig["data"], layout=fig["layout"])
