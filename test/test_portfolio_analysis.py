"""
组合分析指标单元测试（mock-only）
"""

# Front Code X

# 第一组：Python 标准库
import unittest

# 第二组：第三方库（按字母排序）
import numpy as np
import pandas as pd

# 第三组：项目内部导入
from core.analysis import portfolio as pf


class TestPortfolioAnalysis(unittest.TestCase):
    def setUp(self):
        self.prices = pd.Series([100, 102, 101, 105, 103], name="price")
        self.returns = pd.DataFrame(
            {
                "A": [0.01, -0.005, 0.02, -0.01],
                "B": [0.015, 0.0, -0.01, 0.005],
                "C": [0.0, 0.01, 0.005, -0.002],
            }
        )
        self.weights = np.array([0.5, 0.3, 0.2])

    def test_calc_daily_log_returns(self):
        rets = pf.calc_daily_log_returns(self.prices)
        self.assertEqual(len(rets), len(self.prices) - 1)

    def test_month_returns(self):
        rets = pf.calc_daily_log_returns(self.prices)
        monthly = pf.calc_month_returns(rets)
        self.assertTrue(len(monthly) >= 1)

    def test_annual_returns(self):
        rets = pf.calc_daily_log_returns(self.prices)
        yearly = pf.calc_annual_returns(rets)
        self.assertTrue(len(yearly) >= 1)

    def test_portfolio_variance(self):
        value = pf.portfolio_variance(self.returns, self.weights)
        self.assertTrue(np.isfinite(value))

    def test_portfolio_sharpe(self):
        value = pf.portfolio_sharpe_ratio(self.returns, self.weights, risk_free_rate=0.001)
        self.assertTrue(np.isfinite(value))

    def test_portfolio_returns(self):
        series = pf.portfolio_returns(self.returns, self.weights)
        self.assertEqual(len(series), len(self.returns))

    def test_cumulative_returns(self):
        cum = pf.cumulative_returns(self.returns)
        self.assertEqual(cum.shape, self.returns.shape)

    def test_portfolio_stats(self):
        mean, std, skew, kurt = pf.portfolio_stats(self.returns, self.weights)
        self.assertTrue(np.isfinite(mean))
        self.assertTrue(np.isfinite(std))
        self.assertTrue(np.isfinite(skew))
        self.assertTrue(np.isfinite(kurt))

    def test_portfolio_expected_return(self):
        value = pf.portfolio_expected_return(self.returns.mean(), self.weights)
        self.assertTrue(np.isfinite(value))

    def test_cov_matrix(self):
        cov = pf.portfolio_cov_matrix(self.returns, annualize=250)
        self.assertEqual(cov.shape[0], cov.shape[1])

    def test_portfolio_std_var(self):
        cov = pf.portfolio_cov_matrix(self.returns, annualize=250)
        std = pf.portfolio_standard_deviation(self.weights, cov)
        var = pf.portfolio_variance_from_cov(self.weights, cov)
        self.assertTrue(np.isfinite(std))
        self.assertTrue(np.isfinite(var))

    def test_total_and_annualized_return(self):
        series = pf.portfolio_returns(self.returns, self.weights)
        total = pf.total_return((1 + series).cumprod())
        annual = pf.annualized_return_from_total(total, years=1)
        self.assertTrue(np.isfinite(total))
        self.assertTrue(np.isfinite(annual))

    def test_annualized_volatility(self):
        series = pf.portfolio_returns(self.returns, self.weights)
        value = pf.annualized_volatility(series, annualize=250)
        self.assertTrue(np.isfinite(value))

    def test_sortino_ratio(self):
        series = pf.portfolio_returns(self.returns, self.weights)
        value = pf.sortino_ratio(series, risk_free_rate=0.01, target=0.0)
        self.assertTrue(np.isfinite(value))

    def test_rolling_max_drawdown(self):
        series = (1 + pf.portfolio_returns(self.returns, self.weights)).cumprod()
        daily_dd, max_dd = pf.rolling_max_drawdown(series, window=2)
        self.assertEqual(len(daily_dd), len(series))
        self.assertEqual(len(max_dd), len(series))

    def test_risk_return_table(self):
        table = pf.risk_return_table(self.returns)
        self.assertIn("Returns", table.columns)
        self.assertIn("Risk", table.columns)


if __name__ == "__main__":
    unittest.main()
