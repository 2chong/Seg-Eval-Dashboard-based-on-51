"""
plugins/seg_dashboard/sections/__init__.py
───────────────────────────────────────────
섹션 패키지 공개 API.

새 섹션을 추가하는 방법:

  [선언형 틀로 처리 가능한 경우]  ← 권장
    1. 필요하면 새 차트를 charts/ 에 추가하고 @register_chart(role) 를 붙인다.
    2. panels/*.py 의 SECTIONS 리스트에 FieldSection(...) 인스턴스를 직접 선언한다.
    → 별도 섹션 파일 불필요.

  [틀로 처리 불가한 경우]  ← 전용 섹션 파일 작성
    복수 데이터셋/실험 records 조합, 표(table), heatmap 등.
    1. PanelSection 서브클래스를 sections/ 아래 새 파일에 구현한다.
    2. 이 파일에 한 줄 임포트를 추가한다.
    3. 사용할 패널(panels/*.py)의 SECTIONS 리스트에 인스턴스를 추가한다.
"""

from .base import PanelSection
from .field_section import FieldSection          # 선언형 틀 (신규 섹션의 기본 선택)
from .confusion import ConfusionMatrixSection
from .summary import AttributeSummarySection
from .attribute import AttributeSection          # 하위 호환 — 내부적으로 FieldSection 반환
from .correlation import CorrelationSection
from .dataset_selector import DatasetSelectorSection
from .experiment_selector import ExperimentSelectorSection
from .experiment_compare import ExperimentCompareSection
from .metric_breakdown import MetricBreakdownSection  # 하위 호환 — 내부적으로 FieldSection 반환
from .records_table import RecordsTableSection
from .schema_table import SchemaTableSection
from .metric_dist import MetricDistributionSection
from .metric_summary import MetricSummarySection
from .attr_metric_compare import AttrMetricCompareSection
from .dataset_compare import DatasetCompareSection
from .multi_select import (
    MultiSelectSection,
    experiment_items,
    experiment_labels,
    dataset_items,
    dataset_labels,
)
from .section_label import SectionLabel, SampleCountSection

__all__ = [
    "PanelSection",
    "FieldSection",
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
    "MetricDistributionSection",
    "MetricSummarySection",
    "AttrMetricCompareSection",
    "DatasetCompareSection",
    "MultiSelectSection",
    "experiment_items",
    "experiment_labels",
    "dataset_items",
    "dataset_labels",
    "SectionLabel",
    "SampleCountSection",
]
