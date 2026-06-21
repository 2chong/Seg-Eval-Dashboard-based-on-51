"""
plugins/seg_dashboard/sections/experiment_selector.py
───────────────────────────────────────────────────────
ExperimentSelectorSection: experiment 드롭다운.

stats["meta"]["experiments"] 목록이 있을 때만 렌더링한다.
단일 experiment 이거나 v1 스키마에서는 아무것도 표시하지 않는다 (하위호환).
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..stats import list_experiments


class ExperimentSelectorSection(PanelSection):
    """복수 experiment 가 있을 때 experiment 선택 드롭다운을 표시한다."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks = callbacks or {}
        experiments = list_experiments(stats)

        if len(experiments) < 2:
            # 단일 experiment 또는 구 스키마 → 드롭다운 숨김
            return

        meta = stats.get("meta", {})
        labels = {
            exp: meta.get("experiment_labels", {}).get(exp, exp)
            for exp in experiments
        }

        current_exp = state.get("experiment") or experiments[0]

        choices = types.Dropdown(label="Experiment")
        for exp in experiments:
            choices.add_choice(exp, label=labels[exp])

        panel.enum(
            "experiment",
            choices.values(),
            view=choices,
            default=current_exp,
            on_change=callbacks.get("experiment"),
        )
