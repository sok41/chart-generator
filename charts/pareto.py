"""パレート図の描画関数。

項目(企業名など)を件数の多い順に棒で並べ、累積比率を右軸の折れ線で重ねる。
上位何社で全体の何割を占めるか(寡占度)を読み取るのに使う。
"""
from __future__ import annotations

import plotly.graph_objects as go

from charts.bar import BAR_SPAN
from core.data_loader import numeric_series

CUMULATIVE_NAME = "累積比率"
# スタイル処理で累積比率の折れ線を見分けるための目印
PARETO_LINE_META = "pareto_line"
PARETO_BAR_META = "pareto_bar"


def pareto_values(labels: list[str], values: list[float], sort_desc: bool = True):
    """(並べ替えた項目, 値, 累積比率[%]) を返す。"""
    pairs = [(label, 0.0 if v != v or v is None else float(v)) for label, v in zip(labels, values)]
    if sort_desc:
        pairs.sort(key=lambda p: p[1], reverse=True)
    total = sum(v for _, v in pairs) or 1
    cumulative, running = [], 0.0
    for _, v in pairs:
        running += v
        cumulative.append(round(running / total * 100, 10))
    return [p[0] for p in pairs], [p[1] for p in pairs], cumulative


def add_pareto_traces(
    fig: go.Figure,
    df,
    label_col: str,
    value_col: str,
    sort_desc: bool = True,
    guide_line: float | None = 80,
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)にパレート図を追加する(この段は右軸付きで作っておくこと)。"""
    labels, values, cumulative = pareto_values(
        [str(v) for v in df[label_col]], numeric_series(df, value_col).tolist(), sort_desc
    )
    fig.add_trace(go.Bar(x=labels, y=values, name=value_col, meta=PARETO_BAR_META,
                         width=BAR_SPAN, offset=-BAR_SPAN / 2),
                  row=row, col=col, secondary_y=False)
    fig.add_trace(
        go.Scatter(x=labels, y=cumulative, name=CUMULATIVE_NAME, meta=PARETO_LINE_META,
                   mode="lines+markers"),
        row=row, col=col, secondary_y=True,
    )
    if guide_line:
        # add_hline は同じ図に円グラフなどがあると使えないので、軸を指定して線を引く
        subplot = fig.get_subplot(row, col, secondary_y=True)
        x_ref = subplot.xaxis.plotly_name.replace("axis", "")
        y_ref = subplot.yaxis.plotly_name.replace("axis", "")
        fig.add_shape(type="line", xref=f"{x_ref} domain", x0=0, x1=1, yref=y_ref, y0=guide_line,
                      y1=guide_line, line=dict(dash="dash", width=1, color="#999999"))

    fig.update_xaxes(type="category", categoryorder="array", categoryarray=labels, row=row, col=col)
    ticks = [0, 20, 40, 60, 80, 100]
    fig.update_yaxes(range=[0, 105], tickmode="array", tickvals=ticks, ticktext=[f"{t}%" for t in ticks],
                     row=row, col=col, secondary_y=True)
