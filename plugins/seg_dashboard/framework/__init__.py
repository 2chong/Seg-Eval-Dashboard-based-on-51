"""plugins/seg_dashboard/framework — 공통 패널 인프라."""

from .base_panel import BasePanel, _BoundCb
from .multi_select import MultiSelectMixin
from .widgets import add_dropdown, add_bins_slider, resolve_col_type

__all__ = [
    "BasePanel",
    "_BoundCb",
    "MultiSelectMixin",
    "add_dropdown",
    "add_bins_slider",
    "resolve_col_type",
]
