"""
plugins/seg_dashboard/sections/multi_select.py
-----------------------------------------------
MultiSelectSection: 재사용 가능한 compact chips 멀티셀렉트 섹션.

동일한 UI 구성틀을 다른 대상(실험 / 데이터셋)에 재사용할 수 있도록
items_fn / labels_fn 을 주입받아 렌더링한다.

사용 예:
    # 실험 멀티셀렉트
    MultiSelectSection(
        "selected_experiments",
        experiment_items,
        label="Experiments",
        labels_fn=experiment_labels,
    )

    # 데이터셋 멀티셀렉트
    MultiSelectSection(
        "selected_datasets",
        dataset_items,
        label="Datasets",
        labels_fn=dataset_labels,
    )

위젯: FiftyOne List(String) + AutocompleteView
  - 선택된 항목은 칩(chip)으로 표시되며 ×로 제거 가능.
  - ▾ 클릭으로 새 항목 추가.
  - 항목이 10개 이상이어도 한 줄에 표시되므로 체크박스 벽이 생기지 않는다.
"""

from __future__ import annotations

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None

from .base import PanelSection
from ..stats import list_experiments, list_datasets


# ── 공용 items / labels 헬퍼 ─────────────────────────────────────────────────
# sections 와 framework/multi_select.py 양쪽에서 가져다 쓴다 (단일 소스).

def experiment_items(stats: dict) -> list[str]:
    """stats 에 등록된 experiment 키 목록."""
    return list_experiments(stats)


def experiment_labels(stats: dict) -> dict[str, str]:
    """experiment 키 → 표시 이름 매핑."""
    return stats.get("meta", {}).get("experiment_labels", {})


def dataset_items(stats: dict) -> list[str]:
    """설치된 모든 데이터셋 키 목록 (stats 는 시그니처 통일용, 사용 안 함)."""
    return [d["key"] for d in list_datasets()]


def dataset_labels(stats: dict) -> dict[str, str]:
    """데이터셋 키 → 표시 이름 매핑."""
    return {d["key"]: d["label"] for d in list_datasets()}


# ── 섹션 ─────────────────────────────────────────────────────────────────────

class MultiSelectSection(PanelSection):
    """Compact chips 멀티셀렉트 섹션 (실험 / 데이터셋 모두 지원).

    항목이 1개 이하면 아무것도 표시하지 않는다 (비교 의미 없음).
    선택이 비어 있으면 전체 선택으로 fallback 한다.
    """

    def __init__(
        self,
        state_key: str,
        items_fn,
        *,
        label: str,
        labels_fn=None,
    ) -> None:
        """
        Args:
            state_key: panel state 에 저장될 키 이름 (예: "selected_experiments").
            items_fn:  items_fn(stats) -> list[str] 형태의 callable.
            label:     위젯에 표시할 레이블 문자열.
            labels_fn: (optional) labels_fn(stats) -> dict[str, str].
                       제공하면 칩·드롭다운에 사람이 읽기 쉬운 이름을 표시한다.
        """
        self.state_key = state_key
        self.items_fn  = items_fn
        self.label     = label
        self.labels_fn = labels_fn

    def render(
        self,
        panel,
        stats: dict,
        state: dict,
        callbacks: dict | None = None,
    ) -> None:
        callbacks = callbacks or {}
        items     = self.items_fn(stats)

        if len(items) < 2:
            # 비교할 항목이 1개 이하 → 선택기 숨김
            return

        labels   = self.labels_fn(stats) if self.labels_fn else {}
        selected = state.get(self.state_key) or items
        # items 에 없는 키가 state 에 남아 있으면 제거 (데이터셋 교체 후 stale)
        selected = [s for s in selected if s in items] or list(items)

        menu = types.AutocompleteView(allow_user_input=False, allow_duplicates=False)
        for it in items:
            menu.add_choice(it, label=labels.get(it, it))

        panel.list(
            self.state_key,
            types.String(),
            view=menu,
            label=self.label,
            default=selected,
            on_change=callbacks.get(self.state_key),
        )
