"""
plugins/seg_dashboard/panels/combined.py
-----------------------------------------
(3) Combined Panel

Purpose: Attribute x metric combined analysis.
         "How does each metric change across attribute values?"
Shows:   Dataset selector + experiment selector + metric breakdown + correlation heatmap.
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import (
    DatasetSelectorSection,
    ExperimentSelectorSection,
    MetricBreakdownSection,
    CorrelationSection,
)


class CombinedPanel(BasePanel):
    PANEL_NAME  = "seg_combined"
    PANEL_LABEL = "(3) Combined"

    SECTIONS = [
        DatasetSelectorSection(),
        ExperimentSelectorSection(),
        MetricBreakdownSection(),
        CorrelationSection(),
    ]
