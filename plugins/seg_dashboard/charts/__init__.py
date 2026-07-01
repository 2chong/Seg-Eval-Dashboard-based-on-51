"""
plugins/seg_dashboard/charts/__init__.py
─────────────────────────────────────────
차트 패키지 공개 API.

새 차트를 추가하는 방법:
  1. charts/ 아래 새 파일에 BaseChart 서브클래스를 구현한다.
  2. @register_chart(role) 데코레이터를 붙인다 (field_types 있는 차트).
  3. 이 파일에 한 줄 임포트를 추가한다.
  4. __all__ 에 이름을 등록한다.

chart_for(role, col_type):
  섹션에서 categorical/numerical 분기 없이 차트 클래스를 얻는 API.
  이 __init__ 을 통해 임포트하면 모든 @register_chart 가 이미 실행된 상태가 된다.
"""

from .base import BaseChart, _empty_figure
from .registry import register_chart, chart_for
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
from .metric_dist import MetricDistributionChart
from .cross_exp_metric import CrossExpCategoricalChart, CrossExpNumericalChart
from .dataset_compare import DatasetCompareCategoricalChart, DatasetCompareNumericalChart
from .spatial_grid import GridHeatmapChart
from .spatial_scatter import GeoScatterChart
from .morans import MoransIChart

__all__ = [
    "BaseChart",
    "_empty_figure",
    "register_chart",
    "chart_for",
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
    "MetricDistributionChart",
    "CrossExpCategoricalChart",
    "CrossExpNumericalChart",
    "DatasetCompareCategoricalChart",
    "DatasetCompareNumericalChart",
    # 구 이름 별칭
    "CategoricalRecallChart",
    "NumericalRecallChart",
    # Spatial charts
    "GridHeatmapChart",
    "GeoScatterChart",
    "MoransIChart",
]
