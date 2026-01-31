"""
VCP（Volatility Contraction Pattern）指标计算模块。

数学原理：
1. Stage 2 趋势模板：价格高于 MA50/MA150/MA200，且 MA50 > MA150 > MA200。
2. 收缩次数：局部高低点之间的价格收缩幅度递减。
3. 成交量枯竭：短期成交量均线低于长期均线。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

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


def compute_vcp_features(df: pd.DataFrame, params: VCPParams | None = None) -> Dict[str, float | int | List[int] | List[float] | pd.Series | None]:
    """
    计算 VCP 相关技术指标特征（不做条件判定）。

    返回特征包含：
    - 均线数值与斜率
    - 52周高低点
    - 局部高低点索引
    - 收缩次数与幅度
    - 成交量均线
    - 形态持续周数
    """

    if params is None:
        params = VCPParams()

    # 提取 OHLCV 数据列（容错处理大小写）
    close = _resolve_column(df, "close")
    high = _resolve_column(df, "high")
    low = _resolve_column(df, "low")
    volume = _resolve_column(df, "volume")

    # ========== 数据充分性检查 ==========
    # 需要足够的历史数据用于均线计算和极值点识别
    min_required = max(params.ma_200_period + params.ma_trend_period, params.local_extrema_order * 2 + 1)
    if len(df) < min_required:
        return {
            "close_last": None,
            "high_last": None,
            "low_last": None,
            "ma_50": None,
            "ma_150": None,
            "ma_200": None,
            "ma_200_slope": None,
            "week_52_low": None,
            "week_52_high": None,
            "local_high": [],
            "local_low": [],
            "contraction": [],
            "num_contractions": 0,
            "max_contraction": None,
            "min_contraction": None,
            "weeks_of_contraction": 0.0,
            "vol_ma_short": None,
            "vol_ma_long": None,
            "lookback": 0,
        }

    # ========== 回溯周期数据提取 ==========
    # 取最近 lookback_period 条数据（通常252天≈1年）用于 VCP 分析
    lookback = min(len(df), params.lookback_period)
    df_tail = df.tail(lookback)
    close_tail = close.tail(lookback)    # 回溯收盘价
    high_tail = high.tail(lookback)      # 回溯最高价（用于局部高点）
    low_tail = low.tail(lookback)        # 回溯最低价（用于局部低点）
    volume_tail = volume.tail(lookback)  # 回溯成交量（用于成交量枯竭判断）

    # ========== 计算关键均线 ==========
    # MA50：短期均线，判断价格是否处于上升态
    ma_50 = close_tail.rolling(window=params.ma_50_period, min_periods=params.ma_50_period).mean()
    
    # MA150：中期均线，作为中期支撑位
    ma_150 = close_tail.rolling(window=params.ma_150_period, min_periods=params.ma_150_period).mean()
    
    # MA200：长期均线，判断长期趋势是否向上
    ma_200 = close_tail.rolling(window=params.ma_200_period, min_periods=params.ma_200_period).mean()

    # ========== 计算 52 周高低点 ==========
    # 52周最低价（252个交易日），用于判断当前价格相对底部的高度
    week_52_low = low_tail.rolling(window=252, min_periods=252).min()
    
    # 52周最高价（252个交易日），用于判断当前价格相对顶部的位置
    week_52_high = high_tail.rolling(window=252, min_periods=252).max()

    # ========== 计算 MA200 趋势斜率 ==========
    # MA200斜率 = 当前MA200 - 过去N日MA200（N由ma_trend_period决定，默认20）
    # 正数表示长期均线向上，是 Stage 2 上升趋势的判断依据
    ma_200_slope = ma_200.iloc[-1] - ma_200.iloc[-params.ma_trend_period]

    # ========== 提取局部极值点 ==========
    # 将数据转为 numpy 数组便于处理
    highs = high_tail.to_numpy(dtype=float)
    lows = low_tail.to_numpy(dtype=float)

    # 局部高点：当前K线的最高价 = 前后 order 根K线中的最高价（默认order=10）
    # 识别波段的顶部，用于计算收缩
    local_high = _local_extrema(highs, params.local_extrema_order, mode="max")
    
    # 局部低点：当前K线的最低价 = 前后 order 根K线中的最低价（默认order=10）
    # 识别波段的底部，用于计算收缩
    local_low = _local_extrema(lows, params.local_extrema_order, mode="min")

    # ========== 计算波段收缩幅度 ==========
    # 收缩 = (高点 - 低点) / 高点 × 100（百分比形式）
    # 按时间从旧到新，收缩幅度应该逐次递减（即收缩深度越来越小）
    contraction = _contractions(highs, lows, local_high, local_low) if len(local_high) >= 2 and len(local_low) >= 2 else []
    
    num_c = _num_contractions(contraction) if contraction else 0

    # ========== 提取收缩深度数据 ==========
    # 最大收缩幅度：第 num_c 个收缩的幅度（按逐减顺序，最后一个收缩最小）
    max_c = contraction[num_c - 1] if num_c >= 1 else 0.0
    
    # 最小收缩幅度：第一个收缩的幅度（按逐减顺序，第一个收缩最大）
    min_c = contraction[0] if num_c >= 1 else 0.0

    if contraction and num_c >= 1 and len(local_high) >= num_c:
        weeks = (lookback - local_high[::-1][num_c - 1]) / 5
        weeks_of_contraction = weeks
    else:
        weeks_of_contraction = 0.0

    # 短期成交量均线（5日）
    vol_ma_short = volume_tail.rolling(window=params.vol_short_period, min_periods=params.vol_short_period).mean()
    
    # 长期成交量均线（30日）
    vol_ma_long = volume_tail.rolling(window=params.vol_long_period, min_periods=params.vol_long_period).mean()
    
    return {
        "close_last": close_tail.iloc[-1],
        "high_last": high_tail.iloc[-1],
        "low_last": low_tail.iloc[-1],
        "ma_50": ma_50.iloc[-1],
        "ma_150": ma_150.iloc[-1],
        "ma_200": ma_200.iloc[-1],
        "ma_200_slope": ma_200_slope,
        "week_52_low": week_52_low.iloc[-1],
        "week_52_high": week_52_high.iloc[-1],
        "local_high": local_high.tolist(),
        "local_low": local_low.tolist(),
        "contraction": contraction,
        "num_contractions": num_c,
        "max_contraction": max_c,
        "min_contraction": min_c,
        "weeks_of_contraction": weeks_of_contraction,
        "vol_ma_short": vol_ma_short.iloc[-1],
        "vol_ma_long": vol_ma_long.iloc[-1],
        "lookback": lookback,
    }


def evaluate_vcp(df: pd.DataFrame, params: VCPParams | None = None) -> Dict[str, float | int | List[int] | List[float] | pd.Series | None]:
    """
    兼容接口：返回 VCP 技术指标特征，不做条件判定。
    """
    return compute_vcp_features(df, params)
