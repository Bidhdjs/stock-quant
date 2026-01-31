"""
EMA 示例与数据抓取工具。

适用场景：
- 迁移自 x/demo_tsla.py，用于演示 EMA12/EMA26 计算与结果保存。
- 该模块默认不参与核心流程，仅在需要时手动调用。

数学原理：
1. 指数移动平均（EMA）递推公式：
   EMA_t = alpha * Price_t + (1 - alpha) * EMA_{t-1}
2. 平滑因子：
   alpha = 2 / (span + 1)
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from core.stock.manager_common import standardize_stock_data
from settings import stock_data_root


def fetch_yfinance_data(symbol: str, start_date: str, end_date: str, market: str = "US") -> pd.DataFrame:
    """
    使用 yfinance 下载数据并标准化。

    Args:
        symbol: 股票代码
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        market: 市场标识

    Returns:
        标准化后的 DataFrame
    """
    try:
        import yfinance as yf
    except Exception as exc:
        raise RuntimeError(f"缺少 yfinance 依赖，无法抓取数据: {exc}") from exc

    raw_df = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=True)
    if raw_df.empty:
        return pd.DataFrame()
    return standardize_stock_data(raw_df, stock_code=symbol, stock_name=symbol, market=market)


def add_ema_columns(df: pd.DataFrame, spans: Iterable[int] = (12, 26)) -> pd.DataFrame:
    """
    为标准化数据添加 EMA 列。

    Args:
        df: 标准化后的 DataFrame
        spans: EMA 周期列表

    Returns:
        带 EMA 列的新 DataFrame
    """
    data = df.copy()
    if data.empty:
        return data
    if "close" not in data.columns:
        raise ValueError("缺少 close 列，无法计算 EMA。")
    for span in spans:
        data[f"ema_{span}"] = data["close"].ewm(span=span, adjust=False).mean()
    return data


def save_ema_outputs(df: pd.DataFrame, symbol: str, output_dir: Path | None = None) -> tuple[Path, Path]:
    """
    保存 CSV 与 PNG（可选）输出。

    Args:
        df: 包含 ema 列的数据
        symbol: 股票代码
        output_dir: 输出目录

    Returns:
        (csv_path, png_path)
    """
    if output_dir is None:
        output_dir = stock_data_root / "yfinance"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{symbol}_ema.csv"
    df.to_csv(csv_path, index=False)

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError(f"缺少 matplotlib 依赖，无法输出 PNG: {exc}") from exc

    plt.figure(figsize=(12, 6))
    plt.plot(df["date"], df["close"], label="Close", linewidth=1)
    for col in df.columns:
        if col.startswith("ema_"):
            plt.plot(df["date"], df[col], label=col.upper(), linewidth=1)
    plt.title(f"{symbol} Close & EMA")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    png_path = output_dir / f"{symbol}_ema.png"
    plt.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close()
    return csv_path, png_path


if __name__ == "__main__":
    symbol = "TSLA"
    df = fetch_yfinance_data(symbol, "2024-01-01", "2026-01-30", market="US")
    if df.empty:
        raise SystemExit("未获取到数据")
    df = add_ema_columns(df, spans=(12, 26))
    csv_path, png_path = save_ema_outputs(df, symbol)
    print(f"保存 CSV: {csv_path}")
    print(f"保存图片: {png_path}")
