"""
plugins/seg_dashboard/charts/__init__.py
─────────────────────────────────────────
차트 패키지 공개 API.

새 차트를 추가하는 방법:
  1. charts/ 아래 새 파일에 BaseChart 서브클래스를 구현한다.
  2. 이 파일에 한 줄 임포트를 추가한다.
  3. __all__ 에 이름을 등록한다.
"""

from .base import BaseChart, _empty_figure
from .confusion import ConfusionMatrixChart
from .distribution import AttributeDistributionChart
from .metric import (
    CategoricalMetricChart,
    NumericalMetricChart,
    _metric_label,
    CategoricalRecallChart,   # 구 이름 별칭
    NumericalRecallChart,     # 구 이름 별칭
)
from .summary import AttributeSummaryChart
from .correlation import CorrelationChart
from .table import RecordsTableChart, SchemaTableChart
from .grouped_metric import GroupedMetricChart

__all__ = [
    "BaseChart",
    "_empty_figure",
    "ConfusionMatrixChart",
    "AttributeDistributionChart",
    "CategoricalMetricChart",
    "NumericalMetricChart",
    "_metric_label",
    "AttributeSummaryChart",
    "CorrelationChart",
    "RecordsTableChart",
    "SchemaTableChart",
    "GroupedMetricChart",
    # 구 이름 별칭
    "CategoricalRecallChart",
    "NumericalRecallChart",
]
