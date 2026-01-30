"""
Data source router fallback tests (mock-only).
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from core.stock.data_source_router import fetch_history_with_fallback, get_data_source_priority


pytestmark = pytest.mark.mock_only


def test_priority_default():
    order = get_data_source_priority("UNKNOWN")
    assert order


def test_fallback_to_second_source():
    empty_df = pd.DataFrame()
    ok_df = pd.DataFrame({"date": ["2026-01-01"], "open": [1]})

    with patch("core.stock.manager_yfinance.YFinanceManager.get_stock_data", return_value=empty_df), \
         patch("core.stock.manager_akshare.get_us_history", return_value=ok_df):
        df, source = fetch_history_with_fallback(
            market="US",
            stock_code="AAPL",
            start_date="2026-01-01",
            end_date="2026-01-02",
        )
    assert not df.empty
    assert source in ("akshare", "yfinance")


def test_no_source_available():
    with patch("core.stock.data_source_router.read_cached_history", return_value=None), \
         patch("core.stock.manager_yfinance.YFinanceManager.get_stock_data", return_value=pd.DataFrame()), \
         patch("core.stock.manager_akshare.get_us_history", return_value=pd.DataFrame()):
        df, source = fetch_history_with_fallback(
            market="US",
            stock_code="AAPL",
            start_date="2026-01-01",
            end_date="2026-01-02",
            preferred=["yfinance", "akshare"],
        )
    assert df.empty
    assert source is None


def test_cache_hit(monkeypatch, tmp_path):
    import settings
    from core.stock.manager_common import write_cached_history

    monkeypatch.setattr(settings, "stock_data_root", tmp_path)
    df = pd.DataFrame(
        {
            "date": ["2026-01-01"],
            "open": [1],
            "high": [2],
            "low": [0.5],
            "close": [1.5],
            "volume": [10],
            "amount": [15],
            "stock_code": ["US.AAPL"],
            "stock_name": ["AAPL"],
            "market": ["US"],
        }
    )
    write_cached_history(
        df,
        source="yfinance",
        market="US",
        stock_code="AAPL",
        stock_name="AAPL",
        start_date="2026-01-01",
        end_date="2026-01-02",
    )
    out, source = fetch_history_with_fallback(
        market="US",
        stock_code="AAPL",
        start_date="2026-01-01",
        end_date="2026-01-02",
        preferred=["yfinance"],
    )
    assert not out.empty
    assert source == "yfinance"
