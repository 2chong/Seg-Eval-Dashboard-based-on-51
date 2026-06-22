"""
plugins/seg_dashboard/charts/registry.py
──────────────────────────────────────────
차트 레지스트리: (role, col_type) → ChartClass 디스패치.

죽어 있던 BaseChart.is_applicable / field_types 를 살아있는 디스패치로 전환한다.
Voxel51 Dashboard 플러그인의 "차트 타입 선택을 데이터 정의에서 분리" 아이디어를 차용.

──────────────────────────────────────────────────────────────────────────────
언제 쓰는가
  섹션에서 categorical/numerical 조건분기 없이 차트를 선택할 때.

    before:
        if col_type == "categorical":
            fig = CategoricalMetricChart().build_figure(...)
        else:
            fig = NumericalMetricChart().build_figure(...)

    after:
        fig = chart_for("metric", col_type)().build_figure(...)

언제 쓰지 않는가
  field_types 가 없거나 col_type 개념이 없는 차트
  (GroupedMetricChart, ConfusionMatrixChart, CorrelationChart, 표류 등).
  그런 차트는 직접 임포트해서 사용한다.
──────────────────────────────────────────────────────────────────────────────

등록된 role 목록:
  "distribution"    AttributeDistributionChart        (categorical + numerical)
  "metric"          CategoricalMetricChart            (categorical)
                    NumericalMetricChart              (numerical)
  "cross_exp"       CrossExpCategoricalChart          (categorical)
                    CrossExpNumericalChart            (numerical)
  "dataset_compare" DatasetCompareCategoricalChart    (categorical)
                    DatasetCompareNumericalChart      (numerical)
  "metric_dist"     MetricDistributionChart           (numerical)

새 차트를 추가할 때:
  @register_chart("my_role")
  class MyCategoricalChart(BaseChart):
      field_types = ("categorical",)
  그러면 chart_for("my_role", "categorical") 로 즉시 사용 가능.
"""

from __future__ import annotations

_REGISTRY: dict[tuple[str, str], type] = {}


def register_chart(role: str):
    """BaseChart 서브클래스를 (role, field_type) 쌍으로 레지스트리에 등록하는 데코레이터.

    Args:
        role : 섹션이 사용하는 역할 이름 (예: "metric", "distribution").
               chart_for(role, col_type) 호출 시의 첫 번째 인수.

    사용 예:
        @register_chart("metric")
        class CategoricalMetricChart(BaseChart):
            field_types = ("categorical",)
        # → _REGISTRY[("metric", "categorical")] = CategoricalMetricChart
    """
    def decorator(cls):
        for field_type in getattr(cls, "field_types", ()):
            _REGISTRY[(role, field_type)] = cls
        return cls
    return decorator


def chart_for(role: str, col_type: str) -> type:
    """(role, col_type) 에 등록된 차트 클래스를 반환한다.

    섹션에서 categorical/numerical if-else 분기를 제거하는 핵심 API.

    Args:
        role     : "distribution" / "metric" / "cross_exp" /
                   "dataset_compare" / "metric_dist"
        col_type : "categorical" / "numerical"

    Returns:
        등록된 BaseChart 서브클래스 (미인스턴스화).

    Raises:
        KeyError : 등록된 차트가 없을 때.
                   @register_chart 데코레이터 누락 또는 role/col_type 오타 확인.
    """
    key = (role, col_type)
    if key not in _REGISTRY:
        raise KeyError(
            f"No chart registered for role={role!r}, col_type={col_type!r}. "
            f"Registered keys: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[key]
