"""
plugins/seg_dashboard/panels/data_analysis.py
----------------------------------------------
(1) Data Analysis Panel

Purpose: Analyse data attributes (independent of predictions/evaluation).
Shows:   Dataset selector + attribute summary + distribution histograms
         + dataset chips multi-select + dataset distribution comparison.

Comparison axis: DATASETS (not experiments).
Attribute values (brightness, complexity, time, count, density) are
per-image and experiment-independent — the meaningful comparison is
"how does this attribute differ across datasets?", not across models.

State keys:
  "selected_datasets" -- list of currently selected dataset keys
                         (managed by MultiSelectMixin; default: all)
  "attr_sec.*"        -- field / bins (managed by FieldSection + BasePanel)
"""

from __future__ import annotations

from ..framework import BasePanel, MultiSelectMixin
from ..sections import (
    DatasetSelectorSection,
    AttributeSummarySection,
    FieldSection,
    DatasetCompareSection,
    MultiSelectSection,
    dataset_items,
    dataset_labels,
    SectionLabel,
)


class DataAnalysisPanel(MultiSelectMixin, BasePanel):
    PANEL_NAME  = "seg_data_analysis"
    PANEL_LABEL = "(1) Data Analysis"

    MULTI_SELECTS = [
        ("selected_datasets", dataset_items),
    ]

    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "selected_datasets": None,
    }

    SECTIONS = [
        DatasetSelectorSection(),
        SectionLabel("[Overview] Attribute Summary  |  all attributes, experiment-independent"),
        AttributeSummarySection(kind_filter="attribute"),
        SectionLabel("[Interactive] Attribute Distribution  |  Field / Bins selection"),
        FieldSection(
            container="attr_sec",
            dist_role="distribution",
            metric_role=None,
            kind_filter="attribute",
            label="Attribute Distribution",
        ),
        SectionLabel("[Selection] Datasets  |  controls which datasets appear in the comparison below"),
        MultiSelectSection(
            "selected_datasets",
            dataset_items,
            label="Datasets",
            labels_fn=dataset_labels,
        ),
        DatasetCompareSection(),
    ]
