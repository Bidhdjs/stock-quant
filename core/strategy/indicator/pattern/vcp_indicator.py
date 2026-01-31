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

from core.analysis.indicators.vcp import VCPParams, compute_vcp_features
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
            self.p.ma_200_period + self.p.ma_trend_period, 
            self.p.local_extrema_order * 2 + 1,
            self.p.ema_sell_period  # EMA 卖出信号也需要足够的历史数据
        )
        self._debug_printed = False
        self._vcp_bought = False
        self.ema_sell = bt.indicators.EMA(self.data.close, period=self.p.ema_sell_period)
        # 不强制设置超大 minperiod，避免短样本回测时触发 backtrader 内部越界
        # 在 next 中使用 len(self) 自行判断数据是否足够
        self.addminperiod(1)

    def _build_feature_frame(self, lookback: int) -> pd.DataFrame:
        """
        构建特征 DataFrame，安全处理数据获取
        
        防护措施：
        - 确保 lookback 不超过当前可用数据长度
        - 避免索引越界导致回测中断
        """
        # 确保 lookback 不超过实际可用数据
        safe_lookback = min(lookback, len(self))
        
        try:
            data = {
                "high": np.array(self.data.high.get(size=safe_lookback)),
                "low": np.array(self.data.low.get(size=safe_lookback)),
                "close": np.array(self.data.close.get(size=safe_lookback)),
                "volume": np.array(self.data.volume.get(size=safe_lookback)),
            }
            return pd.DataFrame(data)
        except Exception as e:
            # 如果获取数据失败，返回空 DataFrame（evaluate_vcp 会处理）
            print(f"[警告] _build_feature_frame 获取数据失败: {str(e)}, lookback={lookback}, available={len(self)}")
            return pd.DataFrame()

    def next(self):
        # ========== 初始化所有信号输出线 ==========
        # 设为 NaN 表示该 K 线无信号触发（图表上不显示标记）
        self.lines.stage2_pass[0] = 0  # Stage 2 状态：0=未通过，1=已通过
        self.lines.vcp_signal[0] = np.nan  # VCP 买入信号价格位置
        self.lines.vcp_sell_signal[0] = np.nan  # VCP 卖出信号价格位置
        self.lines.num_contractions[0] = 0  # 有效收缩次数
        self.lines.max_contraction[0] = np.nan  # 最大收缩幅度
        self.lines.min_contraction[0] = np.nan  # 最小收缩幅度

        # 数据充分性检查
        if len(self) < self._min_len:
            return
        
        # ========== 数据准备 ==========
        # 取最近 lookback_period 条数据构建 DataFrame（便于 evaluate_vcp 处理）
        # 关键：不能超过当前已加载的数据总长度，否则会导致索引越界
        lookback = min(len(self), self.p.lookback_period)
        df = self._build_feature_frame(lookback)
        
        # 创建参数对象并调用核心计算函数
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
        
        # ========== 调用指标特征计算函数 ==========
        # 返回值包含均线、收缩、成交量等特征（不做条件判定）
        # ========== 调用核心 VCP 计算函数 ==========
        # 返回值包含 6 个关键指标：
        # - stage2_pass: 是否满足 Stage 2 趋势
        # - is_vcp: 是否完全满足 VCP 形态
        # - progress: 进度分值 0-1（反映形态成熟度）
        # - num_contractions: 有效收缩次数
        # - max_contraction: 最小收缩幅度
        # - min_contraction: 最大收缩幅度
              
        # 防护：如果 DataFrame 为空，返回无信号
        if df.empty:
            return
            
        vcp_result = compute_vcp_features(df, params)

        # 调试输出（仅第一次）
        if self.p.debug_once and not self._debug_printed:
            print(f"vcp_result @ {self.data.datetime.date(0)}: {vcp_result}")
            self._debug_printed = True

        # ========== 信号过滤阶段 1：Stage 2 检查 ==========
        close_last = vcp_result.get("close_last")
        ma_50 = vcp_result.get("ma_50")
        ma_150 = vcp_result.get("ma_150")
        ma_200 = vcp_result.get("ma_200")
        ma_200_slope = vcp_result.get("ma_200_slope")
        week_52_low = vcp_result.get("week_52_low")
        week_52_high = vcp_result.get("week_52_high")

        stage2_pass = (
            close_last is not None
            and ma_50 is not None
            and ma_150 is not None
            and ma_200 is not None
            and week_52_low is not None
            and week_52_high is not None
            and close_last > ma_150
            and close_last > ma_200
            and close_last > ma_50
            and ma_50 > ma_150 > ma_200
            and ma_200_slope is not None
            and ma_200_slope > 0
            and close_last > week_52_low * 1.3
            and close_last > week_52_high * 0.75
        )

        # 输出 Stage 2 通过状态到指标线
        self.lines.stage2_pass[0] = 1 if stage2_pass else 0

        # 如果未通过 Stage 2 趋势，则无需继续分析
        if not stage2_pass:
            return

        # ========== 信号过滤阶段 2：VCP 条件检查 ==========
        num_c = vcp_result.get("num_contractions", 0)
        max_c = vcp_result.get("max_contraction")
        min_c = vcp_result.get("min_contraction")
        weeks = vcp_result.get("weeks_of_contraction", 0.0)
        vol_ma_short = vcp_result.get("vol_ma_short")
        vol_ma_long = vcp_result.get("vol_ma_long")

        contraction_count_ok = self.p.min_contractions <= num_c <= self.p.max_contractions
        max_depth_ok = max_c is not None and max_c <= self.p.max_contraction_depth
        min_depth_ok = min_c is not None and min_c <= self.p.min_contraction_depth
        weeks_ok = weeks >= self.p.min_weeks
        volume_dry_ok = (
            vol_ma_short is not None
            and vol_ma_long is not None
            and vol_ma_short < vol_ma_long
        )

        conditions = {
            "stage2": stage2_pass,
            "contraction_count": contraction_count_ok,
            "max_depth": max_depth_ok,
            "min_depth": min_depth_ok,
            "weeks": weeks_ok,
            "volume_dry": volume_dry_ok,
        }
        progress = sum(1.0 for ok in conditions.values() if ok) / len(conditions)

        # progress_threshold 用于控制形态成熟度要求
        # - 1.0：要求完全满足所有条件
        # - <1.0：允许部分条件未满足（接近 VCP 即可触发）
        if progress < self.p.progress_threshold:
            return

        # ========== 信号过滤阶段 3：VCP 完全确认 ==========
        # 当 progress_threshold=1.0 时，只有完全确立的 VCP 才输出信号
        if not all(conditions.values()) and self.p.progress_threshold >= 1.0:
            return

        # ========== VCP 买入信号输出 ==========
        # 将当前收盘价作为信号价格输出（用于图表标记）
        self.lines.vcp_signal[0] = self.data.close[0]
        
        # 输出收缩统计数据到指标线
        self.lines.num_contractions[0] = num_c
        self.lines.max_contraction[0] = max_c if max_c is not None else np.nan
        self.lines.min_contraction[0] = min_c if min_c is not None else np.nan

        # 记录买入信号事件（用于后续回测或交易决策）
        self.signal_record_manager.add_signal_record(
            self.data.datetime.date(),
            "vcp_buy",
            f"VCP形态: {vcp_result['num_contractions']}次收缩",
        )
        
        # 标记已触发 VCP 买入信号（用于后续卖出逻辑判断）
        self._vcp_bought = True

        # ========== VCP 卖出信号：EMA 穿越法 ==========
        # 买入后才检查卖出条件，确保有买卖对应
        if self._vcp_bought and len(self) > self.p.ema_sell_period:
            # 前一日数据
            prev_close = self.data.close[-1]
            prev_ema = self.ema_sell[-1]
            
            # 当前日数据
            curr_close = self.data.close[0]
            curr_ema = self.ema_sell[0]
            
            # ========== 卖出信号条件 ==========
            # 典型的卖出信号：价格从 EMA 上方穿过到下方
            # 即：前日收盘 ≥ EMA5 且 当日收盘 < EMA5
            # 这表示上升趋势被破坏，应该减仓或止损
            if prev_close >= prev_ema and curr_close < curr_ema:
                # 输出卖出信号价格（当前收盘价）
                self.lines.vcp_sell_signal[0] = curr_close
                
                # 记录卖出信号事件
                self.signal_record_manager.add_signal_record(
                    self.data.datetime.date(),
                    "vcp_sell",
                    f"跌破EMA{self.p.ema_sell_period}",
                )
                
                # 卖出后重置买入标记，等待下一次 VCP 信号
                self._vcp_bought = False
                
                # 调试输出（显示卖出具体价格与 EMA 的关系）
                if self.p.debug_once:
                    print(
                        f"vcp_sell @ {self.data.datetime.date(0)}: "
                        f"close={curr_close:.2f} ema={curr_ema:.2f}"
                    )
