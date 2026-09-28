"""ツリーマップの描画関数。"""
from __future__ import annotations

import re

import plotly.graph_objects as go

from core.data_loader import numeric_series

# 階層の作り方
TREE_MODES = ["上位の列を指定", "分類コードの先頭文字から自動作成", "なし(1階層)"]

# 「英字1文字+数字2桁+英字1文字」で始まる階層型の分類コード(例:A01B、A01B 1/00)
_CODE_PATTERN = re.compile(r"^([A-Z])(\d{2})([A-Z])?")


def code_levels(code: str) -> list[str]:
    """分類コードを先頭の文字から順の階層に分ける。例:'A01B 1/00' → ['A', 'A01', 'A01B', 'A01B 1/00']。

    形式に合わないコードは、それ自体を1階層として扱う。
    """
    text = str(code).strip().upper()
    m = _CODE_PATTERN.match(text)
    if not m:
        return [text]
    section, cls, subclass = m.group(1), m.group(1) + m.group(2), m.group(0)
    levels = [section, cls]
    if m.group(3):
        levels.append(subclass)
    if text != levels[-1]:
        levels.append(text)
    return levels


def build_tree(paths: list[list[str]], values: list[float]) -> tuple[list, list, list, list]:
    """各行の階層パスと値から、ツリーマップの ids / labels / parents / values を作る(親は子の合計)。"""
    totals: dict[str, float] = {}
    labels: dict[str, str] = {}
    parents: dict[str, str] = {}
    for path, value in zip(paths, values):
        parent_id = ""
        for depth, label in enumerate(path):
            node_id = "/".join(path[: depth + 1])
            labels[node_id] = label
            parents[node_id] = parent_id
            totals[node_id] = totals.get(node_id, 0.0) + value
            parent_id = node_id
    ids = list(labels)
    return ids, [labels[i] for i in ids], [parents[i] for i in ids], [totals[i] for i in ids]


def add_treemap_trace(
    fig: go.Figure,
    df,
    label_col: str,
    value_col: str,
    mode: str = TREE_MODES[0],
    parent_cols: list[str] | None = None,
    row: int = 1,
    col: int = 1,
) -> None:
    """指定した段(row, col)にツリーマップを追加する。"""
    values = numeric_series(df, value_col).fillna(0).clip(lower=0).tolist()
    paths: list[list[str]] = []
    for _, record in df.iterrows():
        label = str(record[label_col]).strip()
        if mode == TREE_MODES[1]:
            paths.append(code_levels(label))
        elif mode == TREE_MODES[0] and parent_cols:
            paths.append([str(record[c]).strip() or "(空欄)" for c in parent_cols] + [label])
        else:
            paths.append([label])

    ids, labels, parents, totals = build_tree(paths, values)
    fig.add_trace(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=totals,
            branchvalues="total",
            name=value_col,
            sort=True,
            pathbar=dict(visible=False),
            hovertemplate="%{label}: %{value:,}<extra></extra>",
        ),
        row=row, col=col,
    )
