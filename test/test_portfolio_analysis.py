"""
组合分析指标单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import portfolio as pf


pytestmark = pytest.mark.mock_only


def test_equal_weighted_returns(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    returns = pf.portfolio_returns(sample_returns_df, weights)
    assert len(returns) == len(sample_returns_df)
    assert np.isfinite(returns).all()


def test_portfolio_variance(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    value = pf.portfolio_variance(sample_returns_df, weights)
    assert np.isfinite(value)


def test_portfolio_sharpe_ratio(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    sharpe = pf.portfolio_sharpe_ratio(sample_returns_df, weights)
    assert np.isfinite(sharpe)


def test_portfolio_stats(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    mean, vol, skew, kurt = pf.portfolio_stats(sample_returns_df, weights)
    assert np.isfinite(mean)
    assert np.isfinite(vol)
    assert np.isfinite(skew)
    assert np.isfinite(kurt)


def test_cov_and_std(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    cov = pf.portfolio_cov_matrix(sample_returns_df)
    std = pf.portfolio_standard_deviation(weights, cov)
    assert np.isfinite(std)


def test_total_and_annualized_return(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    series = pf.portfolio_returns(sample_returns_df, weights)
    total = pf.total_return((series + 1).cumprod())
    annualized = pf.annualized_return_from_total(total, years=1)
    assert np.isfinite(total)
    assert np.isfinite(annualized)


def test_annualized_volatility(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    series = pf.portfolio_returns(sample_returns_df, weights)
    value = pf.annualized_volatility(series)
    assert np.isfinite(value)


def test_sortino_ratio(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    series = pf.portfolio_returns(sample_returns_df, weights)
    value = pf.sortino_ratio(series)
    assert np.isfinite(value) or np.isnan(value)


def test_rolling_max_drawdown(sample_returns_df):
    weights = np.ones(sample_returns_df.shape[1]) / sample_returns_df.shape[1]
    series = pf.portfolio_returns(sample_returns_df, weights)
    cumulative = (series + 1).cumprod()
    daily_dd, max_dd = pf.rolling_max_drawdown(cumulative)
    assert len(daily_dd) == len(cumulative)
    assert len(max_dd) == len(cumulative)


def test_risk_return_table(sample_returns_df):
    table = pf.risk_return_table(sample_returns_df)
    assert "Returns" in table.columns
    assert "Risk" in table.columns
