"""
组合分析工具模块。
提供组合收益、波动、夏普、VaR、CVaR、跟踪误差等指标。

数学原理：
1. 组合收益：权重与资产收益率加权求和。
2. 组合波动：基于协方差矩阵与权重。
"""


from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Optional, Tuple

# 第二组：第三方库（按字母排序）
import numpy as np
import pandas as pd

# 第三组：项目内部导入

def calc_daily_log_returns(prices: pd.Series) -> pd.Series:
    """
    计算日对数收益率。
    """
    prices = prices.dropna()
    return np.log(prices / prices.shift(1)).dropna()


def calc_month_returns(daily_log_returns: pd.Series) -> pd.Series:
    """
    计算按月聚合收益率（对数收益累加后指数化）。
    """
    grouped = daily_log_returns.groupby(lambda date: date.month).sum()
    return np.exp(grouped) - 1


def calc_annual_returns(daily_log_returns: pd.Series) -> pd.Series:
    """
    计算按年聚合收益率（对数收益累加后指数化）。
    """
    grouped = daily_log_returns.groupby(lambda date: date.year).sum()
    return np.exp(grouped) - 1


def portfolio_variance(returns: pd.DataFrame, weights: Optional[np.ndarray] = None) -> float:
    """
    计算组合方差。
    """
    if weights is None:
        weights = np.ones(returns.columns.size) / returns.columns.size
    sigma = np.cov(returns.T, ddof=0)
    var = float((weights * sigma * weights.T).sum())
    return var


def portfolio_sharpe_ratio(
    returns: pd.DataFrame,
    weights: Optional[np.ndarray] = None,
    risk_free_rate: float = 0.001,
) -> float:
    """
    计算组合 Sharpe Ratio（基于列均值与组合方差）。
    """
    n = returns.columns.size
    if weights is None:
        weights = np.ones(n) / n
    var = portfolio_variance(returns, weights)
    means = returns.mean()
    return float((means.dot(weights) - risk_free_rate) / np.sqrt(var)) if var != 0 else np.nan


def portfolio_returns(returns: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """
    计算组合收益序列。
    """
    return returns.dot(weights)


def cumulative_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """
    计算累计收益（简单收益）。
    """
    return (1 + returns).cumprod()


def portfolio_stats(returns: pd.DataFrame, weights: np.ndarray) -> Tuple[float, float, float, float]:
    """
    计算组合均值、波动、偏度、峰度。
    """
    portfolio = portfolio_returns(returns, weights)
    return (
        float(portfolio.mean()),
        float(portfolio.std()),
        float(portfolio.skew()),
        float(portfolio.kurtosis()),
    )


def portfolio_expected_return(mean_daily_returns: pd.Series, weights: np.ndarray) -> float:
    """
    计算组合预期收益。
    """
    return float(np.sum(mean_daily_returns * weights))


def portfolio_cov_matrix(returns: pd.DataFrame, annualize: int = 250) -> pd.DataFrame:
    """
    计算年化协方差矩阵。
    """
    return returns.cov() * annualize


def portfolio_standard_deviation(weights: np.ndarray, cov_matrix: pd.DataFrame) -> float:
    """
    组合标准差。
    """
    return float(np.sqrt(np.dot(weights.T, np.dot(weights, cov_matrix))))


def portfolio_variance_from_cov(weights: np.ndarray, cov_matrix: pd.DataFrame) -> float:
    """
    组合方差（基于协方差矩阵）。
    """
    return float(np.dot(weights.T, np.dot(cov_matrix, weights)))


def total_return(portfolio_series: pd.Series) -> float:
    """
    组合总收益率（首尾）。
    """
    series = portfolio_series.dropna()
    return float((series.iloc[-1] - series.iloc[0]) / series.iloc[0])


def annualized_return_from_total(total_ret: float, years: float) -> float:
    """
    组合年化收益率（基于总收益和年数）。
    """
    return float((total_ret + 1) ** (1 / years) - 1)


def annualized_volatility(portfolio_returns_series: pd.Series, annualize: int = 250) -> float:
    """
    组合年化波动率。
    """
    return float(portfolio_returns_series.std() * np.sqrt(annualize))


def sortino_ratio(
    portfolio_returns_series: pd.Series,
    risk_free_rate: float = 0.01,
    target: float = 0.0,
) -> float:
    """
    组合 Sortino Ratio（基于下行波动）。
    """
    returns = portfolio_returns_series.dropna()
    downside = returns[returns < target]
    down_stdev = downside.std()
    expected_return = returns.mean()
    return float((expected_return - risk_free_rate) / down_stdev) if down_stdev != 0 else np.nan


def rolling_max_drawdown(portfolio_series: pd.Series, window: int = 252) -> Tuple[pd.Series, pd.Series]:
    """
    滚动最大回撤（基于窗口最大值）。
    返回：
        daily_draw_down, max_daily_draw_down
    """
    series = portfolio_series.dropna()
    roll_max = series.rolling(center=False, min_periods=1, window=window).max()
    daily_draw_down = series / roll_max - 1.0
    max_daily_draw_down = daily_draw_down.rolling(center=False, min_periods=1, window=window).min()
    return daily_draw_down, max_daily_draw_down


def risk_return_table(returns: pd.DataFrame) -> pd.DataFrame:
    """
    构造风险与收益表（均值/标准差）。
    """
    table = pd.DataFrame()
    table["Returns"] = returns.mean()
    table["Risk"] = returns.std()
    return table

