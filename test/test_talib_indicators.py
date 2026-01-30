"""
TA-Lib 指标封装单元测试
验证拆分函数与依赖缺失行为
"""

# Front Code X
import unittest
from unittest.mock import Mock

import numpy as np

from core.strategy.indicator import talib_indicators as ti


class TestTalibIndicators(unittest.TestCase):
    def test_split_kline_list(self):
        """验证 kline 列表拆分。"""
        kline = [
            ["2026-01-01", 10, 11, 9, 10.5, 100],
            ["2026-01-02", 10.5, 12, 10, 11, 200],
        ]
        open_, high, low, close, volume = ti._split_kline(kline)
        self.assertEqual(open_.tolist(), [10.0, 10.5])
        self.assertEqual(high.tolist(), [11.0, 12.0])
        self.assertEqual(low.tolist(), [9.0, 10.0])
        self.assertEqual(close.tolist(), [10.5, 11.0])
        self.assertEqual(volume.tolist(), [100.0, 200.0])

    def test_requires_talib_when_missing(self):
        """验证未安装 TA-Lib 时提示错误。"""
        old_talib = ti.talib
        old_error = ti._talib_import_error
        ti.talib = None
        ti._talib_import_error = ImportError("no talib")
        try:
            with self.assertRaises(ImportError):
                ti.RSI(14, [])
        finally:
            ti.talib = old_talib
            ti._talib_import_error = old_error

    def test_macd_uses_talib(self):
        """验证 MACD 使用 TA-Lib 输出。"""
        fake_talib = Mock()
        fake_talib.MACD.return_value = (np.array([1.0]), np.array([2.0]), np.array([3.0]))
        old_talib = ti.talib
        old_error = ti._talib_import_error
        ti.talib = fake_talib
        ti._talib_import_error = None
        try:
            result = ti.MACD(12, 26, 9, [["t", 1, 2, 0.5, 1.5, 100]])
            self.assertEqual(result["DIF"].tolist(), [1.0])
            self.assertEqual(result["DEA"].tolist(), [2.0])
            self.assertEqual(result["MACD"].tolist(), [6.0])
        finally:
            ti.talib = old_talib
            ti._talib_import_error = old_error


if __name__ == "__main__":
    unittest.main()
