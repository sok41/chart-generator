"""複数段レイアウト・2軸のテスト。"""
import pandas as pd

from core.layout import AxisSpec, PanelSpec, build_figure
from core.style import ChartStyle, apply_style

DF = pd.DataFrame(
    {
        "年": ["2020", "2021", "2022"],
        "件数": ["120", "145", "160"],
        "累積件数": ["120", "265", "425"],
    }
)


def _two_rows():
    panels = [
        PanelSpec("棒", "年", ["件数"], subtitle="上段"),
        PanelSpec(
            "折れ線", "年", ["件数", "累積件数"], right_cols=["累積件数"],
            right_axis=AxisSpec(title="累積", min=0, suffix="件", number_format="桁区切り(1,234)"),
        ),
    ]
    return build_figure(DF, panels, "上下2段", share_x=True, first_row_ratio=0.6, title="推移")


def test_two_rows_bar_top_line_bottom_with_right_axis():
    fig = _two_rows()
    types = [(t.type, t.xaxis, t.yaxis) for t in fig.data]
    assert types[0] == ("bar", "x", "y")
    assert types[1][0] == "scatter" and types[1][1] == "x2"
    # 累積件数は下段の右軸(左軸とは別のY軸)に描かれる
    right_axis = fig.layout[f"yaxis{fig.data[2].yaxis[1:]}"]
    assert fig.data[2].yaxis != fig.data[1].yaxis
    assert right_axis.overlaying is not None
    assert right_axis.title.text == "累積"
    assert right_axis.ticksuffix == "件"
    assert right_axis.tickformat == ",.0f"
    assert list(right_axis.range) == [0, None]


def test_shared_x_and_row_ratio():
    fig = _two_rows()
    assert fig.layout.xaxis.matches == "x2"
    top_height = fig.layout.yaxis.domain[1] - fig.layout.yaxis.domain[0]
    bottom_height = fig.layout.yaxis2.domain[1] - fig.layout.yaxis2.domain[0]
    assert top_height > bottom_height


def test_same_series_shown_once_in_legend():
    fig = apply_style(_two_rows(), ChartStyle())
    shown = [t.name for t in fig.data if t.showlegend]
    assert shown == ["件数", "累積件数"]
    # 同じ系列は段が違っても同じ色
    assert fig.data[0].marker.color == fig.data[1].line.color


def test_frame_color_and_no_grid_on_right_axis():
    fig = apply_style(_two_rows(), ChartStyle(frame_color="#123456"))
    right_axis = fig.layout[f"yaxis{fig.data[2].yaxis[1:]}"]
    assert fig.layout.yaxis.linecolor == "#123456"
    assert fig.layout.yaxis.mirror is True
    assert right_axis.showgrid is False


def test_horizontal_bar_ignores_right_axis():
    panel = PanelSpec("棒", "年", ["件数", "累積件数"], orientation="h", right_cols=["累積件数"])
    fig = build_figure(DF, [panel], "1段")
    assert all(t.orientation == "h" for t in fig.data)
    assert all(t.yaxis in (None, "y") for t in fig.data)


def test_combo_and_2x2_layout():
    combo = PanelSpec("棒+折れ線", "年", ["件数", "累積件数"], line_cols=["累積件数"])
    fig = build_figure(DF, [combo] * 4, "2×2")
    assert [t.type for t in fig.data] == ["bar", "scatter"] * 4
