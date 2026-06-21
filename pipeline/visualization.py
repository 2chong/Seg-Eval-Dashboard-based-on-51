"""
pipeline/visualization.py
──────────────────────────
⚠  DEPRECATED — 이 모듈은 더 이상 사용되지 않습니다.

confusion matrix 표시를 포함한 모든 시각화 역할이
FiftyOne Panel 플러그인(plugins/seg_dashboard/)으로 이관됐습니다.

대체 방법:
  1. python tools/precompute_panel_stats.py   ← 1회성 집계
  2. python main.py                           ← App 실행
  3. 브라우저 http://localhost:5151 → '+' → Segmentation Dashboard

plot_confusion_matrix() 를 직접 호출하면 DeprecationWarning 이 발생합니다.
"""

from __future__ import annotations

import warnings


def plot_confusion_matrix(results) -> None:  # noqa: ARG001
    """[DEPRECATED] Use the Segmentation Dashboard panel instead.

    이 함수는 아무 동작도 하지 않습니다. confusion matrix 는 이제
    App 내 'Segmentation Dashboard' 패널에서 인터랙티브하게 확인할 수 있습니다.
    """
    warnings.warn(
        "pipeline.visualization.plot_confusion_matrix() is deprecated. "
        "Open the 'Segmentation Dashboard' panel in the FiftyOne App instead. "
        "(Run tools/precompute_panel_stats.py first if panel_stats.json is missing.)",
        DeprecationWarning,
        stacklevel=2,
    )
