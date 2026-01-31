"""
RS Rating 计算工具（基于价格序列）。

适用场景：
- 迁移自 x/vcp_from_youtuber/简单过滤v2.py 的 RS 逻辑。

数学原理：
1. 加权收益率：近 3/6/9/12 个月收益按 40/20/20/20 权重合成。
2. 百分位排名作为 RS Rating（0-100）。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RsRatingConfig:
    weight_3m: float = 0.4
    weight_6m: float = 0.2
    weight_9m: float = 0.2
    weight_12m: float = 0.2


def compute_rs_scores(price_map: dict[str, pd.Series], config: RsRatingConfig | None = None) -> pd.DataFrame:
    """
    根据输入的价格序列计算 RS Rating。

    Args:
        price_map: {ticker: close_series}
        config: 权重配置

    Returns:
        DataFrame[Ticker, RS_Score, RS_Rating]
    """
    if config is None:
        config = RsRatingConfig()

    rows = []
    for ticker, series in price_map.items():
        if series is None or len(series) < 252:
            continue
        series = series.dropna()
        if len(series) < 252:
            continue
        current = series.iloc[-1]
        ret_3m = (current - series.iloc[-63]) / series.iloc[-63]
        ret_6m = (current - series.iloc[-126]) / series.iloc[-126]
        ret_9m = (current - series.iloc[-189]) / series.iloc[-189]
        ret_12m = (current - series.iloc[-252]) / series.iloc[-252]
        score = (
            config.weight_3m * ret_3m
            + config.weight_6m * ret_6m
            + config.weight_9m * ret_9m
            + config.weight_12m * ret_12m
        )
        rows.append({"Ticker": ticker, "RS_Score": score})

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["Ticker", "RS_Score", "RS_Rating"])

    df["RS_Rating"] = (df["RS_Score"].rank(pct=True) * 100).round(2)
    df = df.sort_values(by="RS_Rating", ascending=False)
    return df
