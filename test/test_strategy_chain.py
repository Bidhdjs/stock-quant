"""
策略链路测试（指标 → 信号 → 策略）。

数学原理：
1. 通过回测执行路径覆盖指标计算与信号判断。
"""

import numpy as np
import pandas as pd
import backtrader as bt
import pytest

from core.strategy.trading.volume.enhanced_volume import EnhancedVolumeStrategy


class _PandasData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", -1),
    )


@pytest.mark.mock_only
def test_strategy_chain_enhanced_volume_runs():
    length = 120
    dates = pd.date_range("2020-01-01", periods=length, freq="D")
    base = np.linspace(100, 130, length)
    df = pd.DataFrame(
        {
            "open": base,
            "high": base + 1,
            "low": base - 1,
            "close": base + 0.5,
            "volume": np.linspace(1000, 2000, length),
        },
        index=dates,
    )

    cerebro = bt.Cerebro()
    cerebro.adddata(_PandasData(dataname=df))
    cerebro.addstrategy(EnhancedVolumeStrategy)

    results = cerebro.run()
    strategy = results[0]

    assert strategy.indicator is not None
    assert hasattr(strategy.indicator.lines, "enhanced_buy_signal")
    assert hasattr(strategy.indicator.lines, "enhanced_sell_signal")
