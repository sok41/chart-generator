"""円グラフ・ドーナツグラフの描画関数。"""
from __future__ import annotations

import plotly.graph_objects as go

from core.data_loader import numeric_series


def add_pie_trace(
    fig: go.Figure,
    df,
    label_col: str,
    value_col: str,
    donut: bool = False,
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)に円グラフを追加する。表の順に12時の位置から時計回りに並べる。"""
    fig.add_trace(
        go.Pie(
            labels=[str(v) for v in df[label_col]],
            values=numeric_series(df, value_col).fillna(0).clip(lower=0).tolist(),
            name=value_col,
            hole=0.5 if donut else 0,
            sort=False,
            direction="clockwise",
        ),
        row=row, col=col,
    )
