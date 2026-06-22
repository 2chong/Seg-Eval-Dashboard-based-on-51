"""
plugins/seg_dashboard/panels/combined.py
-----------------------------------------
(3) Combined Panel

Purpose: Attribute x metric combined analysis.
         "How does each metric change across attribute values?"
Shows:   Dataset selector + experiment selector
         + metric breakdown (interactive)
         + correlation heatmap (overview).
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import (
    DatasetSelectorSection,
    ExperimentSelectorSection,
    FieldSection,
    CorrelationSection,
    SectionLabel,
)


class CombinedPanel(BasePanel):
    PANEL_NAME  = "seg_combined"
    PANEL_LABEL = "(3) Combined"

    SECTIONS = [
        DatasetSelectorSection(),
        ExperimentSelectorSection(),
        SectionLabel("[Interactive] Metric Breakdown  |  Field / Metric / Bins selection"),
        FieldSection(
            container="attr_sec",
            dist_role=None,
            metric_role="metric",
            kind_filter="attribute",
            label="Metric Breakdown",
        ),
        SectionLabel("[Overview] Attribute-Metric Correlation Heatmap"),
        CorrelationSection(),
    ]
