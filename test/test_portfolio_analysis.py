"""
组合分析指标单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import portfolio as pf


pytestmark = pytest.mark.mock_only


def test_equal_weight_allocation(sample_returns_df):
    weights = pf.equal_weight_allocation(sample_returns_df.shape[1])
    assert np.isclose(weights.sum(), 1.0)


def test_portfolio_returns(sample_returns_df):
    weights = pf.equal_weight_allocation(sample_returns_df.shape[1])
    returns = pf.portfolio_returns(sample_returns_df, weights)
    assert len(returns) == len(sample_returns_df)


def test_portfolio_volatility(sample_returns_df):
    weights = pf.equal_weight_allocation(sample_returns_df.shape[1])
    vol = pf.portfolio_volatility(sample_returns_df, weights)
    assert np.isfinite(vol)


def test_portfolio_sharpe_ratio(sample_returns_df):
    weights = pf.equal_weight_allocation(sample_returns_df.shape[1])
    sharpe = pf.portfolio_sharpe_ratio(sample_returns_df, weights)
    assert np.isfinite(sharpe)


def test_portfolio_var(sample_returns_df):
    weights = pf.equal_weight_allocation(sample_returns_df.shape[1])
    value = pf.portfolio_var(sample_returns_df, weights, level=0.05)
    assert np.isfinite(value)


def test_portfolio_cvar(sample_returns_df):
    weights = pf.equal_weight_allocation(sample_returns_df.shape[1])
    value = pf.portfolio_cvar(sample_returns_df, weights, level=0.05)
    assert np.isfinite(value)


def test_portfolio_drawdown(sample_returns_df):
    returns = pf.portfolio_returns(sample_returns_df, pf.equal_weight_allocation(sample_returns_df.shape[1]))
    value = pf.max_drawdown(returns)
    assert value <= 0


def test_beta_alpha(sample_returns_df):
    returns = pf.portfolio_returns(sample_returns_df, pf.equal_weight_allocation(sample_returns_df.shape[1]))
    benchmark = np.array([0.01, -0.005, 0.02, -0.01])
    beta, alpha = pf.beta_alpha(returns, benchmark)
    assert np.isfinite(beta)
    assert np.isfinite(alpha)


def test_tracking_error(sample_returns_df):
    returns = pf.portfolio_returns(sample_returns_df, pf.equal_weight_allocation(sample_returns_df.shape[1]))
    benchmark = np.array([0.01, -0.005, 0.02, -0.01])
    value = pf.tracking_error(returns, benchmark)
    assert np.isfinite(value)
