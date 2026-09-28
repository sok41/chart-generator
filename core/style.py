"""色・フォント・凡例・グリッドなどのスタイルをFigureに適用する。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from charts.bar import STACK100_META, STACK_META
from charts.bubble import BUBBLE_META
from charts.lifecycle import LIFECYCLE_META
from charts.pareto import PARETO_BAR_META, PARETO_LINE_META

DEFAULT_COLORS = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2",
    "#EECA3B", "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC",
]

# 見やすい配色(項目ごとにはっきり色を分ける)
CATEGORICAL_PALETTES: dict[str, list[str]] = {
    "標準": DEFAULT_COLORS,
    "色覚多様性に配慮(Okabe-Ito)": [
        "#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442", "#999999",
    ],
    "ビビッド": [
        "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
        "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    ],
    "落ち着いた": [
        "#5B7C99", "#C98E5B", "#7A9E7E", "#B5646A", "#8C7AA9", "#A39171", "#6E9FA5", "#9A9A9A",
    ],
    "パステル": [
        "#8DA0CB", "#FC8D62", "#66C2A5", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494", "#B3B3B3",
    ],
    "モノクロ(印刷向け)": ["#252525", "#636363", "#969696", "#BDBDBD", "#D9D9D9", "#4D4D4D", "#838383"],
}

# グラデーション(系列の数に合わせて、濃い色から薄い色へ等間隔に取り出す)
# 名前 → (Plotlyのカラースケール名, 取り出す範囲の始点, 終点)
GRADIENT_PALETTES: dict[str, tuple[str, float, float]] = {
    "青": ("Blues", 0.95, 0.35),
    "緑": ("Greens", 0.95, 0.35),
    "オレンジ": ("Oranges", 0.9, 0.3),
    "紫": ("Purples", 0.95, 0.35),
    "赤": ("Reds", 0.95, 0.35),
    "グレー": ("Greys", 0.9, 0.3),
    "青→緑→黄(Viridis)": ("Viridis", 0.0, 0.9),
    "紺→赤→黄(Plasma)": ("Plasma", 0.0, 0.85),
}

PALETTE_CHOICES = [f"配色:{n}" for n in CATEGORICAL_PALETTES] + [f"グラデーション:{n}" for n in GRADIENT_PALETTES]


def palette_colors(choice: str, count: int, reverse: bool = False) -> list[str]:
    """パレットの選択肢(PALETTE_CHOICES の要素)から、count 色の #RRGGBB のリストを返す。"""
    kind, _, name = choice.partition(":")
    if kind == "グラデーション" and name in GRADIENT_PALETTES:
        scale, start, end = GRADIENT_PALETTES[name]
        n = max(count, 1)
        points = [start] if n == 1 else [start + (end - start) * i / (n - 1) for i in range(n)]
        colors = [_to_hex(c) for c in sample_colorscale(scale, points)]
    else:
        base = CATEGORICAL_PALETTES.get(name, DEFAULT_COLORS)
        # 使う色数だけ取り出す(足りなければ先頭から繰り返す)
        colors = [base[i % len(base)] for i in range(max(count, 1))]
    return colors[::-1] if reverse else colors


def _to_hex(color: str) -> str:
    """'rgb(12, 34, 56)' 形式を '#0C2238' 形式に変換する。"""
    r, g, b = (round(float(v)) for v in color[color.index("(") + 1:color.index(")")].split(",")[:3])
    return f"#{r:02X}{g:02X}{b:02X}"


FONT_FAMILY = "Noto Sans JP, Yu Gothic, Meiryo, sans-serif"

LEGEND_POSITIONS = ["上", "右", "下", "グラフ内(右上)", "非表示"]

# プレビューの高さが未設定のときに位置計算で使う高さ(px)
_FALLBACK_HEIGHT = 450


def mix_colors(color_a: str, color_b: str, ratio: float = 0.5) -> str:
    """2つの色(#RRGGBB)を ratio の割合で混ぜた色を返す(0.5 でちょうど中間)。"""
    a = [int(color_a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(color_b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    mixed = [round(x + (y - x) * ratio) for x, y in zip(a, b)]
    return "#" + "".join(f"{v:02X}" for v in mixed)


@dataclass
class ChartStyle:
    """画面で編集できるスタイル設定一式。"""

    series_colors: dict[str, str] = field(default_factory=dict)
    font_color: str = "#434343"
    frame_color: str = ""  # 空のときは文字色と目盛線色の中間色
    bg_color: str = "#FFFFFF"
    grid_show: bool = True
    grid_color: str = "#E0E0E0"
    title_size: int = 16
    subtitle_size: int = 13
    axis_size: int = 11
    legend_size: int = 11
    legend_position: str = "上"
    data_labels: bool = False
    # 段ごとの値ラベル(段の順)。空のときや段が足りないときは data_labels を使う
    panel_labels: list[bool] = field(default_factory=list)
    # 系列色の既定値に使うカラーパレット(円の項目、ツリーマップの色分けにも使う)
    palette: list[str] = field(default_factory=lambda: list(DEFAULT_COLORS))
    # ウォーターフォールの色
    increase_color: str = "#4C78A8"
    decrease_color: str = "#E45756"
    total_color: str = "#8C8C8C"

    def __post_init__(self) -> None:
        if not self.frame_color:
            self.frame_color = mix_colors(self.font_color, self.grid_color)


def is_dark(color: str) -> bool:
    """#RRGGBB の色が暗い(白い文字のほうが読みやすい)かどうか。"""
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b < 0.55


def default_color(index: int, palette: list[str] | None = None) -> str:
    """系列番号に対応する既定の色を返す(パレットの色が足りなければ先頭から繰り返す)。"""
    palette = palette or DEFAULT_COLORS
    return palette[index % len(palette)]


def _labels_on(fig: go.Figure, trace_index: int, style: ChartStyle) -> bool:
    """このトレースに値ラベルを付けるか(段ごとの設定があればそれに従う)。"""
    meta = fig.layout.meta if isinstance(fig.layout.meta, dict) else {}
    panels = meta.get("trace_panels") or []
    if trace_index < len(panels) and panels[trace_index] < len(style.panel_labels):
        return style.panel_labels[panels[trace_index]]
    return style.data_labels


def _axis_name(ref: str | None, letter: str) -> str:
    """トレースの軸参照('x2' など)をレイアウトの名前('xaxis2')に変換する。"""
    return f"{letter}axis{(ref or letter)[1:]}"


def _is_xy(trace) -> bool:
    """縦軸・横軸の上に描くトレースかどうか(円・ツリーマップは False)。"""
    return "xaxis" in trace


def _style_traces(fig: go.Figure, style: ChartStyle) -> None:
    order: list[str] = []
    for index, trace in enumerate(fig.data):
        labels = _labels_on(fig, index, style)
        name = trace.name
        if "showlegend" in trace and trace.type != "pie":
            # 複数の段に同じ系列があっても、凡例には1回だけ出す(色も系列名で揃える)
            trace.legendgroup = name
            trace.showlegend = name not in order
        if name not in order:
            order.append(name)
        color = style.series_colors.get(name) or default_color(order.index(name), style.palette)
        horizontal = getattr(trace, "orientation", None) == "h"
        label_font = dict(size=style.axis_size, color=style.font_color)

        if trace.meta == BUBBLE_META:
            _style_bubble(trace, color, style, labels)
        elif trace.meta == LIFECYCLE_META:
            trace.line.color = color
            trace.marker.color = color
            trace.textfont = label_font  # 年のラベルは常に表示する
            trace.cliponaxis = False
            trace.showlegend = False
        elif trace.type == "waterfall":
            _style_waterfall(trace, style, labels)
        elif trace.type == "pie":
            _style_pie(trace, style, labels)
        elif trace.type == "treemap":
            trace.textinfo = "label+value" if labels else "label"
            trace.textfont = dict(size=style.axis_size)
            trace.marker.line = dict(color=style.bg_color, width=1)
        elif trace.type == "heatmap":
            trace.showlegend = False
            trace.texttemplate = "%{z:,}" if labels else None
            trace.textfont = dict(size=style.axis_size)  # 文字色はセルの濃さに合わせて自動
            trace.colorbar.tickfont = label_font
        elif trace.type == "bar":
            trace.marker.color = color
            value = "x" if horizontal else "y"
            if not labels or trace.meta == PARETO_BAR_META:
                trace.texttemplate = None
            elif trace.meta in (STACK_META, STACK100_META):
                # 積み上げは各区間の中に書く(100%積み上げは構成比)
                suffix = ":.1f}%" if trace.meta == STACK100_META else ":,}"
                trace.texttemplate = "%{" + value + suffix
                trace.textposition = "inside"
                trace.insidetextanchor = "middle"
                trace.textangle = 0  # 細い区間でも文字を回転させない
                trace.textfont = dict(size=style.axis_size)  # 文字色は棒の色に合わせて自動
            else:
                trace.texttemplate = "%{" + value + ":,}"
                trace.textposition = "outside"
                trace.textfont = label_font
                trace.constraintext = "none"
                trace.cliponaxis = False
        elif trace.type == "scatter":
            trace.line.color = color
            trace.marker.color = color
            if labels:
                trace.mode = "lines+markers+text"
                trace.texttemplate = "%{y:.1f}%" if trace.meta == PARETO_LINE_META else "%{y:,}"
                trace.textposition = "top center"
                trace.textfont = label_font
                trace.cliponaxis = False
            else:
                trace.mode = "lines+markers"
                trace.texttemplate = None


def _style_pie(trace, style: ChartStyle, labels: bool) -> None:
    # 円は項目(企業名など)ごとに色を付ける。色は項目名で決める
    trace.marker.colors = [
        style.series_colors.get(label) or default_color(i, style.palette) for i, label in enumerate(trace.labels)
    ]
    trace.marker.line = dict(color=style.bg_color, width=1)
    trace.texttemplate = "%{value:,}<br>%{percent:.1%}" if labels else "%{percent:.1%}"
    trace.insidetextorientation = "horizontal"
    trace.textfont = dict(size=style.axis_size)


def _style_bubble(trace, color: str, style: ChartStyle, labels: bool) -> None:
    # 横軸の項目名と同じ情報なので、凡例には出さない
    trace.showlegend = False
    trace.marker.color = color
    trace.marker.opacity = 0.85
    if labels:
        trace.mode = "markers+text"
        # 0件のセルには数字を出さない
        trace.text = [f"{v:,g}" if v else "" for v in trace.customdata]
        trace.texttemplate = None
        trace.textposition = "middle center"
        # 濃い色の円の上では白い文字にする。ただし文字が円からはみ出す小さい円は通常の文字色のまま
        # (面積モードの円の直径は sqrt(2 × 値 / sizeref) px)
        sizeref = trace.marker.sizeref or 1
        trace.textfont = dict(size=style.axis_size, color=[
            "#FFFFFF" if is_dark(color) and (2 * v / sizeref) ** 0.5 >= style.axis_size * 2.2
            else style.font_color
            for v in trace.customdata
        ])
        trace.cliponaxis = False
    else:
        trace.mode = "markers"
        trace.texttemplate = None


def _style_waterfall(trace, style: ChartStyle, labels: bool) -> None:
    # 色は増加・減少・合計を表すので、系列名の凡例は出さない(系列名はタイトルに書く)
    trace.showlegend = False
    trace.increasing = dict(marker=dict(color=style.increase_color))
    trace.decreasing = dict(marker=dict(color=style.decrease_color))
    trace.totals = dict(marker=dict(color=style.total_color))
    trace.connector = dict(line=dict(color=style.frame_color, width=1, dash="dot"))
    if labels:
        # 基準・合計の棒はその時点の値、増減の棒は +/- 付きの差を表示する
        trace.texttemplate = [
            "%{delta:+,}" if m == "relative" else "%{final:,}" for m in trace.measure
        ]
        trace.textposition = "outside"
        trace.textfont = dict(size=style.axis_size, color=style.font_color)
        trace.constraintext = "none"  # 棒の幅に合わせて文字を縮めない
        trace.cliponaxis = False
    else:
        trace.texttemplate = None


def _style_axes(fig: go.Figure, style: ChartStyle) -> None:
    # 数値を表す軸にだけ目盛線を引く(縦棒・折れ線はY軸、横棒はX軸、バブルは両方)
    value_axes: set[str] = set()
    for trace in fig.data:
        if not _is_xy(trace) or trace.type == "heatmap":
            continue  # ヒートマップはセルの隙間で区切るので目盛線を引かない
        if trace.meta in (BUBBLE_META, LIFECYCLE_META):
            value_axes.add(_axis_name(trace.xaxis, "x"))
            value_axes.add(_axis_name(trace.yaxis, "y"))
        elif getattr(trace, "orientation", None) == "h":
            value_axes.add(_axis_name(trace.xaxis, "x"))
        else:
            value_axes.add(_axis_name(trace.yaxis, "y"))

    axis_names = [k for k in fig.layout.to_plotly_json() if re.fullmatch(r"[xy]axis\d*", k)]
    for name in axis_names:
        axis = fig.layout[name]
        secondary = axis.overlaying is not None  # 右軸
        axis.update(
            showline=True,
            linecolor=style.frame_color,
            mirror=not secondary,  # 左軸・下軸の線を反対側にも引いて枠にする
            ticks="",
            tickfont=dict(size=style.axis_size, color=style.font_color),
            title_font=dict(size=style.axis_size, color=style.font_color),
            zeroline=False,
            automargin=True,
            showgrid=style.grid_show and name in value_axes and not secondary,
            gridcolor=style.grid_color,
        )


def _make_room_for_line_labels(fig: go.Figure, style: ChartStyle) -> None:
    """折れ線の値ラベルが枠線に重ならないよう、Y軸の上側に余裕をとる(範囲を手動指定した軸は除く)。"""
    values: dict[str, list[float]] = {}
    has_line: set[str] = set()
    has_bar: set[str] = set()
    for index, trace in enumerate(fig.data):
        if (not _is_xy(trace) or getattr(trace, "orientation", None) == "h" or trace.y is None
                or trace.meta in (BUBBLE_META, LIFECYCLE_META)
                or trace.type in ("waterfall", "heatmap")):
            continue
        name = _axis_name(trace.yaxis, "y")
        values.setdefault(name, []).extend(v for v in trace.y if v is not None and v == v)
        if trace.type != "scatter":
            has_bar.add(name)
        elif _labels_on(fig, index, style):  # ラベルを出す折れ線の軸だけ余裕をとる
            has_line.add(name)

    for name in has_line:
        axis = fig.layout[name]
        if axis.range is not None or not values[name]:
            continue
        lo, hi = min(values[name]), max(values[name])
        if name in has_bar:
            lo = min(lo, 0)  # 棒と同じ軸なら0から始める
        span = (hi - lo) or abs(hi) or 1
        bottom = lo if name in has_bar else lo - span * 0.08
        axis.range = [bottom, hi + span * 0.18]


def apply_style(fig: go.Figure, style: ChartStyle) -> go.Figure:
    """FigureにChartStyleを適用して返す(同じFigureを書き換える)。

    タイトル・凡例・小見出しが重ならないよう、図の高さから上部の余白を計算する。
    高さは fig.layout.height を使うので、先に出力サイズを設定しておくこと。
    """
    _style_traces(fig, style)
    _style_axes(fig, style)
    _make_room_for_line_labels(fig, style)

    height = fig.layout.height or _FALLBACK_HEIGHT
    has_title = bool(fig.layout.title.text)
    has_right_axis = any(
        _is_xy(t) and t.yaxis and fig.layout[_axis_name(t.yaxis, "y")].overlaying for t in fig.data
    )
    subtitles = [a for a in fig.layout.annotations if a.text]
    # 円は項目ごとに凡例を出す。ツリーマップ・ヒートマップ・バブルなどは凡例に出す系列がない
    legend_items = any(t.type == "pie" or ("showlegend" in t and t.showlegend) for t in fig.data)
    show_legend = style.legend_position != "非表示" and legend_items
    legend_top = show_legend and style.legend_position == "上"
    legend_bottom = show_legend and style.legend_position == "下"

    for ann in subtitles:
        ann.font = dict(size=style.subtitle_size, color=style.font_color)

    # 上から順に「タイトル → 凡例 → 小見出し → グラフ」と積み上げる(単位:px)
    pad = 8
    title_px = style.title_size * 1.4 + pad if has_title else 0
    legend_px = style.legend_size * 1.6 + pad if legend_top else 0
    top_subtitle_px = style.subtitle_size * 1.4 + 4 if any(a.y >= 0.99 for a in subtitles) else 0
    top = pad + title_px + legend_px + top_subtitle_px

    legend = dict(font=dict(size=style.legend_size, color=style.font_color), bgcolor="rgba(0,0,0,0)")
    if legend_top:
        legend.update(orientation="h", x=0, xanchor="left", yref="container",
                      y=1 - (pad + title_px) / height, yanchor="top")
    elif legend_bottom:
        legend.update(orientation="h", x=0.5, xanchor="center", yref="container",
                      y=pad / height, yanchor="bottom")
    elif style.legend_position == "グラフ内(右上)":
        legend.update(orientation="v", x=0.99, xanchor="right", y=0.99, yanchor="top",
                      bgcolor="rgba(255,255,255,0.7)")
    else:
        legend.update(orientation="v", x=1.02, xanchor="left", y=1, yanchor="top")

    fig.update_layout(
        font=dict(family=FONT_FAMILY, color=style.font_color),
        title=dict(font=dict(size=style.title_size, color=style.font_color),
                   x=0.5, xanchor="center", yref="container", y=1 - pad / height, yanchor="top"),
        treemapcolorway=style.palette,
        uniformtext=dict(minsize=max(style.axis_size - 2, 6), mode="hide"),
        paper_bgcolor=style.bg_color,
        plot_bgcolor=style.bg_color,
        showlegend=show_legend,
        legend=legend,
        margin=dict(
            t=top,
            b=pad + (style.legend_size * 1.6 + style.axis_size * 1.6 + 16 if legend_bottom else 0),
            l=10,
            r=10 if has_right_axis or style.legend_position == "右" else 20,
            autoexpand=True,
        ),
    )
    return fig
