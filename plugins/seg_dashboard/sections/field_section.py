"""
plugins/seg_dashboard/sections/field_section.py
────────────────────────────────────────────────
FieldSection: 선언형 필드+차트 섹션 틀.

MultiSelectSection 과 동일한 발상 — 인자만 주입하면
필드 드롭다운 + 메트릭 드롭다운 + bins 슬라이더 + 차트가 자동으로 구성된다.
차트 선택은 charts/registry.py 를 통해 col_type 으로 디스패치된다.

──────────────────────────────────────────────────────────────────────────────
언제 쓰는가
  - 속성 필드 드롭다운 + (선택) 메트릭 드롭다운 + (선택) bins 슬라이더 + 차트 조합.
  - 아래 6개 파라미터로 섹션 동작 전체가 정의되는 경우.

언제 인라인 PanelSection 을 두는가  ← 이 경우는 틀에 끼워 맞추지 말 것
  - 복수 데이터셋/실험의 records 를 직접 조합하는 경우
    (AttrMetricCompareSection, DatasetCompareSection, ExperimentCompareSection).
  - 표(table), heatmap 처럼 field_types 디스패치가 없는 차트.
  - 이 섹션의 파라미터(6개)로 표현되지 않는 특수 로직.
──────────────────────────────────────────────────────────────────────────────

사용 예 (panels/*.py SECTIONS 리스트):
    # 속성 분포만 (메트릭 차트 없음)
    FieldSection(
        container="attr_sec",
        dist_role="distribution",
        metric_role=None,
        kind_filter="attribute",
        label="Attribute Distribution",
    )

    # 메트릭 breakdown (분포 차트 없음)
    FieldSection(
        container="attr_sec",
        dist_role=None,
        metric_role="metric",
        kind_filter="attribute",
        label="Metric Breakdown",
    )
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None  # type: ignore[assignment]

from .base import PanelSection
from ..charts.base import _empty_figure
from ..charts import chart_for
from ..charts.metric import _metric_label
from ..framework.widgets import add_dropdown, add_bins_slider, resolve_col_type
from ..stats import get_records, get_columns, list_metrics


class FieldSection(PanelSection):
    """선언형 필드 드롭다운 + 레지스트리 차트 섹션.

    Args:
        container   : ObjectView 컨테이너 이름 (state 네임스페이스).
                      예: "attr_sec" → state["attr_sec.field"] / [".bins"] / [".metric"]
        dist_role   : 분포 차트 registry role (예: "distribution"). None=분포 차트 없음.
        metric_role : 메트릭 차트 registry role (예: "metric"). None=메트릭 차트·드롭다운 없음.
        kind_filter : "attribute"=속성 필드만, "metric"=메트릭 필드만, None=전체.
        show_bins   : True=numerical 필드일 때 bins 슬라이더 표시 (기본 True).
        label       : 섹션 레이블 (ObjectView 헤더 문자열).
    """

    def __init__(
        self,
        *,
        container: str,
        dist_role: str | None = None,
        metric_role: str | None = None,
        kind_filter: str | None = "attribute",
        show_bins: bool = True,
        label: str = "Distribution",
    ) -> None:
        self.container   = container
        self.dist_role   = dist_role
        self.metric_role = metric_role
        self.kind_filter = kind_filter
        self.show_bins   = show_bins
        self.label       = label

    def render(
        self,
        panel,
        stats: dict,
        state: dict,
        callbacks: dict | None = None,
    ) -> None:
        callbacks  = callbacks or {}
        experiment = state.get("experiment")
        records    = get_records(stats, experiment)
        columns    = get_columns(stats)

        # ── 표시할 필드 목록 ──────────────────────────────────────────────────
        if self.kind_filter:
            attr_cols = [
                k for k, m in columns.items()
                if m.get("kind") == self.kind_filter
            ]
        else:
            attr_cols = [
                k for k in columns
                if columns[k].get("kind") != "metric" and k != "image_path"
            ]

        grp = types.Object()

        if not attr_cols:
            fig = _empty_figure("No attribute fields found")
            grp.plot("figure", data=fig["data"], layout=fig["layout"])
            panel.define_property(
                self.container, grp,
                label=self.label,
                view=types.ObjectView(),
            )
            return

        # ── 필드 드롭다운 ─────────────────────────────────────────────────────
        field = state.get(f"{self.container}.field")
        if field not in attr_cols:
            field = attr_cols[0]

        add_dropdown(
            grp, "field", attr_cols,
            label="Attribute Field", default=field,
            on_change=callbacks.get("field"),
        )

        if not field:
            panel.define_property(
                self.container, grp,
                label=self.label,
                view=types.ObjectView(),
            )
            return

        # ── col_type 판별 ─────────────────────────────────────────────────────
        col_type = resolve_col_type(field, columns, records)

        bins   = max(2, int(state.get(f"{self.container}.bins", 10)))
        params: dict = {"records": records, "bins": bins}

        # ── 메트릭 드롭다운 (metric_role 있을 때만) ───────────────────────────
        available_metrics: list[str] = []
        if self.metric_role:
            all_metrics = list_metrics(stats)
            available_metrics = (
                [m for m in all_metrics if m in records[0]]
                if all_metrics and records else (all_metrics or [])
            )
            if available_metrics:
                metric = state.get(f"{self.container}.metric", "")
                if metric not in available_metrics:
                    metric = available_metrics[0]
                params["metric"] = metric
                add_dropdown(
                    grp, "metric", available_metrics,
                    label="Metric", default=metric,
                    on_change=callbacks.get("metric"),
                    labels=_metric_label,
                )

        # ── Bins 슬라이더 (numerical + show_bins) ─────────────────────────────
        if self.show_bins and col_type == "numerical":
            add_bins_slider(
                grp, "bins", value=bins,
                on_change=callbacks.get("bins"),
            )

        # ── 분포 차트 ─────────────────────────────────────────────────────────
        if self.dist_role and col_type:
            dist_fig = chart_for(self.dist_role, col_type)().build_figure(
                stats, field, params
            )
            grp.plot("dist_figure", data=dist_fig["data"], layout=dist_fig["layout"])

        # ── 메트릭 차트 (메트릭 드롭다운과 함께) ─────────────────────────────
        if self.metric_role and col_type and available_metrics:
            metric_fig = chart_for(self.metric_role, col_type)().build_figure(
                stats, field, params
            )
            grp.plot("metric_figure", data=metric_fig["data"], layout=metric_fig["layout"])

        panel.define_property(
            self.container, grp,
            label=self.label,
            view=types.ObjectView(),
        )
