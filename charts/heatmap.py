"""ヒートマップ(クロス集計表)の描画関数。"""
from __future__ import annotations

import plotly.graph_objects as go

from core.data_loader import numeric_series

# 画面の選択肢 → Plotly のカラースケール名
COLOR_SCALES: dict[str, str] = {
    "青": "Blues",
    "緑": "Greens",
    "オレンジ": "Oranges",
    "赤": "Reds",
    "グレー(モノクロ印刷向け)": "Greys",
    "青→黄(色覚多様性に配慮)": "Viridis",
}


def add_heatmap_trace(
    fig: go.Figure,
    df,
    label_col: str,
    value_cols: list[str],
    color_scale: str = "青",
    show_scale: bool = True,
    labels_on_x: bool = False,
    row: int = 1,
    col: int = 1,
) -> None:
    """クロス集計表をヒートマップで描く。セルの値(件数)を色の濃さで表し、空欄は色を塗らない。

    labels_on_x が False のときは label_col の値(例:企業)を縦軸に、value_cols の列名(例:分野)を
    横軸に並べる。True のときはその逆(例:横軸に年、縦軸に分野)。
    """
    labels = [str(v) for v in df[label_col]]
    by_item = [[None if v != v else v for v in numeric_series(df, c).tolist()] for c in value_cols]
    if labels_on_x:
        x, y, z = labels, list(value_cols), by_item  # 行=項目、列=ラベル
    else:
        x, y, z = list(value_cols), labels, [list(r) for r in zip(*by_item)]  # 行=ラベル、列=項目
    label_ref = "x" if labels_on_x else "y"
    item_ref = "y" if labels_on_x else "x"
    fig.add_trace(
        go.Heatmap(
            x=x,
            y=y,
            z=z,
            name=", ".join(value_cols),
            colorscale=COLOR_SCALES.get(color_scale, "Blues"),
            showscale=show_scale,
            xgap=1,
            ygap=1,
            hovertemplate=f"{label_col}: %{{{label_ref}}}<br>%{{{item_ref}}}: %{{z:,}}<extra></extra>",
        ),
        row=row, col=col,
    )
    fig.update_xaxes(type="category", row=row, col=col)
    # 縦軸は表の順(一番上が先頭)に並べる
    fig.update_yaxes(type="category", autorange="reversed", row=row, col=col)
