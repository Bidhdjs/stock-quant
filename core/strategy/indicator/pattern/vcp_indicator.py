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
import pandas as pd

from core.analysis.indicators.vcp import VCPParams, evaluate_vcp
from core.strategy.indicator.common import SignalRecordManager


class VCPIndicator(bt.Indicator):
    lines = (
        "stage2_pass",
        "vcp_signal",
        "vcp_sell_signal",
        "num_contractions",
        "max_contraction",
        "min_contraction",
    )
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
        ("progress_threshold", 1.0),
        ("ema_sell_period", 5),
        ("debug_once", False),
    )

    plotinfo = dict(subplot=False)
    plotlines = dict(vcp_signal=dict(marker="", _plotskip=True))

    def __init__(self):
        self.signal_record_manager = SignalRecordManager()
        self._min_len = max(
            self.p.ma_200_period + self.p.ma_trend_period, self.p.local_extrema_order * 2 + 1
        )
        self._debug_printed = False
        self._vcp_bought = False
        self.ema_sell = bt.indicators.EMA(self.data.close, period=self.p.ema_sell_period)
        self.addminperiod(self._min_len)

    def _build_feature_frame(self, lookback: int) -> pd.DataFrame:
        data = {
            "high": np.array(self.data.high.get(size=lookback)),
            "low": np.array(self.data.low.get(size=lookback)),
            "close": np.array(self.data.close.get(size=lookback)),
            "volume": np.array(self.data.volume.get(size=lookback)),
        }
        return pd.DataFrame(data)

    def next(self):
        self.lines.stage2_pass[0] = 0
        self.lines.vcp_signal[0] = np.nan
        self.lines.vcp_sell_signal[0] = np.nan
        self.lines.num_contractions[0] = 0
        self.lines.max_contraction[0] = np.nan
        self.lines.min_contraction[0] = np.nan

        if len(self) < self._min_len:
            return
        lookback = min(len(self), self.p.lookback_period)
        df = self._build_feature_frame(lookback)
        params = VCPParams(
            ma_50_period=self.p.ma_50_period,
            ma_150_period=self.p.ma_150_period,
            ma_200_period=self.p.ma_200_period,
            ma_trend_period=self.p.ma_trend_period,
            local_extrema_order=self.p.local_extrema_order,
            min_contractions=self.p.min_contractions,
            max_contractions=self.p.max_contractions,
            max_contraction_depth=self.p.max_contraction_depth,
            min_contraction_depth=self.p.min_contraction_depth,
            min_weeks=self.p.min_weeks,
            lookback_period=self.p.lookback_period,
            vol_short_period=self.p.vol_short_period,
            vol_long_period=self.p.vol_long_period,
        )
        vcp_result = evaluate_vcp(df, params)

        if self.p.debug_once and not self._debug_printed:
            print(f"vcp_result @ {self.data.datetime.date(0)}: {vcp_result}")
            self._debug_printed = True

        self.lines.stage2_pass[0] = 1 if vcp_result["stage2_pass"] else 0
        if not vcp_result["stage2_pass"]:
            return

        if vcp_result["progress"] < self.p.progress_threshold:
            return

        if not vcp_result["is_vcp"] and self.p.progress_threshold >= 1.0:
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
        self._vcp_bought = True

        if self._vcp_bought and len(self) > self.p.ema_sell_period:
            prev_close = self.data.close[-1]
            prev_ema = self.ema_sell[-1]
            curr_close = self.data.close[0]
            curr_ema = self.ema_sell[0]
            if prev_close >= prev_ema and curr_close < curr_ema:
                self.lines.vcp_sell_signal[0] = curr_close
                self.signal_record_manager.add_signal_record(
                    self.data.datetime.date(),
                    "vcp_sell",
                    f"跌破EMA{self.p.ema_sell_period}",
                )
                self._vcp_bought = False
                if self.p.debug_once:
                    print(
                        f"vcp_sell @ {self.data.datetime.date(0)}: "
                        f"close={curr_close:.2f} ema={curr_ema:.2f}"
                    )
