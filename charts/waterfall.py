"""ウォーターフォールチャートの描画関数。"""
from __future__ import annotations

import plotly.graph_objects as go

from core.data_loader import numeric_series

# 値の意味
WATERFALL_MODES = ["各時点の水準(前との差を自動計算)", "増減量"]


def waterfall_steps(values: list, mode: str, add_total: bool) -> tuple[list, list[str]]:
    """棒の長さ(y)と種類(measure)を返す。

    - 水準モード:先頭を基準の棒(absolute)とし、以降は前との差(relative)を積み上げる。
    - 増減量モード:すべての値をそのまま増減として積み上げる。
    add_total が True のとき、最後に合計(到達点)の棒を追加する。
    """
    values = [0.0 if v is None or v != v else float(v) for v in values]
    if mode == WATERFALL_MODES[0] and values:
        # 3284.1 - 3208.2 = 75.8999… のような誤差が表示に出ないよう丸める
        steps = [values[0]] + [round(b - a, 10) for a, b in zip(values, values[1:])]
        measures = ["absolute"] + ["relative"] * (len(values) - 1)
    else:
        steps = values
        measures = ["relative"] * len(values)
    if add_total:
        steps = steps + [0.0]
        measures = measures + ["total"]
    return steps, measures


def add_waterfall_traces(
    fig: go.Figure,
    df,
    x_col: str,
    y_cols: list[str],
    mode: str = WATERFALL_MODES[0],
    add_total: bool = False,
    total_label: str = "合計",
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)にウォーターフォールを追加する(系列ごとに1本)。"""
    x_values = [str(v) for v in df[x_col]]
    if add_total:
        x_values = x_values + [total_label]
    for y_col in y_cols:
        steps, measures = waterfall_steps(numeric_series(df, y_col).tolist(), mode, add_total)
        fig.add_trace(
            go.Waterfall(x=x_values, y=steps, measure=measures, name=y_col),
            row=row, col=col,
        )
    fig.update_xaxes(type="category", row=row, col=col)
