"""分析向けグラフ(積み上げ・パレート図・ツリーマップなど)のテスト。"""
import pandas as pd
import pytest

from charts.pareto import CUMULATIVE_NAME, pareto_values
from charts.treemap import TREE_MODES, build_tree, code_levels
from core.layout import CHART_TYPES, PanelSpec, build_figure
from core.style import ChartStyle, apply_style

CROSS = pd.DataFrame(
    {"企業": ["A社", "B社"], "通信": ["82", "40"], "AI": ["18", ""], "半導体": ["0", "60"]}
)
COMPANIES = pd.DataFrame({"企業": ["A社", "B社", "C社"], "件数": ["20", "50", "30"]})
YEARLY = pd.DataFrame(
    {"年": ["2020", "2021", "2022"], "件数": ["10", "30", "25"], "参加企業数": ["5", "12", "9"]}
)


def test_stacked_bar_uses_base_per_panel():
    panel = PanelSpec("積み上げ棒", "企業", ["通信", "AI", "半導体"])
    fig = build_figure(CROSS, [panel])
    assert list(fig.data[1].base) == [82.0, 40.0]  # AI は 通信 の上に積む
    assert list(fig.data[2].base) == [100.0, 40.0]
    assert fig.layout.barmode == "group"  # 他の段の棒は積み上げにしない


def test_percent_stacked_bar_sums_to_100():
    panel = PanelSpec("100%積み上げ棒", "企業", ["通信", "AI", "半導体"], orientation="h")
    fig = build_figure(CROSS, [panel])
    totals = [sum(t.x[i] for t in fig.data) for i in range(2)]
    assert totals == pytest.approx([100, 100])
    assert fig.layout.xaxis.ticksuffix == "%"


def test_pareto_sorted_with_cumulative_on_right_axis():
    labels, values, cumulative = pareto_values(["A社", "B社", "C社"], [20, 50, 30])
    assert labels == ["B社", "C社", "A社"]
    assert cumulative == [50.0, 80.0, 100.0]

    fig = build_figure(COMPANIES, [PanelSpec("パレート図", "企業", ["件数"])])
    line = [t for t in fig.data if t.name == CUMULATIVE_NAME][0]
    assert fig.layout[f"yaxis{line.yaxis[1:]}"].overlaying is not None
    assert len(fig.layout.shapes) == 1  # 80% の目安線


def test_code_hierarchy():
    assert code_levels("A01B") == ["A", "A01", "A01B"]
    assert code_levels("a01b 1/00") == ["A", "A01", "A01B", "A01B 1/00"]
    assert code_levels("Z99") == ["Z", "Z99"]
    assert code_levels("その他") == ["その他"]

    ids, labels, parents, values = build_tree([["電機", "家電"], ["電機", "半導体"], ["医療", "医薬品"]], [3, 2, 4])
    tree = dict(zip(ids, zip(labels, parents, values)))
    assert tree["電機"] == ("電機", "", 5)
    assert tree["電機/半導体"] == ("半導体", "電機", 2)


def test_treemap_with_parent_columns():
    df = pd.DataFrame({"分野": ["通信", "通信", "AI"], "項目": ["5G", "Wi-Fi", "学習"], "件数": ["3", "2", "4"]})
    panel = PanelSpec("ツリーマップ", "項目", ["件数"], tree_mode=TREE_MODES[0], tree_parent_cols=["分野"])
    trace = build_figure(df, [panel]).data[0]
    assert dict(zip(trace.ids, trace.values))["通信"] == 5


def test_heatmap_blank_cells_and_orientation():
    fig = build_figure(CROSS, [PanelSpec("ヒートマップ", "企業", ["通信", "AI", "半導体"])])
    heat = fig.data[0]
    assert list(heat.y) == ["A社", "B社"]
    assert [list(r) for r in heat.z] == [[82.0, 18.0, 0.0], [40.0, None, 60.0]]


def test_lifecycle_connects_years():
    panel = PanelSpec("ライフサイクル図", "年", ["件数"], lifecycle_x_col="参加企業数")
    fig = apply_style(build_figure(YEARLY, [panel]), ChartStyle())
    trace = fig.data[0]
    assert list(trace.x) == [5.0, 12.0, 9.0] and list(trace.y) == [10.0, 30.0, 25.0]
    assert list(trace.text) == ["2020", "2021", "2022"]
    assert trace.marker.symbol[-1] == "arrow"
    assert fig.layout.xaxis.title.text == "参加企業数"


def test_pie_colors_by_label():
    fig = build_figure(COMPANIES, [PanelSpec("円・ドーナツ", "企業", ["件数"], donut=True)])
    apply_style(fig, ChartStyle(series_colors={"B社": "#123456"}))
    assert fig.data[0].hole == 0.5
    assert fig.data[0].marker.colors[1] == "#123456"
    assert fig.layout.showlegend is True


def test_all_chart_types_in_2x2_with_style():
    """全種類を2×2の段に入れて、スタイル適用までエラーにならないこと。"""
    df = CROSS.assign(年=["2021", "2022"], 参加企業数=["3", "4"])
    for start in range(0, len(CHART_TYPES), 4):
        panels = []
        for kind in CHART_TYPES[start:start + 4]:
            y = ["通信", "AI"] if kind not in ("円・ドーナツ", "パレート図", "ツリーマップ") else ["通信"]
            x = "年" if kind == "ライフサイクル図" else "企業"
            panels.append(PanelSpec(kind, x, y, lifecycle_x_col="参加企業数", right_cols=["AI"]))
        layout = "2×2" if len(panels) == 4 else "1段"
        fig = build_figure(df, panels if layout == "2×2" else panels[:1], layout=layout)
        apply_style(fig, ChartStyle(data_labels=True))
