"""plugins/seg_dashboard/sections/attr_metric_compare.py
Attribute x Metric cross-experiment comparison section.

속성과 평가지표를 선택하면, 속성 변화에 따른 메트릭 추이를 실험별로 비교한다.
categorical 속성 -> grouped bar / numerical 속성 -> multi-line.

Private state keys (prefixed with container name "attr_cmp"):
  attr_cmp.cmp_field  -- selected attribute field
  attr_cmp.cmp_metric -- selected metric
  attr_cmp.cmp_bins   -- histogram bin count (numerical fields only)

모든 컨트롤(field, metric, bins)과 차트는 "attr_cmp" ObjectView 컨테이너 안에 묶인다.
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..charts import chart_for
from ..charts.base import _empty_figure
from ..charts.metric import _metric_label
from ..framework.widgets import add_dropdown, add_bins_slider, resolve_col_type
from ..stats import get_records, get_columns, list_experiments, list_metrics, list_attributes

_PLACEHOLDER = (
    "Records data not yet available.<br>"
    "Re-run precompute_panel_stats.py to generate this chart."
)

_CONTAINER = "attr_cmp"


class AttrMetricCompareSection(PanelSection):
    """속성 × 메트릭 cross-experiment 비교 차트.

    실험이 2개 미만이면 placeholder 를 표시한다.
    field/metric/bins 컨트롤과 차트가 같은 ObjectView 컨테이너 안에 묶인다.
    """

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks    = callbacks or {}
        all_exps     = list_experiments(stats)
        selected_set = set(state.get("selected_experiments") or all_exps)
        experiments  = [e for e in all_exps if e in selected_set] or all_exps
        columns      = get_columns(stats)

        grp = types.Object()

        # ── 속성 드롭다운 ─────────────────────────────────────────────────────
        attr_cols = list_attributes(stats)
        if not attr_cols:
            fig = _empty_figure("No attribute columns found")
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Attribute × Metric Comparison",
                view=types.ObjectView(),
            )
            return

        field = state.get(f"{_CONTAINER}.cmp_field")
        if field not in attr_cols:
            field = attr_cols[0]

        add_dropdown(
            grp, "cmp_field", attr_cols,
            label="Attribute", default=field,
            on_change=callbacks.get(f"{_CONTAINER}.cmp_field"),
        )

        if len(experiments) < 2:
            fig = _empty_figure(
                "Select 2 or more experiments above to compare.<br>"
                "(If only 1 experiment exists, run inference for another model.)"
            )
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Attribute × Metric Comparison",
                view=types.ObjectView(),
            )
            return

        # ── 메트릭 드롭다운 ───────────────────────────────────────────────────
        all_metrics   = list_metrics(stats)
        first_records = get_records(stats, experiments[0])
        available     = (
            [m for m in all_metrics if first_records and m in first_records[0]]
            if all_metrics else []
        )
        if not available:
            fig = _empty_figure("No metrics in records.<br>Re-run precompute_panel_stats.py.")
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Attribute × Metric Comparison",
                view=types.ObjectView(),
            )
            return

        metric = state.get(f"{_CONTAINER}.cmp_metric") or ""
        if metric not in available:
            metric = available[0]

        add_dropdown(
            grp, "cmp_metric", available,
            label="Metric", default=metric,
            on_change=callbacks.get(f"{_CONTAINER}.cmp_metric"),
            labels=_metric_label,
        )

        all_records = {exp: get_records(stats, exp) for exp in experiments}
        all_records = {exp: r for exp, r in all_records.items() if r}
        if not all_records:
            fig = _empty_figure(_PLACEHOLDER)
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                _CONTAINER, grp,
                label="Attribute × Metric Comparison",
                view=types.ObjectView(),
            )
            return

        # col_type: columns 메타 우선, 없으면 첫 experiment records 로 추론
        col_type = resolve_col_type(field, columns, next(iter(all_records.values()), []))

        meta_labels = stats.get("meta", {}).get("experiment_labels", {})
        params = {
            "all_records":       all_records,
            "metric":            metric,
            "experiment_labels": meta_labels,
        }

        if col_type == "numerical":
            bins = max(2, int(state.get(f"{_CONTAINER}.cmp_bins", 10)))
            add_bins_slider(
                grp, "cmp_bins", value=bins,
                on_change=callbacks.get(f"{_CONTAINER}.cmp_bins"),
            )
            params["bins"] = bins

        if col_type:
            fig = chart_for("cross_exp", col_type)().build_figure(stats, field, params)
        else:
            fig = _empty_figure(f"No data for field '{field}'")

        grp.plot("figure", data=fig["data"], layout=fig["layout"])

        panel.define_property(
            _CONTAINER, grp,
            label="Attribute × Metric Comparison",
            view=types.ObjectView(),
        )
