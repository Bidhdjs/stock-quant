"""
VCP（Volatility Contraction Pattern）指标计算模块。

数学原理：
1. Stage 2 趋势模板：价格高于 MA50/MA150/MA200，且 MA50 > MA150 > MA200。
2. 收缩次数：局部高低点之间的价格收缩幅度递减。
3. 成交量枯竭：短期成交量均线低于长期均线。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VCPParams:
    ma_50_period: int = 50
    ma_150_period: int = 150
    ma_200_period: int = 200
    ma_trend_period: int = 20
    local_extrema_order: int = 10
    min_contractions: int = 2
    max_contractions: int = 4
    max_contraction_depth: float = 50.0
    min_contraction_depth: float = 15.0
    min_weeks: int = 2
    lookback_period: int = 252
    vol_short_period: int = 5
    vol_long_period: int = 30


def _resolve_column(df: pd.DataFrame, name: str) -> pd.Series:
    for candidate in (name, name.lower(), name.upper(), name.capitalize()):
        if candidate in df.columns:
            return df[candidate]
    raise KeyError(f"缺少列: {name}")


def _local_extrema(arr: np.ndarray, order: int, mode: str) -> np.ndarray:
    if len(arr) < order * 2 + 1:
        return np.array([], dtype=int)
    idx = []
    for i in range(order, len(arr) - order):
        window = arr[i - order : i + order + 1]
        center = arr[i]
        if mode == "max" and center == window.max():
            idx.append(i)
        if mode == "min" and center == window.min():
            idx.append(i)
    return np.array(idx, dtype=int)


def _contractions(highs: np.ndarray, lows: np.ndarray, local_high: np.ndarray, local_low: np.ndarray) -> list[float]:
    contraction = []
    high_idx = local_high[::-1]
    low_idx = local_low[::-1]
    i = 0
    j = 0
    while i < len(low_idx) and j < len(high_idx):
        if low_idx[i] > high_idx[j]:
            high_val = highs[high_idx[j]]
            low_val = lows[low_idx[i]]
            contraction.append(round((high_val - low_val) / high_val * 100, 2))
            i += 1
            j += 1
        else:
            j += 1
    return contraction


def _num_contractions(contraction: list[float]) -> int:
    new_c = 0
    num = 0
    for c in contraction:
        if c > new_c:
            num += 1
            new_c = c
        else:
            break
    return num


def evaluate_vcp(df: pd.DataFrame, params: VCPParams | None = None) -> Dict[str, float | int | bool]:
    """计算 VCP 指标是否成立，并输出进度分值。"""

    if params is None:
        params = VCPParams()

    close = _resolve_column(df, "close")
    high = _resolve_column(df, "high")
    low = _resolve_column(df, "low")
    volume = _resolve_column(df, "volume")

    if len(df) < max(params.ma_200_period + params.ma_trend_period, params.local_extrema_order * 2 + 1):
        return {
            "stage2_pass": False,
            "is_vcp": False,
            "progress": 0.0,
            "num_contractions": 0,
            "max_contraction": 0.0,
            "min_contraction": 0.0,
        }

    lookback = min(len(df), params.lookback_period)
    df_tail = df.tail(lookback)
    close_tail = close.tail(lookback)
    high_tail = high.tail(lookback)
    low_tail = low.tail(lookback)
    volume_tail = volume.tail(lookback)

    ma_50 = close_tail.rolling(window=params.ma_50_period, min_periods=params.ma_50_period).mean()
    ma_150 = close_tail.rolling(window=params.ma_150_period, min_periods=params.ma_150_period).mean()
    ma_200 = close_tail.rolling(window=params.ma_200_period, min_periods=params.ma_200_period).mean()

    week_52_low = low_tail.rolling(window=252, min_periods=252).min()
    week_52_high = high_tail.rolling(window=252, min_periods=252).max()

    ma_200_slope = ma_200.iloc[-1] - ma_200.iloc[-params.ma_trend_period]

    stage2 = (
        close_tail.iloc[-1] > ma_50.iloc[-1]
        and close_tail.iloc[-1] > ma_150.iloc[-1]
        and close_tail.iloc[-1] > ma_200.iloc[-1]
        and ma_50.iloc[-1] > ma_150.iloc[-1] > ma_200.iloc[-1]
        and ma_200_slope > 0
        and close_tail.iloc[-1] > week_52_low.iloc[-1] * 1.3
        and close_tail.iloc[-1] > week_52_high.iloc[-1] * 0.75
    )

    highs = high_tail.to_numpy(dtype=float)
    lows = low_tail.to_numpy(dtype=float)

    local_high = _local_extrema(highs, params.local_extrema_order, mode="max")
    local_low = _local_extrema(lows, params.local_extrema_order, mode="min")

    contraction = _contractions(highs, lows, local_high, local_low) if len(local_high) >= 2 and len(local_low) >= 2 else []
    num_c = _num_contractions(contraction) if contraction else 0

    max_c = contraction[num_c - 1] if num_c >= 1 else 0.0
    min_c = contraction[0] if num_c >= 1 else 0.0

    contraction_count_ok = params.min_contractions <= num_c <= params.max_contractions
    max_depth_ok = max_c <= params.max_contraction_depth
    min_depth_ok = min_c <= params.min_contraction_depth

    weeks_ok = False
    if contraction and num_c >= 1 and len(local_high) >= num_c:
        weeks = (lookback - local_high[::-1][num_c - 1]) / 5
        weeks_ok = weeks >= params.min_weeks

    vol_ma_short = volume_tail.rolling(window=params.vol_short_period, min_periods=params.vol_short_period).mean()
    vol_ma_long = volume_tail.rolling(window=params.vol_long_period, min_periods=params.vol_long_period).mean()
    volume_dry_ok = vol_ma_short.iloc[-1] < vol_ma_long.iloc[-1]

    conditions = {
        "stage2": stage2,
        "contraction_count": contraction_count_ok,
        "max_depth": max_depth_ok,
        "min_depth": min_depth_ok,
        "weeks": weeks_ok,
        "volume_dry": volume_dry_ok,
    }
    progress = sum(1.0 for ok in conditions.values() if ok) / len(conditions)
    is_vcp = all(conditions.values())

    return {
        "stage2_pass": stage2,
        "is_vcp": is_vcp,
        "progress": progress,
        "num_contractions": num_c,
        "max_contraction": max_c,
        "min_contraction": min_c,
    }
