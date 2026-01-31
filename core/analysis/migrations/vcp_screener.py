"""
VCP 筛选器（拆分与精简版）。

适用场景：
- 迁移自 x/vcp_screener.github.io-main 的示例脚本。
- 提供可复用的 VCP 形态检测与筛选逻辑（默认不联网）。

数学原理：
1. 趋势模板：MA50/MA150/MA200 多头排列 + MA200 上升斜率。
2. VCP 收缩：局部高低点间的收缩幅度递减。
3. 成交量收缩：近 5 日均量 < 近 30 日均量。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VcpScreenerConfig:
    order: int = 10
    max_contraction: float = 50.0
    min_contraction: float = 15.0
    min_weeks: float = 2.0
    max_weeks: float = 26.0
    min_contractions: int = 2
    max_contractions: int = 4
    rs_threshold: float = 70.0


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    data = data.rename(columns=rename_map)
    if "close" not in data.columns and "adj_close" in data.columns:
        data["close"] = data["adj_close"]
    return data


def _require_columns(data: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [col for col in cols if col not in data.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")


def _local_extrema(arr: np.ndarray, order: int, mode: str) -> np.ndarray:
    if len(arr) < order * 2 + 1:
        return np.array([], dtype=int)
    if mode not in {"max", "min"}:
        raise ValueError("mode 必须是 'max' 或 'min'")
    idx = []
    for i in range(order, len(arr) - order):
        window = arr[i - order : i + order + 1]
        center = arr[i]
        if mode == "max" and np.all(center >= window) and center == window.max():
            idx.append(i)
        if mode == "min" and np.all(center <= window) and center == window.min():
            idx.append(i)
    return np.array(idx, dtype=int)


def local_high_low(data: pd.DataFrame, order: int = 10) -> tuple[np.ndarray, np.ndarray]:
    _require_columns(data, ["high", "low"])
    highs = data["high"].to_numpy()
    lows = data["low"].to_numpy()
    return _local_extrema(highs, order, "max"), _local_extrema(lows, order, "min")


def contractions(data: pd.DataFrame, local_high: np.ndarray, local_low: np.ndarray) -> list[float]:
    if len(local_high) == 0 or len(local_low) == 0:
        return []
    highs = local_high[::-1]
    lows = local_low[::-1]
    contraction = []
    i = 0
    j = 0
    while i < len(lows) and j < len(highs):
        if lows[i] > highs[j]:
            high_price = data["high"].iloc[highs[j]]
            low_price = data["low"].iloc[lows[i]]
            contraction.append(round((high_price - low_price) / high_price * 100, 2))
            i += 1
            j += 1
        else:
            j += 1
    return contraction


def num_of_contractions(contraction: list[float]) -> int:
    if not contraction:
        return 0
    new_c = 0
    num = 0
    for c in contraction:
        if c > new_c:
            num += 1
            new_c = c
        else:
            break
    return num


def max_min_contraction(contraction: list[float], num: int) -> tuple[float, float]:
    if num == 0:
        return 0.0, 0.0
    return contraction[num - 1], contraction[0]


def weeks_of_contraction(data: pd.DataFrame, local_high: np.ndarray, num: int) -> float:
    if num == 0:
        return 0.0
    idx = local_high[::-1][num - 1]
    return (len(data.index) - idx) / 5


def trend_template(data: pd.DataFrame, df_spx: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    基于 Minervini 趋势模板判断 Stage 2。
    """
    df = data.copy()
    df["MA_50"] = df["close"].rolling(window=50).mean()
    df["MA_150"] = df["close"].rolling(window=150).mean()
    df["MA_200"] = df["close"].rolling(window=200).mean()

    if len(df.index) > 5 * 52:
        df["52_week_low"] = df["low"].rolling(window=5 * 52).min()
        df["52_week_high"] = df["high"].rolling(window=5 * 52).max()
    else:
        df["52_week_low"] = df["low"].rolling(window=len(df.index)).min()
        df["52_week_high"] = df["high"].rolling(window=len(df.index)).max()

    df["condition_1"] = (df["close"] > df["MA_150"]) & (df["close"] > df["MA_200"]) & (df["close"] > df["MA_50"])
    df["condition_2"] = (df["MA_150"] > df["MA_200"]) & (df["MA_50"] > df["MA_150"])
    slope = df["MA_200"].rolling(window=20).apply(lambda x: _slope(x), raw=False)
    df["condition_3"] = slope > 0.0
    df["condition_6"] = df["low"] > (df["52_week_low"] * 1.3)
    df["condition_7"] = df["high"] > (df["52_week_high"] * 0.75)

    if df_spx is not None and "close" in df_spx.columns:
        rs = df["close"] / df_spx["close"].reindex(df.index).ffill()
        slope_rs = rs.rolling(window=20).apply(lambda x: _slope(x), raw=False)
        df["condition_8"] = slope_rs > 0.0
    else:
        df["condition_8"] = True

    df["Pass"] = df[
        ["condition_1", "condition_2", "condition_3", "condition_6", "condition_7", "condition_8"]
    ].all(axis="columns")
    return df


def _slope(nums: pd.Series | np.ndarray) -> float:
    values = np.asarray(nums, dtype=float)
    if len(values) < 2:
        return 0.0
    x = np.arange(1, len(values) + 1, dtype=float)
    y = values
    numerator = (len(values) * (x * y).sum()) - (x.sum() * y.sum())
    denominator = (len(values) * (x * x).sum()) - (x.sum() ** 2)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def vcp(data: pd.DataFrame, config: VcpScreenerConfig | None = None) -> tuple[int, float, float, float, int]:
    """
    返回 (收缩次数, 最大收缩, 最小收缩, 收缩周数, 是否符合VCP)。
    """
    if config is None:
        config = VcpScreenerConfig()
    local_high, local_low = local_high_low(data, order=config.order)
    contraction = contractions(data, local_high, local_low)
    num = num_of_contractions(contraction)
    if num == 0:
        return 0, 0.0, 0.0, 0.0, 0
    max_c, min_c = max_min_contraction(contraction, num)
    weeks = weeks_of_contraction(data, local_high, num)

    flag_num = int(config.min_contractions <= num <= config.max_contractions)
    flag_max = int(max_c <= config.max_contraction)
    flag_min = int(min_c <= config.min_contraction)
    flag_week = int(config.min_weeks <= weeks <= config.max_weeks)

    data = data.copy()
    data["30_day_avg_volume"] = data["volume"].rolling(window=30).mean()
    data["5_day_avg_volume"] = data["volume"].rolling(window=5).mean()
    data["vol_contraction"] = data["5_day_avg_volume"] < data["30_day_avg_volume"]
    flag_vol = int(bool(data["vol_contraction"].iloc[-1]))

    if len(local_high) == 0:
        flag_consolidation = 0
    else:
        last_high_idx = local_high[-1]
        flag_consolidation = int(data["high"].iloc[-1] < data["high"].iloc[last_high_idx])

    flag_final = int(flag_num and flag_max and flag_min and flag_week and flag_vol and flag_consolidation)
    return num, max_c, min_c, weeks, flag_final


def rs_rating(ticker: str, rs_list: list[str]) -> float:
    if not rs_list or ticker not in rs_list:
        return 0.0
    ticker_index = rs_list.index(ticker)
    return round(ticker_index / len(rs_list) * 100, 0)


def screen_universe(
    ticker_data: dict[str, pd.DataFrame],
    rs_list: list[str] | None = None,
    df_spx: pd.DataFrame | None = None,
    config: VcpScreenerConfig | None = None,
) -> pd.DataFrame:
    """
    对传入的股票数据字典进行 VCP 筛选，返回结果表。
    """
    if config is None:
        config = VcpScreenerConfig()
    columns = [
        "Ticker",
        "Num_of_contraction",
        "Max_contraction",
        "Min_contraction",
        "Weeks_of_contraction",
        "RS_rating",
    ]
    results = []
    for ticker, raw_df in ticker_data.items():
        data = _normalize_ohlcv(raw_df)
        _require_columns(data, ["close", "high", "low", "volume"])
        trend = trend_template(data, df_spx=df_spx)
        if not bool(trend["Pass"].iloc[-1]):
            continue
        vcp_result = vcp(data, config=config)
        rs = rs_rating(ticker, rs_list or [])
        if vcp_result[-1] == 1 and rs >= config.rs_threshold:
            results.append(
                {
                    "Ticker": ticker,
                    "Num_of_contraction": vcp_result[0],
                    "Max_contraction": vcp_result[1],
                    "Min_contraction": vcp_result[2],
                    "Weeks_of_contraction": vcp_result[3],
                    "RS_rating": rs,
                }
            )
    return pd.DataFrame(results, columns=columns)


if __name__ == "__main__":
    print("该模块已拆分为可复用函数，默认不执行联网筛选。")
