"""
plugins/seg_dashboard/panels/experiment.py
-------------------------------------------
(4) Experiment Panel

Purpose: Compare multiple experiment (mask set) results side by side.
Shows:   Dataset selector
         + experiment chips multi-select (compact; scales to 10+ models)
         + per-class metric grouped bar (selected experiments only)
         + [attr_cmp container] attribute x metric cross-experiment line/bar comparison.

State keys:
  "selected_experiments"  -- list of currently selected experiment keys
                             (managed by MultiSelectMixin; default: all)
  "attr_cmp.cmp_field"    -- private to AttrMetricCompareSection container
  "attr_cmp.cmp_metric"   -- private to AttrMetricCompareSection container
  "attr_cmp.cmp_bins"     -- private to AttrMetricCompareSection container
"""

from __future__ import annotations

from ..framework import BasePanel, MultiSelectMixin
from ..sections import (
    DatasetSelectorSection,
    ExperimentCompareSection,
    AttrMetricCompareSection,
    MultiSelectSection,
    experiment_items,
    experiment_labels,
    SectionLabel,
)
from ..stats import load_stats, list_attributes


class ExperimentPanel(MultiSelectMixin, BasePanel):
    PANEL_NAME  = "seg_4_experiment"
    PANEL_LABEL = "(4) Experiment"

    MULTI_SELECTS = [
        ("selected_experiments", experiment_items),
    ]

    STATE_DEFAULTS = {
        **BasePanel.STATE_DEFAULTS,
        "attr_cmp.cmp_field":   None,
        "attr_cmp.cmp_metric":  "",
        "attr_cmp.cmp_bins":    10,
        "selected_experiments": None,
    }

    SECTIONS = [
        DatasetSelectorSection(),
        SectionLabel("[Selection] Experiments to include in comparison charts"),
        MultiSelectSection(
            "selected_experiments",
            experiment_items,
            label="Experiments",
            labels_fn=experiment_labels,
        ),
        SectionLabel("[Overview] Per-Class Metric Comparison  |  selected experiments"),
        ExperimentCompareSection(),
        AttrMetricCompareSection(),
    ]

    # ── 라이프사이클 ──────────────────────────────────────────────────────────
    # MultiSelectMixin.on_load / on_change_dataset 이 super() 체이닝으로
    # BasePanel.on_load / on_change_dataset 을 감싸므로,
    # 여기서는 attr_cmp 전용 추가 초기화만 수행한다.

    def on_load(self, ctx) -> None:
        super().on_load(ctx)   # MultiSelectMixin → BasePanel → selected_experiments 초기화
        self._reset_cmp_field(ctx)

    def on_change_dataset(self, ctx) -> None:
        super().on_change_dataset(ctx)  # MultiSelectMixin → BasePanel → 리셋
        self._reset_cmp_field(ctx)

    def _reset_cmp_field(self, ctx) -> None:
        stats = load_stats(ctx.panel.get_state("dataset"))
        if not stats:
            return
        attrs = list_attributes(stats)
        if attrs:
            ctx.panel.set_state("attr_cmp.cmp_field", attrs[0])

    # ── 콜백 ──────────────────────────────────────────────────────────────────

    def on_change_cmp_field(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("attr_cmp.cmp_field", v)

    def on_change_cmp_metric(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("attr_cmp.cmp_metric", v)

    def on_change_cmp_bins(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("attr_cmp.cmp_bins", max(2, int(v)))

    def _extra_callbacks(self) -> dict:
        # MultiSelectMixin._extra_callbacks() 가 selected_experiments 콜백을 포함한다.
        extra = dict(super()._extra_callbacks())
        extra.update({
            "attr_cmp.cmp_field":  self.on_change_cmp_field,
            "attr_cmp.cmp_metric": self.on_change_cmp_metric,
            "attr_cmp.cmp_bins":   self.on_change_cmp_bins,
        })
        return extra
