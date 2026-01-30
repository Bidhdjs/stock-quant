"""
数据源通用标准化与校验工具。

功能：
1. 统一列名与输出格式
2. 缺失字段补齐
3. 日期与排序标准化
4. 缺失成交量提示并兜底
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import pandas as pd
from pandas import DataFrame

from common.logger import create_log


logger = create_log("manager_common")

REQUIRED_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "stock_code",
    "stock_name",
    "market",
]

_COLUMN_MAP = {
    # 中文列名
    "日期": "date",
    "交易日期": "date",
    "开盘": "open",
    "开盘价": "open",
    "收盘": "close",
    "收盘价": "close",
    "最高": "high",
    "最高价": "high",
    "最低": "low",
    "最低价": "low",
    "成交量": "volume",
    "成交量(股)": "volume",
    "成交额": "amount",
    "成交额(元)": "amount",
    "成交额(港元)": "amount",
    "振幅": "amplitude",
    "振幅(%)": "amplitude",
    "涨跌幅": "change_pct",
    "涨跌幅(%)": "change_pct",
    "涨跌额": "change",
    "换手率": "turnover_rate",
    "换手率(%)": "turnover_rate",
    # 英文字段常见变体
    "date": "date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "adj close": "adj_close",
    "adj_close": "adj_close",
    "volume": "volume",
}


def _normalize_column_name(col: str) -> str:
    key = str(col).strip()
    if key in _COLUMN_MAP:
        return _COLUMN_MAP[key]
    lower_key = key.lower()
    return _COLUMN_MAP.get(lower_key, key)


def validate_stock_data_schema(df: DataFrame, required_columns: Iterable[str] | None = None) -> List[str]:
    """
    校验 DataFrame 是否包含必需列。

    Returns:
        List[str]: 缺失列名列表
    """
    required = list(required_columns or REQUIRED_COLUMNS)
    missing = [col for col in required if col not in df.columns]
    return missing


def _normalize_code_with_market(stock_code: str, market: str) -> str:
    code = str(stock_code)
    if "." in code:
        return code
    market_key = (market or "").upper()
    return f"{market_key}.{code}" if market_key else code


def _sanitize_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in str(value))


def read_cached_history(
    source: str,
    market: str,
    stock_code: str,
    start_date: str,
    end_date: str,
) -> Optional[DataFrame]:
    """
    读取本地缓存数据（若存在）。
    """
    from settings import stock_data_root

    code = _normalize_code_with_market(stock_code, market)
    source_dir = stock_data_root / source
    if not source_dir.exists():
        return None
    pattern = f"{code}_*_{start_date.replace('-', '')}_{end_date.replace('-', '')}.csv"
    matches = list(source_dir.glob(pattern))
    if not matches:
        return None
    file_path = matches[0]
    try:
        df = pd.read_csv(file_path)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        logger.info("Cache hit: %s", file_path)
        return df
    except Exception as exc:
        logger.warning("Failed to read cache %s: %s", file_path, exc)
        return None


def write_cached_history(
    df: DataFrame,
    source: str,
    market: str,
    stock_code: str,
    stock_name: str,
    start_date: str,
    end_date: str,
) -> Optional[str]:
    """
    写入本地缓存数据。
    """
    from settings import stock_data_root

    if df is None or df.empty:
        return None
    code = _normalize_code_with_market(stock_code, market)
    name = _sanitize_name(stock_name)
    start_key = start_date.replace("-", "")
    end_key = end_date.replace("-", "")
    source_dir = stock_data_root / source
    source_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{code}_{name}_{start_key}_{end_key}.csv"
    file_path = source_dir / filename
    try:
        df.to_csv(file_path, index=False)
        logger.info("Cache saved: %s", file_path)
        return str(file_path)
    except Exception as exc:
        logger.warning("Failed to save cache %s: %s", file_path, exc)
        return None


def standardize_stock_data(df: DataFrame | None, stock_code: str, stock_name: str, market: str) -> DataFrame:
    """
    标准化股票数据为统一英文列名与固定输出字段。

    Args:
        df: 原始数据
        stock_code: 股票代码
        stock_name: 股票名称
        market: 市场代码（US/HK/CN等）

    Returns:
        DataFrame: 标准化数据
    """
    if df is None:
        df = pd.DataFrame()

    data = df.copy()

    if "date" not in data.columns and isinstance(data.index, pd.DatetimeIndex):
        data = data.reset_index().rename(columns={"index": "date"})

    rename_map = {col: _normalize_column_name(col) for col in data.columns}
    data = data.rename(columns=rename_map)

    if "close" not in data.columns and "adj_close" in data.columns:
        data["close"] = data["adj_close"]

    data["stock_code"] = stock_code
    data["stock_name"] = stock_name
    data["market"] = market

    for col in REQUIRED_COLUMNS:
        if col not in data.columns:
            data[col] = pd.NA

    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")

    missing_volume = data["volume"].isna().all()
    if missing_volume:
        data["volume"] = 0
        logger.warning(
            "成交量缺失，已填充为 0: stock_code=%s market=%s",
            stock_code,
            market,
        )

    data = data[REQUIRED_COLUMNS].sort_values("date")
    return data
