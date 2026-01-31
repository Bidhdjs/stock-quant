"""
VCP 波动收缩形态交易策略。

适用场景：
- 使用 VCPIndicator 产生交易信号，接入统一回测流程。

数学原理：
1. VCP 形态作为买入信号。
2. 卖出策略沿用基类的策略规则（可扩展）。
"""

from __future__ import annotations

import numpy as np
from common.logger import create_log
from core.strategy.indicator.pattern.vcp_indicator import VCPIndicator
from core.strategy.trading.common import StrategyBase

logger = create_log("trade_strategy_pattern")


class VCPStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.set_indicator(VCPIndicator())

    def next(self):
        if self.order:
            return

        if not np.isnan(self.indicator.lines.vcp_signal[0]):
            logger.info(
                f"*** VCP 买入信号 时间：{self.data.datetime.date(0)} 价格：{self.data.close[0]} ***"
            )
            self.trading_strategy_buy()
            self.buy_signals_count += 1
        elif self.position:
            # 简单卖出条件：出现反向形态或持仓管理规则可扩展
            pass
