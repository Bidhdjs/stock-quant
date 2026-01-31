"""
VCP 宽松版形态交易策略（用于回测验证信号触发）。

适用场景：
- 在保持 VCP 形态框架不变的前提下，降低触发门槛。

数学原理：
1. 保留 Stage 2 趋势模板条件。
2. 通过降低进度阈值，提高触发概率以验证回测管线。
"""

from __future__ import annotations

import numpy as np

from common.logger import create_log
from core.strategy.indicator.pattern.vcp_indicator import VCPIndicator
from core.strategy.trading.common import StrategyBase

logger = create_log("trade_strategy_pattern")


class VCPStrategyLoose(StrategyBase):
    def __init__(self):
        super().__init__()
        self.set_indicator(
            VCPIndicator(
                progress_threshold=0.34,
                debug_once=True,
            )
        )

    def next(self):
        if self.order:
            return

        if self.position and not np.isnan(self.indicator.lines.vcp_sell_signal[0]):
            logger.info(
                f"*** VCP 卖出信号 时间：{self.data.datetime.date(0)} 价格：{self.data.close[0]} ***"
            )
            self.trading_strategy_sell()
            self.sell_signals_count += 1
        elif not self.position and not np.isnan(self.indicator.lines.vcp_signal[0]):
            logger.info(
                f"*** VCP 买入信号 时间：{self.data.datetime.date(0)} 价格：{self.data.close[0]} ***"
            )
            self.trading_strategy_buy()
            self.buy_signals_count += 1

    def trading_strategy_buy(self):
        total_asset_value = self.broker.getvalue()
        available_cash = self.broker.getcash()
        max_single_trade_cash = total_asset_value * self.max_single_buy_percent
        max_portfolio_value = total_asset_value * self.max_portfolio_percent
        usable_cash = min(available_cash, max_single_trade_cash, max_portfolio_value)

        price = self.data.close[0]
        if price > 0 and usable_cash >= price * self.min_order_size:
            shares_based_on_cash = usable_cash // price
            buy_size = max(shares_based_on_cash, self.min_order_size)
            if buy_size >= self.min_order_size:
                buy_size = buy_size // self.min_order_size * self.min_order_size
                logger.info(
                    f"【买入挂单】: 可用资金={available_cash:.2f}, 总资产={total_asset_value:.2f}, "
                    f"买入股数={buy_size}，理论买入价格={price:.2f}，买入后持仓={self.position.size + buy_size}"
                )
                trade_commission = self.calculate_commission(buy_size, price)
                if trade_commission:
                    logger.info(f"【理论交易手续费】: {trade_commission['total_commission']:.2f}")
                self.order = self.buy(size=buy_size, price=price)
            else:
                logger.info(f"资金有限，预购买股数={buy_size}，小于最小交易单位={self.min_order_size}，无法购买")
        else:
            logger.info(
                f"资金有限，可用资金={usable_cash:.2f}，成交最小金额={price * self.min_order_size:.2f}，无法购买"
            )

    def trading_strategy_sell(self):
        if self.position:
            current_position_size = self.position.size
            remaining_sell_size = current_position_size // self.min_order_size * self.min_order_size
            total_asset_value = self.broker.getvalue()
            available_cash = self.broker.getcash()
            price = self.data.close[0]
            max_single_sell_size = (
                total_asset_value
                * self.max_single_sell_percent
                / price
                // self.min_order_size
                * self.min_order_size
            )
            sell_size = min(remaining_sell_size, max_single_sell_size)
            if sell_size >= self.min_order_size:
                logger.info(
                    f"【卖出挂单】: 可用资金={available_cash:.2f}, 总资产={total_asset_value:.2f}, "
                    f"当前持仓={self.position.size}, 卖出股数={sell_size}，理论卖出价格={price:.2f}，"
                    f"卖出后持仓={current_position_size - sell_size}"
                )
                trade_commission = self.calculate_commission(sell_size, price)
                if trade_commission:
                    logger.info(f"【理论交易手续费】: {trade_commission['total_commission']:.2f}")
                self.order = self.sell(size=sell_size, price=price)
            else:
                logger.info(
                    f"持仓有限，持仓股数={current_position_size}，预卖出股数={sell_size}，"
                    f"小于最小交易单位={self.min_order_size}，无法卖出"
                )
        else:
            logger.info("【卖出挂单失败，当前无持仓，不执行卖出操作】")
