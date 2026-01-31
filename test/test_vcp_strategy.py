"""
VCP 策略注册测试。
"""

import pytest
import pandas as pd

from core.strategy.strategy_manager import StrategyManager


@pytest.mark.mock_only
def test_vcp_strategy_registered():
    manager = StrategyManager()
    names = manager.get_strategy_names()
    assert "VCPStrategy" in names


@pytest.mark.mock_only
def test_vcp_strategy_backtest_smoke(tmp_path):
    csv_path = tmp_path / "sample.csv"
    rows = []
    base_dates = pd.date_range("2023-01-01", periods=300, freq="D")
    for i, dt in enumerate(base_dates):
        rows.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "open": 100 + i * 0.1,
                "high": 101 + i * 0.1,
                "low": 99 + i * 0.1,
                "close": 100 + i * 0.1,
                "volume": 1000000 - i * 100,
                "amount": 0,
                "stock_code": "US.TEST",
                "stock_name": "TEST",
                "market": "US",
            }
        )
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
    from core.strategy.trading.pattern.vcp_strategy import VCPStrategy

    run_backtest_enhanced_volume_strategy(csv_path, VCPStrategy)
