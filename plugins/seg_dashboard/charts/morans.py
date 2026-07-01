"""
plugins/seg_dashboard/charts/morans.py
────────────────────────────────────────
Moran's I 공간자기상관 지수 가로 막대 차트.

비-디스패치 차트 (EXTENDING 레시피 6-B).
  - 선택 없이 전체 필드의 I 값을 한눈에 표시한다.
  - I > 0 (양의 군집), I < 0 (음의 군집), I ≈ 0 (랜덤)
  - 막대 색: I 부호에 따라 RdBu (파랑=양의 군집, 빨강=음의 군집)
  - hover: I 값, p값, 유의성(p<0.05)
  - FiftyOne import 금지 (numpy 전용)
  - {"data": [...], "layout": {...}} 반환
  - 데이터 없으면 _empty_figure(msg) 반환
"""

from __future__ import annotations

from .base import BaseChart, _empty_figure

_PLACEHOLDER = (
    "Moran's I data not available.<br>"
    "manifest.json 에 patch_id / geo 블록이 있는 데이터셋에서만 표시됩니다.<br>"
    "Re-run make regen-stats to generate spatial block."
)


class MoransIChart(BaseChart):
    """Moran's I 가로 막대 차트.

    spatial["morans_i"] = {field: {"I": float, "p": float, "n": int}}
    """

    def build_figure(
        self,
        stats: dict,
        field: str | None = None,
        params: dict | None = None,
    ) -> dict:
        params = params or {}
        spatial = params.get("spatial", {})

        if not spatial or not spatial.get("has_geo"):
            return _empty_figure(_PLACEHOLDER)

        morans = spatial.get("morans_i", {})
        if not morans:
            return _empty_figure("Moran's I 데이터가 없습니다.")

        # None 값 제외 후 I 절댓값 내림차순 정렬
        items = [
            (f, v) for f, v in morans.items()
            if v.get("I") is not None
        ]
        items.sort(key=lambda x: abs(x[1]["I"]), reverse=True)

        if not items:
            return _empty_figure("Moran's I 계산 결과가 없습니다.")

        fields   = [f for f, _ in items]
        I_values = [v["I"] for _, v in items]
        p_values = [v.get("p") for _, v in items]
        n_values = [v.get("n") for _, v in items]

        # 막대 색: I > 0 → 파랑 계열, I < 0 → 빨강 계열, |I| 로 채도
        colors = []
        for i_val in I_values:
            if i_val >= 0:
                # 0→연파랑, 1→진파랑
                intensity = int(min(255, 100 + 155 * i_val))
                colors.append(f"rgba(30, 100, {intensity}, 0.85)")
            else:
                # 0→연빨강, -1→진빨강
                intensity = int(min(255, 100 + 155 * abs(i_val)))
                colors.append(f"rgba({intensity}, 50, 30, 0.85)")

        hover_texts = []
        for f, i_val, p_val, n_val in zip(fields, I_values, p_values, n_values):
            sig = "p < 0.05 (유의)" if (p_val is not None and p_val < 0.05) else "n.s."
            p_str = f"{p_val:.3f}" if p_val is not None else "N/A"
            hover_texts.append(
                f"<b>{f}</b><br>"
                f"Moran's I: {i_val:.4f}<br>"
                f"p-value: {p_str}  [{sig}]<br>"
                f"n: {n_val}"
            )

        trace = {
            "type": "bar",
            "orientation": "h",
            "x": I_values,
            "y": fields,
            "text": hover_texts,
            "hovertemplate": "%{text}<extra></extra>",
            "marker": {"color": colors},
        }

        layout = {
            "title": {"text": "Moran's I — Spatial Autocorrelation Index"},
            "xaxis": {
                "title": "Moran's I",
                "range": [-1.05, 1.05],
                "zeroline": True,
                "zerolinecolor": "#888",
                "zerolinewidth": 1.5,
            },
            "yaxis": {
                "title": "",
                "autorange": "reversed",
            },
            "height": max(300, 60 + 35 * len(fields)),
            "margin": {"t": 50, "b": 60, "l": max(80, 10 * max(len(f) for f in fields))},
            "annotations": [{
                "x": 1.02, "y": 0.98,
                "xref": "paper", "yref": "paper",
                "text": "I>0: 군집  I<0: 분산",
                "showarrow": False,
                "font": {"size": 10, "color": "#666"},
                "xanchor": "left",
            }],
        }

        return {"data": [trace], "layout": layout}
