"""
期权定价与 Greeks 单元测试（mock-only）
"""

# Front Code X

# 第一组：Python 标准库
import unittest
from unittest.mock import Mock, patch

# 第二组：第三方库（按字母排序）
import numpy as np

# 第三组：项目内部导入
from core.analysis import options_pricing as op


class TestOptionsPricing(unittest.TestCase):
    def test_d1_d2(self):
        d1 = op.d1(100, 100, 0.1, 0.3, 1)
        d2 = op.d2(100, 100, 0.1, 0.3, 1)
        self.assertTrue(np.isfinite(d1))
        self.assertTrue(np.isfinite(d2))

    def test_black_scholes_prices(self):
        with patch("core.analysis.options_pricing._norm_cdf", return_value=0.5):
            call = op.black_scholes_call(100, 100, 0.1, 0.3, 1)
            put = op.black_scholes_put(100, 100, 0.1, 0.3, 1)
        self.assertTrue(np.isfinite(call))
        self.assertTrue(np.isfinite(put))

    def test_parity(self):
        diff = op.call_put_parity(10, 8, 100, 100, 0.1, 1)
        self.assertTrue(np.isfinite(diff))

    def test_greeks(self):
        with patch("core.analysis.options_pricing._norm_cdf", return_value=0.5), \
             patch("core.analysis.options_pricing._norm_pdf", return_value=0.4):
            delta, gamma, theta, vega, rho = op.greeks(100, 100, 0.1, 0.3, 1)
        self.assertTrue(np.isfinite(delta))
        self.assertTrue(np.isfinite(gamma))
        self.assertTrue(np.isfinite(theta))
        self.assertTrue(np.isfinite(vega))
        self.assertTrue(np.isfinite(rho))

    def test_norm_cdf_pdf_import_error(self):
        with patch("core.analysis.options_pricing.stats", new=None, create=True):
            with self.assertRaises(ImportError):
                op._norm_cdf(0.0)
            with self.assertRaises(ImportError):
                op._norm_pdf(0.0)


if __name__ == "__main__":
    unittest.main()
