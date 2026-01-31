"""
RSI 信号示例（简化版）。

适用场景：
- 迁移自 x/vcp_from_youtuber/rsi.py，保留核心 RSI 逻辑。

数学原理：
1. RSI = 100 - 100 / (1 + RS)
2. RS = 平均上涨幅度 / 平均下跌幅度（使用滚动均值）
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RsiConfig:
    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0


def compute_rsi_signal(df: pd.DataFrame, config: RsiConfig | None = None) -> pd.DataFrame:
    """
    计算 RSI 并生成信号列（1=超卖，-1=超买）。
    """
    if config is None:
        config = RsiConfig()
    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    if "close" not in data.columns:
        raise ValueError("缺少 close 列，无法计算 RSI。")

    delta = data["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=config.period).mean()
    avg_loss = loss.rolling(window=config.period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    data["rsi"] = rsi
    data["rsi_signal"] = 0
    data.loc[data["rsi"] <= config.oversold, "rsi_signal"] = 1
    data.loc[data["rsi"] >= config.overbought, "rsi_signal"] = -1
    return data

