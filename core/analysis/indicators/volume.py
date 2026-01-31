"""
成交量与动量指标计算模块。
用于策略信号层的指标计算基础。

数学原理：
1. 移动平均与标准差用于量能放大判断。
2. RSI / Bollinger / KDJ 用于动量与波动区间识别。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeIndicatorParams:
    """成交量信号指标参数集合。"""

    n1: int = 1
    n2: int = 5
    n3: int = 20
    rsi_period: int = 14
    boll_period: int = 20
    boll_width: float = 2.0
    kdj_period: int = 9


def _resolve_column(df: pd.DataFrame, name: str) -> pd.Series:
    for candidate in (name, name.lower(), name.upper(), name.capitalize()):
        if candidate in df.columns:
            return df[candidate]
    raise KeyError(f"缺少列: {name}")


def compute_volume_features(df: pd.DataFrame, params: VolumeIndicatorParams | None = None) -> pd.DataFrame:
    """计算成交量策略所需的基础指标序列。"""

    if params is None:
        params = VolumeIndicatorParams()

    # 解析 OHLCV 数据列（容错处理大小写）
    open_ = _resolve_column(df, "open")
    high = _resolve_column(df, "high")
    low = _resolve_column(df, "low")
    close = _resolve_column(df, "close")
    volume = _resolve_column(df, "volume")

    # ========== 成交量与收盘价的移动平均 ==========
    # n1=1：今日均线（基本为原值）
    ma_vol_today = volume.rolling(window=params.n1, min_periods=params.n1).mean()
    ma_close_today = close.rolling(window=params.n1, min_periods=params.n1).mean()

    # n2=5：5日均线，用于短期趋势识别
    ma_vol_5 = volume.rolling(window=params.n2, min_periods=params.n2).mean()
    ma_close_5 = close.rolling(window=params.n2, min_periods=params.n2).mean()

    # n3=20：20日均线，用于中期趋势识别
    ma_vol_20 = volume.rolling(window=params.n3, min_periods=params.n3).mean()
    ma_close_20 = close.rolling(window=params.n3, min_periods=params.n3).mean()

    # ========== 成交量标准差（量能波动程度） ==========
    # 用于判断成交量是否显著放大或缩小
    vol_std_5 = volume.rolling(window=params.n2, min_periods=params.n2).std(ddof=0)
    vol_std_20 = volume.rolling(window=params.n3, min_periods=params.n3).std(ddof=0)

    # ========== RSI（相对强弱指数）==========
    # 衡量近期上涨与下跌的强度对比，范围 [0, 100]
    delta = close.diff()  # 收盘价变化
    rsi_up = delta.clip(lower=0)  # 仅保留上涨部分
    rsi_down = -delta.clip(upper=0)  # 仅保留下跌部分（转正数）
    
    # 计算平均涨幅与平均跌幅
    rsi_avg_up = rsi_up.rolling(window=params.rsi_period, min_periods=params.rsi_period).mean()
    rsi_avg_down = rsi_down.rolling(window=params.rsi_period, min_periods=params.rsi_period).mean()
    
    # RSI = (平均涨幅 / (平均涨幅 + 平均跌幅)) * 100，避免除零
    rsi = rsi_avg_up / (rsi_avg_up + rsi_avg_down + 1e-10) * 100

    # ========== 布林带（Bollinger Bands）==========
    # 用于识别价格的高低位置与波动区间
    boll_mid = close.rolling(window=params.boll_period, min_periods=params.boll_period).mean()  # 中线
    boll_std = close.rolling(window=params.boll_period, min_periods=params.boll_period).std(ddof=0)  # 标准差
    boll_top = boll_mid + boll_std * params.boll_width  # 上轨（中线 + 2*std）
    boll_bot = boll_mid - boll_std * params.boll_width  # 下轨（中线 - 2*std）

    # ========== KDJ 指标（随机指标）==========
    # 用于识别超买超卖状态
    lowest = low.rolling(window=params.kdj_period, min_periods=params.kdj_period).min()  # N期最低价
    highest_3 = high.rolling(window=3, min_periods=3).max()  # 3期最高价
    lowest_3 = low.rolling(window=3, min_periods=3).min()  # 3期最低价
    
    # RSV（未成熟随机值）= (收盘价 - N期最低价) / (3期最高价 - 3期最低价) * 100
    rsv = (close - lowest) / (highest_3 - lowest_3 + 1e-10) * 100
    
    # K线：RSV的3期简单移动平均
    k = rsv.rolling(window=3, min_periods=3).mean()
    
    # D线：K线的3期简单移动平均
    d = k.rolling(window=3, min_periods=3).mean()
    
    # J线：3*K - 2*D，用于增强信号灵敏度
    j = 3 * k - 2 * d

    # ========== 连续涨跌判断 ==========
    # 用于识别连续上涨或下跌的模式
    is_down = close < open_  # 下跌K线（收盘 < 开盘）
    is_up = close > open_  # 上涨K线（收盘 > 开盘）
    
    # 连续3根下跌K线
    is_3_down = (
        is_down.rolling(window=3, min_periods=3)
        .apply(lambda x: 1.0 if np.all(x) else 0.0, raw=True)
        .astype(bool)
    )
    
    # 连续3根上涨K线
    is_3_up = (
        is_up.rolling(window=3, min_periods=3)
        .apply(lambda x: 1.0 if np.all(x) else 0.0, raw=True)
        .astype(bool)
    )

    # ========== 返回特征 DataFrame ==========
    features = pd.DataFrame(
        {
            "ma_vol_today": ma_vol_today,
            "ma_close_today": ma_close_today,
            "ma_vol_5": ma_vol_5,
            "ma_close_5": ma_close_5,
            "ma_vol_20": ma_vol_20,
            "ma_close_20": ma_close_20,
            "vol_std_5": vol_std_5,
            "vol_std_20": vol_std_20,
            "rsi": rsi,
            "rsi_prev": rsi.shift(1),  # 前一日 RSI（用于信号交叉判断）
            "boll_top": boll_top,
            "boll_bot": boll_bot,
            "k": k,
            "d": d,
            "j": j,
            "is_3_down": is_3_down,
            "is_3_up": is_3_up,
        },
        index=df.index,
    )

    return features


def compute_latest_volume_features(
    df: pd.DataFrame, params: VolumeIndicatorParams | None = None
) -> Dict[str, float | bool]:
    """计算最近一条数据的指标值。"""

    features = compute_volume_features(df, params)
    if features.empty:
        return {}
    latest = features.iloc[-1]
    return latest.to_dict()
