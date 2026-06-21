"""
plugins/seg_dashboard/sections/base.py
────────────────────────────────────────
PanelSection 추상 기반 클래스.

새 섹션을 추가하는 방법
  1. PanelSection 을 상속한 클래스를 sections/ 아래 새 파일에 구현한다.
  2. render() 메서드에 UI 요소(위젯 + 차트)를 작성한다.
  3. panel.py 의 _SECTIONS 리스트에 인스턴스를 추가한다.
  → 다른 섹션 코드는 수정 불필요.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PanelSection(ABC):
    """패널에 렌더링할 UI 그룹 단위.

    Args:
        panel    : types.Object  — FiftyOne panel 객체
        stats    : dict          — panel_stats.json 전체 내용
        state    : dict          — 현재 패널 상태 (_STATE_DEFAULTS 키 집합)
        callbacks: dict          — {"field": fn, "bins": fn, "metric": fn}
                                   패널 콜백 메서드 참조
    """

    @abstractmethod
    def render(
        self,
        panel,
        stats: dict,
        state: dict,
        callbacks: dict | None = None,
    ) -> None: ...
