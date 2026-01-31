"""
VCP（Volatility Contraction Pattern）波动收缩形态指标。

适用场景：
- 作为交易策略的核心信号指标，输出 VCP 信号与收缩统计。

数学原理：
1. Stage 2 趋势模板：价格高于 MA50/MA150/MA200，且 MA50 > MA150 > MA200。
2. 收缩次数：局部高低点之间的价格收缩幅度递减。
3. 成交量枯竭：短期成交量均线低于长期均线。
"""

from __future__ import annotations

import numpy as np
import backtrader as bt

from core.strategy.indicator.common import SignalRecordManager


class VCPIndicator(bt.Indicator):
    lines = ("stage2_pass", "vcp_signal", "num_contractions", "max_contraction", "min_contraction")
    params = (
        ("ma_50_period", 50),
        ("ma_150_period", 150),
        ("ma_200_period", 200),
        ("ma_trend_period", 20),
        ("local_extrema_order", 10),
        ("min_contractions", 2),
        ("max_contractions", 4),
        ("max_contraction_depth", 50.0),
        ("min_contraction_depth", 15.0),
        ("min_weeks", 2),
        ("lookback_period", 252),
        ("vol_short_period", 5),
        ("vol_long_period", 30),
    )

    plotinfo = dict(subplot=False)
    plotlines = dict(vcp_signal=dict(marker="", _plotskip=True))

    def __init__(self):
        self.signal_record_manager = SignalRecordManager()
        self.ma_50 = bt.indicators.SMA(self.data.close, period=self.p.ma_50_period)
        self.ma_150 = bt.indicators.SMA(self.data.close, period=self.p.ma_150_period)
        self.ma_200 = bt.indicators.SMA(self.data.close, period=self.p.ma_200_period)
        self.week_52_low = bt.indicators.Lowest(self.data.low, period=252)
        self.week_52_high = bt.indicators.Highest(self.data.high, period=252)
        self.vol_ma_short = bt.indicators.SMA(self.data.volume, period=self.p.vol_short_period)
        self.vol_ma_long = bt.indicators.SMA(self.data.volume, period=self.p.vol_long_period)

    def next(self):
        self.lines.stage2_pass[0] = 0
        self.lines.vcp_signal[0] = np.nan
        self.lines.num_contractions[0] = 0
        self.lines.max_contraction[0] = np.nan
        self.lines.min_contraction[0] = np.nan

        if len(self) < self.p.ma_200_period + self.p.ma_trend_period:
            return

        stage2 = self._check_stage2()
        self.lines.stage2_pass[0] = 1 if stage2 else 0
        if not stage2:
            return

        vcp_result = self._check_vcp()
        if not vcp_result["is_vcp"]:
            return

        self.lines.vcp_signal[0] = self.data.close[0]
        self.lines.num_contractions[0] = vcp_result["num_contractions"]
        self.lines.max_contraction[0] = vcp_result["max_contraction"]
        self.lines.min_contraction[0] = vcp_result["min_contraction"]

        self.signal_record_manager.add_signal_record(
            self.data.datetime.date(),
            "vcp_buy",
            f"VCP形态: {vcp_result['num_contractions']}次收缩",
        )

    def _check_stage2(self) -> bool:
        close = self.data.close[0]
        cond1 = close > self.ma_50[0] and close > self.ma_150[0] and close > self.ma_200[0]
        cond2 = self.ma_50[0] > self.ma_150[0] > self.ma_200[0]
        ma200_slope = self.ma_200[0] - self.ma_200[-self.p.ma_trend_period]
        cond3 = ma200_slope > 0
        cond4 = close > self.week_52_low[0] * 1.3
        cond5 = close > self.week_52_high[0] * 0.75
        return cond1 and cond2 and cond3 and cond4 and cond5

    def _check_vcp(self) -> dict:
        result = {
            "is_vcp": False,
            "num_contractions": 0,
            "max_contraction": 0.0,
            "min_contraction": 0.0,
        }

        lookback = min(len(self), self.p.lookback_period)
        if lookback < max(self.p.ma_200_period, self.p.local_extrema_order * 2 + 1):
            return result

        highs = np.array([self.data.high[-i] for i in range(lookback - 1, -1, -1)], dtype=float)
        lows = np.array([self.data.low[-i] for i in range(lookback - 1, -1, -1)], dtype=float)

        local_high = self._local_extrema(highs, self.p.local_extrema_order, mode="max")
        local_low = self._local_extrema(lows, self.p.local_extrema_order, mode="min")
        if len(local_high) < 2 or len(local_low) < 2:
            return result

        contraction = self._contractions(highs, lows, local_high, local_low)
        if len(contraction) < self.p.min_contractions:
            return result

        num_c = self._num_contractions(contraction)
        if not (self.p.min_contractions <= num_c <= self.p.max_contractions):
            return result

        max_c = contraction[num_c - 1]
        min_c = contraction[0]
        if max_c > self.p.max_contraction_depth:
            return result
        if min_c > self.p.min_contraction_depth:
            return result

        weeks = (lookback - local_high[::-1][num_c - 1]) / 5
        if weeks < self.p.min_weeks:
            return result

        if self.vol_ma_short[0] >= self.vol_ma_long[0]:
            return result

        result["is_vcp"] = True
        result["num_contractions"] = num_c
        result["max_contraction"] = max_c
        result["min_contraction"] = min_c
        return result

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
