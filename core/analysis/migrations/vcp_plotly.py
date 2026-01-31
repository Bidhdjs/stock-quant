"""
VCP Plotly 报表工具。

适用场景：
- 为 CLI 的 VCP 分析输出更直观的 HTML 报表。

数学原理：
1. K 线图展示价格走势。
2. 以散点标记 VCP 信号位置。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _require_plotly():
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except Exception as exc:
        raise RuntimeError(f"缺少 plotly 依赖，无法生成图表: {exc}") from exc
    return go, make_subplots


def build_vcp_plotly_report(df: pd.DataFrame, output_path: Path, title: str = "VCP Signals") -> Path:
    """
    生成 VCP Plotly HTML 报表。

    Args:
        df: 包含 open/high/low/close/volume 与 vcp_signal 列的 DataFrame
        output_path: 输出 HTML 路径
        title: 标题

    Returns:
        HTML 路径
    """
    go, make_subplots = _require_plotly()

    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        x_axis = data["date"]
    else:
        x_axis = data.index

    for col in ["open", "high", "low", "close", "volume"]:
        if col not in data.columns:
            data[col] = pd.NA

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.7, 0.3],
    )

    fig.add_trace(
        go.Candlestick(
            x=x_axis,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    if "vcp_signal" in data.columns:
        signal_mask = data["vcp_signal"].fillna(False).astype(bool)
        fig.add_trace(
            go.Scatter(
                x=x_axis[signal_mask],
                y=data.loc[signal_mask, "close"],
                mode="markers",
                marker=dict(color="purple", size=8, symbol="triangle-up"),
                name="VCP Signal",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(x=x_axis, y=data["volume"], name="Volume", marker_color="#888888"),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=900,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path
