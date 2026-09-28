"""棒グラフ(通常・積み上げ・100%積み上げ)の描画関数。"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.data_loader import numeric_series

# スタイル処理で積み上げ棒を見分けるための目印
STACK_META = "stack"
STACK100_META = "stack100"

# 1つの項目に棒を並べる幅(項目の間隔を1としたときの割合)
BAR_SPAN = 0.8


def add_bar_traces(
    fig: go.Figure,
    df,
    x_col: str,
    y_cols: list[str],
    orientation: str = "v",
    right_cols: tuple[str, ...] | list[str] = (),
    stack: str = "",
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)に棒を追加する。orientation は 'v'(縦) か 'h'(横)。

    right_cols に含まれる系列は右軸に描く(縦棒・積み上げなしのみ)。
    stack は ''(並べる)/ 'stack'(積み上げ)/ 'percent'(100%積み上げ)。
    積み上げは図全体の設定(barmode)に頼らず、各系列の開始位置(base)を計算して段ごとに行う。
    棒の位置と幅も自前で決める。X軸を共有する段どうしで Plotly が棒をまとめて並べ、
    ほかの段の棒のぶんだけ細く・ずれて描かれるのを防ぐため。
    """
    slot = BAR_SPAN / (1 if stack else max(len(y_cols), 1))
    values = {c: numeric_series(df, c).fillna(0) for c in y_cols}
    if stack == "percent":
        total = sum(values.values(), pd.Series(0.0, index=df.index)).replace(0, float("nan"))
        values = {c: (v / total * 100).fillna(0) for c, v in values.items()}
    base = pd.Series(0.0, index=df.index)

    for i, y_col in enumerate(y_cols):
        y_values = values[y_col] if stack else numeric_series(df, y_col)
        # 積み上げは全系列が同じ位置、並べるときは系列ごとに隣へずらす(左軸と右軸の棒も重ならない)
        kwargs: dict = {"name": y_col, "width": slot, "offset": -BAR_SPAN / 2 + (0 if stack else i * slot)}
        if stack:
            kwargs.update(base=base.tolist(), meta=STACK100_META if stack == "percent" else STACK_META)
            base = base + y_values

        if orientation == "h":
            fig.add_trace(go.Bar(y=df[x_col], x=y_values, orientation="h", **kwargs), row=row, col=col)
        else:
            fig.add_trace(
                go.Bar(x=df[x_col], y=y_values, **kwargs),
                row=row, col=col,
                secondary_y=True if y_col in right_cols and not stack else None,
            )

    # 年などの数値に見える見出しも、そのまま項目として並べる
    value_axis = {"ticksuffix": "%", "range": [0, 100]} if stack == "percent" else {}
    if orientation == "h":
        fig.update_yaxes(type="category", autorange="reversed", row=row, col=col)
        fig.update_xaxes(**value_axis, row=row, col=col)
    else:
        fig.update_xaxes(type="category", row=row, col=col)
        fig.update_yaxes(**value_axis, row=row, col=col, secondary_y=False)


def create_bar_chart(
    df,
    x_col: str,
    y_cols: list[str],
    orientation: str = "v",
    stacked: bool = False,
    title: str = "",
) -> go.Figure:
    """1段の縦棒/横棒グラフを作成する。"""
    fig = make_subplots(rows=1, cols=1)
    add_bar_traces(fig, df, x_col, y_cols, orientation=orientation, stack="stack" if stacked else "")
    fig.update_layout(title=title, barmode="group", legend_title_text="")
    return fig
