"""
绩效与风险指标单元测试（mock-only）
"""

# Front Code X

# 第一组：Python 标准库
import unittest

# 第二组：第三方库（按字母排序）
import numpy as np
import pandas as pd

# 第三组：项目内部导入
from core.analysis import performance_metrics as pm


class TestPerformanceMetrics(unittest.TestCase):
    def setUp(self):
        self.prices = pd.Series([100, 102, 101, 105, 103], name="price")
        self.returns = self.prices.pct_change().dropna()
        self.benchmark = pd.Series([0.01, -0.005, 0.02, -0.01], name="bench")

    def test_daily_returns(self):
        rets = pm.daily_returns(self.prices)
        self.assertEqual(len(rets), len(self.prices) - 1)

    def test_annualized_return(self):
        value = pm.annualized_return(self.returns, periods_per_year=252)
        self.assertTrue(np.isfinite(value))

    def test_annualized_volatility(self):
        value = pm.annualized_volatility(self.returns, periods_per_year=252)
        self.assertTrue(np.isfinite(value))

    def test_sharpe_ratio(self):
        value = pm.sharpe_ratio(self.returns)
        self.assertTrue(np.isfinite(value))

    def test_sortino_ratio(self):
        value = pm.sortino_ratio(self.returns)
        self.assertTrue(np.isfinite(value))

    def test_max_drawdown(self):
        value = pm.max_drawdown(self.prices)
        self.assertTrue(value <= 0)

    def test_realized_variance(self):
        value = pm.realized_variance(self.returns)
        self.assertEqual(len(value), len(self.returns))

    def test_realized_volatility(self):
        value = pm.realized_volatility(self.returns)
        self.assertEqual(len(value), len(self.returns))

    def test_alpha_beta(self):
        alpha, beta, r2 = pm.alpha_beta(self.returns, self.benchmark)
        self.assertTrue(np.isfinite(alpha))
        self.assertTrue(np.isfinite(beta))
        self.assertTrue(np.isfinite(r2))

    def test_var_historical(self):
        value = pm.var_historical(self.returns, level=0.05)
        self.assertTrue(np.isfinite(value))

    def test_var_monte_carlo(self):
        var_value, q = pm.var_monte_carlo(10.0, days=10, runs=1000, level=0.01, seed=1)
        self.assertTrue(np.isfinite(var_value))
        self.assertTrue(np.isfinite(q))

    def test_profit_metrics(self):
        self.assertEqual(pm.profit_or_loss(120, 100), 20.0)
        self.assertEqual(pm.percentage_gain_or_loss(120, 100), 20.0)
        self.assertEqual(pm.percentage_returns(120, 100), 0.2)
        self.assertTrue(np.isfinite(pm.net_gains_or_losses(self.prices)))
        self.assertEqual(pm.total_return(120, 100), 20.0)


if __name__ == "__main__":
    unittest.main()
