"""
plugins/seg_dashboard/panels/__init__.py
─────────────────────────────────────────
5개 구체 패널 공개 API.

새 패널 추가:
  1. panels/<이름>.py 에 BasePanel 서브클래스 작성
  2. 이 파일에 임포트 한 줄 추가
  3. seg_dashboard/__init__.py 의 register() 에 패널 추가
  4. fiftyone.yml 의 panels: 에 PANEL_NAME 추가
"""

from .data_analysis import DataAnalysisPanel
from .evaluation import EvaluationPanel
from .combined import CombinedPanel
from .experiment import ExperimentPanel
from .schema import SchemaPanel

__all__ = [
    "DataAnalysisPanel",
    "EvaluationPanel",
    "CombinedPanel",
    "ExperimentPanel",
    "SchemaPanel",
]
