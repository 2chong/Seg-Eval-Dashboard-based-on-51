"""
plugins/seg_dashboard/panels/evaluation.py
-------------------------------------------
(2) Evaluation Panel

Purpose: Analyse evaluation results for the selected experiment.
Shows:   Dataset selector + experiment selector
         + [metric_dist container] metric distribution histogram (interactive)
         + confusion matrix (overview per experiment).

State key naming convention:
  "metric_dist.dist_metric"  -- private to MetricDistributionSection container
  "metric_dist.dist_bins"    -- private to MetricDistributionSection container
"""

from __future__ import annotations

from ..framework import BasePanel
from ..sections import (
    DatasetSelectorSection,
    ExperimentSelectorSection,
    MetricSummarySection,
    MetricDistributionSection,
    ConfusionMatrixSection,
    SectionLabel,
)


class EvaluationPanel(BasePanel):
    PANEL_NAME  = "seg_2_evaluation"
    PANEL_LABEL = "(2) Evaluation"

    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "metric_dist.dist_metric": "",
        "metric_dist.dist_bins":   10,
    }

    SECTIONS = [
        DatasetSelectorSection(),
        ExperimentSelectorSection(),
        SectionLabel("[Overview] Overall Metrics  |  per-sample mean / min / max"),
        MetricSummarySection(),
        SectionLabel("[Interactive] Metric Distribution  |  Metric / Bins selection"),
        MetricDistributionSection(),
        SectionLabel("[Overview] Confusion Matrix  |  Experiment selector above"),
        ConfusionMatrixSection(),
    ]

    def on_change_dist_metric(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("metric_dist.dist_metric", v)

    def on_change_dist_bins(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("metric_dist.dist_bins", max(2, int(v)))

    def _extra_callbacks(self) -> dict:
        return {
            "metric_dist.dist_metric": self.on_change_dist_metric,
            "metric_dist.dist_bins":   self.on_change_dist_bins,
        }
