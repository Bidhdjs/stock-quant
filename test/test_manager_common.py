"""
manager_common 标准化与校验测试（mock-only）。
"""

import pandas as pd
import pytest

from core.stock.manager_common import REQUIRED_COLUMNS, standardize_stock_data, validate_stock_data_schema


pytestmark = pytest.mark.mock_only


def test_validate_schema_missing():
    df = pd.DataFrame({"date": ["2026-01-01"], "open": [1]})
    missing = validate_stock_data_schema(df, REQUIRED_COLUMNS)
    assert "close" in missing
    assert "volume" in missing


def test_standardize_fills_volume_and_logs(caplog):
    raw = pd.DataFrame({
        "date": ["2026-01-01"],
        "open": [1],
        "high": [2],
        "low": [0.5],
        "close": [1.5],
    })
    with caplog.at_level("WARNING"):
        out = standardize_stock_data(raw, "AAPL", "Apple", "US")
    assert out["volume"].iloc[0] == 0
    assert any("成交量缺失" in record.message for record in caplog.records)


def test_standardize_from_datetime_index():
    raw = pd.DataFrame({
        "Open": [1],
        "High": [2],
        "Low": [0.5],
        "Close": [1.5],
        "Volume": [10],
    }, index=pd.to_datetime(["2026-01-01"]))
    out = standardize_stock_data(raw, "AAPL", "Apple", "US")
    assert list(out.columns) == REQUIRED_COLUMNS
    assert not out["date"].isna().any()