"""
plugins/seg_dashboard/charts/_common.py
─────────────────────────────────────────
차트 공유 상수.

여러 차트에서 중복 선언되던 값을 단일 소스로 유지한다.
차트 파일은 여기서 임포트해서 사용한다.
"""

# 실험·데이터셋 비교 차트(trace 별 색)에 사용하는 팔레트 (8색 순환).
# cross_exp_metric.py / dataset_compare.py 에서 중복 선언되던 것을 통합.
_COLORS: list[str] = [
    "steelblue", "tomato", "seagreen", "darkorange",
    "mediumpurple", "sienna", "deeppink", "teal",
]
