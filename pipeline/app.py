"""
pipeline/app.py
───────────────
역할: FiftyOne App 실행 + 사용법 안내

  launch(dataset)  — fo.launch_app() 호출 후 session.wait() 로 App 유지.
                     Ctrl+C 로 종료.

App 에서 확인 가능한 것:
  - 이미지 그리드 + GT/예측 마스크 오버레이 (ground_truth, predictions_<exp> 필드)
  - Sample Attributes 사이드바 그룹: time, complexity, count, brightness, density 등
  - Metrics · {model} 사이드바 그룹 (experiment 당 1개):
      recall_{exp}, precision_{exp}, accuracy_{exp}  ← fiftyone_eval
      f1_{exp}, f2_{exp}, biou_{exp}                 ← derived/mask
  - Segmentation Dashboard 패널 (tools/precompute_panel_stats.py 실행 후)
"""

from __future__ import annotations

try:
    import fiftyone as fo
except ImportError as exc:
    import sys
    sys.exit(f"FiftyOne not installed.\nError: {exc}")


def configure_sidebar(dataset: fo.Dataset) -> None:
    """App 사이드바 그룹을 의미 단위로 나눠 정의한다.

    속성 목록은 config.PANEL_COLUMN_META (kind="attribute") 에서 동적으로 읽는다.
    새 속성이나 새 평가지표가 추가되면 여기 코드 수정 없이 자동 반영된다.
    """
    import config as _cfg

    schema = dataset.get_field_schema()

    # ── 마스크 레이블 필드 ─────────────────────────────────────────────────────
    pred_fields = [
        f"predictions_{exp}" for exp in _cfg.EXPERIMENTS
        if f"predictions_{exp}" in schema
    ]

    # ── 속성 필드 (PANEL_COLUMN_META 기반, 실제 schema 에 있는 것만) ────────────
    attr_fields = [
        name for name in schema
        if _cfg.PANEL_COLUMN_META.get(name, {}).get("kind") == "attribute"
    ]

    groups = [
        fo.SidebarGroupDocument(name="tags"),
        fo.SidebarGroupDocument(name="metadata"),
        fo.SidebarGroupDocument(name="Labels", paths=pred_fields + ["ground_truth"]),
    ]
    if attr_fields:
        groups.append(
            fo.SidebarGroupDocument(name="Sample Attributes", paths=attr_fields)
        )

    # ── experiment 별 평가 메트릭 필드 ({metric}_{exp} 패턴, 수치형만) ──────────
    for exp_name, exp_cfg in _cfg.EXPERIMENTS.items():
        exp_label  = exp_cfg.get("label", exp_name)
        suffix     = f"_{exp_name}"
        exp_fields = sorted(
            f for f, ftype in schema.items()
            if f.endswith(suffix) and isinstance(ftype, (fo.FloatField, fo.IntField))
        )
        if exp_fields:
            groups.append(
                fo.SidebarGroupDocument(name=f"Metrics · {exp_label}", paths=exp_fields)
            )

    dataset.app_config.sidebar_groups = groups
    dataset.save()


def launch(dataset: fo.Dataset) -> None:
    """FiftyOne App 을 실행하고 사용자가 Ctrl+C 로 종료할 때까지 대기한다."""
    print("\n" + "=" * 70)
    print("  FiftyOne App")
    print("=" * 70)
    print("  브라우저에서 열기: http://localhost:5151")
    print()
    print("  [마스크 오버레이]")
    print("  → 썸네일 클릭 → 좌측 Labels 패널에서")
    print("    ground_truth / predictions 눈 아이콘으로 각각 on/off")
    print()
    print("  [Filters 사이드바 그룹]")
    print("  → Sample Attributes  : time, complexity, count, brightness, density 등")
    print("  → Metrics · {model}  : recall_{exp}, precision_{exp}, f1_{exp}, biou_{exp} 등")
    print("  → 위 필드로 정렬(Sort by)도 가능")
    print()
    print("  [5개 분석 패널]  App 우상단 '+' 에서 열기 (Panels 탭)")
    print("  → ① Data Analysis   : 속성 요약 + 분포 차트")
    print("  → ② Evaluation      : experiment 선택 + Confusion Matrix")
    print("  → ③ Combined        : 속성 × 메트릭 분석 + 상관 heatmap")
    print("  → ④ Experiment      : experiment 간 per-class 메트릭 비교")
    print("  → ⑤ Schema & Table  : 컬럼 스키마 + per-sample 표")
    print("  ※ panel_stats.json 없으면 먼저:")
    print("     python tools/precompute_panel_stats.py")
    print()
    print("  종료: 터미널에서 Ctrl+C")
    print("=" * 70 + "\n")

    # 사이드바는 _build_all_datasets 루프에서 이미 각 데이터셋별로 설정됐다.
    # 여기선 활성 데이터셋에 대해 한 번 더 실행해 최신 상태를 보장한다.
    configure_sidebar(dataset)
    session = fo.launch_app(dataset)
    session.wait()
