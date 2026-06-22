"""
plugins/seg_dashboard/framework/widgets.py
───────────────────────────────────────────
UI 위젯 헬퍼: types.Object / panel 에 공통 컨트롤을 한 줄로 추가한다.

──────────────────────────────────────────────────────────────────────────────
언제 쓰는가
  섹션에서 아래 패턴이 반복될 때 헬퍼로 대체한다:

    before (드롭다운):
        choices = types.Dropdown(label="Metric")
        for m in metrics:
            choices.add_choice(m, label=_metric_label(m))
        grp.enum("metric", choices.values(), view=choices,
                 default=metric, on_change=cb.get("metric"))

    after:
        add_dropdown(grp, "metric", metrics, label="Metric",
                     default=metric, on_change=cb.get("metric"),
                     labels=_metric_label)

    before (bins 슬라이더):
        grp.int("bins", min=2, max=50,
                view=types.SliderView(label=f"Bins  (current: {bins})"),
                default=bins, on_change=cb.get("bins"))

    after:
        add_bins_slider(grp, "bins", value=bins, on_change=cb.get("bins"))

언제 인라인으로 두는가
  - FiftyOne 의 다른 view 타입(AutocompleteView, LabelValueView 등)이 필요할 때.
  - 멀티셀렉트 위젯 → MultiSelectSection 을 사용한다.
  - barmode, tickformat 등 드롭다운/슬라이더 이외의 특수 옵션이 필요할 때.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Callable

try:
    import fiftyone.operators.types as types
except ImportError:
    types = None  # type: ignore[assignment]


def add_dropdown(
    target,
    key: str,
    choices: list[str],
    *,
    label: str,
    default,
    on_change,
    labels: dict | Callable | None = None,
) -> None:
    """target 에 Dropdown 컨트롤을 추가한다.

    Args:
        target    : types.Object (grp) 또는 panel 등 .enum() 을 지원하는 객체.
        key       : 상태 키 이름 (컨테이너 기준 상대 경로).
        choices   : 드롭다운 선택지 값 목록.
        label     : 드롭다운 헤더 레이블.
        default   : 초기 선택값.
        on_change : on_change 콜백 (None 허용).
        labels    : 표시 이름 매핑.
                    dict[str, str]  → choice 별 표시 이름 (없으면 choice 그대로).
                    callable(str)->str → 각 choice 에 적용.
                    None            → choice 값 그대로 표시.
    """
    dd = types.Dropdown(label=label)
    for c in choices:
        if callable(labels):
            lbl = labels(c)
        elif isinstance(labels, dict):
            lbl = labels.get(c, c)
        else:
            lbl = c
        dd.add_choice(c, label=lbl)
    target.enum(key, dd.values(), view=dd, default=default, on_change=on_change)


def add_bins_slider(
    target,
    key: str,
    *,
    value: int,
    on_change,
    lo: int = 2,
    hi: int = 50,
) -> None:
    """target 에 Bins 슬라이더 컨트롤을 추가한다.

    Args:
        target    : types.Object (grp) 또는 panel.
        key       : 상태 키 이름.
        value     : 현재 bins 값 (슬라이더 레이블에도 표시됨).
        on_change : on_change 콜백.
        lo, hi    : 슬라이더 최솟값/최댓값 (기본 2–50).
    """
    target.int(
        key,
        min=lo,
        max=hi,
        view=types.SliderView(label=f"Bins  (current: {value})"),
        default=value,
        on_change=on_change,
    )


def resolve_col_type(
    field: str,
    columns: dict,
    records: list[dict],
) -> str | None:
    """field 의 col_type 을 "categorical" 또는 "numerical" 로 반환한다.

    판별 우선순위:
      1. columns 메타의 "type" 키 (config.py 에서 정의된 공식 타입).
      2. records 의 첫 번째 비-None 값으로 파이썬 타입 추론.
      3. 판별 불가 시 None.

    Args:
        field   : 판별할 필드 이름.
        columns : stats["columns"] dict (get_columns() 결과).
        records : get_records() 결과 list[dict].

    Returns:
        "categorical" | "numerical" | None
    """
    col_type = columns.get(field, {}).get("type")
    if col_type is not None:
        return col_type
    if not records:
        return None
    sample = next((r.get(field) for r in records if r.get(field) is not None), None)
    if sample is None:
        return None
    return "numerical" if isinstance(sample, (int, float)) else "categorical"
