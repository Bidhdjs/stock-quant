"""
成交量与动量指标计算模块。
用于策略信号层的指标计算基础。

数学原理：
1. 移动平均与标准差用于量能放大判断。
2. RSI / Bollinger / KDJ 用于动量与波动区间识别。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeIndicatorParams:
    """成交量信号指标参数集合。"""

    n1: int = 1
    n2: int = 5
    n3: int = 20
    rsi_period: int = 14
    boll_period: int = 20
    boll_width: float = 2.0
    kdj_period: int = 9


def _resolve_column(df: pd.DataFrame, name: str) -> pd.Series:
    for candidate in (name, name.lower(), name.upper(), name.capitalize()):
        if candidate in df.columns:
            return df[candidate]
    raise KeyError(f"缺少列: {name}")


def compute_volume_features(df: pd.DataFrame, params: VolumeIndicatorParams | None = None) -> pd.DataFrame:
    """计算成交量策略所需的基础指标序列。"""

    if params is None:
        params = VolumeIndicatorParams()

    open_ = _resolve_column(df, "open")
    high = _resolve_column(df, "high")
    low = _resolve_column(df, "low")
    close = _resolve_column(df, "close")
    volume = _resolve_column(df, "volume")

    ma_vol_today = volume.rolling(window=params.n1, min_periods=params.n1).mean()
    ma_close_today = close.rolling(window=params.n1, min_periods=params.n1).mean()

    ma_vol_5 = volume.rolling(window=params.n2, min_periods=params.n2).mean()
    ma_close_5 = close.rolling(window=params.n2, min_periods=params.n2).mean()

    ma_vol_20 = volume.rolling(window=params.n3, min_periods=params.n3).mean()
    ma_close_20 = close.rolling(window=params.n3, min_periods=params.n3).mean()

    vol_std_5 = volume.rolling(window=params.n2, min_periods=params.n2).std(ddof=0)
    vol_std_20 = volume.rolling(window=params.n3, min_periods=params.n3).std(ddof=0)

    delta = close.diff()
    rsi_up = delta.clip(lower=0)
    rsi_down = -delta.clip(upper=0)
    rsi_avg_up = rsi_up.rolling(window=params.rsi_period, min_periods=params.rsi_period).mean()
    rsi_avg_down = rsi_down.rolling(window=params.rsi_period, min_periods=params.rsi_period).mean()
    rsi = rsi_avg_up / (rsi_avg_up + rsi_avg_down + 1e-10) * 100

    boll_mid = close.rolling(window=params.boll_period, min_periods=params.boll_period).mean()
    boll_std = close.rolling(window=params.boll_period, min_periods=params.boll_period).std(ddof=0)
    boll_top = boll_mid + boll_std * params.boll_width
    boll_bot = boll_mid - boll_std * params.boll_width

    lowest = low.rolling(window=params.kdj_period, min_periods=params.kdj_period).min()
    highest_3 = high.rolling(window=3, min_periods=3).max()
    lowest_3 = low.rolling(window=3, min_periods=3).min()
    rsv = (close - lowest) / (highest_3 - lowest_3 + 1e-10) * 100
    k = rsv.rolling(window=3, min_periods=3).mean()
    d = k.rolling(window=3, min_periods=3).mean()
    j = 3 * k - 2 * d

    is_down = close < open_
    is_up = close > open_
    is_3_down = (
        is_down.rolling(window=3, min_periods=3)
        .apply(lambda x: 1.0 if np.all(x) else 0.0, raw=True)
        .astype(bool)
    )
    is_3_up = (
        is_up.rolling(window=3, min_periods=3)
        .apply(lambda x: 1.0 if np.all(x) else 0.0, raw=True)
        .astype(bool)
    )

    features = pd.DataFrame(
        {
            "ma_vol_today": ma_vol_today,
            "ma_close_today": ma_close_today,
            "ma_vol_5": ma_vol_5,
            "ma_close_5": ma_close_5,
            "ma_vol_20": ma_vol_20,
            "ma_close_20": ma_close_20,
            "vol_std_5": vol_std_5,
            "vol_std_20": vol_std_20,
            "rsi": rsi,
            "rsi_prev": rsi.shift(1),
            "boll_top": boll_top,
            "boll_bot": boll_bot,
            "k": k,
            "d": d,
            "j": j,
            "is_3_down": is_3_down,
            "is_3_up": is_3_up,
        },
        index=df.index,
    )

    return features


def compute_latest_volume_features(
    df: pd.DataFrame, params: VolumeIndicatorParams | None = None
) -> Dict[str, float | bool]:
    """计算最近一条数据的指标值。"""

    features = compute_volume_features(df, params)
    if features.empty:
        return {}
    latest = features.iloc[-1]
    return latest.to_dict()
