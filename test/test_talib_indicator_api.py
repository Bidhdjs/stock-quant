"""
TA-Lib 指标 API 兼容性测试
验证接口调用方式与返回结构
"""

# Front Code X
import unittest
from unittest.mock import Mock

import numpy as np

from core.strategy.indicator import talib_indicators as ti


class TestTalibIndicatorApi(unittest.TestCase):
    def setUp(self):
        self.kline = [
            ["2026-01-01", 10, 11, 9, 10.5, 100],
            ["2026-01-02", 10.5, 12, 10, 11, 200],
            ["2026-01-03", 11, 13, 10.5, 12, 300],
        ]
        self.fake_talib = Mock()
        self.fake_talib.ATR.return_value = np.array([1, 2, 3], dtype=float)
        self.fake_talib.BBANDS.return_value = (np.array([1]), np.array([2]), np.array([3]))
        self.fake_talib.CCI.return_value = np.array([1])
        self.fake_talib.MAX.return_value = np.array([1])
        self.fake_talib.SMA.return_value = np.array([1])
        self.fake_talib.MACD.return_value = (np.array([1]), np.array([2]), np.array([3]))
        self.fake_talib.EMA.return_value = np.array([1])
        self.fake_talib.KAMA.return_value = np.array([1])
        self.fake_talib.STOCH.return_value = (np.array([1]), np.array([2]))
        self.fake_talib.MIN.return_value = np.array([1])
        self.fake_talib.OBV.return_value = np.array([1])
        self.fake_talib.RSI.return_value = np.array([1])
        self.fake_talib.ROC.return_value = np.array([1])
        self.fake_talib.STOCHRSI.return_value = (np.array([1]), np.array([2]))
        self.fake_talib.MA.return_value = np.array([1])
        self.fake_talib.SAR.return_value = np.array([1])
        self.fake_talib.STDDEV.return_value = np.array([1])
        self.fake_talib.TRIX.return_value = np.array([1])

        self._old_talib = ti.talib
        self._old_error = ti._talib_import_error
        ti.talib = self.fake_talib
        ti._talib_import_error = None

    def tearDown(self):
        ti.talib = self._old_talib
        ti._talib_import_error = self._old_error

    def test_atr(self):
        self.assertEqual(ti.ATR(14, kline=self.kline).shape, (3,))

    def test_current_bar(self):
        self.assertEqual(ti.CurrentBar(kline=self.kline), 3)

    def test_boll(self):
        result = ti.BOLL(20, kline=self.kline)
        self.assertIn("upperband", result)
        self.assertIn("middleband", result)
        self.assertIn("lowerband", result)

    def test_cci(self):
        self.assertEqual(ti.CCI(20, kline=self.kline).shape, (1,))

    def test_highest(self):
        self.assertEqual(ti.HIGHEST(20, kline=self.kline).shape, (1,))

    def test_ma(self):
        self.assertEqual(ti.MA(20, 30, kline=self.kline).shape, (1,))

    def test_macd(self):
        result = ti.MACD(14, 26, 9, kline=self.kline)
        self.assertIn("DIF", result)
        self.assertIn("DEA", result)
        self.assertIn("MACD", result)

    def test_ema(self):
        self.assertEqual(ti.EMA(20, 30, kline=self.kline).shape, (1,))

    def test_kama(self):
        self.assertEqual(ti.KAMA(20, 30, kline=self.kline).shape, (1,))

    def test_kdj(self):
        result = ti.KDJ(20, 30, 9, kline=self.kline)
        self.assertIn("k", result)
        self.assertIn("d", result)

    def test_lowest(self):
        self.assertEqual(ti.LOWEST(20, kline=self.kline).shape, (1,))

    def test_obv(self):
        self.assertEqual(ti.OBV(kline=self.kline).shape, (1,))

    def test_rsi(self):
        self.assertEqual(ti.RSI(20, kline=self.kline).shape, (1,))

    def test_roc(self):
        self.assertEqual(ti.ROC(20, kline=self.kline).shape, (1,))

    def test_stochrsi(self):
        result = ti.STOCHRSI(20, 30, 9, kline=self.kline)
        self.assertIn("stochrsi", result)
        self.assertIn("fastk", result)

    def test_sar(self):
        self.assertEqual(ti.SAR(kline=self.kline).shape, (1,))

    def test_stddev(self):
        self.assertEqual(ti.STDDEV(20, kline=self.kline, nbdev=None).shape, (1,))

    def test_trix(self):
        self.assertEqual(ti.TRIX(20, kline=self.kline).shape, (1,))

    def test_volume(self):
        self.assertEqual(ti.VOLUME(kline=self.kline).shape, (3,))


if __name__ == "__main__":
    unittest.main()
