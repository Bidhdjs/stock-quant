"""
交易策略推断测试。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.trade_strategy_infer import infer_strategy


@pytest.mark.mock_only
def test_infer_strategy_profile():
    data = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA", "AAA", "AAA"],
            "time": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"],
            "side": ["buy", "sell", "buy", "sell"],
            "qty": [10, 10, 10, 10],
            "price": [100, 110, 105, 120],
            "pnl": [np.nan, 10, np.nan, 15],
        }
    )
    profile = infer_strategy(data)
    assert profile.trade_count == 4
    assert profile.avg_holding_days >= 0
