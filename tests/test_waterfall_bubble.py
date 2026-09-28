"""ウォーターフォールとバブルのテスト。"""
import pandas as pd

from charts.waterfall import WATERFALL_MODES, waterfall_steps
from core.layout import PanelSpec, build_figure
from core.style import ChartStyle, apply_style

SALES = pd.DataFrame({"年": ["2017", "2018", "2019"], "売上": ["3,208.2", "3,284.1", "3,136.9"]})
CROSS = pd.DataFrame(
    {"企業": ["A社", "B社"], "通信": ["82", "40"], "AI": ["45", ""], "半導体": ["30", "22"]}
)


def test_waterfall_levels_become_differences():
    steps, measures = waterfall_steps([3208.2, 3284.1, 3136.9], WATERFALL_MODES[0], add_total=True)
    assert steps == [3208.2, 75.9, -147.2, 0.0]
    assert measures == ["absolute", "relative", "relative", "total"]


def test_waterfall_deltas_are_used_as_is():
    steps, measures = waterfall_steps([10, -3, None], WATERFALL_MODES[1], add_total=False)
    assert steps == [10.0, -3.0, 0.0]
    assert measures == ["relative"] * 3


def test_waterfall_panel_and_colors():
    panel = PanelSpec("ウォーターフォール", "年", ["売上"], waterfall_total=True, right_cols=["売上"])
    fig = apply_style(build_figure(SALES, [panel]), ChartStyle(decrease_color="#FF0000", data_labels=True))
    trace = fig.data[0]
    assert trace.type == "waterfall"
    assert list(trace.x) == ["2017", "2018", "2019", "合計"]
    assert trace.decreasing.marker.color == "#FF0000"
    assert list(trace.texttemplate) == ["%{final:,}", "%{delta:+,}", "%{delta:+,}", "%{final:,}"]
    # ウォーターフォールでは右軸を使わない
    assert all(t.yaxis in (None, "y") for t in fig.data)


def test_bubble_from_cross_table():
    panel = PanelSpec("バブル", "企業", ["通信", "AI", "半導体"], bubble_max_size=40)
    fig = apply_style(build_figure(CROSS, [panel]), ChartStyle(data_labels=True))
    assert len(fig.data) == 3
    g06f = fig.data[0]
    assert list(g06f.x) == ["通信", "通信"]
    assert list(g06f.y) == ["A社", "B社"]
    # 最大値(82)の円の直径が40pxになるよう sizeref を決める
    assert abs(g06f.marker.sizeref - 2 * 82 / 40 ** 2) < 1e-9
    # 空欄は0件として扱う
    assert list(fig.data[1].marker.size) == [45.0, 0.0]
    assert g06f.showlegend is False
    assert g06f.mode == "markers+text"
    assert fig.layout.xaxis.showgrid and fig.layout.yaxis.showgrid


def test_bubble_labels_on_x_axis():
    yearly = pd.DataFrame({"年": ["2017", "2018"], "全体": ["118", "110"], "ドア": ["15", "8"]})
    panel = PanelSpec("バブル", "年", ["全体", "ドア"], labels_on_x=True)
    fig = apply_style(build_figure(yearly, [panel]), ChartStyle(data_labels=True, palette=["#08306B", "#C6DBEF"]))
    assert list(fig.data[0].x) == ["2017", "2018"]  # 年が横軸
    assert list(fig.data[0].y) == ["全体", "全体"]  # 項目が縦軸
    assert list(fig.layout.yaxis.categoryarray) == ["全体", "ドア"]
    # 濃い色の大きい円は白文字、薄い色の円は通常の文字色
    assert list(fig.data[0].textfont.color) == ["#FFFFFF", "#FFFFFF"]
    assert "#FFFFFF" not in list(fig.data[1].textfont.color)


def test_heatmap_labels_on_x_axis():
    panel = PanelSpec("ヒートマップ", "企業", ["通信", "AI", "半導体"], labels_on_x=True)
    heat = build_figure(CROSS, [panel]).data[0]
    assert list(heat.x) == ["A社", "B社"]
    assert list(heat.y) == ["通信", "AI", "半導体"]
    assert [list(r) for r in heat.z] == [[82.0, 40.0], [45.0, None], [30.0, 22.0]]
