"""Graph Maker(グラフ作成ツール):貼り付け読込・プレビュー・複数段/2軸グラフ・スタイル編集・PNG出力"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib

import streamlit as st

from core.data_loader import (
    is_row_series,
    load_result_from_dataframe,
    load_uploaded_file,
    parse_pasted_text,
    rows_to_series,
)
from core.exporter import export_png
from charts.bubble import BUBBLE_LABEL_POSITIONS
from charts.heatmap import COLOR_SCALES
from charts.pareto import CUMULATIVE_NAME
from charts.treemap import TREE_MODES
from charts.waterfall import WATERFALL_MODES
from core.layout import (
    BAR_TYPES,
    CHART_TYPES,
    LAYOUTS,
    NO_VALUE_AXIS_TYPES,
    NUMBER_FORMATS,
    RIGHT_AXIS_TYPES,
    SINGLE_SERIES_TYPES,
    AxisSpec,
    PanelSpec,
    build_figure,
)
from core.style import (
    LEGEND_POSITIONS,
    PALETTE_CHOICES,
    ChartStyle,
    apply_style,
    default_color,
    mix_colors,
    palette_colors,
)

# 出力サイズのプリセット(名前 → 幅, 高さ px)。先頭が既定値
# スライドの px はアプリ上の標準サイズ(Googleスライド 16:9 = 960×540、PowerPoint 16:9 = 1280×720)。
# A4 は 96dpi 換算(210×297mm ≒ 794×1123 px)
CUSTOM_SIZE = "カスタム(幅・高さを直接入力)"
SIZE_PRESETS: dict[str, tuple[int, int]] = {
    "Googleスライド 横半分(480×360)": (480, 360),
    "Googleスライド 全体 16:9(960×540)": (960, 540),
    "PowerPoint 横半分(640×480)": (640, 480),
    "PowerPoint 全体 16:9(1280×720)": (1280, 720),
    "16:9 高解像度(1600×900)": (1600, 900),
    "A4横(1123×794)": (1123, 794),
    "A4縦・上下2段向け(794×1123)": (794, 1123),
    "正方形(1200×1200)": (1200, 1200),
}
DEFAULT_SIZE = next(iter(SIZE_PRESETS))

st.set_page_config(page_title="Graph Maker", layout="wide")

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.5rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }
    h1 {
        font-size: 1.5rem !important;
        margin-bottom: 0.2rem !important;
    }
    h2 {
        font-size: 1.1rem !important;
        margin-top: 0.4rem !important;
        margin-bottom: 0.2rem !important;
    }
    h3 {
        font-size: 1rem !important;
        margin-top: 0.3rem !important;
        margin-bottom: 0.2rem !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
    }
    div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0.2rem;
    }
    div[data-testid="stCaptionContainer"] {
        margin-bottom: 0.1rem;
    }
    [data-testid="stWidgetLabel"] {
        margin-bottom: 0.1rem;
    }
    [data-testid="stSelectbox"] [role="group"],
    [data-testid="stTextInputRootElement"],
    [data-testid="stNumberInputContainer"] {
        height: 34px !important;
    }
    [data-testid="stMultiSelect"] [role="group"] {
        min-height: 34px !important;
    }
    [data-testid="stSelectbox"] input[role="combobox"],
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInputField"] {
        padding-top: 4px !important;
        padding-bottom: 4px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Graph Maker")

TAB_INPUT = "1. データを入力"
TAB_PREVIEW = "2. プレビュー"

if "df" not in st.session_state:
    st.session_state.df = None


def _load_pasted() -> None:
    """「読み込む」ボタン:貼り付けデータを読み込み、プレビュータブへ切り替える。"""
    pasted = st.session_state.get("pasted_text", "")
    if pasted.strip():
        st.session_state.df = parse_pasted_text(pasted)
        st.session_state.paste_empty = False
        st.session_state.data_tab = TAB_PREVIEW
    else:
        st.session_state.paste_empty = True


def _show_preview_tab() -> None:
    st.session_state.data_tab = TAB_PREVIEW


tab_input, tab_preview = st.tabs([TAB_INPUT, TAB_PREVIEW], key="data_tab", on_change="rerun")

with tab_input:
    input_mode = st.radio("入力方法", ["貼り付け", "ファイルアップロード"], horizontal=True)

    if input_mode == "貼り付け":
        st.text_area(
            "スプレッドシートからコピーした表を貼り付けてください(タブ区切り・カンマ区切りのどちらも可)",
            height=200,
            placeholder="年\t件数\n2020\t120\n2021\t145",
            key="pasted_text",
        )
        st.button("読み込む", type="primary", on_click=_load_pasted)
        if st.session_state.get("paste_empty"):
            st.warning("貼り付け欄が空です。")
    else:
        uploaded = st.file_uploader(
            "CSVまたはXLSXファイルを選択してください",
            type=["csv", "xlsx", "xls"],
            on_change=_show_preview_tab,
        )
        if uploaded is not None:
            try:
                st.session_state.df = load_uploaded_file(uploaded)
            except Exception as exc:  # noqa: BLE001
                st.error(f"ファイルの読み込みに失敗しました: {exc}")

df = st.session_state.df

if df is None or df.empty:
    with tab_preview:
        st.info("「1. データを入力」タブでデータを読み込むと、ここに表が表示されます。")
    st.info("データを入力すると、グラフ設定が表示されます。")
    st.stop()

with tab_preview:
    auto_rows = is_row_series(df)
    c_dir, c_dir_note = st.columns([2, 5], vertical_alignment="bottom")
    with c_dir:
        direction = st.radio(
            "データの向き",
            ["自動判定", "1行が1系列", "1列が1系列"],
            horizontal=True,
            help="「1行が1系列」は、1行目に年などの見出しが並び、各行が売上・利益などの系列になっている表です。",
        )
    use_rows = auto_rows if direction == "自動判定" else direction == "1行が1系列"
    if use_rows:
        df = rows_to_series(df)
    with c_dir_note:
        if use_rows:
            note = "1行が1系列の表として、行と列を入れ替えて使います。"
            if direction == "自動判定":
                note = "自動判定:" + note
            st.caption(note)

    result = load_result_from_dataframe(df)

    st.caption(f"{len(result.df)}行 × {len(result.df.columns)}列")
    st.dataframe(result.df, width="stretch", row_height=28)

    type_labels = " / ".join(f"{col}:{t}" for col, t in result.column_types.items())
    st.caption(f"列の型(自動判定): {type_labels}")

    for w in result.warnings:
        st.warning(w)

st.header("3. グラフ設定")

all_cols = result.df.columns.tolist()
numeric_cols = [c for c in all_cols if result.column_types.get(c) in ("数値", "年")]

c_layout, c_title, c_share, c_ratio, c_space = st.columns([1, 2, 1, 2, 1], vertical_alignment="bottom")
with c_layout:
    layout_name = st.selectbox("レイアウト", list(LAYOUTS))
rows, cols, panel_names = LAYOUTS[layout_name]
with c_title:
    title = st.text_input("グラフタイトル(全体)", value="")
with c_share:
    share_x = st.checkbox(
        "X軸を共有",
        value=True,
        disabled=rows == 1,
        help="上下の段でX軸(年など)をそろえ、目盛りの文字は一番下の段だけに表示します。",
    )
with c_ratio:
    first_row_pct, first_col_pct = 50, 50
    ratio_cols = st.columns(2)
    if rows == 2:
        with ratio_cols[0]:
            first_row_pct = st.slider("上段の高さ(%)", 20, 80, 50, step=5)
    if cols == 2:
        with ratio_cols[1]:
            first_col_pct = st.slider("左列の幅(%)", 20, 80, 50, step=5)
with c_space:
    spacing_pct = st.slider("段の間隔(%)", 2, 30, 12, disabled=rows * cols == 1)


def axis_settings(prefix: str, label: str) -> AxisSpec:
    """数値軸1本ぶんの設定欄を1行で表示し、AxisSpecを返す。"""
    c = st.columns([1, 2, 1, 1, 1, 1, 2], vertical_alignment="bottom")
    c[0].markdown(f"**{label}**")
    return AxisSpec(
        title=c[1].text_input("軸タイトル", key=prefix + "title"),
        min=c[2].number_input("最小", value=None, placeholder="自動", key=prefix + "min"),
        max=c[3].number_input("最大", value=None, placeholder="自動", key=prefix + "max"),
        dtick=c[4].number_input("目盛間隔", value=None, min_value=0.0, placeholder="自動",
                                key=prefix + "dtick"),
        suffix=c[5].text_input("単位", placeholder="例: 件", key=prefix + "suffix"),
        number_format=c[6].selectbox("数値の書式", list(NUMBER_FORMATS), key=prefix + "fmt"),
    )


def _guess(columns: list[str], keyword: str, fallback: int = 0) -> int:
    """列名に keyword を含む列の位置を返す(なければ fallback)。"""
    for i, c in enumerate(columns):
        if keyword in c:
            return i
    return min(fallback, max(len(columns) - 1, 0))


# グラフ種類ごとの「項目の列(X軸)」欄の見出し
X_LABELS = {
    "円・ドーナツ": "項目の列(企業名など)",
    "パレート図": "項目の列(企業名など)",
    "ツリーマップ": "項目の列(最も細かい分類)",
    "ライフサイクル図": "年の列",
}


def panel_settings(i: int) -> PanelSpec:
    """1つの段の設定欄を表示し、PanelSpecを返す。"""
    p = f"p{i}_"
    c_type, c_x, c_y, c_orient, c_sub = st.columns([1, 1, 2, 1, 2])
    with c_type:
        chart_type = st.selectbox(
            "グラフ種類", CHART_TYPES, index=CHART_TYPES.index("棒" if i == 0 else "折れ線"), key=p + "type"
        )
    is_cross = chart_type in ("バブル", "ヒートマップ")
    labels_on_x = False
    with c_orient:
        if is_cross:
            # 既定:バブルは年などの推移を見るので行の項目を横軸に、ヒートマップは企業×分野のような表向けに縦軸に
            placement = st.radio(
                "行の項目の位置",
                ["横軸", "縦軸"],
                index=0 if chart_type == "バブル" else 1,
                horizontal=True,
                key=p + "cross_place_" + chart_type,
                help="「横軸」は年などを横に並べて推移を見るとき、「縦軸」は企業×分野のように行の項目を縦に並べるときに選びます。",
            )
            labels_on_x = placement == "横軸"
    label_axis, item_axis = ("横軸", "縦軸") if labels_on_x else ("縦軸", "横軸")
    with c_x:
        x_label = f"{label_axis}の項目(行)" if is_cross else X_LABELS.get(chart_type, "X軸")
        x_col = st.selectbox(x_label, all_cols, key=p + "x")
    y_candidates = [c for c in numeric_cols if c != x_col] or [c for c in all_cols if c != x_col]
    lifecycle_x_col = ""
    orientation = "v"
    with c_y:
        if chart_type == "ライフサイクル図":
            y_cols = [st.selectbox("縦軸:件数(量)の列", y_candidates,
                                   index=_guess(y_candidates, "件数"), key=p + "lc_y_" + x_col)]
        elif chart_type in SINGLE_SERIES_TYPES:
            y_cols = [st.selectbox("値の列(件数など)", y_candidates, key=p + "value_" + x_col)]
        else:
            y_cols = st.multiselect(
                f"{item_axis}に並べる列" if is_cross else "Y軸(系列)",
                y_candidates,
                default=y_candidates[:10],
                key=p + "y_" + x_col,
                help=f"選んだ列の名前が{item_axis}に並び、各セルの値を円の大きさ・色の濃さで表します。" if is_cross else None,
            )
    with c_orient:
        if chart_type in BAR_TYPES:
            direction = st.radio("向き", ["縦棒", "横棒"], horizontal=True, key=p + "orient")
            orientation = "h" if direction == "横棒" else "v"
        elif chart_type == "ライフサイクル図":
            others = [c for c in y_candidates if c not in y_cols] or y_candidates
            lifecycle_x_col = st.selectbox(
                "横軸:参加数(企業数など)の列", others,
                index=_guess(others, "社", _guess(others, "人", 0)), key=p + "lc_x_" + x_col,
            )
    with c_sub:
        subtitle = st.text_input("小見出し", key=p + "sub") if rows * cols > 1 else ""

    series_key = "|".join(y_cols)
    horizontal = chart_type in BAR_TYPES and orientation == "h"
    spec = PanelSpec(chart_type=chart_type, x_col=x_col, y_cols=y_cols, orientation=orientation,
                     subtitle=subtitle, lifecycle_x_col=lifecycle_x_col, labels_on_x=labels_on_x)

    c_opt1, c_opt2 = st.columns(2)
    if chart_type in RIGHT_AXIS_TYPES:
        with c_opt1:
            spec.right_cols = st.multiselect(
                "右軸に表示する系列",
                y_cols,
                default=[],
                key=p + "right_" + series_key,
                disabled=horizontal,
                help="桁の大きく違う系列(例:件数と累積件数、売上と利益)を右側の軸で表示します。横棒では使えません。",
            )
        with c_opt2:
            if chart_type == "棒+折れ線":
                spec.line_cols = st.multiselect(
                    "折れ線にする系列(残りは棒)", y_cols, default=y_cols[-1:], key=p + "line_" + series_key
                )
    elif chart_type == "ウォーターフォール":
        with c_opt1:
            spec.waterfall_mode = st.selectbox(
                "表の値の意味",
                WATERFALL_MODES,
                key=p + "wf_mode",
                help="「各時点の水準」は売上高のような各年の値の表です。先頭を基準にして、前年からの増減を積み上げます。"
                "「増減量」は、表の値そのものが増減(要因別の増減など)の場合に選びます。",
            )
        with c_opt2:
            spec.waterfall_total = st.checkbox("最後に合計(到達点)の棒を追加", key=p + "wf_total")
    elif chart_type == "バブル":
        with c_opt1:
            spec.bubble_max_size = st.slider("最大の円の直径(px)", 10, 80, 30, key=p + "bubble_size")
        with c_opt2:
            spec.bubble_label_position = st.radio(
                "値ラベルの位置",
                list(BUBBLE_LABEL_POSITIONS),
                horizontal=True,
                key=p + "bubble_label_pos",
                help="「円の中央」は円を半透明にして数字を中に書きます。「円の右横」は円をそのままの色にして、"
                "数字を円の外の右側に書きます。値ラベルは「凡例・ラベル」タブでオンにします。",
            )
    elif chart_type == "ヒートマップ":
        with c_opt1:
            spec.color_scale = st.selectbox("色の種類", list(COLOR_SCALES), key=p + "hm_scale")
        with c_opt2:
            spec.show_color_scale = st.checkbox("カラーバー(色の目盛り)を表示", value=True, key=p + "hm_bar")
    elif chart_type == "円・ドーナツ":
        with c_opt1:
            spec.donut = st.checkbox("ドーナツにする(中央を空ける)", key=p + "donut")
    elif chart_type == "ツリーマップ":
        with c_opt1:
            spec.tree_mode = st.selectbox(
                "階層の作り方",
                TREE_MODES,
                key=p + "tree_mode",
                help="「上位の列を指定」は、大分類・中分類などの列を上位の階層として使います。"
                "「分類コードの先頭文字から自動作成」は、A01B → A / A01 / A01B のように、"
                "英字1文字+数字2桁+英字1文字の分類コードから階層を作ります。",
            )
        with c_opt2:
            if spec.tree_mode == "上位の列を指定":
                parent_candidates = [c for c in all_cols if c not in (x_col, *y_cols)]
                spec.tree_parent_cols = st.multiselect(
                    "上位の階層の列(上の階層から順に選ぶ)",
                    parent_candidates,
                    # 既定:表で項目の列より左にある文字の列(大分類 → 中分類 …)
                    default=[c for c in all_cols[: all_cols.index(x_col)]
                             if c in parent_candidates and c not in numeric_cols],
                    key=p + "tree_parents_" + x_col,
                )
    elif chart_type == "パレート図":
        with c_opt1:
            spec.pareto_sort = st.checkbox("件数の多い順に並べ替える", value=True, key=p + "pareto_sort")
        with c_opt2:
            guide = st.number_input("目安線(%)", min_value=0, max_value=100, value=80, key=p + "pareto_guide",
                                    help="累積比率の目安線(80%など)を点線で引きます。0 で線を消します。")
            spec.pareto_guide = guide or None

    if chart_type not in NO_VALUE_AXIS_TYPES:
        left_label = {"ライフサイクル図": "縦軸", "パレート図": "左軸(件数)"}.get(
            chart_type, "数値軸(横)" if horizontal else "左軸"
        )
        with st.expander("軸の詳細設定(軸タイトル・範囲・目盛間隔・単位・書式)"):
            spec.left_axis = axis_settings(p + "l_", left_label)
            if spec.effective_right_cols:
                spec.right_axis = axis_settings(p + "r_", "右軸")

    return spec


panels: list[PanelSpec] = []
if rows * cols == 1:
    panels.append(panel_settings(0))
else:
    for i, tab in enumerate(st.tabs(panel_names)):
        with tab:
            panels.append(panel_settings(i))

empty_panels = [panel_names[i] for i, p in enumerate(panels) if not p.y_cols]
if empty_panels:
    st.info(f"Y軸(系列)を1つ以上選んでください(未選択:{'、'.join(empty_panels)})。")
    st.stop()



def colored_names(panel: PanelSpec) -> list[str]:
    """色を選べる名前(系列名、円では項目名)を返す。

    ウォーターフォールは増加・減少・合計で、ヒートマップは色の濃さで、
    ツリーマップは上位の階層ごとに自動で色分けするので、ここには含めない。
    """
    if panel.chart_type in ("ウォーターフォール", "ヒートマップ", "ツリーマップ"):
        return []
    if panel.chart_type == "円・ドーナツ":
        return [str(v) for v in result.df[panel.x_col]]
    if panel.chart_type == "パレート図":
        return panel.y_cols + [CUMULATIVE_NAME]
    return panel.y_cols


all_series = list(dict.fromkeys(name for p in panels for name in colored_names(p)))
has_waterfall = any(p.chart_type == "ウォーターフォール" for p in panels)

st.header("4. スタイルとプレビュー")
st.caption("左の設定を変えると、右のプレビューにすぐ反映されます。プレビューは出力画像と同じサイズで表示します。")

style_col, preview_col = st.columns([1, 3])
with style_col:
    tab_color, tab_text, tab_other = st.tabs(["色", "文字", "凡例・ラベル"])
    with tab_color:
        c_pal, c_rev = st.columns([3, 1], vertical_alignment="bottom")
        palette_choice = c_pal.selectbox(
            "カラーパレット",
            PALETTE_CHOICES,
            help="「配色」は項目ごとに色をはっきり分けます。「グラデーション」は系列の数に合わせて、"
            "濃い色から薄い色へ順に色を振ります(積み上げ棒などに向きます)。",
        )
        palette_reverse = c_rev.checkbox("逆順", help="色を割り当てる順番を逆にします。")
        palette = palette_colors(palette_choice, len(all_series), reverse=palette_reverse)
        st.markdown(
            "".join(
                f'<span style="display:inline-block;width:18px;height:18px;margin-right:2px;'
                f'border-radius:3px;background:{c}"></span>'
                for c in palette[: max(len(all_series), 1)]
            ),
            unsafe_allow_html=True,
        )
        st.caption("パレットを選んだあと、系列ごとに色を変えることもできます。")
        series_colors = {}
        color_cols = st.columns(2)
        # パレットや系列の数が変わったら、個別の色をパレットの色に戻す
        palette_key = f"{palette_choice}_{palette_reverse}_{len(all_series)}"
        for i, name in enumerate(all_series):
            with color_cols[i % 2]:
                series_colors[name] = st.color_picker(
                    name, value=default_color(i, palette), key=f"color_{palette_key}_{name}"
                )
        c1, c2 = st.columns(2)
        with c1:
            font_color = st.color_picker("文字の色", value="#434343")
            bg_color = st.color_picker("背景色", value="#FFFFFF")
        with c2:
            grid_color = st.color_picker("目盛線の色", value="#E0E0E0")
        # 横棒・バブル・ライフサイクル図は横方向にも値や項目を読むので、X軸の目盛線も既定で表示する
        grid_x_default = any(
            p.horizontal or p.chart_type in ("バブル", "ライフサイクル図") for p in panels
        )
        c1, c2 = st.columns(2)
        grid_x = c1.checkbox("目盛線を表示(X軸)", value=grid_x_default, key=f"grid_x_{grid_x_default}",
                             help="X軸の目盛りの位置に縦の線を引きます。")
        grid_y = c2.checkbox("目盛線を表示(Y軸)", value=True, key="grid_y",
                             help="Y軸の目盛りの位置に横の線を引きます。")
        frame_auto = st.checkbox(
            "グラフ枠の色を自動にする", value=True, help="文字の色と目盛線の色のちょうど中間の色にします。"
        )
        auto_frame_color = mix_colors(font_color, grid_color)
        frame_color = st.color_picker(
            "グラフ枠の色",
            value=auto_frame_color,
            disabled=frame_auto,
            # 自動のときは文字色・目盛線色の変更に合わせて表示色も追従させる
            key=f"frame_color_{auto_frame_color}" if frame_auto else "frame_color_manual",
        )
        if frame_auto:
            frame_color = auto_frame_color
        increase_color, decrease_color, total_color = "#4C78A8", "#E45756", "#8C8C8C"
        if has_waterfall:
            st.caption("ウォーターフォールの色")
            c1, c2, c3 = st.columns(3)
            increase_color = c1.color_picker("増加", value=increase_color)
            decrease_color = c2.color_picker("減少", value=decrease_color)
            total_color = c3.color_picker("基準・合計", value=total_color)
    with tab_text:
        st.caption("文字サイズ(px)")
        c1, c2 = st.columns(2)
        title_size = c1.number_input("タイトル", min_value=6, max_value=60, value=16)
        subtitle_size = c2.number_input("小見出し", min_value=6, max_value=60, value=13)
        axis_size = c1.number_input("軸", min_value=6, max_value=40, value=11)
        legend_size = c2.number_input("凡例", min_value=6, max_value=40, value=11)
    with tab_other:
        legend_position = st.selectbox("凡例の位置", LEGEND_POSITIONS)
        if len(panels) == 1:
            panel_labels = [st.checkbox("値ラベルを表示", value=False, key="labels_0")]
        else:
            st.caption("値ラベルを表示する段")
            label_cols = st.columns(2)
            panel_labels = [
                label_cols[i % 2].checkbox(panel_names[i], value=False, key=f"labels_{i}")
                for i in range(len(panels))
            ]

style = ChartStyle(
    series_colors=series_colors,
    font_color=font_color,
    frame_color=frame_color,
    bg_color=bg_color,
    grid_x=grid_x,
    grid_y=grid_y,
    grid_color=grid_color,
    title_size=int(title_size),
    subtitle_size=int(subtitle_size),
    axis_size=int(axis_size),
    legend_size=int(legend_size),
    legend_position=legend_position,
    panel_labels=panel_labels,
    palette=palette,
    increase_color=increase_color,
    decrease_color=decrease_color,
    total_color=total_color,
)

with preview_col:
    preview_area = st.empty()

st.header("5. 画像出力")

c_w, c_h, c_s, c_name, c_btn = st.columns([1, 1, 1, 3, 1], vertical_alignment="bottom")
if "out_w" not in st.session_state:
    st.session_state.out_w, st.session_state.out_h = SIZE_PRESETS[DEFAULT_SIZE]


def _apply_size_preset() -> None:
    """プリセットを選んだら、幅・高さをその値にする。"""
    size = SIZE_PRESETS.get(st.session_state.size_preset)
    if size:
        st.session_state.out_w, st.session_state.out_h = size


def _mark_custom_size() -> None:
    """幅・高さを直接変えたら、プリセットの表示を「カスタム」にする。"""
    if SIZE_PRESETS.get(st.session_state.size_preset) != (st.session_state.out_w, st.session_state.out_h):
        st.session_state.size_preset = CUSTOM_SIZE


st.selectbox(
    "サイズのプリセット",
    [*SIZE_PRESETS, CUSTOM_SIZE],
    key="size_preset",
    on_change=_apply_size_preset,
    help="選ぶと幅・高さがそのサイズになります。スライドの「横半分」は、スライドの左右どちらかに貼る想定のサイズです。",
)
c_w, c_h, c_s, c_name, c_btn = st.columns([1, 1, 1, 3, 1], vertical_alignment="bottom")
with c_w:
    width = st.number_input("幅(px)", min_value=100, max_value=5000, step=10, key="out_w",
                            on_change=_mark_custom_size)
with c_h:
    height = st.number_input("高さ(px)", min_value=100, max_value=5000, step=10, key="out_h",
                             on_change=_mark_custom_size)
with c_s:
    scale = st.selectbox(
        "倍率", [1, 2, 3], index=1,
        help="同じ見た目のまま画素数を増やし、貼り付け先で文字がぼやけないようにします。貼り付け後は目的の大きさに縮めてください。",
    )
with c_name:
    default_name = f"{title or 'graph'}_{dt.date.today():%Y%m%d}.png"
    file_name = st.text_input("ファイル名", value=default_name)
with c_btn:
    make_png = st.button("PNG画像を作成", type="primary", width="stretch")

fig = build_figure(
    result.df,
    panels,
    layout=layout_name,
    share_x=share_x,
    first_row_ratio=first_row_pct / 100,
    first_col_ratio=first_col_pct / 100,
    v_spacing=spacing_pct / 100,
    h_spacing=spacing_pct / 100,
    title=title,
)
fig.update_layout(width=int(width), height=int(height))
apply_style(fig, style)

preview_area.plotly_chart(
    fig,
    width="content",
    theme=None,
    config={
        "toImageButtonOptions": {
            "format": "png",
            "filename": file_name.removesuffix(".png"),
            "width": int(width),
            "height": int(height),
            "scale": int(scale),
        },
    },
)

image_key = hashlib.sha1(
    f"{fig.to_json()}|{width}|{height}|{scale}".encode("utf-8")
).hexdigest()

if make_png:
    try:
        with st.spinner("画像を作成しています…"):
            st.session_state.png_bytes = export_png(
                fig, width=int(width), height=int(height), scale=float(scale)
            )
        st.session_state.png_key = image_key
    except Exception as exc:  # noqa: BLE001
        st.error(
            "画像の作成に失敗しました。Kaleido/Chromeが正しく導入されているか、"
            f"README.mdの「6. 画像出力の確認」を参照してください。詳細: {exc}"
        )

png_bytes = st.session_state.get("png_bytes")
if png_bytes is not None:
    if st.session_state.get("png_key") == image_key:
        st.download_button("ダウンロード", data=png_bytes, file_name=file_name, mime="image/png")
        st.caption(
            f"実際の出力画像({int(width * scale)}×{int(height * scale)} px)です。"
            "右クリックで「名前を付けて画像を保存」や「画像をコピー」ができます"
            "(コピーした画像はGoogleスライドなどにそのまま貼り付けられます)。"
            + (f"倍率{scale}で出力しているので、貼り付け後に1/{scale}の大きさ(横{int(width)}px相当)に縮めると、くっきり表示されます。"
               if scale > 1 else "")
        )
        encoded = base64.b64encode(png_bytes).decode("ascii")
        st.markdown(
            f'<img src="data:image/png;base64,{encoded}" alt="出力画像" '
            'style="max-width:100%; border:1px solid #DDDDDD;">',
            unsafe_allow_html=True,
        )
    else:
        st.info("設定が変更されました。「PNG画像を作成」を押すと出力画像が更新されます。")
