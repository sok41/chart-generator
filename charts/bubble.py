"""バブルチャート(クロス集計表)の描画関数。"""
from __future__ import annotations

import plotly.graph_objects as go

from core.data_loader import numeric_series

# スタイル処理でバブルを見分けるための目印
BUBBLE_META = "bubble"


def add_bubble_traces(
    fig: go.Figure,
    df,
    label_col: str,
    value_cols: list[str],
    max_size: int = 30,
    labels_on_x: bool = True,
    row: int = 1,
    col: int = 1,
) -> None:
    """クロス集計表をバブルで描く。セルの値(件数)を円の面積で表す。

    labels_on_x が True のときは label_col の値(年など)を横軸に、value_cols の列名(項目)を縦軸に並べる。
    False のときはその逆(例:縦軸に企業、横軸に分野)。1つの列(項目)が1系列で、列ごとに色が付く。
    """
    labels = [str(v) for v in df[label_col]]
    columns = {c: numeric_series(df, c).fillna(0).clip(lower=0) for c in value_cols}
    max_value = max((float(s.max()) for s in columns.values()), default=0) or 1
    # sizemode="area" では、sizeref = 2 × 最大値 / 最大直径² で最大の円が max_size px になる
    sizeref = 2 * max_value / (max_size ** 2)

    for c, values in columns.items():
        positions = (labels, [c] * len(labels)) if labels_on_x else ([c] * len(labels), labels)
        fig.add_trace(
            go.Scatter(
                x=positions[0],
                y=positions[1],
                mode="markers",
                name=c,
                meta=BUBBLE_META,
                customdata=values.tolist(),
                marker=dict(size=values.tolist(), sizemode="area", sizeref=sizeref, sizemin=0,
                            line=dict(width=0)),
                hovertemplate=f"{label_col}: %{{{'x' if labels_on_x else 'y'}}}<br>{c}: %{{customdata:,}}"
                              "<extra></extra>",
            ),
            row=row, col=col,
        )

    label_axis = dict(type="category", categoryorder="array", categoryarray=labels)
    # 項目の軸は、表の左の列(縦軸なら一番上)から順に並べる
    item_axis = dict(type="category", categoryorder="array", categoryarray=list(value_cols))
    if labels_on_x:
        fig.update_xaxes(**label_axis, row=row, col=col)
        fig.update_yaxes(**item_axis, autorange="reversed", row=row, col=col)
    else:
        fig.update_xaxes(**item_axis, row=row, col=col)
        fig.update_yaxes(**label_axis, autorange="reversed", row=row, col=col)
