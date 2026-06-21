"""
plugins/seg_dashboard/sections/metric_breakdown.py
────────────────────────────────────────────────────
MetricBreakdownSection: records 기반 속성값/구간별 평균 메트릭 차트.

AttributeSection 과 달리 Combined 패널 전용 — 속성 × 메트릭 조합에 집중한다.
메트릭 목록은 stats["columns"] (kind=="metric") 에서 동적으로 읽는다.
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..charts.base import _empty_figure
from ..charts.metric import CategoricalMetricChart, NumericalMetricChart, _metric_label
from ..stats import get_records, get_columns, list_metrics

_PLACEHOLDER = (
    "Records data not yet available.<br>"
    "Re-run precompute_panel_stats.py to generate this chart."
)


class MetricBreakdownSection(PanelSection):
    """records 기반 속성별 평균 메트릭 라인/바 차트."""

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks = callbacks or {}
        records   = get_records(stats, state.get("experiment"))
        columns   = get_columns(stats)

        if not records:
            fig = _empty_figure(_PLACEHOLDER)
            panel.plot("breakdown_figure", data=fig["data"], layout=fig["layout"])
            return

        # attribute 컬럼 목록 (columns 메타 기반, 없으면 records 키 추론)
        attr_cols = [
            c for c, m in columns.items() if m.get("kind") == "attribute"
        ] if columns else [
            k for k in records[0].keys()
            if k not in ("image_path",) and k not in list_metrics(stats)
        ]

        if not attr_cols:
            fig = _empty_figure("No attribute columns found")
            panel.plot("breakdown_figure", data=fig["data"], layout=fig["layout"])
            return

        field = state.get("field")
        if field not in attr_cols:
            field = attr_cols[0]

        # 속성 드롭다운
        choices = types.Dropdown(label="Attribute Field")
        for name in attr_cols:
            choices.add_choice(name, label=name)
        panel.enum(
            "field",
            choices.values(),
            view=choices,
            default=field,
            on_change=callbacks.get("field"),
        )

        # 메트릭 드롭다운 (columns kind=metric ∩ records 실제 키)
        all_metrics = list_metrics(stats)
        available_metrics = [m for m in all_metrics if m in records[0]] if all_metrics else []
        if not available_metrics:
            fig = _empty_figure("No metrics available in records.<br>Re-run precompute_panel_stats.py.")
            panel.plot("breakdown_figure", data=fig["data"], layout=fig["layout"])
            return

        metric = state.get("metric", available_metrics[0])
        if metric not in available_metrics:
            metric = available_metrics[0]

        mc = types.Dropdown(label="Metric")
        for m in available_metrics:
            mc.add_choice(m, label=_metric_label(m))
        panel.enum(
            "metric",
            mc.values(),
            view=mc,
            default=metric,
            on_change=callbacks.get("metric"),
        )

        # 필드 타입 판별 (columns 메타 우선, records 값 타입 추론 폴백)
        col_type = columns.get(field, {}).get("type")
        if col_type is None and records:
            sample_val = next((r.get(field) for r in records if r.get(field) is not None), None)
            col_type = "numerical" if isinstance(sample_val, (int, float)) else "categorical"

        bins   = max(2, int(state.get("bins", 10)))
        params = {"metric": metric, "bins": bins, "records": records}

        # Bins 슬라이더 (numerical 전용)
        if col_type == "numerical":
            panel.int(
                "bins",
                min=2, max=50,
                view=types.SliderView(label=f"Bins  (current: {bins})"),
                default=bins,
                on_change=callbacks.get("bins"),
            )

        if col_type == "categorical":
            fig = CategoricalMetricChart().build_figure(stats, field, params)
        else:
            fig = NumericalMetricChart().build_figure(stats, field, params)

        panel.plot("breakdown_figure", data=fig["data"], layout=fig["layout"])
