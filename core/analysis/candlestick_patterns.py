"""
蜡烛图形态检测模块。
基于 TA-Lib 识别常见形态（锤头线、晨星、吞没等）。
"""


from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Dict

# 第二组：第三方库（按字母排序）
import pandas as pd

# 第三组：项目内部导入

def _require_talib():
    try:
        import talib  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("TA-Lib is required for candlestick patterns") from exc
    return talib


def _get_ohlc(df: pd.DataFrame):
    return df["Open"].to_numpy(), df["High"].to_numpy(), df["Low"].to_numpy(), df["Close"].to_numpy()


def detect_doji(df: pd.DataFrame) -> pd.Series:
    """Doji 形态。"""
    talib = _require_talib()
    o, h, l, c = _get_ohlc(df)
    return pd.Series(talib.CDLDOJI(o, h, l, c), index=df.index, name="Doji")


def detect_morning_star(df: pd.DataFrame) -> pd.Series:
    """Morning Star 形态。"""
    talib = _require_talib()
    o, h, l, c = _get_ohlc(df)
    return pd.Series(talib.CDLMORNINGSTAR(o, h, l, c), index=df.index, name="MorningStar")


def detect_dark_cloud_cover(df: pd.DataFrame, penetration: float = 0.0) -> pd.Series:
    """Dark Cloud Cover 形态。"""
    talib = _require_talib()
    o, h, l, c = _get_ohlc(df)
    return pd.Series(talib.CDLDARKCLOUDCOVER(o, h, l, c, penetration=penetration), index=df.index, name="DarkCloudCover")


def detect_abandoned_baby(df: pd.DataFrame) -> pd.Series:
    """Abandoned Baby 形态。"""
    talib = _require_talib()
    o, h, l, c = _get_ohlc(df)
    return pd.Series(talib.CDLABANDONEDBABY(o, h, l, c), index=df.index, name="AbandonedBaby")


def detect_belt_hold(df: pd.DataFrame) -> pd.Series:
    """Belt Hold 形态。"""
    talib = _require_talib()
    o, h, l, c = _get_ohlc(df)
    return pd.Series(talib.CDLBELTHOLD(o, h, l, c), index=df.index, name="BeltHold")


def detect_patterns(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    批量检测常见形态。
    """
    return {
        "Doji": detect_doji(df),
        "MorningStar": detect_morning_star(df),
        "DarkCloudCover": detect_dark_cloud_cover(df),
        "AbandonedBaby": detect_abandoned_baby(df),
        "BeltHold": detect_belt_hold(df),
    }

