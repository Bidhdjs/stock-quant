"""
RSRS 指标实现（向量化）。

适用场景：
- 迁移自 x/vcp_from_youtuber/RSRS趋势指标.py（修复原脚本问题）。

数学原理：
1. 以低价为自变量、最高价为因变量，计算滚动线性回归斜率 Beta。
2. 计算 Beta 的 Z-Score（窗口 M）。
3. 修正指标：RSRS = Zscore * R2。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RsrsConfig:
    window: int = 18
    z_window: int = 600
    threshold_buy: float = 0.7
    threshold_sell: float = -0.7


def _rolling_beta_r2(high: np.ndarray, low: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    size = len(high)
    beta = np.full(size, np.nan)
    r2 = np.full(size, np.nan)
    if size < window:
        return beta, r2

    try:
        low_wins = np.lib.stride_tricks.sliding_window_view(low, window)
        high_wins = np.lib.stride_tricks.sliding_window_view(high, window)
    except Exception:
        low_wins = np.stack([low[i : i + window] for i in range(size - window + 1)], axis=0)
        high_wins = np.stack([high[i : i + window] for i in range(size - window + 1)], axis=0)

    mean_low = low_wins.mean(axis=1, keepdims=True)
    mean_high = high_wins.mean(axis=1, keepdims=True)
    low_diff = low_wins - mean_low
    high_diff = high_wins - mean_high

    cov = np.sum(low_diff * high_diff, axis=1)
    var_low = np.sum(low_diff ** 2, axis=1)
    var_high = np.sum(high_diff ** 2, axis=1)

    valid = var_low != 0
    beta_vals = np.full(len(cov), np.nan)
    beta_vals[valid] = cov[valid] / var_low[valid]

    denom = np.sqrt(var_low * var_high)
    valid_r2 = denom != 0
    corr = np.full(len(cov), np.nan)
    corr[valid_r2] = cov[valid_r2] / denom[valid_r2]
    r2_vals = corr ** 2

    start = window - 1
    beta[start:] = beta_vals
    r2[start:] = r2_vals
    return beta, r2


def compute_rsrs(df: pd.DataFrame, config: RsrsConfig | None = None) -> pd.DataFrame:
    """
    计算 RSRS 指标与信号。

    Args:
        df: 包含 high/low/close 列的 DataFrame
        config: RSRS 参数

    Returns:
        增加列: beta, r2, zscore, rsrs, position
    """
    if config is None:
        config = RsrsConfig()

    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    required = {"high", "low", "close"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"缺少必要列: {sorted(missing)}")

    beta, r2 = _rolling_beta_r2(data["high"].to_numpy(), data["low"].to_numpy(), config.window)
    data["beta"] = beta
    data["r2"] = r2

    z_mean = data["beta"].rolling(window=config.z_window).mean()
    z_std = data["beta"].rolling(window=config.z_window).std()
    data["zscore"] = (data["beta"] - z_mean) / z_std
    data["rsrs"] = data["zscore"] * data["r2"]

    position = np.zeros(len(data))
    current = 0
    for i in range(len(data)):
        z = data["zscore"].iloc[i]
        if np.isnan(z):
            position[i] = current
            continue
        if z > config.threshold_buy:
            current = 1
        elif z < config.threshold_sell:
            current = 0
        position[i] = current
    data["position"] = position
    return data

