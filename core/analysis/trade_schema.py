"""
交易数据 schema 与解析器。

适用场景：
- 统一历史交易字段，便于后续策略推断与报表输出。

数学原理：
1. 通过字段映射实现标准化，保持数据一致性。
2. 使用向量化处理生成统一字段与派生列。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TradeSchema:
    symbol: str = "symbol"
    time: str = "time"
    side: str = "side"
    qty: str = "qty"
    price: str = "price"
    fee: str = "fee"
    pnl: str = "pnl"


_COLUMN_ALIASES = {
    "symbol": ["symbol", "ticker", "code", "stock_code"],
    "time": ["time", "timestamp", "datetime", "date"],
    "side": ["side", "action", "direction", "type"],
    "qty": ["qty", "quantity", "size", "amount"],
    "price": ["price", "avg_price", "fill_price", "trade_price"],
    "fee": ["fee", "commission", "cost"],
    "pnl": ["pnl", "profit", "profit_loss", "pnl_value"],
}


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    for cand in candidates:
        if cand in columns:
            return cand
    return None


def normalize_trades(df: pd.DataFrame, schema: TradeSchema | None = None) -> pd.DataFrame:
    """
    将任意交易数据标准化为统一字段。
    """
    if schema is None:
        schema = TradeSchema()

    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    mapping = {}
    for target, aliases in _COLUMN_ALIASES.items():
        col = _find_column(list(data.columns), aliases)
        if col:
            mapping[col] = target
    data = data.rename(columns=mapping)

    for col in [schema.symbol, schema.time, schema.side, schema.qty, schema.price]:
        if col not in data.columns:
            data[col] = pd.NA

    if schema.fee not in data.columns:
        data[schema.fee] = 0.0
    if schema.pnl not in data.columns:
        data[schema.pnl] = pd.NA

    data[schema.time] = pd.to_datetime(data[schema.time], errors="coerce")
    data[schema.qty] = pd.to_numeric(data[schema.qty], errors="coerce")
    data[schema.price] = pd.to_numeric(data[schema.price], errors="coerce")
    data[schema.fee] = pd.to_numeric(data[schema.fee], errors="coerce").fillna(0.0)
    data[schema.pnl] = pd.to_numeric(data[schema.pnl], errors="coerce")

    data[schema.side] = (
        data[schema.side]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"b": "buy", "s": "sell", "long": "buy", "short": "sell"})
    )

    data = data.sort_values(schema.time)
    return data[[schema.symbol, schema.time, schema.side, schema.qty, schema.price, schema.fee, schema.pnl]]
