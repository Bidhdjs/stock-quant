"""
VCP（Volatility Contraction Pattern）工具集。

适用场景：
- 迁移自 x/vcp_from_youtuber/VCP成交量分析策略v2.py 等脚本。
- 提供可复用、可测试的 VCP 成交量收缩与价格紧缩信号。

数学原理：
1. 成交量均线：Vol_MA = rolling_mean(Volume, N)
2. 绝对缩量：Vol_t < Vol_{t-1}
3. 相对缩量：Vol_t < Vol_MA
4. 连续缩量：rolling_min(Vol_t < Vol_MA, window=k) == True
5. 价格紧缩：max((High-Low)/Close, window=k) < threshold
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class VcpConfig:
    ma_window: int = 50
    tight_window: int = 3
    price_tight_threshold: float = 0.03
    dry_ratio: float = 0.5
    price_ma_window: int = 200


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    return data


def _validate_columns(df: pd.DataFrame) -> None:
    required = {"high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列: {sorted(missing)}")


def compute_vcp_features(df: pd.DataFrame, config: VcpConfig | None = None) -> pd.DataFrame:
    """
    计算 VCP 相关特征列。

    Returns:
        带特征列的 DataFrame
    """
    if config is None:
        config = VcpConfig()

    data = _normalize_columns(df)
    _validate_columns(data)

    data = data.copy()
    data["vol_ma"] = data["volume"].rolling(window=config.ma_window).mean()
    data["price_ma"] = data["close"].rolling(window=config.price_ma_window).mean()

    data["vol_below_prev"] = data["volume"] < data["volume"].shift(1)
    data["vol_below_ma"] = data["volume"] < data["vol_ma"]
    data["vol_dry_consecutive"] = (
        data["vol_below_ma"].rolling(window=config.tight_window).min().fillna(0).astype(bool)
    )
    data["vol_extreme_dry"] = data["volume"] < (data["vol_ma"] * config.dry_ratio)

    price_range = (data["high"] - data["low"]) / data["close"]
    data["price_tight"] = price_range.rolling(window=config.tight_window).max() < config.price_tight_threshold

    return data


def identify_vcp_setup(df: pd.DataFrame, config: VcpConfig | None = None) -> pd.Series:
    """
    基于趋势 + 成交量 + 价格紧缩识别 VCP 关注信号。
    """
    data = compute_vcp_features(df, config=config)
    trend_ok = data["close"] > data["price_ma"]
    signal = trend_ok & data["vol_dry_consecutive"] & data["price_tight"]
    return signal


def build_vcp_signal_frame(df: pd.DataFrame, config: VcpConfig | None = None) -> pd.DataFrame:
    """
    返回带 VCP 信号列的 DataFrame。
    """
    data = compute_vcp_features(df, config=config)
    data["vcp_signal"] = identify_vcp_setup(df, config=config)
    return data

