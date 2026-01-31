"""
VCPPlus 指标计算模块（基于完整 VCP 筛选逻辑）。
用于在本地 CSV 数据上复现 VCP 选股条件，供信号层调用。

数学原理：
1. Stage 2 趋势模板：价格与均线多头排列 + 52 周区间约束。
2. 收缩识别：局部高低点形成收缩，收缩幅度逐次减小。
3. 成交量枯竭与盘整：短期均量低于长期均量且未突破。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VCPPlusParams:
    ma_50_period: int = 50
    ma_150_period: int = 150
    ma_200_period: int = 200
    ma_trend_period: int = 20
    rs_trend_period: int = 20
    week_window: int = 260
    local_extrema_order: int = 10
    min_contractions: int = 2
    max_contractions: int = 4
    max_contraction_depth: float = 50.0
    min_contraction_depth: float = 15.0
    min_weeks: int = 2
    vol_short_period: int = 5
    vol_long_period: int = 30
    lookback_period: int = 520
    require_rs_slope: bool = True
    require_rs_rating: bool = True
    min_rs_rating: int = 70
    require_consolidation: bool = True
    benchmark_close_column: str = "benchmark_close"
    rs_rating_column: str = "rs_rating"


def _resolve_column(df: pd.DataFrame, name: str) -> pd.Series:
    for candidate in (name, name.lower(), name.upper(), name.capitalize()):
        if candidate in df.columns:
            return df[candidate]
    raise KeyError(f"缺少列: {name}")


def _resolve_optional_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[pd.Series]:
    for candidate in candidates:
        if candidate in df.columns:
            return df[candidate]
    return None


def _trend_value(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    y = values.astype(float)
    x = np.arange(1, len(y) + 1, dtype=float)
    summed_x = x.sum()
    summed_y = np.nansum(y)
    summed_x2 = np.dot(x, x)
    summed_xy = np.nansum(x * y)
    numerator = len(y) * summed_xy - summed_x * summed_y
    denominator = len(y) * summed_x2 - summed_x ** 2
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _local_extrema(arr: np.ndarray, order: int, mode: str) -> np.ndarray:
    if len(arr) < order * 2 + 1:
        return np.array([], dtype=int)
    idx = []
    for i in range(order, len(arr) - order):
        window = arr[i - order : i + order + 1]
        if mode == "max":
            if arr[i] == np.nanmax(window):
                idx.append(i)
        elif mode == "min":
            if arr[i] == np.nanmin(window):
                idx.append(i)
    return np.array(idx, dtype=int)


def _adjust_local_high_low(local_high: np.ndarray, local_low: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if local_high.size == 0 or local_low.size == 0:
        return np.array([], dtype=int), np.array([], dtype=int)

    i = 0
    j = 0
    adjusted_high: list[int] = []
    adjusted_low: list[int] = []

    while i < len(local_high) and j < len(local_low):
        if local_high[i] < local_low[j]:
            while i < len(local_high) and local_high[i] < local_low[j]:
                i += 1
            if i > 0:
                adjusted_high.append(local_high[i - 1])
        elif local_high[i] > local_low[j]:
            while j < len(local_low) and local_high[i] > local_low[j]:
                j += 1
            if j > 0:
                adjusted_low.append(local_low[j - 1])
        else:
            i += 1
            j += 1

    if i < len(local_high) and adjusted_high and j > 0:
        adjusted_high.pop(-1)
        while i < len(local_high) and local_high[i] > local_low[j - 1]:
            i += 1
        if i > 0:
            adjusted_high.append(local_high[i - 1])
        adjusted_high.append(local_high[-1])
        adjusted_low.append(local_low[j - 1])

    if j < len(local_low) and adjusted_low and i > 0:
        adjusted_low.pop(-1)
        while j < len(local_low) and local_high[i - 1] > local_low[j]:
            j += 1
        if j > 0:
            adjusted_low.append(local_low[j - 1])
        adjusted_low.append(local_low[-1])
        adjusted_high.append(local_high[i - 1])

    return np.array(adjusted_high, dtype=int), np.array(adjusted_low, dtype=int)


def _contractions(
    highs: np.ndarray,
    lows: np.ndarray,
    local_high: np.ndarray,
    local_low: np.ndarray,
) -> list[float]:
    contraction = []
    high_idx = local_high[::-1]
    low_idx = local_low[::-1]
    i = 0
    j = 0
    while i < len(low_idx) and j < len(high_idx):
        if low_idx[i] > high_idx[j]:
            high_val = highs[high_idx[j]]
            low_val = lows[low_idx[i]]
            if high_val != 0:
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


def evaluate_vcp_plus(df: pd.DataFrame, params: VCPPlusParams | None = None) -> Dict[str, float | int | bool | None]:
    """
    评估 VCPPlus 形态是否成立，并返回关键统计值。
    """
    if params is None:
        params = VCPPlusParams()

    close = _resolve_column(df, "close")
    high = _resolve_column(df, "high")
    low = _resolve_column(df, "low")
    volume = _resolve_column(df, "volume")

    benchmark_close = _resolve_optional_column(
        df,
        [params.benchmark_close_column, "spx_close", "benchmark_close", "index_close"],
    )
    rs_rating_series = _resolve_optional_column(
        df,
        [params.rs_rating_column, "rs_rating", "rs_score"],
    )

    lookback = min(len(df), params.lookback_period)
    df_tail = df.tail(lookback).copy()
    close_tail = close.tail(lookback)
    high_tail = high.tail(lookback)
    low_tail = low.tail(lookback)
    volume_tail = volume.tail(lookback)

    if len(df_tail) < max(params.ma_200_period + params.ma_trend_period, params.local_extrema_order * 2 + 1):
        return {
            "stage2_pass": False,
            "vcp_pass": False,
            "rs_pass": False,
            "num_contractions": 0,
            "max_contraction": np.nan,
            "min_contraction": np.nan,
            "weeks_of_contraction": 0.0,
            "rs_rating": None,
        }

    ma_50 = close_tail.rolling(window=params.ma_50_period, min_periods=params.ma_50_period).mean()
    ma_150 = close_tail.rolling(window=params.ma_150_period, min_periods=params.ma_150_period).mean()
    ma_200 = close_tail.rolling(window=params.ma_200_period, min_periods=params.ma_200_period).mean()

    week_window = params.week_window if len(df_tail) >= params.week_window else len(df_tail)
    week_low = low_tail.rolling(window=week_window, min_periods=week_window).min()
    week_high = high_tail.rolling(window=week_window, min_periods=week_window).max()

    ma_200_slope = ma_200.rolling(
        window=params.ma_trend_period,
        min_periods=params.ma_trend_period,
    ).apply(_trend_value, raw=True)

    condition_1 = (close_tail > ma_150) & (close_tail > ma_200) & (close_tail > ma_50)
    condition_2 = (ma_150 > ma_200) & (ma_50 > ma_150)
    condition_3 = ma_200_slope > 0.0
    condition_6 = low_tail > (week_low * 1.3)
    condition_7 = high_tail > (week_high * 0.75)

    if benchmark_close is not None:
        benchmark_tail = benchmark_close.tail(lookback)
        rs_line = close_tail / benchmark_tail.replace(0, np.nan)
        rs_slope = rs_line.rolling(
            window=params.rs_trend_period,
            min_periods=params.rs_trend_period,
        ).apply(_trend_value, raw=True)
        condition_8 = rs_slope > 0.0
    else:
        condition_8 = pd.Series([False] * len(df_tail), index=df_tail.index)

    if not params.require_rs_slope:
        condition_8 = pd.Series([True] * len(df_tail), index=df_tail.index)

    stage2_pass = bool(
        condition_1.iloc[-1]
        and condition_2.iloc[-1]
        and condition_3.iloc[-1]
        and condition_6.iloc[-1]
        and condition_7.iloc[-1]
        and condition_8.iloc[-1]
    )

    highs = high_tail.to_numpy(dtype=float)
    lows = low_tail.to_numpy(dtype=float)
    local_high = _local_extrema(highs, params.local_extrema_order, mode="max")
    local_low = _local_extrema(lows, params.local_extrema_order, mode="min")
    local_high, local_low = _adjust_local_high_low(local_high, local_low)

    contraction = (
        _contractions(highs, lows, local_high, local_low)
        if local_high.size >= 2 and local_low.size >= 2
        else []
    )
    num_c = _num_contractions(contraction) if contraction else 0
    max_c = contraction[num_c - 1] if num_c >= 1 else np.nan
    min_c = contraction[0] if num_c >= 1 else np.nan

    weeks_of_contraction = 0.0
    if contraction and num_c >= 1 and local_high.size >= num_c:
        weeks_of_contraction = (len(df_tail.index) - local_high[::-1][num_c - 1]) / 5

    vol_ma_short = volume_tail.rolling(
        window=params.vol_short_period,
        min_periods=params.vol_short_period,
    ).mean()
    vol_ma_long = volume_tail.rolling(
        window=params.vol_long_period,
        min_periods=params.vol_long_period,
    ).mean()
    vol_contraction = bool(vol_ma_short.iloc[-1] < vol_ma_long.iloc[-1])

    consolidation_ok = False
    if local_high.size > 0:
        consolidation_ok = bool(high_tail.iloc[-1] < high_tail.iloc[local_high[-1]])
    if not params.require_consolidation:
        consolidation_ok = True

    flag_num = params.min_contractions <= num_c <= params.max_contractions
    flag_max = bool(max_c <= params.max_contraction_depth) if not np.isnan(max_c) else False
    flag_min = bool(min_c <= params.min_contraction_depth) if not np.isnan(min_c) else False
    flag_week = weeks_of_contraction >= params.min_weeks

    vcp_pass = bool(flag_num and flag_max and flag_min and flag_week and vol_contraction and consolidation_ok)

    rs_rating = None
    rs_pass = True
    if rs_rating_series is not None:
        rs_rating_value = rs_rating_series.tail(lookback).iloc[-1]
        rs_rating = float(rs_rating_value) if pd.notna(rs_rating_value) else None
        if params.require_rs_rating:
            rs_pass = rs_rating is not None and rs_rating >= params.min_rs_rating
    elif params.require_rs_rating:
        rs_pass = False

    return {
        "stage2_pass": stage2_pass,
        "vcp_pass": vcp_pass,
        "rs_pass": rs_pass,
        "num_contractions": num_c,
        "max_contraction": max_c,
        "min_contraction": min_c,
        "weeks_of_contraction": weeks_of_contraction,
        "rs_rating": rs_rating,
    }
