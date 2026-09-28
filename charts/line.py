"""折れ線グラフの描画関数。"""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.data_loader import numeric_series


def add_line_traces(
    fig: go.Figure,
    df,
    x_col: str,
    y_cols: list[str],
    right_cols: tuple[str, ...] | list[str] = (),
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)に折れ線を追加する。right_cols に含まれる系列は右軸に描く。"""
    for y_col in y_cols:
        fig.add_trace(
            go.Scatter(x=df[x_col], y=numeric_series(df, y_col), mode="lines+markers", name=y_col),
            row=row, col=col, secondary_y=True if y_col in right_cols else None,
        )

    # 年などの数値に見える見出しも、そのまま項目として並べる
    fig.update_xaxes(type="category", row=row, col=col)


def create_line_chart(df, x_col: str, y_cols: list[str], title: str = "") -> go.Figure:
    """1段の折れ線グラフを作成する。"""
    fig = make_subplots(rows=1, cols=1)
    add_line_traces(fig, df, x_col, y_cols)
    fig.update_layout(title=title, legend_title_text="")
    return fig
