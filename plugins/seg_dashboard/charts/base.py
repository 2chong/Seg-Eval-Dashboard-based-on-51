"""
plugins/seg_dashboard/charts/base.py
──────────────────────────────────────
BaseChart 공통 인터페이스 + 빈 figure 유틸리티.

새 차트를 추가하는 방법
  1. BaseChart 를 상속한 클래스를 charts/ 아래 새 파일에 구현한다.
  2. build_figure() 가 항상 {"data": [...], "layout": {...}} dict 를 반환하도록 한다.
  3. charts/__init__.py 에 임포트 한 줄을 추가한다.
"""

from __future__ import annotations


class BaseChart:
    """Plotly figure 빌더 공통 인터페이스."""

    field_types: tuple = ()

    def is_applicable(self, field_type: str) -> bool:
        return field_type in self.field_types

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        raise NotImplementedError


def _empty_figure(message: str) -> dict:
    """데이터가 없거나 아직 미구현인 차트에 표시할 빈 figure."""
    return {
        "data": [],
        "layout": {
            "annotations": [{
                "text": message,
                "x": 0.5, "y": 0.5,
                "xref": "paper", "yref": "paper",
                "showarrow": False,
                "font": {"size": 13},
            }],
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
        },
    }
