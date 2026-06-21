"""
plugins/seg_dashboard/sections/attribute.py
─────────────────────────────────────────────
AttributeSection: 속성 선택 + 분포 차트 + (선택) 메트릭 차트.

records 를 단일 소스로 사용한다 (T12/T2 개선).
메트릭 목록은 stats["columns"] (kind=="metric") 에서 동적으로 읽는다.

생성자 파라미터:
  show_metric : bool = True
      False 이면 메트릭 드롭다운과 메트릭 차트를 숨긴다 (Data Analysis 패널용).
  kind_filter : str | None = None
      "attribute" -> columns 메타가 있을 때 attribute 종류 필드만 표시.
      None        -> 전체 표시.
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..charts import (
    AttributeDistributionChart,
    CategoricalMetricChart,
    NumericalMetricChart,
    _metric_label,
)
from ..stats import get_records, get_columns, list_metrics


class AttributeSection(PanelSection):
    """속성 드롭다운 선택 후 분포·메트릭 차트를 표시하는 섹션."""

    def __init__(
        self,
        show_metric: bool = True,
        kind_filter: str | None = None,
    ) -> None:
        self.show_metric = show_metric
        self.kind_filter = kind_filter

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    def _visible_attr_fields(self, stats: dict) -> list[str]:
        """kind_filter 에 따라 표시할 속성 필드 목록을 반환한다."""
        columns = get_columns(stats)
        if self.kind_filter is None or not columns:
            # 메트릭이 아닌 것 전부 (image_path 제외)
            return [
                k for k in columns
                if columns.get(k, {}).get("kind") != "metric" and k != "image_path"
            ]
        return [
            name for name, meta in columns.items()
            if meta.get("kind") == self.kind_filter
        ]

    def _available_metrics(self, stats: dict, records: list[dict]) -> list[str]:
        """stats columns (kind=metric) ∩ records 실제 키 목록."""
        all_metrics = list_metrics(stats)
        if not all_metrics or not records:
            return all_metrics
        return [m for m in all_metrics if m in records[0]]

    # ── 렌더 ──────────────────────────────────────────────────────────────────

    def render(self, panel, stats: dict, state: dict, callbacks: dict | None = None) -> None:
        callbacks = callbacks or {}
        experiment = state.get("experiment")
        records    = get_records(stats, experiment)
        columns    = get_columns(stats)

        attr_fields = self._visible_attr_fields(stats)
        field = state.get("field")
        if field not in attr_fields:
            field = attr_fields[0] if attr_fields else None

        bins   = max(2, int(state.get("bins", 10)))
        metric = state.get("metric", "recall")

        # ── 속성 드롭다운 ─────────────────────────────────────────────────────
        if attr_fields:
            choices = types.Dropdown(label="Attribute Field")
            for name in attr_fields:
                choices.add_choice(name, label=name)
            panel.enum(
                "field",
                choices.values(),
                view=choices,
                default=field,
                on_change=callbacks.get("field"),
            )

        if not field:
            return

        # 필드 타입 판별 (columns 메타 우선, records 값 타입 추론 폴백)
        col_meta = columns.get(field, {})
        col_type = col_meta.get("type")
        if col_type is None and records:
            sample_val = next((r.get(field) for r in records if r.get(field) is not None), None)
            col_type = "numerical" if isinstance(sample_val, (int, float)) else "categorical"

        params = {"bins": bins, "metric": metric, "records": records}

        # ── Bins 슬라이더 (numerical 전용) ────────────────────────────────────
        if col_type == "numerical":
            panel.int(
                "bins",
                min=2,
                max=50,
                view=types.SliderView(label=f"Bins  (current: {bins})"),
                default=bins,
                on_change=callbacks.get("bins"),
            )

        # ── 메트릭 드롭다운 (show_metric=True 일 때만) ────────────────────────
        available_metrics = []
        if self.show_metric:
            available_metrics = self._available_metrics(stats, records)
            if available_metrics:
                if metric not in available_metrics:
                    metric = available_metrics[0]
                    params["metric"] = metric
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

        # ── 분포 차트 ─────────────────────────────────────────────────────────
        dist_fig = AttributeDistributionChart().build_figure(stats, field, params)
        panel.plot("dist_figure", data=dist_fig["data"], layout=dist_fig["layout"])

        # ── 메트릭 차트 (show_metric=True 일 때만) ────────────────────────────
        if self.show_metric and available_metrics:
            if col_type == "categorical":
                mfig = CategoricalMetricChart().build_figure(stats, field, params)
            else:
                mfig = NumericalMetricChart().build_figure(stats, field, params)
            panel.plot("metric_figure", data=mfig["data"], layout=mfig["layout"])
