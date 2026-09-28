"""棒+折れ線の複合グラフの描画関数。"""
from __future__ import annotations

import plotly.graph_objects as go

from charts.bar import add_bar_traces
from charts.line import add_line_traces


def add_combo_traces(
    fig: go.Figure,
    df,
    x_col: str,
    y_cols: list[str],
    line_cols: tuple[str, ...] | list[str] = (),
    right_cols: tuple[str, ...] | list[str] = (),
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)に、line_cols の系列を折れ線、それ以外を棒として追加する。"""
    bar_cols = [c for c in y_cols if c not in line_cols]
    lines = [c for c in y_cols if c in line_cols]
    add_bar_traces(fig, df, x_col, bar_cols, right_cols=right_cols, row=row, col=col)
    add_line_traces(fig, df, x_col, lines, right_cols=right_cols, row=row, col=col)
