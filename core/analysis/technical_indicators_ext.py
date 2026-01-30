"""
技术指标扩展模块。
包含 SMA/EMA/RSI/MACD/BOLL/OBV/ATR 等。

数学原理：
1. 移动平均与动量指标。
2. 波动率与成交量衍生指标。
"""


from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Tuple

# 第二组：第三方库（按字母排序）
import numpy as np
import pandas as pd

# 第三组：项目内部导入

def accumulation_distribution_line(df: pd.DataFrame, period: int = 1) -> pd.Series:
    """
    计算累积/派发线（ADL）。
    """
    high = df["High"].shift(period)
    low = df["Low"].shift(period)
    close = df["Adj Close"]
    mfm = ((close - low) - (high - close)) / (high - low)
    mfv = mfm * df["Volume"].shift(period)
    return mfv.cumsum()


def adxvma(data: pd.DataFrame, period: int = 14, multiplier: float = 2, offset: float = 0.5) -> pd.Series:
    """
    ADXVMA 指标（基于 ADX 与 EMA 的混合）。
    """
    tr = pd.DataFrame(index=data.index)
    tr["hl"] = (data["High"] - data["Low"]).abs()
    tr["hc"] = (data["High"] - data["Close"].shift()).abs()
    tr["lc"] = (data["Low"] - data["Close"].shift()).abs()
    tr["tr"] = tr.max(axis=1)
    atr = tr["tr"].rolling(period).mean()

    dx = pd.DataFrame(index=data.index)
    dx["hd"] = data["High"] - data["High"].shift()
    dx["ld"] = data["Low"].shift() - data["Low"]
    dx["plus_dm"] = np.where((dx["hd"] > 0) & (dx["hd"] > dx["ld"]), dx["hd"], 0)
    dx["minus_dm"] = np.where((dx["ld"] > 0) & (dx["ld"] > dx["hd"]), dx["ld"], 0)
    dx["plus_di"] = 100 * dx["plus_dm"].rolling(period).sum() / atr
    dx["minus_di"] = 100 * dx["minus_dm"].rolling(period).sum() / atr
    dx["dx"] = 100 * (dx["plus_di"] - dx["minus_di"]).abs() / (dx["plus_di"] + dx["minus_di"])
    return dx["dx"] * multiplier + data["Close"].ewm(alpha=1 / (period * offset)).mean() * (1 - multiplier)


def ease_of_movement(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Ease of Movement（EVM/EMV）。
    """
    distance = ((df["High"] + df["Low"]) / 2) - ((df["High"].shift(1) + df["Low"].shift(1)) / 2)
    box_ratio = (df["Volume"] / 100000000) / (df["High"] - df["Low"])
    emv = distance / box_ratio
    return emv.rolling(period).mean()


def force_index(df: pd.DataFrame, period: int = 1) -> pd.Series:
    """
    Force Index。
    """
    return (df["Adj Close"].diff(period) * df["Volume"]).rename("ForceIndex")


def chaikin_oscillator(df: pd.DataFrame, short: int = 3, long: int = 10) -> pd.Series:
    """
    Chaikin Oscillator。
    """
    mfv = (2 * df["Adj Close"] - df["High"] - df["Low"]) / (df["High"] - df["Low"]) * df["Volume"]
    ad = mfv.cumsum()
    ema_short = ad.ewm(com=(short - 1) / 2).mean()
    ema_long = ad.ewm(com=(long - 1) / 2).mean()
    return (ema_short - ema_long).rename("Chaikin")


def tsi(df: pd.DataFrame, r: int = 25, s: int = 13) -> pd.Series:
    """
    Ergodic True Strength Index。
    """
    close = df["Adj Close"]
    pc = close.pct_change().fillna(0)

    def _double_smooth(x: pd.Series, w: int) -> pd.Series:
        return x.ewm(span=w).mean().ewm(span=w).mean()

    ema_r = _double_smooth(pc, r)
    ema_s = _double_smooth(ema_r, s)
    abs_ema_r = _double_smooth(pc.abs(), r)
    abs_ema_s = _double_smooth(abs_ema_r, s)
    return 100 * ema_s / abs_ema_s


def weighted_moving_average(series: pd.Series, window: int) -> pd.Series:
    """
    线性加权移动平均（WMA）。
    """
    weights = np.arange(1, window + 1)
    return series.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def fishy_turbo(df: pd.DataFrame, rsi_window: int = 6, wma_window: int = 6) -> pd.Series:
    """
    Fishy Turbo 指标。
    """
    delta = df["Adj Close"].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.rolling(window=rsi_window, min_periods=1).mean()
    avg_loss = down.rolling(window=rsi_window, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    x = weighted_moving_average(0.1 * (rsi - 50), wma_window)
    return (np.exp(2 * x) - 1) / (np.exp(2 * x) + 1)


def guppy_ema(series: pd.Series, lookback_period: int) -> pd.Series:
    """
    Guppy EMA 计算。
    """
    return series.ewm(span=lookback_period, adjust=False).mean()


def heiken_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算 Heiken Ashi K 线。
    """
    ha = df.copy()
    ha["HA_Close"] = (ha["Open"] + ha["High"] + ha["Low"] + ha["Close"]) / 4
    ha_open = np.zeros(len(ha))
    ha_open[0] = (ha["Open"].iloc[0] + ha["Close"].iloc[0]) / 2
    for i in range(1, len(ha)):
        ha_open[i] = (ha_open[i - 1] + ha["HA_Close"].iloc[i - 1]) / 2
    ha["HA_Open"] = ha_open
    ha["HA_High"] = ha[["HA_Open", "HA_Close", "High"]].max(axis=1)
    ha["HA_Low"] = ha[["HA_Open", "HA_Close", "Low"]].min(axis=1)
    return ha


def linear_weighted_moving_average(close: pd.Series, window: int) -> pd.Series:
    """
    线性加权移动平均（数组权重版）。
    """
    values = close.to_numpy()
    lwma = [np.nan] * window
    weights = np.arange(window) + 1
    denom = weights.sum()
    for i in range(window, len(values)):
        lwma.append((values[i - window : i] * weights).sum() / denom)
    return pd.Series(lwma, index=close.index)


def parabolic_sar(high: pd.Series, low: pd.Series, acceleration_factor: float = 0.02, max_acceleration_factor: float = 0.2) -> pd.Series:
    """
    Parabolic SAR。
    """
    high_vals = high.to_numpy()
    low_vals = low.to_numpy()
    sar = low_vals[0]
    ep = high_vals[0]
    af = acceleration_factor
    trend = 1
    sar_list = [sar]
    for i in range(1, len(high_vals)):
        if trend == 1:
            if low_vals[i] < sar:
                trend = -1
                sar = ep
                ep = high_vals[i]
                af = acceleration_factor
            else:
                sar = sar + af * (ep - sar)
                if high_vals[i] > ep:
                    ep = high_vals[i]
                    af = min(af + acceleration_factor, max_acceleration_factor)
        else:
            if high_vals[i] > sar:
                trend = 1
                sar = ep
                ep = low_vals[i]
                af = acceleration_factor
            else:
                sar = sar - af * (sar - ep)
                if low_vals[i] < ep:
                    ep = low_vals[i]
                    af = min(af + acceleration_factor, max_acceleration_factor)
        sar_list.append(sar)
    return pd.Series(sar_list, index=high.index)


def pmo(df: pd.DataFrame, fast: int = 35, slow: int = 20, signal: int = 10) -> Tuple[pd.Series, pd.Series]:
    """
    Price Momentum Oscillator (PMO)。
    """
    smoothing_multiplier = 2 / (fast + 1)
    smoothed = [df["Close"].iloc[0]]
    for i in range(1, len(df)):
        smoothed_value = ((df["Close"].iloc[i] - smoothed[-1]) * smoothing_multiplier) + smoothed[-1]
        smoothed.append(smoothed_value)
    smoothed = pd.Series(smoothed, index=df.index)
    price_change = (df["Close"] / df["Close"].shift(1) * 100) - 100
    pmo_line = 10 * pd.Series(smoothed).ewm(span=slow, adjust=False).mean()
    pmo_signal = pmo_line.ewm(span=signal, adjust=False).mean()
    return pmo_line, pmo_signal


def special_k(df: pd.DataFrame) -> pd.Series:
    """
    Pring's Special K。
    """
    roc_periods = [10, 15, 20, 30, 40, 65, 75, 100, 195, 265, 390, 530]
    weights = [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]
    sma_periods = [10, 10, 10, 15, 50, 65, 75, 100, 130, 130, 130, 195]
    result = pd.Series(0, index=df.index, dtype=float)
    for roc_period, weight, sma_period in zip(roc_periods, weights, sma_periods):
        roc = df["Close"].pct_change(periods=roc_period) * 100
        sma = roc.rolling(window=sma_period).mean()
        result += sma * weight
    return result


def rs_ratio_momentum(df: pd.DataFrame, benchmark: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series]:
    """
    Relative Strength Ratio & Momentum。
    """
    rs = df["Adj Close"] / benchmark
    rs_ratio = rs / rs.rolling(window=period).mean()
    rs_momentum = rs_ratio.diff(period)
    return rs_ratio, rs_momentum


def tma(df: pd.DataFrame, period: int = 30, column: str = "Close") -> pd.Series:
    """
    Triangular Moving Average（TMA）。
    """
    sma = df[column].rolling(window=period).mean()
    return pd.Series(sma).rolling(window=period).mean()


def vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    """
    Volume Weighted Moving Average（VWMA）。
    """
    cv = close.shift(window) * volume.shift(window)
    tv = volume.rolling(window).sum()
    return cv / tv


def vwap(df: pd.DataFrame) -> float:
    """
    Volume Weighted Average Price（VWAP）。
    """
    return float((df["Adj Close"] * df["Volume"]).sum() / df["Volume"].sum())


def wma(data: pd.Series, window: int) -> np.ndarray:
    """
    Weighted Moving Average（数组版）。
    """
    ws = np.zeros(data.shape[0])
    t_sum = sum(range(1, window + 1))
    values = data.to_numpy()
    for i in range(window - 1, data.shape[0]):
        ws[i] = sum(values[i - window + 1 : i + 1] * np.linspace(1, window, window)) / t_sum
    return ws


def wsma(df: pd.DataFrame, column: str = "Adj Close", window: int = 14) -> pd.Series:
    """
    Wilder's Smoothing Moving Average（WSMA）。
    """
    ema = df[column].ewm(span=window, min_periods=window - 1).mean()
    k = 1 / window
    return df[column] * k + ema * (1 - k)

