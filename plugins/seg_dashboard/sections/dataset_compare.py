"""plugins/seg_dashboard/sections/dataset_compare.py
Dataset attribute distribution comparison section.

Data Analysis panel -- overlay the same attribute(field) distribution across
selected datasets. Only datasets chosen in the MultiSelectSection
("selected_datasets") are rendered; falls back to all when None.

Attributes are experiment-independent, so records are loaded with the
default experiment for each dataset (no experiment selector needed here).

- If fewer than 2 selected datasets have records, show a placeholder.
- Reuses "field" and "bins" state keys from AttributeSection (no new state key).
"""

from __future__ import annotations

from .base import PanelSection
from ..charts import chart_for
from ..charts.base import _empty_figure
from ..framework.widgets import resolve_col_type
from ..stats import load_stats, get_records, get_columns, list_datasets, list_attributes


class DatasetCompareSection(PanelSection):
    """Selected attribute distribution compared across chosen datasets (proportion y-axis)."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        all_datasets = list_datasets()
        if len(all_datasets) < 2:
            return  # single-dataset env -- nothing to compare

        # Resolve which datasets the user selected (fallback: all)
        selected_keys = state.get("selected_datasets") or [d["key"] for d in all_datasets]
        # Keep ordering from all_datasets; filter to selected
        datasets = [d for d in all_datasets if d["key"] in set(selected_keys)]

        # Load records for every selected dataset using the default experiment
        # (attributes are model-independent, so experiment choice doesn't matter)
        all_records:    dict[str, list[dict]] = {}
        dataset_labels: dict[str, str]        = {}
        for ds in datasets:
            ds_stats = load_stats(ds["key"])
            if not ds_stats:
                continue
            ds_records = get_records(ds_stats)   # None → default experiment
            if ds_records:
                all_records[ds["key"]] = ds_records
                dataset_labels[ds["key"]] = ds["label"]

        if len(all_records) < 2:
            fig = _empty_figure(
                "Select 2 or more datasets above to compare.<br>"
                "Run the full pipeline for more datasets if needed."
            )
            panel.plot("dataset_compare_figure", data=fig["data"], layout=fig["layout"])
            return

        # field / bins -- shared with AttributeSection via "attr_sec" container namespace
        attr_cols = list_attributes(stats)
        columns   = get_columns(stats)

        field = state.get("attr_sec.field")
        if field not in attr_cols:
            field = attr_cols[0] if attr_cols else None

        if not field:
            fig = _empty_figure("No attribute field available")
            panel.plot("dataset_compare_figure", data=fig["data"], layout=fig["layout"])
            return

        # col_type: columns 메타 우선, 없으면 첫 번째 데이터셋 records 로 추론
        col_type = resolve_col_type(field, columns, next(iter(all_records.values()), []))

        bins   = max(2, int(state.get("attr_sec.bins", 10)))
        params = {
            "all_records":    all_records,
            "dataset_labels": dataset_labels,
            "bins":           bins,
        }

        if col_type:
            fig = chart_for("dataset_compare", col_type)().build_figure(stats, field, params)
        else:
            fig = _empty_figure(f"No data for field '{field}'")

        panel.plot("dataset_compare_figure", data=fig["data"], layout=fig["layout"])
