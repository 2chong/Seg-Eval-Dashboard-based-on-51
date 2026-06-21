"""
plugins/seg_dashboard/panels/experiment.py
-------------------------------------------
(4) Experiment Panel

Purpose: Compare multiple experiment (mask set) results side by side.
Shows:   Dataset selector + per-class metric grouped bar across experiments.

Shows a placeholder when fewer than 2 experiments are available.
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import DatasetSelectorSection, ExperimentCompareSection


class ExperimentPanel(BasePanel):
    PANEL_NAME  = "seg_experiment"
    PANEL_LABEL = "(4) Experiment"

    SECTIONS = [
        DatasetSelectorSection(),
        ExperimentCompareSection(),   # 메트릭 드롭다운 + 모든 experiment 비교
    ]
