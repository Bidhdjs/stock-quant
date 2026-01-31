"""
Minervini 趋势模板过滤器（简化版）。

适用场景：
- 从 youtuber 脚本中提炼的趋势过滤逻辑。

数学原理：
1. 价格在 MA50/MA150/MA200 上方
2. MA50 > MA150 > MA200
3. MA200 上升趋势（20 日斜率）
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(1, len(values) + 1, dtype=float)
    y = values.astype(float)
    numerator = (len(values) * (x * y).sum()) - (x.sum() * y.sum())
    denominator = (len(values) * (x * x).sum()) - (x.sum() ** 2)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def minervini_trend_template(df: pd.DataFrame) -> pd.DataFrame:
    """
    返回包含 Pass 列的 DataFrame。
    """
    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    for col in ["close", "high", "low"]:
        if col not in data.columns:
            raise ValueError(f"缺少必要列: {col}")

    data["ma_50"] = data["close"].rolling(window=50).mean()
    data["ma_150"] = data["close"].rolling(window=150).mean()
    data["ma_200"] = data["close"].rolling(window=200).mean()

    data["condition_1"] = (data["close"] > data["ma_150"]) & (data["close"] > data["ma_200"]) & (
        data["close"] > data["ma_50"]
    )
    data["condition_2"] = (data["ma_150"] > data["ma_200"]) & (data["ma_50"] > data["ma_150"])
    slope = data["ma_200"].rolling(window=20).apply(lambda x: _slope(x), raw=False)
    data["condition_3"] = slope > 0.0

    data["pass"] = data[["condition_1", "condition_2", "condition_3"]].all(axis="columns")
    return data
