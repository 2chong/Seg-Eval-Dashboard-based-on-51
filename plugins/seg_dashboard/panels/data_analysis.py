"""
plugins/seg_dashboard/panels/data_analysis.py
----------------------------------------------
(1) Data Analysis Panel

Purpose: Analyse data attributes (independent of predictions/evaluation).
Shows:   Dataset selector + attribute summary table + distribution histograms.
No experiment selector -- attributes are experiment-independent.
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import DatasetSelectorSection, AttributeSummarySection, AttributeSection


class DataAnalysisPanel(BasePanel):
    PANEL_NAME  = "seg_data_analysis"
    PANEL_LABEL = "(1) Data Analysis"

    SECTIONS = [
        DatasetSelectorSection(),
        AttributeSummarySection(kind_filter="attribute"),
        AttributeSection(show_metric=False, kind_filter="attribute"),
    ]
