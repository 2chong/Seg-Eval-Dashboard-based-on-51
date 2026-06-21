"""
plugins/seg_dashboard/sections/__init__.py
───────────────────────────────────────────
섹션 패키지 공개 API.

새 섹션을 추가하는 방법:
  1. sections/ 아래 새 파일에 PanelSection 서브클래스를 구현한다.
  2. 이 파일에 한 줄 임포트를 추가한다.
  3. 사용할 패널(panels/*.py)의 SECTIONS 리스트에 인스턴스를 추가한다.
"""

from .base import PanelSection
from .confusion import ConfusionMatrixSection
from .summary import AttributeSummarySection
from .attribute import AttributeSection
from .correlation import CorrelationSection
from .dataset_selector import DatasetSelectorSection
from .experiment_selector import ExperimentSelectorSection
from .experiment_compare import ExperimentCompareSection
from .metric_breakdown import MetricBreakdownSection
from .records_table import RecordsTableSection
from .schema_table import SchemaTableSection

__all__ = [
    "PanelSection",
    "ConfusionMatrixSection",
    "AttributeSummarySection",
    "AttributeSection",
    "CorrelationSection",
    "DatasetSelectorSection",
    "ExperimentSelectorSection",
    "ExperimentCompareSection",
    "MetricBreakdownSection",
    "RecordsTableSection",
    "SchemaTableSection",
]
