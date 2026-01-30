"""
数据源管理器 Mock 测试。
仅验证接口分支与返回结构，不触发外部网络。
"""

# Front Code X
import sys
import types
from unittest.mock import Mock, patch

import pandas as pd
import pytest


def _install_fake_modules():
    if "akshare" not in sys.modules:
        ak = types.ModuleType("akshare")
        ak.stock_hk_hist = None
        ak.stock_hk_daily = None
        ak.stock_us_daily = None
        sys.modules["akshare"] = ak
    if "baostock" not in sys.modules:
        bs = types.ModuleType("baostock")
        bs.login = None
        bs.logout = None
        bs.query_history_k_data_plus = None
        sys.modules["baostock"] = bs
    if "futu" not in sys.modules:
        futu = types.ModuleType("futu")
        futu.RET_OK = 0
        class _DummyContext:
            def request_history_kline(self, *args, **kwargs):
                return 0, pd.DataFrame(), None
        futu.OpenQuoteContext = _DummyContext
        class _AuType:
            QFQ = 0
        futu.AuType = _AuType
        sys.modules["futu"] = futu
    if "yfinance" not in sys.modules:
        yf = types.ModuleType("yfinance")
        yf.download = None
        class _DummyTicker:
            info = {}
        yf.Ticker = _DummyTicker
        sys.modules["yfinance"] = yf


_install_fake_modules()

from core.stock import manager_akshare, manager_baostock, manager_futu, manager_yfinance


pytestmark = pytest.mark.mock_only


def test_akshare_hk_fallback():
    """akshare 港股接口走备用分支。"""
    empty_df = pd.DataFrame()
    backup_df = pd.DataFrame({
        "日期": ["2026-01-01"],
        "开盘": [10],
        "最高": [11],
        "最低": [9],
        "收盘": [10.5],
        "成交量": [100],
        "成交额": [200],
    })
    with patch("core.stock.manager_akshare.ak.stock_hk_hist", return_value=empty_df), \
         patch("core.stock.manager_akshare.ak.stock_hk_daily", return_value=backup_df):
        df = manager_akshare.get_hk_stock_history("00700", "2026-01-01", "2026-01-02")
    assert not df.empty
    assert "volume" in df.columns


def test_akshare_us_history():
    """akshare 美股日线接口。"""
    df = pd.DataFrame({
        "date": ["2026-01-01"],
        "open": [10],
        "high": [11],
        "low": [9],
        "close": [10.5],
        "volume": [100],
        "amount": [200],
    })
    with patch("core.stock.manager_akshare.ak.stock_us_daily", return_value=df):
        out = manager_akshare.get_us_history("AAPL", "2026-01-01", "2026-01-02")
    assert not out.empty
    assert "volume" in out.columns


def test_baostock_history():
    """baostock 历史数据接口。"""
    fake_rs = Mock()
    fake_rs.error_code = "0"
    fake_rs.fields = ["date", "code", "open", "high", "low", "close", "volume"]
    rows = [["2026-01-01", "sh.600519", "10", "11", "9", "10.5", "100"]]
    fake_iter = iter(rows)

    def _next():
        try:
            fake_rs._row = next(fake_iter)
            return True
        except StopIteration:
            return False

    fake_rs.next.side_effect = _next
    fake_rs.get_row_data.side_effect = lambda: fake_rs._row

    with patch("core.stock.manager_baostock.bs.login", return_value=Mock(error_code="0")), \
         patch("core.stock.manager_baostock.bs.logout"), \
         patch("core.stock.manager_baostock.bs.query_history_k_data_plus", return_value=fake_rs), \
         patch("core.stock.manager_baostock.get_stock_name", return_value="贵州茅台"):
        df = manager_baostock.get_stock_history("sh.600519", "2026-01-01", "2026-01-02", "2")
    assert not df.empty
    assert "volume" in df.columns


def test_futu_history_empty():
    """futu 空数据返回 False。"""
    fake_ctx = Mock()
    fake_ctx.request_history_kline.return_value = (0, pd.DataFrame(), None)
    with patch("core.stock.manager_futu.ft.OpenQuoteContext", return_value=fake_ctx):
        success, _ = manager_futu.get_single_hk_stock_history("HK.00700", "2026-01-01", "2026-01-02")
    assert not success


def test_yfinance_single():
    """yfinance 单只股票数据处理。"""
    df = pd.DataFrame({
        "Date": ["2026-01-01"],
        "Open": [10],
        "High": [11],
        "Low": [9],
        "Close": [10.5],
        "Volume": [100],
    })
    with patch("core.stock.manager_yfinance.yf.download", return_value=df), \
         patch("core.stock.manager_yfinance.yf.Ticker") as ticker_cls:
        ticker_cls.return_value.info = {"shortName": "AAPL"}
        manager = manager_yfinance.YFinanceManager()
        out = manager.get_stock_data("AAPL", "US", "2026-01-01", "2026-01-02")
    assert not out.empty
    assert "volume" in out.columns
