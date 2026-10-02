"""1段/上下2段/左右2列/2×2 のレイアウトと、左右2軸の設定を組み立てる。"""
from __future__ import annotations

from dataclasses import dataclass, field

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.bar import add_bar_traces
from charts.bubble import add_bubble_traces
from charts.combo import add_combo_traces
from charts.heatmap import COLOR_SCALES, add_heatmap_trace
from charts.lifecycle import add_lifecycle_trace
from charts.line import add_line_traces
from charts.pareto import add_pareto_traces
from charts.pie import add_pie_trace
from charts.treemap import TREE_MODES, add_treemap_trace
from charts.waterfall import WATERFALL_MODES, add_waterfall_traces

# レイアウト名 → (行数, 列数, 各段の呼び名)
LAYOUTS: dict[str, tuple[int, int, list[str]]] = {
    "1段": (1, 1, ["グラフ"]),
    "上下2段": (2, 1, ["上段", "下段"]),
    "左右2列": (1, 2, ["左", "右"]),
    "2×2": (2, 2, ["左上", "右上", "左下", "右下"]),
}

CHART_TYPES = [
    "棒", "積み上げ棒", "100%積み上げ棒", "折れ線", "棒+折れ線", "円・ドーナツ",
    "ウォーターフォール", "パレート図", "バブル", "ヒートマップ", "ツリーマップ", "ライフサイクル図",
]

# 棒の向き(縦・横)を選べるグラフ種類
BAR_TYPES = {"棒": "", "積み上げ棒": "stack", "100%積み上げ棒": "percent"}

# 右軸(2軸)を使えるグラフ種類
RIGHT_AXIS_TYPES = {"棒", "折れ線", "棒+折れ線"}

# 縦軸・横軸を持たないグラフ種類(円・ツリーマップ)
DOMAIN_TYPES = {"円・ドーナツ", "ツリーマップ"}

# 数値軸の詳細設定(範囲・目盛間隔など)が使えないグラフ種類
NO_VALUE_AXIS_TYPES = DOMAIN_TYPES | {"バブル", "ヒートマップ"}

# 系列(値の列)を1つだけ使うグラフ種類
SINGLE_SERIES_TYPES = {"円・ドーナツ", "パレート図", "ツリーマップ"}

# 画面の選択肢 → Plotly の tickformat
NUMBER_FORMATS: dict[str, str] = {
    "自動": "",
    "桁区切り(1,234)": ",.0f",
    "小数1桁(1,234.5)": ",.1f",
    "小数2桁(1,234.56)": ",.2f",
}


@dataclass
class AxisSpec:
    """数値軸(左軸・右軸)の設定。空欄の項目はグラフ側の既定値をそのまま使う。"""

    title: str = ""
    min: float | None = None
    max: float | None = None
    dtick: float | None = None
    suffix: str = ""
    number_format: str = "自動"

    def to_plotly(self) -> dict:
        kwargs: dict = {}
        if self.title:
            kwargs["title_text"] = self.title
        if self.suffix:
            kwargs["ticksuffix"] = self.suffix
        if self.min is not None or self.max is not None:
            kwargs["range"] = [self.min, self.max]
        if self.dtick:
            kwargs.update(tickmode="linear", dtick=self.dtick)
        if NUMBER_FORMATS.get(self.number_format):
            kwargs["tickformat"] = NUMBER_FORMATS[self.number_format]
        return kwargs


@dataclass
class PanelSpec:
    """1つの段(グラフ)の設定。"""

    chart_type: str
    x_col: str
    y_cols: list[str]
    orientation: str = "v"
    right_cols: list[str] = field(default_factory=list)
    line_cols: list[str] = field(default_factory=list)
    subtitle: str = ""
    left_axis: AxisSpec = field(default_factory=AxisSpec)
    right_axis: AxisSpec = field(default_factory=AxisSpec)
    # ウォーターフォール用
    waterfall_mode: str = WATERFALL_MODES[0]
    waterfall_total: bool = False
    # バブル用:最大の円の直径(px)
    bubble_max_size: int = 30
    # バブル用:値ラベルの位置(「円の中央」または「円の右横」)
    bubble_label_position: str = "円の中央"
    # バブル・ヒートマップ用:行の項目(x_col の値。年など)を横軸に並べるか(False なら縦軸)
    labels_on_x: bool = False
    # 円用
    donut: bool = False
    # ヒートマップ用
    color_scale: str = next(iter(COLOR_SCALES))
    show_color_scale: bool = True
    # ツリーマップ用
    tree_mode: str = TREE_MODES[0]
    tree_parent_cols: list[str] = field(default_factory=list)
    # パレート図用
    pareto_sort: bool = True
    pareto_guide: float | None = 80
    # ライフサイクル図用:横軸(参加数)の列。縦軸(件数)は y_cols[0]
    lifecycle_x_col: str = ""

    @property
    def horizontal(self) -> bool:
        return self.chart_type in BAR_TYPES and self.orientation == "h"

    @property
    def effective_right_cols(self) -> list[str]:
        """実際に右軸へ描く系列(横棒や、2軸に対応しないグラフでは使わない)。"""
        if self.horizontal or self.chart_type not in RIGHT_AXIS_TYPES:
            return []
        return [c for c in self.right_cols if c in self.y_cols]

    @property
    def uses_right_axis(self) -> bool:
        return bool(self.effective_right_cols) or self.chart_type == "パレート図"


def _cell_spec(panel: PanelSpec | None) -> dict:
    if panel is not None and panel.chart_type in DOMAIN_TYPES:
        return {"type": "domain"}
    return {"secondary_y": bool(panel and panel.uses_right_axis)}


def _add_panel(fig: go.Figure, df, panel: PanelSpec, row: int, col: int) -> None:
    """1つの段にグラフを描き、数値軸の詳細設定を反映する。"""
    kind = panel.chart_type
    right = panel.effective_right_cols
    first = panel.y_cols[0]
    at = dict(row=row, col=col)

    if kind in BAR_TYPES:
        add_bar_traces(fig, df, panel.x_col, panel.y_cols, orientation=panel.orientation,
                       right_cols=right, stack=BAR_TYPES[kind], **at)
    elif kind == "折れ線":
        add_line_traces(fig, df, panel.x_col, panel.y_cols, right_cols=right, **at)
    elif kind == "棒+折れ線":
        add_combo_traces(fig, df, panel.x_col, panel.y_cols, line_cols=panel.line_cols,
                         right_cols=right, **at)
    elif kind == "円・ドーナツ":
        add_pie_trace(fig, df, panel.x_col, first, donut=panel.donut, **at)
    elif kind == "ウォーターフォール":
        add_waterfall_traces(fig, df, panel.x_col, panel.y_cols, mode=panel.waterfall_mode,
                             add_total=panel.waterfall_total, **at)
    elif kind == "パレート図":
        add_pareto_traces(fig, df, panel.x_col, first, sort_desc=panel.pareto_sort,
                          guide_line=panel.pareto_guide, **at)
    elif kind == "バブル":
        add_bubble_traces(fig, df, panel.x_col, panel.y_cols, max_size=panel.bubble_max_size,
                          labels_on_x=panel.labels_on_x, label_position=panel.bubble_label_position, **at)
    elif kind == "ヒートマップ":
        add_heatmap_trace(fig, df, panel.x_col, panel.y_cols, color_scale=panel.color_scale,
                          show_scale=panel.show_color_scale, labels_on_x=panel.labels_on_x, **at)
    elif kind == "ツリーマップ":
        add_treemap_trace(fig, df, panel.x_col, first, mode=panel.tree_mode,
                          parent_cols=panel.tree_parent_cols, **at)
    elif kind == "ライフサイクル図":
        add_lifecycle_trace(fig, df, panel.x_col, panel.lifecycle_x_col, first, **at)
    else:
        raise ValueError(f"未対応のグラフ種類です: {kind}")

    if kind in NO_VALUE_AXIS_TYPES:
        return
    if panel.horizontal:
        fig.update_xaxes(**panel.left_axis.to_plotly(), **at)
    elif panel.uses_right_axis:
        fig.update_yaxes(**panel.left_axis.to_plotly(), **at, secondary_y=False)
        if kind != "パレート図":  # パレート図の右軸は累積比率(0〜100%)で固定
            fig.update_yaxes(**panel.right_axis.to_plotly(), **at, secondary_y=True)
    else:
        fig.update_yaxes(**panel.left_axis.to_plotly(), **at)


def _place_color_bars(fig: go.Figure) -> None:
    """複数のヒートマップのカラーバーが重ならないよう、それぞれの段の右横に置く。"""
    for trace in fig.data:
        if trace.type != "heatmap" or not trace.showscale:
            continue
        x_domain = fig.layout[f"xaxis{(trace.xaxis or 'x')[1:]}"].domain
        y_domain = fig.layout[f"yaxis{(trace.yaxis or 'y')[1:]}"].domain
        trace.colorbar = dict(x=x_domain[1] + 0.01, xanchor="left", y=sum(y_domain) / 2,
                              len=y_domain[1] - y_domain[0], thickness=10, outlinewidth=0)


def build_figure(
    df,
    panels: list[PanelSpec],
    layout: str = "1段",
    share_x: bool = False,
    first_row_ratio: float = 0.5,
    first_col_ratio: float = 0.5,
    v_spacing: float = 0.12,
    h_spacing: float = 0.12,
    title: str = "",
) -> go.Figure:
    """レイアウトと各段の設定から、1枚のFigureを組み立てる。"""
    rows, cols, _ = LAYOUTS[layout]
    panels = panels[: rows * cols]
    cells: list[PanelSpec | None] = panels + [None] * (rows * cols - len(panels))

    grid: dict = {}
    if rows > 1:
        grid.update(row_heights=[first_row_ratio, 1 - first_row_ratio], vertical_spacing=v_spacing,
                    shared_xaxes=share_x)
    if cols > 1:
        grid.update(column_widths=[first_col_ratio, 1 - first_col_ratio], horizontal_spacing=h_spacing)

    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=[[_cell_spec(cells[r * cols + c]) for c in range(cols)] for r in range(rows)],
        subplot_titles=[p.subtitle if p else "" for p in cells],
        **grid,
    )

    # 各トレースがどの段のものかを記録する(段ごとの値ラベルのオン/オフに使う)
    trace_panels: list[int] = []
    for k, panel in enumerate(panels):
        _add_panel(fig, df, panel, row=k // cols + 1, col=k % cols + 1)
        trace_panels += [k] * (len(fig.data) - len(trace_panels))

    _place_color_bars(fig)
    fig.update_layout(title=title, barmode="group", legend_title_text="",
                      meta={"trace_panels": trace_panels})
    return fig
