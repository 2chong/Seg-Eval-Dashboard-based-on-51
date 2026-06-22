"""
plugins/seg_dashboard/sections/attribute.py
────────────────────────────────────────────
AttributeSection — 하위 호환 팩토리. FieldSection 을 반환한다.

새 코드에서는 FieldSection 을 직접 사용하는 것이 권장된다:

    from ..sections import FieldSection
    FieldSection(
        container="attr_sec",
        dist_role="distribution",
        metric_role="metric",       # show_metric=True
        # metric_role=None,         # show_metric=False
        kind_filter="attribute",
        label="Attribute Distribution",
    )
"""

from __future__ import annotations

from .field_section import FieldSection


def AttributeSection(
    show_metric: bool = True,
    kind_filter: str | None = "attribute",
) -> FieldSection:
    """FieldSection 팩토리 — 하위 호환용. 새 코드는 FieldSection 을 직접 쓰세요."""
    return FieldSection(
        container="attr_sec",
        dist_role="distribution",
        metric_role="metric" if show_metric else None,
        kind_filter=kind_filter,
        label="Attribute Distribution",
    )
