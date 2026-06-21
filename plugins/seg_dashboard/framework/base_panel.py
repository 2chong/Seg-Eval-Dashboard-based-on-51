"""
plugins/seg_dashboard/framework/base_panel.py
----------------------------------------------
BasePanel: 모든 패널이 상속하는 공통 클래스.

서브클래스 선언 패턴 (panels/*.py):
  class MyPanel(BasePanel):
      PANEL_NAME  = "seg_my_panel"   # FiftyOne 등록 key (fiftyone.yml 과 일치)
      PANEL_LABEL = "My Panel"       # App '+' 메뉴에 표시되는 이름
      SECTIONS    = [SectionA(), SectionB()]
      # STATE_DEFAULTS 는 필요 시 오버라이드

새 패널 추가:
  1. panels/<이름>.py 에 BasePanel 서브클래스 작성
  2. panels/__init__.py 에 임포트 추가
  3. seg_dashboard/__init__.py 의 register() 에 추가
  4. fiftyone.yml 의 panels: 에 PANEL_NAME 추가
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import fiftyone.operators as foo
    import fiftyone.operators.types as types
except ImportError as exc:
    raise ImportError(f"FiftyOne not installed: {exc}") from exc

from ..stats import load_stats, list_experiments, list_datasets, get_columns, list_metrics

_NO_STATS_MSG = (
    "panel_stats.json not found.\n"
    "Run:  python tools/precompute_panel_stats.py"
)

# 기본 상태 스키마 — 서브클래스에서 오버라이드 가능
# "metric" 기본값은 on_load 에서 stats 의 첫 번째 메트릭으로 동적 설정된다.
# 여기서는 빈 문자열로만 두어 "recall" 리터럴 하드코딩을 방지한다.
_BASE_STATE_DEFAULTS: dict = {
    "dataset":    None,      # 선택된 데이터셋 키
    "field":      None,      # 선택된 속성 필드
    "bins":       10,        # histogram 구간 수
    "metric":     "",        # 선택된 성능 메트릭 (on_load 에서 첫 메트릭으로 초기화)
    "experiment": None,      # 선택된 experiment 이름
}


class BasePanel(foo.Panel):
    """공통 패널 기반 클래스.

    서브클래스는 PANEL_NAME, PANEL_LABEL, SECTIONS 만 선언하면
    상태 관리·렌더 루프·콜백 라우팅은 이 클래스가 자동으로 제공한다.
    """

    # 서브클래스에서 반드시 선언
    PANEL_NAME:  str  = ""
    PANEL_LABEL: str  = ""
    SECTIONS:    list = []

    # 필요 시 서브클래스에서 오버라이드
    STATE_DEFAULTS: dict = dict(_BASE_STATE_DEFAULTS)

    # ── 설정 ──────────────────────────────────────────────────────────────────

    @property
    def config(self) -> foo.PanelConfig:
        return foo.PanelConfig(
            name=self.PANEL_NAME,
            label=self.PANEL_LABEL,
            allow_multiple=False,
        )

    # ── 라이프사이클 ──────────────────────────────────────────────────────────

    def on_load(self, ctx) -> None:
        """패널 첫 로드 시 STATE_DEFAULTS 기준으로 상태 초기화."""
        for key, default in self.STATE_DEFAULTS.items():
            ctx.panel.set_state(key, default)

        # dataset: 빌드된 첫 번째 데이터셋으로 초기화
        import config as _cfg
        available = list_datasets()
        init_dataset = _cfg.ACTIVE_DATASET if any(
            d["key"] == _cfg.ACTIVE_DATASET for d in available
        ) else (available[0]["key"] if available else None)
        ctx.panel.set_state("dataset", init_dataset)

        stats = load_stats(init_dataset)
        if not stats:
            return

        # field: columns 메타에서 첫 번째 attribute 필드로 초기화
        columns = get_columns(stats)
        attr_fields = [k for k, v in columns.items() if v.get("kind") == "attribute"]
        if attr_fields:
            ctx.panel.set_state("field", attr_fields[0])

        # metric: columns 메타에서 첫 번째 metric 으로 초기화 (하드코딩 없음)
        metrics = list_metrics(stats)
        if metrics:
            ctx.panel.set_state("metric", metrics[0])

        # experiment: meta.experiments 에서 기본값
        experiments = list_experiments(stats)
        if experiments:
            default_exp = stats.get("meta", {}).get("default_experiment", experiments[0])
            ctx.panel.set_state("experiment", default_exp)

    # ── 콜백 ──────────────────────────────────────────────────────────────────

    def on_change_dataset(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("dataset", v)
            # 데이터셋이 바뀌면 experiment/field 초기화
            stats = load_stats(v)
            if stats:
                columns = get_columns(stats)
                attr_fields = [k for k, v2 in columns.items() if v2.get("kind") == "attribute"]
                if attr_fields:
                    ctx.panel.set_state("field", attr_fields[0])
                metrics = list_metrics(stats)
                if metrics:
                    ctx.panel.set_state("metric", metrics[0])
                exps = list_experiments(stats)
                if exps:
                    default_exp = stats.get("meta", {}).get("default_experiment", exps[0])
                    ctx.panel.set_state("experiment", default_exp)

    def on_change_field(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("field", v)
            ctx.panel.set_state("bins", self.STATE_DEFAULTS.get("bins", 10))

    def on_change_bins(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("bins", max(2, int(v)))

    def on_change_metric(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("metric", v)

    def on_change_experiment(self, ctx) -> None:
        v = ctx.params.get("value")
        if v is not None:
            ctx.panel.set_state("experiment", v)

    # ── 렌더 ──────────────────────────────────────────────────────────────────

    def render(self, ctx) -> types.Property:
        """SECTIONS 를 순서대로 렌더링한다."""
        panel = types.Object()

        # 현재 상태 읽기
        state: dict = {
            key: (ctx.panel.get_state(key) if ctx.panel.get_state(key) is not None else default)
            for key, default in self.STATE_DEFAULTS.items()
        }
        state["bins"] = max(2, int(state["bins"]))

        # 선택된 데이터셋의 stats 로드
        stats = load_stats(state.get("dataset"))

        if stats is None:
            panel.str(
                "no_stats",
                label=_NO_STATS_MSG,
                view=types.LabelValueView(read_only=True),
            )
            return types.Property(panel)

        # field 가 None 이면 columns attribute 첫 번째로 대체
        if not state.get("field"):
            columns = get_columns(stats)
            attr_fields = [k for k, v in columns.items() if v.get("kind") == "attribute"]
            state["field"] = attr_fields[0] if attr_fields else None

        # experiment 가 None 이면 meta 에서 대체
        if not state.get("experiment"):
            experiments = list_experiments(stats)
            if experiments:
                state["experiment"] = stats.get("meta", {}).get(
                    "default_experiment", experiments[0]
                )

        callbacks = {
            "dataset":    self.on_change_dataset,
            "field":      self.on_change_field,
            "bins":       self.on_change_bins,
            "metric":     self.on_change_metric,
            "experiment": self.on_change_experiment,
        }

        for section in self.SECTIONS:
            section.render(panel, stats, state, callbacks)

        return types.Property(panel)
