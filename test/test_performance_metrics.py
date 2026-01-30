"""
绩效与风险指标单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import performance_metrics as pm


pytestmark = pytest.mark.mock_only


def test_daily_returns(sample_prices):
    rets = pm.daily_returns(sample_prices)
    assert len(rets) == len(sample_prices) - 1


def test_annualized_return(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.annualized_return(returns, periods_per_year=252)
    assert np.isfinite(value)


def test_annualized_volatility(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.annualized_volatility(returns, periods_per_year=252)
    assert np.isfinite(value)


def test_sharpe_ratio(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.sharpe_ratio(returns)
    assert np.isfinite(value)


def test_sortino_ratio(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.sortino_ratio(returns)
    assert np.isfinite(value)


def test_max_drawdown(sample_prices):
    value = pm.max_drawdown(sample_prices)
    assert value <= 0


def test_realized_variance(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.realized_variance(returns)
    assert len(value) == len(returns)


def test_realized_volatility(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.realized_volatility(returns)
    assert len(value) == len(returns)


def test_alpha_beta(sample_prices):
    returns = sample_prices.pct_change().dropna()
    benchmark = np.array([0.01, -0.005, 0.02, -0.01])
    alpha, beta, r2 = pm.alpha_beta(returns, benchmark)
    assert np.isfinite(alpha)
    assert np.isfinite(beta)
    assert np.isfinite(r2)


def test_var_historical(sample_prices):
    returns = sample_prices.pct_change().dropna()
    value = pm.var_historical(returns, level=0.05)
    assert np.isfinite(value)


def test_var_monte_carlo():
    var_value, q = pm.var_monte_carlo(10.0, days=10, runs=1000, level=0.01, seed=1)
    assert np.isfinite(var_value)
    assert np.isfinite(q)


def test_profit_metrics(sample_prices):
    assert pm.profit_or_loss(120, 100) == 20.0
    assert pm.percentage_gain_or_loss(120, 100) == 20.0
    assert pm.percentage_returns(120, 100) == 0.2
    assert np.isfinite(pm.net_gains_or_losses(sample_prices))
    assert pm.total_return(120, 100) <= 20.0
