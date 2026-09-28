"""グラフ画像の書き出し(ステップ1はPNGのみ)。"""
from __future__ import annotations

import plotly.graph_objects as go


def export_png(fig: go.Figure, width: int, height: int, scale: float = 1.0) -> bytes:
    """FigureをPNGのバイト列として書き出す。"""
    return fig.to_image(format="png", width=width, height=height, scale=scale)
