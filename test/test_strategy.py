"""
回测策略手动运行入口（pytest 默认跳过）。
"""

# Front Code X
import pytest


@pytest.mark.skip(reason="manual backtest runner")
def test_strategy_manual_entrypoint():
    assert True
