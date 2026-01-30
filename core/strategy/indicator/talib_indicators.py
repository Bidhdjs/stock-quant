"""
TA-Lib 指标函数集合。
用于快速复用常见技术指标计算。

数学原理：
1. 指标公式基于 TA-Lib 实现（如 EMA、MACD、RSI 等）。
2. 输入支持 kline 列表或 DataFrame，统一为 numpy 数组计算。
"""

# 第一组：Python 标准库

# 第二组：第三方库（按字母排序）
import numpy as np

# 第三组：项目内部导入

# Front Code X


talib = None
_talib_import_error = None


__all__ = [
    "ATR",
    "CurrentBar",
    "BOLL",
    "CCI",
    "HIGHEST",
    "MA",
    "MACD",
    "EMA",
    "KAMA",
    "KDJ",
    "LOWEST",
    "OBV",
    "RSI",
    "ROC",
    "STOCHRSI",
    "SAR",
    "STDDEV",
    "TRIX",
    "VOLUME",
]


def _require_talib():
    """确保 TA-Lib 可用。"""
    global talib
    global _talib_import_error
    if talib is None and _talib_import_error is None:
        try:
            import talib as _talib  # type: ignore
        except Exception as exc:  # pragma: no cover - runtime dependency
            _talib_import_error = exc
        else:
            talib = _talib
    if talib is None:
        raise ImportError(
            "TA-Lib is required for talib_indicators. "
            "Install `TA-Lib` and retry."
        ) from _talib_import_error


def _split_kline(kline):
    """拆分 kline 为 open/high/low/close/volume 数组。"""
    if hasattr(kline, "columns"):
        high = kline["high"].to_numpy(dtype=float)
        low = kline["low"].to_numpy(dtype=float)
        close = kline["close"].to_numpy(dtype=float)
        open_ = kline["open"].to_numpy(dtype=float)
        volume = kline["volume"].to_numpy(dtype=float)
        return open_, high, low, close, volume
    records = kline
    length = len(records)
    open_ = np.zeros(length)
    high = np.zeros(length)
    low = np.zeros(length)
    close = np.zeros(length)
    volume = np.zeros(length)
    for idx, item in enumerate(records):
        open_[idx] = item[1]
        high[idx] = item[2]
        low[idx] = item[3]
        close[idx] = item[4]
        volume[idx] = item[5]
    return open_, high, low, close, volume


def ATR(length, kline):
    """计算 ATR 指标。"""
    _require_talib()
    _, high, low, close, _ = _split_kline(kline)
    return talib.ATR(high, low, close, timeperiod=length)


def CurrentBar(kline):
    """返回 k 线数据长度。"""
    return len(kline)


def BOLL(length, kline):
    """计算布林带指标。"""
    _require_talib()
    _, _, _, close, _ = _split_kline(kline)
    upper, middle, lower = talib.BBANDS(close, timeperiod=length, nbdevup=2, nbdevdn=2, matype=0)
    return {"upperband": upper, "middleband": middle, "lowerband": lower}


def CCI(length, kline):
    """计算 CCI 指标。"""
    _require_talib()
    _, high, low, close, _ = _split_kline(kline)
    return talib.CCI(high, low, close, timeperiod=length)


def HIGHEST(length, kline):
    """计算周期内最高价序列。"""
    _require_talib()
    _, high, _, _, _ = _split_kline(kline)
    return talib.MAX(high, length)


def MA(length, *args, kline=None):
    """计算简单移动平均线。"""
    _require_talib()
    if kline is None and args:
        kline = args[-1]
    _, _, _, close, _ = _split_kline(kline)
    return talib.SMA(close, length)


def MACD(fastperiod, slowperiod, signalperiod, kline):
    """计算 MACD 指标。"""
    _require_talib()
    _, _, _, close, _ = _split_kline(kline)
    dif, dea, macd = talib.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
    return {"DIF": dif, "DEA": dea, "MACD": macd * 2}


def EMA(length, *args, kline=None):
    """计算指数移动平均线。"""
    _require_talib()
    if kline is None and args:
        kline = args[-1]
    _, _, _, close, _ = _split_kline(kline)
    return talib.EMA(close, length)


def KAMA(length, *args, kline=None):
    """计算考夫曼自适应移动平均线。"""
    _require_talib()
    if kline is None and args:
        kline = args[-1]
    _, _, _, close, _ = _split_kline(kline)
    return talib.KAMA(close, length)


def KDJ(fastk_period, slowk_period, slowd_period, kline):
    """计算 KDJ 指标。"""
    _require_talib()
    _, high, low, close, _ = _split_kline(kline)
    slowk, slowd = talib.STOCH(
        high,
        low,
        close,
        fastk_period=fastk_period,
        slowk_period=slowk_period,
        slowk_matype=0,
        slowd_period=slowd_period,
        slowd_matype=0,
    )
    return {"k": slowk, "d": slowd}


def LOWEST(length, kline):
    """计算周期内最低价序列。"""
    _require_talib()
    _, _, low, _, _ = _split_kline(kline)
    return talib.MIN(low, length)


def OBV(kline):
    """计算 OBV 指标。"""
    _require_talib()
    _, _, _, close, volume = _split_kline(kline)
    return talib.OBV(close, volume)


def RSI(length, kline):
    """计算 RSI 指标。"""
    _require_talib()
    _, _, _, close, _ = _split_kline(kline)
    return talib.RSI(close, timeperiod=length)


def ROC(length, kline):
    """计算 ROC 指标。"""
    _require_talib()
    _, _, _, close, _ = _split_kline(kline)
    return talib.ROC(close, timeperiod=length)


def STOCHRSI(timeperiod, fastk_period, fastd_period, kline):
    """计算 STOCHRSI 指标。"""
    _require_talib()
    _, _, _, close, _ = _split_kline(kline)
    stochrsi, fastk = talib.STOCHRSI(
        close,
        timeperiod=timeperiod,
        fastk_period=fastk_period,
        fastd_period=fastd_period,
        fastd_matype=0,
    )
    fastk_ma = talib.MA(stochrsi, 3)
    return {"stochrsi": stochrsi, "fastk": fastk_ma}


def SAR(kline):
    """计算抛物线 SAR 指标。"""
    _require_talib()
    _, high, low, _, _ = _split_kline(kline)
    return talib.SAR(high, low, acceleration=0.02, maximum=0.2)


def STDDEV(length, kline, nbdev=None):
    """计算标准差。"""
    _require_talib()
    nbdev = 1 if nbdev is None else nbdev
    _, _, _, close, _ = _split_kline(kline)
    return talib.STDDEV(close, timeperiod=length, nbdev=nbdev)


def TRIX(length, kline):
    """计算 TRIX 指标。"""
    _require_talib()
    _, _, _, close, _ = _split_kline(kline)
    return talib.TRIX(close, timeperiod=length)


def VOLUME(kline):
    """返回成交量序列。"""
    _, _, _, _, volume = _split_kline(kline)
    return volume
