"""ライフサイクル図の描画関数。

横軸に参加数(企業数など)、縦軸に件数(量)をとり、年の順に点を線で結ぶ。
右上へ伸びていれば成長期、左下へ戻っていれば衰退期、と市場や分野の段階を読み取る。
"""
from __future__ import annotations

import plotly.graph_objects as go

from core.data_loader import numeric_series

# スタイル処理でライフサイクル図を見分けるための目印
LIFECYCLE_META = "lifecycle"


def _padded_range(values: list[float], ratio: float) -> list[float] | None:
    values = [v for v in values if v == v]
    if not values:
        return None
    lo, hi = min(values), max(values)
    span = (hi - lo) or abs(hi) or 1
    return [lo - span * ratio, hi + span * ratio]


def add_lifecycle_trace(
    fig: go.Figure,
    df,
    year_col: str,
    participants_col: str,
    count_col: str,
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)にライフサイクル図を追加する(最後の点は進む向きの矢印)。"""
    x = numeric_series(df, participants_col).tolist()
    y = numeric_series(df, count_col).tolist()
    years = [str(v) for v in df[year_col]]
    symbols = ["circle"] * (len(years) - 1) + ["arrow"]
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            text=years,
            name=count_col,
            meta=LIFECYCLE_META,
            mode="lines+markers+text",
            textposition="top center",
            marker=dict(symbol=symbols, angleref="previous", size=[7] * (len(years) - 1) + [14]),
            hovertemplate=(f"%{{text}}<br>{participants_col}: %{{x:,}}<br>"
                           f"{count_col}: %{{y:,}}<extra></extra>"),
        ),
        row=row, col=col,
    )
    # 年のラベルが枠からはみ出さないよう、上下左右に余裕をとる
    fig.update_xaxes(type="linear", title_text=participants_col, range=_padded_range(x, 0.08),
                     row=row, col=col)
    fig.update_yaxes(title_text=count_col, range=_padded_range(y, 0.15), row=row, col=col)
