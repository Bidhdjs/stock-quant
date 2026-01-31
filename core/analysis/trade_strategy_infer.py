"""
策略推断启发式规则。

适用场景：
- 基于交易数据推断策略类型画像与置信度。

数学原理：
1. 通过买卖配对估计持仓周期。
2. 用交易频率、持仓周期、胜率等统计特征推断策略类型。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.analysis.trade_schema import TradeSchema, normalize_trades


@dataclass(frozen=True)
class StrategyProfile:
    tag: str
    confidence: float
    avg_holding_days: float
    median_holding_days: float
    trade_interval_days: float
    win_rate: float | None
    trade_count: int


def _pair_trades(data: pd.DataFrame, schema: TradeSchema) -> pd.DataFrame:
    buys = data[data[schema.side] == "buy"][[
        schema.symbol,
        schema.time,
        schema.qty,
        schema.price,
    ]].rename(columns={schema.time: "buy_time", schema.qty: "buy_qty", schema.price: "buy_price"})
    sells = data[data[schema.side] == "sell"][[
        schema.symbol,
        schema.time,
        schema.qty,
        schema.price,
    ]].rename(columns={schema.time: "sell_time", schema.qty: "sell_qty", schema.price: "sell_price"})

    if buys.empty or sells.empty:
        return pd.DataFrame()

    buys = buys.sort_values(["symbol", "buy_time"])
    sells = sells.sort_values(["symbol", "sell_time"])
    paired = pd.merge_asof(
        buys,
        sells,
        left_on="buy_time",
        right_on="sell_time",
        by="symbol",
        direction="forward",
        allow_exact_matches=False,
    )
    paired = paired.dropna(subset=["sell_time"])
    return paired


def infer_strategy(trades: pd.DataFrame) -> StrategyProfile:
    """
    基于交易数据输出策略画像。
    """
    schema = TradeSchema()
    data = normalize_trades(trades, schema=schema)
    data = data.dropna(subset=[schema.symbol, schema.time, schema.side])

    trade_count = len(data)
    if trade_count == 0:
        return StrategyProfile(
            tag="unknown",
            confidence=0.0,
            avg_holding_days=0.0,
            median_holding_days=0.0,
            trade_interval_days=0.0,
            win_rate=None,
            trade_count=0,
        )

    data = data.sort_values(schema.time)
    intervals = data[schema.time].diff().dt.total_seconds().div(86400)
    trade_interval_days = float(intervals.median()) if intervals.notna().any() else 0.0

    paired = _pair_trades(data, schema)
    if paired.empty:
        avg_holding = 0.0
        med_holding = 0.0
    else:
        holding_days = (paired["sell_time"] - paired["buy_time"]).dt.total_seconds().div(86400)
        avg_holding = float(holding_days.mean())
        med_holding = float(holding_days.median())

    win_rate = None
    if data[schema.pnl].notna().any():
        win_rate = float((data[schema.pnl] > 0).mean())

    tag = "unclear"
    if avg_holding >= 30 and (win_rate is None or win_rate >= 0.5):
        tag = "trend_following"
    elif avg_holding <= 5 and trade_interval_days <= 5:
        tag = "short_term"
    elif avg_holding > 0 and win_rate is not None and win_rate < 0.5:
        tag = "mean_reversion"

    confidence = min(1.0, trade_count / 50)
    return StrategyProfile(
        tag=tag,
        confidence=round(confidence, 2),
        avg_holding_days=round(avg_holding, 2),
        median_holding_days=round(med_holding, 2),
        trade_interval_days=round(trade_interval_days, 2),
        win_rate=None if win_rate is None else round(win_rate, 2),
        trade_count=trade_count,
    )


def profile_to_frame(profile: StrategyProfile) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "tag": profile.tag,
                "confidence": profile.confidence,
                "avg_holding_days": profile.avg_holding_days,
                "median_holding_days": profile.median_holding_days,
                "trade_interval_days": profile.trade_interval_days,
                "win_rate": profile.win_rate,
                "trade_count": profile.trade_count,
            }
        ]
    )
