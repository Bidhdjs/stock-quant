"""
SuperTrend + VCP 简化过滤器。

适用场景：
- 从 youtuber 脚本中提取 SuperTrend + VCP 组合逻辑。
- 需要 pandas_ta 支持（未安装会抛错）。

数学原理：
1. SuperTrend 方向为多头。
2. 价格在 MA200 之上。
3. 波动率收缩 + 成交量枯竭。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SupertrendVcpConfig:
    atr_period: int = 10
    atr_multiplier: float = 3.0
    contraction_tolerance: float = 0.85
    tightness_threshold: float = 0.6
    volume_dryup_ratio: float = 0.75


def _require_pandas_ta():
    try:
        import pandas_ta as ta
    except Exception as exc:
        raise RuntimeError(f"缺少 pandas_ta 依赖，无法计算 SuperTrend: {exc}") from exc
    return ta


def supertrend_vcp_signal(df: pd.DataFrame, config: SupertrendVcpConfig | None = None) -> tuple[bool, str]:
    """
    返回 (是否通过, 失败原因)。
    """
    if config is None:
        config = SupertrendVcpConfig()

    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in data.columns:
            raise ValueError(f"缺少必要列: {col}")

    if len(data) < 200:
        return False, "数据不足"

    ta = _require_pandas_ta()
    st = ta.supertrend(
        data["high"],
        data["low"],
        data["close"],
        length=config.atr_period,
        multiplier=config.atr_multiplier,
    )
    st_val_col = f"SUPERT_{config.atr_period}_{config.atr_multiplier}"
    st_dir_col = f"SUPERTd_{config.atr_period}_{config.atr_multiplier}"
    if st_val_col not in st.columns or st_dir_col not in st.columns:
        return False, "SuperTrend 计算失败"
    data["supertrend"] = st[st_val_col]
    data["supertrend_dir"] = st[st_dir_col]

    data["ma_200"] = data["close"].rolling(window=200).mean()
    current = data.iloc[-1]

    if current["supertrend_dir"] != 1:
        return False, "SuperTrend 为看跌"
    if current["close"] <= current["ma_200"]:
        return False, "价格低于 MA200"

    window_long = 60
    window_short = 30
    period_1 = data.iloc[-window_long:-window_short]
    period_2 = data.iloc[-window_short:]
    vol_1 = (period_1["high"].max() - period_1["low"].min()) / period_1["low"].min()
    vol_2 = (period_2["high"].max() - period_2["low"].min()) / period_2["low"].min()
    if vol_2 >= vol_1 * config.contraction_tolerance:
        return False, "波动率未收缩"

    recent_5 = data.iloc[-5:]
    avg_range_5 = (recent_5["high"] - recent_5["low"]).mean()
    atr_14 = ta.atr(data["high"], data["low"], data["close"], length=14).iloc[-1]
    if avg_range_5 > (atr_14 * config.tightness_threshold):
        return False, "价格不够紧凑"

    recent_vol_avg = recent_5["volume"].mean()
    vol_avg_50 = data["volume"].rolling(window=50).mean().iloc[-1]
    if recent_vol_avg > (vol_avg_50 * config.volume_dryup_ratio):
        return False, "成交量未枯竭"

    return True, "VCP + SuperTrend 通过"
