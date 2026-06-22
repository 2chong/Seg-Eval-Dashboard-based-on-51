"""
plugins/seg_dashboard/sections/metric_breakdown.py
────────────────────────────────────────────────────
MetricBreakdownSection — 하위 호환 팩토리. FieldSection 을 반환한다.

새 코드에서는 FieldSection 을 직접 사용하는 것이 권장된다:

    from ..sections import FieldSection
    FieldSection(
        container="attr_sec",
        dist_role=None,
        metric_role="metric",
        kind_filter="attribute",
        label="Metric Breakdown",
    )
"""

from __future__ import annotations

from .field_section import FieldSection


def MetricBreakdownSection() -> FieldSection:
    """FieldSection 팩토리 — 하위 호환용. 새 코드는 FieldSection 을 직접 쓰세요."""
    return FieldSection(
        container="attr_sec",
        dist_role=None,
        metric_role="metric",
        kind_filter="attribute",
        label="Metric Breakdown",
    )
