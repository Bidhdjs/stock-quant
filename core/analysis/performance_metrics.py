"""
绩效与风险指标计算模块
提取并迁移自 Stock_Analysis_For_Quant 的风险/收益相关 notebooks

数学原理：
1. 年化收益/波动：基于日收益率均值与标准差缩放
2. 最大回撤：基于净值曲线峰值回撤
3. VaR：历史分位数/参数法/蒙特卡洛模拟
"""

from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Tuple, Optional

# 第二组：第三方库（按字母排序）
import numpy as np
import pandas as pd

# 第三组：项目内部导入


def _to_series(data) -> pd.Series:
    """将输入转换为 pandas Series。"""
    if isinstance(data, pd.Series):
        return data.dropna()
    if isinstance(data, pd.DataFrame):
        if data.shape[1] != 1:
            raise ValueError("DataFrame 必须为单列数据")
        return data.iloc[:, 0].dropna()
    return pd.Series(data).dropna()


def daily_returns(price_series) -> pd.Series:
    """
    计算日收益率（简单收益率）。

    Args:
        price_series: 价格序列（Series / list / ndarray）

    Returns:
        Series: 日收益率
    """
    prices = _to_series(price_series)
    return prices.pct_change().dropna()


def annualized_return(returns, periods_per_year: int = 252) -> float:
    """
    年化收益率（基于均值缩放）。
    """
    rets = _to_series(returns)
    return float(rets.mean() * periods_per_year)


def annualized_volatility(returns, periods_per_year: int = 252) -> float:
    """
    年化波动率（基于标准差缩放）。
    """
    rets = _to_series(returns)
    return float(rets.std() * np.sqrt(periods_per_year))


def sharpe_ratio(returns, risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    """
    夏普比率： (均值 - 无风险利率) / 波动率
    """
    rets = _to_series(returns)
    excess = rets - risk_free / periods_per_year
    vol = excess.std()
    return float(excess.mean() / vol) if vol != 0 else np.nan


def sortino_ratio(returns, risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    """
    索提诺比率：仅使用下行波动。
    """
    rets = _to_series(returns)
    excess = rets - risk_free / periods_per_year
    downside = excess[excess < 0]
    downside_std = downside.std()
    return float(excess.mean() / downside_std) if downside_std != 0 else np.nan


def max_drawdown(price_series) -> float:
    """
    最大回撤（基于价格序列计算）。
    """
    prices = _to_series(price_series)
    cumulative = prices / prices.iloc[0]
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    return float(drawdown.min())


def realized_variance(returns, periods_per_year: int = 252) -> pd.Series:
    """
    实现方差（基于累计平方收益率）。
    """
    rets = _to_series(returns)
    cumsum = np.cumsum(rets ** 2)
    denom = np.arange(1, len(rets) + 1)
    return periods_per_year * (cumsum / denom)


def realized_volatility(returns, periods_per_year: int = 252) -> pd.Series:
    """
    实现波动率（实现方差开方）。
    """
    return np.sqrt(realized_variance(returns, periods_per_year=periods_per_year))


def alpha_beta(returns, benchmark_returns) -> Tuple[float, float, float]:
    """
    计算 Alpha、Beta 与 R^2（线性回归简化）。
    """
    y = _to_series(returns)
    x = _to_series(benchmark_returns)
    min_len = min(len(x), len(y))
    x = x.iloc[-min_len:]
    y = y.iloc[-min_len:]
    if min_len < 2:
        return np.nan, np.nan, np.nan
    beta = float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))
    alpha = float(y.mean() - beta * x.mean())
    corr = np.corrcoef(x, y)[0, 1]
    r_squared = float(corr ** 2)
    return alpha, beta, r_squared


def var_historical(returns, level: float = 0.05) -> float:
    """
    历史法 VaR（分位数）。
    """
    rets = _to_series(returns)
    return float(rets.quantile(level))


def var_parametric_normal(returns, level: float = 0.05) -> float:
    """
    参数法 VaR（正态分布）。
    依赖 scipy.stats.norm，若未安装将报错。
    """
    try:
        from scipy import stats  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("scipy is required for var_parametric_normal") from exc
    rets = _to_series(returns)
    mean = rets.mean()
    sigma = rets.std()
    return float(stats.norm.ppf(level, mean, sigma))


def var_parametric_t(returns, level: float = 0.05) -> float:
    """
    参数法 VaR（t 分布拟合）。
    依赖 scipy.stats.t，若未安装将报错。
    """
    try:
        from scipy import stats  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("scipy is required for var_parametric_t") from exc
    rets = _to_series(returns)
    tdf, tmean, tsigma = stats.t.fit(rets.to_numpy())
    return float(stats.t.ppf(level, tdf, loc=tmean, scale=tsigma))


def var_monte_carlo(
    start_price: float,
    days: int = 300,
    mu: float = 0.05,
    sigma: float = 0.04,
    runs: int = 10000,
    level: float = 0.01,
    seed: Optional[int] = None,
) -> Tuple[float, float]:
    """
    蒙特卡洛 VaR 模拟（几何随机游走）。
    """
    rng = np.random.default_rng(seed)
    dt = 1 / float(days)
    shocks = rng.normal(loc=mu * dt, scale=sigma * np.sqrt(dt), size=(runs, days))
    prices = np.zeros((runs, days))
    prices[:, 0] = start_price
    for i in range(1, days):
        prices[:, i] = np.maximum(0, prices[:, i - 1] + shocks[:, i] * prices[:, i - 1])
    final_prices = prices[:, -1]
    q = np.percentile(final_prices, level * 100)
    var_value = start_price - q
    return float(var_value), float(q)


def profit_or_loss(current_value: float, purchase_cost: float) -> float:
    """
    盈亏金额。
    """
    return float(current_value - purchase_cost)


def percentage_gain_or_loss(current_value: float, purchase_cost: float) -> float:
    """
    百分比盈亏。
    """
    if purchase_cost == 0:
        return np.nan
    return float((current_value - purchase_cost) / purchase_cost * 100)


def percentage_returns(current_value: float, purchase_cost: float) -> float:
    """
    回报率（小数）。
    """
    if purchase_cost == 0:
        return np.nan
    return float((current_value - purchase_cost) / purchase_cost)


def net_gains_or_losses(price_series) -> float:
    """
    期间净收益率（基于首尾价格）。
    """
    prices = _to_series(price_series)
    if prices.empty:
        return np.nan
    return float((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0])


def total_return(current_value: float, purchase_cost: float) -> float:
    """
    总回报（百分比）。
    """
    if purchase_cost == 0:
        return np.nan
    return float((current_value / purchase_cost - 1) * 100)

