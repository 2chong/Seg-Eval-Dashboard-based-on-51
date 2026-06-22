"""
plugins/seg_dashboard/sections/dataset_selector.py
----------------------------------------------------
DatasetSelectorSection: 패널 상단 데이터셋 드롭다운.

panel_stats.json 이 실제로 존재하는 데이터셋이 2개 이상일 때만 표시한다.
App 그리드(썸네일)와 완전히 독립적 -- 패널 통계만 전환한다.
"""

from __future__ import annotations

from .base import PanelSection
from ..framework.widgets import add_dropdown
from ..stats import list_datasets


class DatasetSelectorSection(PanelSection):
    """빌드된 데이터셋이 2개 이상일 때 Dataset 드롭다운을 표시한다."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks = callbacks or {}
        datasets  = list_datasets()

        if len(datasets) < 2:
            return  # 단일 데이터셋 -> 드롭다운 숨김

        current = state.get("dataset") or datasets[0]["key"]
        labels  = {ds["key"]: ds["label"] for ds in datasets}

        add_dropdown(
            panel, "dataset",
            [ds["key"] for ds in datasets],
            label="Dataset", default=current,
            on_change=callbacks.get("dataset"),
            labels=labels,
        )
