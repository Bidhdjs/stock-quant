"""
VCPPlus 形态信号指标。
基于完整 VCP 筛选逻辑输出买卖信号线，供策略层调用。

数学原理：
1. Stage 2 趋势模板 + RS 斜率过滤，确认上升趋势。
2. 收缩次数与幅度递减，识别 VCP 盘整结构。
3. 成交量枯竭与未突破盘整区间，等待突破前信号。
"""

from __future__ import annotations

import numpy as np
import backtrader as bt
import pandas as pd

import settings
from core.analysis.indicators.vcp_plus import VCPPlusParams, evaluate_vcp_plus
from core.strategy.indicator.common import SignalRecordManager


class VCPPlusIndicator(bt.Indicator):
    lines = (
        "vcp_plus_stage2_pass",
        "vcp_plus_signal",
        "vcp_plus_sell_signal",
        "vcp_plus_num_contractions",
        "vcp_plus_max_contraction",
        "vcp_plus_min_contraction",
        "vcp_plus_weeks",
        "vcp_plus_rs_rating",
    )
    params = (
        ("ma_50_period", settings.VCP_PLUS_MA_50_PERIOD),
        ("ma_150_period", settings.VCP_PLUS_MA_150_PERIOD),
        ("ma_200_period", settings.VCP_PLUS_MA_200_PERIOD),
        ("ma_trend_period", settings.VCP_PLUS_MA_TREND_PERIOD),
        ("rs_trend_period", settings.VCP_PLUS_RS_TREND_PERIOD),
        ("week_window", settings.VCP_PLUS_WEEK_WINDOW),
        ("local_extrema_order", settings.VCP_PLUS_LOCAL_EXTREMA_ORDER),
        ("min_contractions", settings.VCP_PLUS_MIN_CONTRACTIONS),
        ("max_contractions", settings.VCP_PLUS_MAX_CONTRACTIONS),
        ("max_contraction_depth", settings.VCP_PLUS_MAX_CONTRACTION_DEPTH),
        ("min_contraction_depth", settings.VCP_PLUS_MIN_CONTRACTION_DEPTH),
        ("min_weeks", settings.VCP_PLUS_MIN_WEEKS),
        ("vol_short_period", settings.VCP_PLUS_VOL_SHORT_PERIOD),
        ("vol_long_period", settings.VCP_PLUS_VOL_LONG_PERIOD),
        ("lookback_period", settings.VCP_PLUS_LOOKBACK_PERIOD),
        ("require_rs_slope", settings.VCP_PLUS_REQUIRE_RS_SLOPE),
        ("require_rs_rating", settings.VCP_PLUS_REQUIRE_RS_RATING),
        ("min_rs_rating", settings.VCP_PLUS_MIN_RS_RATING),
        ("require_consolidation", settings.VCP_PLUS_REQUIRE_CONSOLIDATION),
        ("ema_sell_period", settings.VCP_PLUS_EMA_SELL_PERIOD),
        ("benchmark_close_column", settings.VCP_PLUS_BENCHMARK_CLOSE_COLUMN),
        ("rs_rating_column", settings.VCP_PLUS_RS_RATING_COLUMN),
        ("debug_once", False),
    )

    plotinfo = dict(subplot=False)
    plotlines = dict(vcp_plus_signal=dict(marker="", _plotskip=True))

    def __init__(self):
        self.signal_record_manager = SignalRecordManager()
        self._min_len = max(
            self.p.ma_200_period + self.p.ma_trend_period,
            self.p.local_extrema_order * 2 + 1,
            self.p.ema_sell_period,
            self.p.vol_long_period,
        )
        self._debug_printed = False
        self._vcp_bought = False
        self.ema_sell = bt.indicators.EMA(self.data.close, period=self.p.ema_sell_period)
        self.addminperiod(1)

    def _build_feature_frame(self, lookback: int) -> pd.DataFrame:
        safe_lookback = min(lookback, len(self))
        data = {
            "high": np.array(self.data.high.get(size=safe_lookback)),
            "low": np.array(self.data.low.get(size=safe_lookback)),
            "close": np.array(self.data.close.get(size=safe_lookback)),
            "volume": np.array(self.data.volume.get(size=safe_lookback)),
        }
        if hasattr(self.data, "benchmark_close"):
            data[self.p.benchmark_close_column] = np.array(
                self.data.benchmark_close.get(size=safe_lookback)
            )
        if hasattr(self.data, "rs_rating"):
            data[self.p.rs_rating_column] = np.array(
                self.data.rs_rating.get(size=safe_lookback)
            )
        return pd.DataFrame(data)

    def next(self):
        self.lines.vcp_plus_stage2_pass[0] = 0
        self.lines.vcp_plus_signal[0] = np.nan
        self.lines.vcp_plus_sell_signal[0] = np.nan
        self.lines.vcp_plus_num_contractions[0] = 0
        self.lines.vcp_plus_max_contraction[0] = np.nan
        self.lines.vcp_plus_min_contraction[0] = np.nan
        self.lines.vcp_plus_weeks[0] = 0
        self.lines.vcp_plus_rs_rating[0] = np.nan

        if len(self) < self._min_len:
            return

        lookback = min(len(self), self.p.lookback_period)
        df = self._build_feature_frame(lookback)
        if df.empty:
            return

        params = VCPPlusParams(
            ma_50_period=self.p.ma_50_period,
            ma_150_period=self.p.ma_150_period,
            ma_200_period=self.p.ma_200_period,
            ma_trend_period=self.p.ma_trend_period,
            rs_trend_period=self.p.rs_trend_period,
            week_window=self.p.week_window,
            local_extrema_order=self.p.local_extrema_order,
            min_contractions=self.p.min_contractions,
            max_contractions=self.p.max_contractions,
            max_contraction_depth=self.p.max_contraction_depth,
            min_contraction_depth=self.p.min_contraction_depth,
            min_weeks=self.p.min_weeks,
            vol_short_period=self.p.vol_short_period,
            vol_long_period=self.p.vol_long_period,
            lookback_period=self.p.lookback_period,
            require_rs_slope=self.p.require_rs_slope,
            require_rs_rating=self.p.require_rs_rating,
            min_rs_rating=self.p.min_rs_rating,
            require_consolidation=self.p.require_consolidation,
            benchmark_close_column=self.p.benchmark_close_column,
            rs_rating_column=self.p.rs_rating_column,
        )

        result = evaluate_vcp_plus(df, params)

        if self.p.debug_once and not self._debug_printed:
            print(f"vcp_plus_result @ {self.data.datetime.date(0)}: {result}")
            self._debug_printed = True

        self.lines.vcp_plus_stage2_pass[0] = 1 if result["stage2_pass"] else 0
        self.lines.vcp_plus_num_contractions[0] = result["num_contractions"]
        self.lines.vcp_plus_max_contraction[0] = result["max_contraction"]
        self.lines.vcp_plus_min_contraction[0] = result["min_contraction"]
        self.lines.vcp_plus_weeks[0] = result["weeks_of_contraction"]
        if result["rs_rating"] is not None:
            self.lines.vcp_plus_rs_rating[0] = result["rs_rating"]

        if not result["stage2_pass"]:
            return

        if not (result["vcp_pass"] and result["rs_pass"]):
            return

        self.lines.vcp_plus_signal[0] = self.data.close[0]
        rs_text = f", RS={result['rs_rating']:.0f}" if result["rs_rating"] is not None else ""
        self.signal_record_manager.add_signal_record(
            self.data.datetime.date(),
            "vcp_plus_buy",
            f"VCPPlus: {result['num_contractions']}次收缩, "
            f"max={result['max_contraction']:.2f}, min={result['min_contraction']:.2f}{rs_text}",
        )
        self._vcp_bought = True

        if self._vcp_bought and len(self) > self.p.ema_sell_period:
            prev_close = self.data.close[-1]
            prev_ema = self.ema_sell[-1]
            curr_close = self.data.close[0]
            curr_ema = self.ema_sell[0]
            if prev_close >= prev_ema and curr_close < curr_ema:
                self.lines.vcp_plus_sell_signal[0] = curr_close
                self.signal_record_manager.add_signal_record(
                    self.data.datetime.date(),
                    "vcp_plus_sell",
                    f"跌破EMA{self.p.ema_sell_period}",
                )
                self._vcp_bought = False
