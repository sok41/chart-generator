"""スタイル適用のテスト。"""
import pandas as pd

from charts.bar import create_bar_chart
from charts.line import create_line_chart
from core.style import ChartStyle, apply_style

DF = pd.DataFrame({"年": ["2020", "2021"], "件数": [10, 20], "累積件数": [10, 30]})


def test_series_color_and_fonts_applied():
    fig = create_bar_chart(DF, "年", ["件数", "累積件数"], title="推移")
    style = ChartStyle(series_colors={"累積件数": "#123456"}, font_color="#AA0000", title_size=30)
    apply_style(fig, style)
    assert fig.data[1].marker.color == "#123456"
    assert fig.layout.font.color == "#AA0000"
    assert fig.layout.title.font.size == 30


def test_grid_x_and_y_switch_separately():
    fig = create_bar_chart(DF, "年", ["件数"], orientation="h")
    apply_style(fig, ChartStyle(grid_color="#00FF00", grid_x=True, grid_y=False))
    assert fig.layout.xaxis.showgrid is True
    assert fig.layout.xaxis.gridcolor == "#00FF00"
    assert fig.layout.yaxis.showgrid is False


def test_line_labels_and_hidden_legend():
    fig = create_line_chart(DF, "年", ["件数"])
    apply_style(fig, ChartStyle(data_labels=True, legend_position="非表示"))
    assert fig.data[0].mode == "lines+markers+text"
    assert fig.layout.showlegend is False


def test_default_frame_color_is_between_font_and_grid():
    from core.style import mix_colors

    assert mix_colors("#000000", "#FFFFFF") == "#808080"
    assert ChartStyle().frame_color == "#929292"  # #434343 と #E0E0E0 の中間
    assert ChartStyle(font_color="#000000", grid_color="#FFFFFF").frame_color == "#808080"
    assert ChartStyle(frame_color="#FF0000").frame_color == "#FF0000"


def test_no_outside_ticks_and_labels_not_clipped():
    fig = create_line_chart(DF, "年", ["件数"])
    apply_style(fig, ChartStyle(data_labels=True))
    assert fig.layout.xaxis.ticks == ""
    assert fig.layout.yaxis.ticks == ""
    assert fig.data[0].cliponaxis is False


def test_data_labels_per_panel():
    from core.layout import PanelSpec, build_figure

    panels = [PanelSpec("折れ線", "年", ["件数"]), PanelSpec("積み上げ棒", "年", ["件数"])]
    fig = build_figure(DF, panels, "上下2段")
    apply_style(fig, ChartStyle(panel_labels=[True, False]))
    assert fig.data[0].mode == "lines+markers+text"  # 上段はラベルあり
    assert fig.data[1].texttemplate is None  # 下段はラベルなし


def test_palettes():
    from core.style import CATEGORICAL_PALETTES, PALETTE_CHOICES, palette_colors

    assert len(palette_colors("グラデーション:青", 5)) == 5
    blues = palette_colors("グラデーション:青", 3)
    assert blues[0] < blues[-1]  # 先頭ほど濃い(#08... のように値が小さい)
    assert palette_colors("グラデーション:青", 3, reverse=True) == blues[::-1]
    okabe = CATEGORICAL_PALETTES["色覚多様性に配慮(Okabe-Ito)"]
    assert palette_colors("配色:色覚多様性に配慮(Okabe-Ito)", 10)[8] == okabe[0]  # 足りなければ繰り返す
    for choice in PALETTE_CHOICES:
        assert all(c.startswith("#") and len(c) == 7 for c in palette_colors(choice, 4))

    # パレットは系列の既定色とツリーマップの色分けに使われる
    fig = create_bar_chart(DF, "年", ["件数", "累積件数"])
    apply_style(fig, ChartStyle(palette=["#111111", "#222222"]))
    assert fig.data[1].marker.color == "#222222"
    assert list(fig.layout.treemapcolorway) == ["#111111", "#222222"]
