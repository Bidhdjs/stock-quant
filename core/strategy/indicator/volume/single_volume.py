import numpy as np
import backtrader as bt
import pandas as pd

from core.analysis.indicators.volume import VolumeIndicatorParams, compute_latest_volume_features
from core.strategy.indicator.common import SignalRecordManager


class SingleVolumeIndicator(bt.Indicator):
    """
    基于成交量和多个技术指标的增强交易信号指示器
    包含成交量分析、RSI、布林带和KDJ指标的综合分析
    """
    lines = ('main_buy_signal', 'main_sell_signal', 'enhanced_buy_signal', 'enhanced_sell_signal')
    params = (
        ('n1', 1),  # 短期均线周期
        ('n2', 5),  # 中期均线周期
        ('n3', 20),  # 长期均线周期
        ('rsi_period', 14),  # RSI计算周期
        ('boll_period', 20),  # 布林带周期
        ('boll_width', 2),  # 布林带宽度倍数
        ('kdj_period', 9)  # KDJ周期
    )

    # 设置绘图参数，让信号在主图上显示
    plotinfo = dict(subplot=False)

    # 为每个信号线设置绘图样式
    plotlines = dict(
        main_buy_signal=dict(marker='', _plotskip=True),  # 不直接显示线
        main_sell_signal=dict(marker='', _plotskip=True),  # 不直接显示线
        enhanced_buy_signal=dict(marker='', _plotskip=True),  # 不直接显示线
        enhanced_sell_signal=dict(marker='', _plotskip=True)  # 不直接显示线
    )

    def __init__(self):
        self.signal_record_manager = SignalRecordManager()
        self._min_len = max(self.p.n3, self.p.rsi_period + 1, self.p.boll_period, self.p.kdj_period, 3)
        self.addminperiod(self._min_len)

    def _build_feature_frame(self, lookback: int) -> pd.DataFrame:
        data = {
            "open": np.array(self.data.open.get(size=lookback)),
            "high": np.array(self.data.high.get(size=lookback)),
            "low": np.array(self.data.low.get(size=lookback)),
            "close": np.array(self.data.close.get(size=lookback)),
            "volume": np.array(self.data.volume.get(size=lookback)),
        }
        return pd.DataFrame(data)

    def next(self):
        # 初始化信号值
        self.lines.main_buy_signal[0] = np.nan
        self.lines.main_sell_signal[0] = np.nan
        self.lines.enhanced_buy_signal[0] = np.nan
        self.lines.enhanced_sell_signal[0] = np.nan

        if len(self) < self._min_len:
            return

        params = VolumeIndicatorParams(
            n1=self.p.n1,
            n2=self.p.n2,
            n3=self.p.n3,
            rsi_period=self.p.rsi_period,
            boll_period=self.p.boll_period,
            boll_width=self.p.boll_width,
            kdj_period=self.p.kdj_period,
        )
        df = self._build_feature_frame(self._min_len)
        features = compute_latest_volume_features(df, params)
        if not features:
            return

        # ========== 提取特征值 ==========
        ma_vol_today = features["ma_vol_today"]  # 今日成交量均线（基本为当日值）
        ma_close_today = features["ma_close_today"]  # 今日收盘价均线（基本为当日值）
        ma_vol_5 = features["ma_vol_5"]  # 5日成交量均线
        ma_close_5 = features["ma_close_5"]  # 5日收盘价均线
        ma_vol_20 = features["ma_vol_20"]  # 20日成交量均线
        ma_close_20 = features["ma_close_20"]  # 20日收盘价均线
        vol_std_5 = features["vol_std_5"]  # 5日成交量标准差（波动程度）
        vol_std_20 = features["vol_std_20"]  # 20日成交量标准差（波动程度）
        rsi = features["rsi"]  # 相对强弱指数，范围[0,100]
        rsi_prev = features["rsi_prev"]  # 前一日RSI值（用于穿越判断）
        boll_bot = features["boll_bot"]  # 布林带下轨（中线 - 2*std）
        boll_top = features["boll_top"]  # 布林带上轨（中线 + 2*std）
        k_val = features["k"]  # KDJ快线K值
        d_val = features["d"]  # KDJ慢线D值
        j_val = features["j"]  # KDJ超前线J值（3*K - 2*D）
        is_3_down = bool(features["is_3_down"])  # 是否连续3根下跌K线
        is_3_up = bool(features["is_3_up"])  # 是否连续3根上涨K线

        # ========== 成交量倍数计算 ==========
        # 计算短期成交量倍数：基础倍数0.9 + 成交量波动系数（最多增加0.6倍）
        # vol_multiplier_5 = 0.9 + min(波动率, 0.6)，用于判断当日成交量是否相对5日均线显著放大
        vol_multiplier_5 = 0.9 + min(vol_std_5 / (ma_vol_5 + 1e-10), 0.6)
        
        # 计算长期成交量倍数：基础倍数0.8 + 成交量波动系数（最多增加0.5倍）
        # vol_multiplier_20 = 0.8 + min(波动率, 0.5)，用于判断当日成交量是否相对20日均线显著放大
        vol_multiplier_20 = 0.8 + min(vol_std_20 / (ma_vol_20 + 1e-10), 0.5)

        # ========== 成交量信号计算 ==========
        # 计算短期成交量信号：当今日成交量 > 5日均线 × 倍数 时，取差值；否则为0
        # vo_count_5 = ma_vol_today - ma_vol_5（体现成交量超额部分的绝对量）
        vo_count_5 = ma_vol_today - ma_vol_5 if ma_vol_today > ma_vol_5 * vol_multiplier_5 else 0
        
        # 计算长期成交量信号：当今日成交量 > 20日均线 × 倍数 时，取差值；否则为0
        # vo_count_20 = ma_vol_today - ma_vol_20（体现成交量超额部分的绝对量）
        vo_count_20 = ma_vol_today - ma_vol_20 if ma_vol_today > ma_vol_20 * vol_multiplier_20 else 0

        # ========== 均线方向信号计算 ==========
        # 买入信号（短期）：连续3根下跌 AND 短期均线高于当日收盘 时，取差值ma_close_5 - ma_close_today
        # 表示价格下跌到短期均线下方，是潜在的买入点
        ma_count_buy_5 = ma_close_5 - ma_close_today if is_3_down and ma_close_5 > ma_close_today else 0
        
        # 卖出信号（短期）：连续3根上涨 AND 短期均线低于当日收盘 时，取差值ma_close_today - ma_close_5
        # 表示价格上涨到短期均线上方，是潜在的卖出点
        ma_count_sell_5 = ma_close_today - ma_close_5 if is_3_up and ma_close_5 < ma_close_today else 0

        # 买入信号（长期）：连续3根下跌 AND 长期均线高于当日收盘 时，取差值ma_close_20 - ma_close_today
        ma_count_buy_20 = ma_close_20 - ma_close_today if is_3_down and ma_close_20 > ma_close_today else 0
        
        # 卖出信号（长期）：连续3根上涨 AND 长期均线低于当日收盘 时，取差值ma_close_today - ma_close_20
        ma_count_sell_20 = ma_close_today - ma_close_20 if is_3_up and ma_close_20 < ma_close_today else 0

        # ========== 综合信号计算 ==========
        # 短期买入信号 = -(成交量差) × (均线差)
        # 负号表示当成交量放大+价格下跌时为买入信号（强烈看涨信号）
        buy_signal_5 = -vo_count_5 * ma_count_buy_5 if vo_count_5 > 0 and ma_count_buy_5 > 0 else 0
        
        # 短期卖出信号 = (成交量差) × (均线差)
        # 正号表示当成交量放大+价格上涨时为卖出信号（强烈看跌信号）
        sell_signal_5 = vo_count_5 * ma_count_sell_5 if vo_count_5 > 0 and ma_count_sell_5 > 0 else 0

        # 长期买入信号 = -(成交量差) × (均线差)
        buy_signal_20 = -vo_count_20 * ma_count_buy_20 if vo_count_20 > 0 and ma_count_buy_20 > 0 else 0
        
        # 长期卖出信号 = (成交量差) × (均线差)
        sell_signal_20 = vo_count_20 * ma_count_sell_20 if vo_count_20 > 0 and ma_count_sell_20 > 0 else 0

        # ========== 信号计数 ==========
        # 统计非零买入信号的个数（短期+长期），0或1或2
        # 当计数≥2时表示多个周期都确认买入信号
        buy_signal_count = (1 if buy_signal_5 != 0 else 0) + (1 if buy_signal_20 != 0 else 0)
        
        # 统计非零卖出信号的个数（短期+长期），0或1或2
        # 当计数≥2时表示多个周期都确认卖出信号
        sell_signal_count = (1 if sell_signal_5 != 0 else 0) + (1 if sell_signal_20 != 0 else 0)

        # ========== 主信号判定 ==========
        # 主买入信号：需要满足
        # 1. 买入信号数≥2（即短期和长期都触发）
        # 2. 累积K线数>50（对应富途的历史数据量要求，确保数据充分）
        main_buy = buy_signal_count >= 2 and len(self) > 50
        
        # 主卖出信号：需要满足
        # 1. 卖出信号数≥2（即短期和长期都触发）
        # 2. 累积K线数>50
        main_sell = sell_signal_count >= 2 and len(self) > 50

        # ========== RSI条件判定 ==========
        # 超卖状态：RSI < 30 表示强烈看涨信号
        rsi_oversold = rsi < 30
        
        # 超买状态：RSI > 70 表示强烈看跌信号
        rsi_overbought = rsi > 70

        # RSI上穿信号：当前RSI > 30 且 前日RSI < 30，表示从超卖反弹
        rsi_buy_condition = False
        rsi_sell_condition = False
        if len(self) > self.p.rsi_period:
            rsi_buy_condition = rsi > 30 and rsi_prev < 30
            # RSI下穿信号：当前RSI < 70 且 前日RSI > 70，表示从超买下跌
            rsi_sell_condition = rsi < 70 and rsi_prev > 70

        # ========== 布林带条件判定 ==========
        # 布林带买入信号：当日最低价 < 布林带下轨，表示价格进入超卖区间
        boll_buy_cond = self.data.low[0] < boll_bot
        
        # 布林带卖出信号：当日最高价 > 布林带上轨，表示价格进入超买区间
        boll_sell_cond = self.data.high[0] > boll_top
        
        # 布林带买入确认：收盘价 > 布林带下轨，价格在下轨上方，弱看涨
        boll_confirm_buy = self.data.close[0] > boll_bot
        
        # 布林带卖出确认：收盘价 < 布林带上轨，价格在上轨下方，弱看跌
        boll_confirm_sell = self.data.close[0] < boll_top

        # ========== KDJ条件判定 ==========
        # KDJ买入信号：K<20 AND D<20（超卖）OR J<20（J线更敏感）
        # 表示动量指标显示极弱
        kdj_buy_cond = (k_val < 20 and d_val < 20) or j_val < 20
        
        # KDJ卖出信号：K>80 AND D>80（超买）OR J>80
        # 表示动量指标显示极强
        kdj_sell_cond = (k_val > 80 and d_val > 80) or j_val > 80

        # ========== 主信号输出 ==========
        # 主买入信号输出位置：LOW × 0.96（略低于当日最低价，便于在图表上标记）
        if main_buy:
            self.lines.main_buy_signal[0] = self.data.low[0] * 0.96
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'normal_buy', '多')

        # 主卖出信号输出位置：HIGH × 1.05（略高于当日最高价，便于在图表上标记）
        if main_sell:
            self.lines.main_sell_signal[0] = self.data.high[0] * 1.05
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'normal_sell', '空')

        # ========== 增强信号判定 ==========
        # 增强买入信号 = 主买 AND (RSI超卖或上穿) AND (布林带买入或确认) AND KDJ超卖
        # 需要四个条件都满足，确保高度确定性的看涨信号
        enhanced_buy = main_buy and ((rsi_oversold or rsi_buy_condition) and (boll_buy_cond or boll_confirm_buy)) and kdj_buy_cond
        
        # 增强卖出信号 = 主卖 AND (RSI超买或下穿) AND (布林带卖出或确认) AND KDJ超买
        # 需要四个条件都满足，确保高度确定性的看跌信号
        enhanced_sell = main_sell and ((rsi_overbought or rsi_sell_condition) and (boll_sell_cond or boll_confirm_sell)) and kdj_sell_cond

        # ========== 增强信号输出 ==========
        # 增强买入信号输出位置：LOW × 0.90（更低，表示更强的买入）
        if enhanced_buy:
            self.lines.enhanced_buy_signal[0] = self.data.low[0] * 0.90
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'strong_buy', '强多')

        # 增强卖出信号输出位置：HIGH × 1.08（更高，表示更强的卖出）
        if enhanced_sell:
            self.lines.enhanced_sell_signal[0] = self.data.high[0] * 1.08
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'strong_sell', '强空')
