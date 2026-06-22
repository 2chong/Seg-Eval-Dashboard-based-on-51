"""
plugins/seg_dashboard/panels/schema.py
----------------------------------------
(5) Schema & Table Panel

Purpose: Browse data/metric schema and inspect per-sample raw data.
Shows:   Dataset selector + column schema table (overview)
         + experiment selector + per-sample records table (interactive).
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import (
    DatasetSelectorSection,
    SchemaTableSection,
    ExperimentSelectorSection,
    RecordsTableSection,
    SectionLabel,
)


class SchemaPanel(BasePanel):
    PANEL_NAME  = "seg_schema"
    PANEL_LABEL = "(5) Schema & Table"

    SECTIONS = [
        DatasetSelectorSection(),
        SectionLabel("[Overview] Column Schema  |  all columns, experiment-independent"),
        SchemaTableSection(),
        ExperimentSelectorSection(),
        SectionLabel("[Interactive] Per-Sample Records  |  Experiment selector above"),
        RecordsTableSection(),
    ]
