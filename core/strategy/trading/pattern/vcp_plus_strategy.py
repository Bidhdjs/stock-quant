"""
VCPPlus 波动收缩形态交易策略。
使用 VCPPlusIndicator 产生买卖信号，接入统一回测流程。

数学原理：
1. Stage 2 趋势模板 + VCP 收缩结构 + RS 过滤形成买入信号。
2. 卖出策略使用 EMA(5) 跌破触发。
"""

from __future__ import annotations

import numpy as np
from common.logger import create_log
from core.strategy.indicator.pattern.vcp_plus_indicator import VCPPlusIndicator
from core.strategy.trading.common import StrategyBase

logger = create_log("trade_strategy_pattern")


class VCPPlusStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.set_indicator(VCPPlusIndicator())

    def next(self):
        if self.order:
            return

        if self.position and not np.isnan(self.indicator.lines.vcp_plus_sell_signal[0]):
            logger.info(
                f"*** VCPPlus 卖出信号 时间：{self.data.datetime.date(0)} 价格：{self.data.close[0]} ***"
            )
            self.trading_strategy_sell()
            self.sell_signals_count += 1
        elif not self.position and not np.isnan(self.indicator.lines.vcp_plus_signal[0]):
            logger.info(
                f"*** VCPPlus 买入信号 时间：{self.data.datetime.date(0)} 价格：{self.data.close[0]} ***"
            )
            self.trading_strategy_buy()
            self.buy_signals_count += 1
