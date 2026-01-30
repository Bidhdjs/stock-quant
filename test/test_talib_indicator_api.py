"""
TA-Lib 指标 API 兼容性测试。
验证接口调用方式与返回结构。
"""

# Front Code X
from unittest.mock import Mock

import numpy as np
import pytest

from core.strategy.indicator import talib_indicators as ti


pytestmark = pytest.mark.mock_only


def _mock_talib():
    fake = Mock()
    fake.ATR.return_value = np.array([1, 2, 3], dtype=float)
    fake.BBANDS.return_value = (np.array([1]), np.array([2]), np.array([3]))
    fake.CCI.return_value = np.array([1])
    fake.MAX.return_value = np.array([1])
    fake.SMA.return_value = np.array([1])
    fake.MACD.return_value = (np.array([1]), np.array([2]), np.array([3]))
    fake.EMA.return_value = np.array([1])
    fake.KAMA.return_value = np.array([1])
    fake.STOCH.return_value = (np.array([1]), np.array([2]))
    fake.MIN.return_value = np.array([1])
    fake.OBV.return_value = np.array([1])
    fake.RSI.return_value = np.array([1])
    fake.ROC.return_value = np.array([1])
    fake.STOCHRSI.return_value = (np.array([1]), np.array([2]))
    fake.MA.return_value = np.array([1])
    fake.SAR.return_value = np.array([1])
    fake.STDDEV.return_value = np.array([1])
    fake.TRIX.return_value = np.array([1])
    return fake


def test_indicator_api_shapes():
    kline = [
        ["2026-01-01", 10, 11, 9, 10.5, 100],
        ["2026-01-02", 10.5, 12, 10, 11, 200],
        ["2026-01-03", 11, 13, 10.5, 12, 300],
    ]
    fake_talib = _mock_talib()
    old_talib = ti.talib
    old_error = ti._talib_import_error
    ti.talib = fake_talib
    ti._talib_import_error = None
    try:
        assert ti.ATR(14, kline=kline).shape == (3,)
        assert ti.CurrentBar(kline=kline) == 3
        boll = ti.BOLL(20, kline=kline)
        assert "upperband" in boll and "middleband" in boll and "lowerband" in boll
        assert ti.CCI(20, kline=kline).shape == (1,)
        assert ti.HIGHEST(20, kline=kline).shape == (1,)
        assert ti.MA(20, 30, kline=kline).shape == (1,)
        macd = ti.MACD(14, 26, 9, kline=kline)
        assert "DIF" in macd and "DEA" in macd and "MACD" in macd
        assert ti.EMA(20, 30, kline=kline).shape == (1,)
        assert ti.KAMA(20, 30, kline=kline).shape == (1,)
        kdj = ti.KDJ(20, 30, 9, kline=kline)
        assert "k" in kdj and "d" in kdj
        assert ti.LOWEST(20, kline=kline).shape == (1,)
        assert ti.OBV(kline=kline).shape == (1,)
        assert ti.RSI(20, kline=kline).shape == (1,)
        assert ti.ROC(20, kline=kline).shape == (1,)
        stochrsi = ti.STOCHRSI(20, 30, 9, kline=kline)
        assert "stochrsi" in stochrsi and "fastk" in stochrsi
        assert ti.SAR(kline=kline).shape == (1,)
        assert ti.STDDEV(20, kline=kline, nbdev=None).shape == (1,)
        assert ti.TRIX(20, kline=kline).shape == (1,)
        assert ti.VOLUME(kline=kline).shape == (3,)
    finally:
        ti.talib = old_talib
        ti._talib_import_error = old_error
