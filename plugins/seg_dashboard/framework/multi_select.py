"""
plugins/seg_dashboard/framework/multi_select.py
------------------------------------------------
MultiSelectMixin: 패널에 compact chips 멀티셀렉트 기능을 추가하는 믹스인.

사용 방법 (패널 선언 시):
    from ..framework import BasePanel, MultiSelectMixin
    from ..sections.multi_select import experiment_items, dataset_items

    class MyPanel(MultiSelectMixin, BasePanel):
        MULTI_SELECTS = [
            ("selected_experiments", experiment_items),
        ]
        STATE_DEFAULTS = {
            **BasePanel.STATE_DEFAULTS,
            "selected_experiments": None,
        }

특징:
- 기존 per-checkbox (_make_exp_sel_callback, exp_sel_<exp>) 방식 완전 대체.
- 값은 list[str] 으로 state 에 저장된다 (FiftyOne List+AutocompleteView 반환값).
- 빈 선택 → 전체 선택으로 자동 복구 (차트가 항상 데이터를 받음).
- on_load / on_change_dataset 을 super() 체이닝으로 안전하게 오버라이드.
- hot-reload 안전: __getattr__ 로 미리 등록되지 않은 콜백도 즉시 생성.
"""

from __future__ import annotations

from ..framework.base_panel import _BoundCb
from ..stats import load_stats


class MultiSelectMixin:
    """패널에 compact chips 멀티셀렉트 선택기를 부여하는 믹스인.

    MRO 순서: class MyPanel(MultiSelectMixin, BasePanel)
    MultiSelectMixin 이 BasePanel 보다 먼저 와야 super() 체이닝이 올바르게 동작한다.
    """

    # 서브클래스에서 선언: [(state_key, items_fn(stats) -> list[str]), ...]
    MULTI_SELECTS: list = []

    # ── 라이프사이클 ─────────────────────────────────────────────────────────

    def on_load(self, ctx) -> None:
        super().on_load(ctx)  # type: ignore[misc]
        self._reset_multi(ctx)

    def on_change_dataset(self, ctx) -> None:
        super().on_change_dataset(ctx)  # type: ignore[misc]
        self._reset_multi(ctx)

    def _reset_multi(self, ctx) -> None:
        """데이터셋 로드/변경 시 모든 멀티셀렉트를 '전체 선택' 으로 초기화한다."""
        stats = load_stats(ctx.panel.get_state("dataset"))
        if not stats:
            return
        for key, items_fn in self.MULTI_SELECTS:
            ctx.panel.set_state(key, list(items_fn(stats)))

    # ── 콜백 ────────────────────────────────────────────────────────────────

    def _make_cb(self, key: str, items_fn) -> _BoundCb:
        """state_key 에 대응하는 AutocompleteView on_change 콜백을 반환한다."""
        def _cb(ctx) -> None:
            stats = load_stats(ctx.panel.get_state("dataset"))
            all_items = list(items_fn(stats)) if stats else []
            raw = ctx.params.get("value") or []
            # list 또는 단일 값 정규화
            if isinstance(raw, str):
                raw = [raw]
            sel = [x for x in raw if x in all_items]
            # 빈 선택 → 전체 선택으로 복구 (차트가 데이터 없는 상태 방지)
            if not sel:
                sel = all_items
            ctx.panel.set_state(key, sel)
        return _BoundCb(self, f"on_change_{key}", _cb)

    def __getattr__(self, name: str):
        """hot-reload 안전: on_change_<key> 메서드를 즉시 생성·반환한다."""
        for key, items_fn in type(self).MULTI_SELECTS:
            if name == f"on_change_{key}":
                return self._make_cb(key, items_fn)
        raise AttributeError(name)

    def _extra_callbacks(self) -> dict:
        """상위(BasePanel / 서브클래스) 콜백에 멀티셀렉트 콜백을 추가한다."""
        extra = dict(super()._extra_callbacks())  # type: ignore[misc]
        for key, items_fn in self.MULTI_SELECTS:
            extra[key] = self._make_cb(key, items_fn)
        return extra
