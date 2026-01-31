"""
交易 schema 解析测试。
"""

import pandas as pd
import pytest

from core.analysis.trade_schema import normalize_trades


@pytest.mark.mock_only
def test_normalize_trades_basic():
    df = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB"],
            "Datetime": ["2024-01-01", "2024-01-02"],
            "Action": ["BUY", "SELL"],
            "Quantity": [10, 10],
            "Price": [100, 110],
            "Commission": [1.0, 1.0],
        }
    )
    normalized = normalize_trades(df)
    assert set(normalized.columns) == {"symbol", "time", "side", "qty", "price", "fee", "pnl"}
    assert normalized["side"].iloc[0] == "buy"
