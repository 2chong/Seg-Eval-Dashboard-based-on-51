"""plugins/seg_dashboard/sections/section_label.py
Extensible UI grouping primitive -- read-only section header.

Usage in a panel's SECTIONS list:

    SECTIONS = [
        DatasetSelectorSection(),
        SectionLabel("[Overview] Attribute Summary"),
        AttributeSummarySection(),
        SectionLabel("[Interactive] Field / Bins Selection"),
        AttributeSection(),
    ]

Convention for label text:
  "[Overview]"     -- chart is independent of dropdown selections
  "[Interactive]"  -- chart responds to the dropdown/slider selections listed
  "[Selection]"    -- UI controls that filter the sections below

Design rules:
  - Use unique label text within each panel (duplicate text -> duplicate widget ID).
  - SectionLabel has no state keys and no callback.
  - Extensible: to add new label styles, subclass SectionLabel and override render().
"""

from __future__ import annotations

from .base import PanelSection


class SectionLabel(PanelSection):
    """Read-only markdown header that visually separates panel sections into groups."""

    def __init__(self, text: str) -> None:
        self._text = text

    def render(self, panel, stats, state, callbacks=None) -> None:
        safe_id = "_lbl_" + "".join(
            c if c.isalnum() else "_" for c in self._text
        )[:36]
        panel.md(f"**{self._text}**", name=safe_id)


class SampleCountSection(PanelSection):
    """현재 선택된 데이터셋의 총 패치 수를 표시한다."""

    def render(self, panel, stats, state, callbacks=None) -> None:
        if not stats:
            return
        n = stats.get("meta", {}).get("num_samples")
        if n is None:
            return
        panel.md(f"**Total: {n:,} patches**", name="_sample_count")
