"""
plugins/seg_dashboard/panels/evaluation.py
-------------------------------------------
(2) Evaluation Panel

Purpose: Analyse evaluation results for the selected experiment.
Shows:   Dataset selector + experiment selector + confusion matrix.
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import DatasetSelectorSection, ExperimentSelectorSection, ConfusionMatrixSection


class EvaluationPanel(BasePanel):
    PANEL_NAME  = "seg_evaluation"
    PANEL_LABEL = "(2) Evaluation"

    SECTIONS = [
        DatasetSelectorSection(),
        ExperimentSelectorSection(),
        ConfusionMatrixSection(),
    ]
