"""
plugins/seg_dashboard/__init__.py
──────────────────────────────────
FiftyOne plugin entry point. 5개 패널을 등록한다.

새 패널 추가 순서:
  1. panels/<이름>.py 에 BasePanel 서브클래스 작성
  2. panels/__init__.py 에 임포트 추가
  3. 이 파일의 register() 에 p.register(<패널클래스>) 한 줄 추가
  4. fiftyone.yml 의 panels: 에 PANEL_NAME 추가
"""

import traceback

try:
    from .panels import (
        DataAnalysisPanel,
        EvaluationPanel,
        CombinedPanel,
        ExperimentPanel,
        SchemaPanel,
    )
    _IMPORT_ERROR = None
except Exception as _e:
    _IMPORT_ERROR = _e
    traceback.print_exc()


def register(p):
    if _IMPORT_ERROR is not None:
        print(f"[seg_dashboard] Plugin failed to import: {_IMPORT_ERROR}")
        return

    for cls in (
        DataAnalysisPanel,
        EvaluationPanel,
        CombinedPanel,
        ExperimentPanel,
        SchemaPanel,
    ):
        try:
            p.register(cls)
        except Exception as e:
            print(f"[seg_dashboard] Failed to register {cls.__name__}: {e}")
