"""
Data source routing and fallback utilities.

Provides a simple fallback mechanism to fetch historical data with priority
by market. Returns the first non-empty DataFrame along with the source used.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import pandas as pd
from pandas import DataFrame

from common.logger import create_log
from core.stock import manager_akshare, manager_baostock, manager_yfinance
from settings import DATA_SOURCE_PRIORITY


logger = create_log("data_source_router")


def get_data_source_priority(market: str, override: Iterable[str] | None = None) -> list[str]:
    """
    Get data source priority list for a given market.
    """
    if override:
        return [item for item in override]
    market_key = (market or "").upper()
    return list(DATA_SOURCE_PRIORITY.get(market_key, DATA_SOURCE_PRIORITY.get("DEFAULT", [])))


def fetch_history_with_fallback(
    market: str,
    stock_code: str,
    start_date: str,
    end_date: str,
    preferred: Iterable[str] | None = None,
) -> Tuple[DataFrame, str | None]:
    """
    Try data sources in order and return first non-empty DataFrame.

    Returns:
        (df, source_used)
    """
    order = get_data_source_priority(market, preferred)
    for source in order:
        df = _fetch_from_source(source, market, stock_code, start_date, end_date)
        if isinstance(df, pd.DataFrame) and not df.empty:
            logger.info(
                "Data source succeeded: source=%s market=%s stock_code=%s",
                source,
                market,
                stock_code,
            )
            return df, source
        logger.warning(
            "Data source returned empty: source=%s market=%s stock_code=%s",
            source,
            market,
            stock_code,
        )
    return pd.DataFrame(), None


def _fetch_from_source(
    source: str,
    market: str,
    stock_code: str,
    start_date: str,
    end_date: str,
) -> DataFrame:
    market_key = (market or "").upper()
    if source == "yfinance":
        manager = manager_yfinance.YFinanceManager()
        return manager.get_stock_data(stock_code, market_key, start_date, end_date)
    if source == "akshare":
        if market_key == "HK":
            return manager_akshare.get_hk_stock_history(stock_code, start_date, end_date)
        if market_key == "US":
            return manager_akshare.get_us_history(stock_code, start_date, end_date)
        return pd.DataFrame()
    if source == "baostock":
        if market_key == "CN":
            return manager_baostock.get_stock_history(stock_code, start_date, end_date)
        return pd.DataFrame()
    logger.warning("Unknown data source: %s", source)
    return pd.DataFrame()
