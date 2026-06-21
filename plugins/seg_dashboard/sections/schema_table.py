"""
plugins/seg_dashboard/sections/schema_table.py
───────────────────────────────────────────────
SchemaTableSection: 컬럼 설명표 (속성명 / 종류 / 타입 / 설명 / 값 범위).

데이터 소스:
  stats["columns"]  (v2 스키마, Phase B+)
  stats["meta"]["field_meta"]  (v1 스키마, 하위호환)
"""

from __future__ import annotations

from .base import PanelSection
from ..charts.table import SchemaTableChart


class SchemaTableSection(PanelSection):
    """컬럼 메타데이터 설명 테이블."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        fig = SchemaTableChart().build_figure(stats)
        panel.plot("schema_table", data=fig["data"], layout=fig["layout"])
