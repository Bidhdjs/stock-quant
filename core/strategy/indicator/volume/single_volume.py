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

        ma_vol_today = features["ma_vol_today"]
        ma_close_today = features["ma_close_today"]
        ma_vol_5 = features["ma_vol_5"]
        ma_close_5 = features["ma_close_5"]
        ma_vol_20 = features["ma_vol_20"]
        ma_close_20 = features["ma_close_20"]
        vol_std_5 = features["vol_std_5"]
        vol_std_20 = features["vol_std_20"]
        rsi = features["rsi"]
        rsi_prev = features["rsi_prev"]
        boll_bot = features["boll_bot"]
        boll_top = features["boll_top"]
        k_val = features["k"]
        d_val = features["d"]
        j_val = features["j"]
        is_3_down = bool(features["is_3_down"])
        is_3_up = bool(features["is_3_up"])

        # 计算成交量相关指标
        vol_multiplier_5 = 0.9 + min(vol_std_5 / (ma_vol_5 + 1e-10), 0.6)
        vol_multiplier_20 = 0.8 + min(vol_std_20 / (ma_vol_20 + 1e-10), 0.5)

        # 计算买入/卖出计数
        vo_count_5 = ma_vol_today - ma_vol_5 if ma_vol_today > ma_vol_5 * vol_multiplier_5 else 0
        vo_count_20 = ma_vol_today - ma_vol_20 if ma_vol_today > ma_vol_20 * vol_multiplier_20 else 0


        # 计算均线相关买入/卖出计数
        ma_count_buy_5 = ma_close_5 - ma_close_today if is_3_down and ma_close_5 > ma_close_today else 0
        ma_count_sell_5 = ma_close_today - ma_close_5 if is_3_up and ma_close_5 < ma_close_today else 0

        ma_count_buy_20 = ma_close_20 - ma_close_today if is_3_down and ma_close_20 > ma_close_today else 0
        ma_count_sell_20 = ma_close_today - ma_close_20 if is_3_up and ma_close_20 < ma_close_today else 0

        # 计算买入/卖出信号
        buy_signal_5 = -vo_count_5 * ma_count_buy_5 if vo_count_5 > 0 and ma_count_buy_5 > 0 else 0
        sell_signal_5 = vo_count_5 * ma_count_sell_5 if vo_count_5 > 0 and ma_count_sell_5 > 0 else 0

        buy_signal_20 = -vo_count_20 * ma_count_buy_20 if vo_count_20 > 0 and ma_count_buy_20 > 0 else 0
        sell_signal_20 = vo_count_20 * ma_count_sell_20 if vo_count_20 > 0 and ma_count_sell_20 > 0 else 0

        # 计算信号计数
        buy_signal_count = (1 if buy_signal_5 != 0 else 0) + (1 if buy_signal_20 != 0 else 0)
        sell_signal_count = (1 if sell_signal_5 != 0 else 0) + (1 if sell_signal_20 != 0 else 0)

        # 主信号 - 使用BARSCOUNT(1)>50对应富途的条件
        main_buy = buy_signal_count >= 2 and len(self) > 50
        main_sell = sell_signal_count >= 2 and len(self) > 50

        # RSI条件
        rsi_oversold = rsi < 30
        rsi_overbought = rsi > 70

        # RSI穿越条件
        rsi_buy_condition = False
        rsi_sell_condition = False
        if len(self) > self.p.rsi_period:
            rsi_buy_condition = rsi > 30 and rsi_prev < 30
            rsi_sell_condition = rsi < 70 and rsi_prev > 70

        # 布林带条件
        boll_buy_cond = self.data.low[0] < boll_bot
        boll_sell_cond = self.data.high[0] > boll_top
        boll_confirm_buy = self.data.close[0] > boll_bot
        boll_confirm_sell = self.data.close[0] < boll_top

        # KDJ条件
        kdj_buy_cond = (k_val < 20 and d_val < 20) or j_val < 20
        kdj_sell_cond = (k_val > 80 and d_val > 80) or j_val > 80

        # 设置主信号值 - 按照用户要求的位置
        if main_buy:
            self.lines.main_buy_signal[0] = self.data.low[0] * 0.96  # 在LOW * 0.96的位置显示多
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'normal_buy', '多')

        if main_sell:
            self.lines.main_sell_signal[0] = self.data.high[0] * 1.05  # 在HIGH * 1.05的位置显示
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'normal_sell', '空')
        # TODO DEBUG不包含RSI指标，暂时不使用RSI，信号更多
        # enhanced_buy = main_buy and ((boll_buy_cond or boll_confirm_buy)) and kdj_buy_cond
        # enhanced_sell = main_sell and ((boll_sell_cond or boll_confirm_sell)) and kdj_sell_cond
        # 包含RSI指标，RSI过滤掉了很多信号指标
        enhanced_buy = main_buy and ((rsi_oversold or rsi_buy_condition) and (boll_buy_cond or boll_confirm_buy)) and kdj_buy_cond
        enhanced_sell = main_sell and ((rsi_overbought or rsi_sell_condition) and (boll_sell_cond or boll_confirm_sell)) and kdj_sell_cond
        # 设置增强信号值 - 按照用户要求的位置
        if enhanced_buy:
            self.lines.enhanced_buy_signal[0] = self.data.low[0] * 0.90  # 在LOW * 0.90的位置显示
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'strong_buy', '强多')

        if enhanced_sell:
            self.lines.enhanced_sell_signal[0] = self.data.high[0] * 1.08  # 在HIGH * 1.08的位置显示
            self.signal_record_manager.add_signal_record(self.data.datetime.date(), 'strong_sell', '强空')


# if __name__ == '__main__':
#     signal_record_manager = SignalRecordManager()
#     signal_record_manager.add_signal_record(datetime.date(2024, 1, 15), 'normal_buy', '多')
#     signal_record_manager.add_signal_record(datetime.date(2024, 1, 16), 'normal_sell', '空')
#     signal_record_manager.add_signal_record(datetime.date(2024, 1, 17), 'strong_buy', '强多')
#     signal_record_manager.add_signal_record(datetime.date(2024, 1, 18), 'strong_sell', '强空')
#     signal_record_manager.add_signal_record('2024-01-15', 'normal_buy', '多')
#     record = signal_record_manager.transform_to_dataframe()
#     print(record)
