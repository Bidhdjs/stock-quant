"""
期权定价与 Greeks
提取并迁移自 Stock_Analysis_For_Quant 的 Black-Scholes 相关 notebooks

数学原理：
1. Black-Scholes 模型通过 d1/d2 计算欧式期权定价
2. Greeks 通过对价格对参数的偏导数计算
"""

from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Tuple

# 第二组：第三方库（按字母排序）
import numpy as np

# 第三组：项目内部导入


def _norm_cdf(x: float) -> float:
    """标准正态分布 CDF。"""
    try:
        from scipy import stats  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("scipy is required for normal CDF") from exc
    return float(stats.norm.cdf(x))


def _norm_pdf(x: float) -> float:
    """标准正态分布 PDF。"""
    try:
        from scipy import stats  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("scipy is required for normal PDF") from exc
    return float(stats.norm.pdf(x))


def d1(S0: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Black-Scholes d1。
    """
    return float((np.log(S0 / K) + (r + sigma**2 / 2) * T) / (sigma * np.sqrt(T)))


def d2(S0: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Black-Scholes d2。
    """
    return float((np.log(S0 / K) + (r - sigma**2 / 2) * T) / (sigma * np.sqrt(T)))


def black_scholes_call(S0: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    欧式看涨期权定价。
    """
    return float(S0 * _norm_cdf(d1(S0, K, r, sigma, T)) - K * np.exp(-r * T) * _norm_cdf(d2(S0, K, r, sigma, T)))


def black_scholes_put(S0: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    欧式看跌期权定价。
    """
    return float(K * np.exp(-r * T) * _norm_cdf(-d2(S0, K, r, sigma, T)) - S0 * _norm_cdf(-d1(S0, K, r, sigma, T)))


def call_put_parity(call_price: float, put_price: float, S0: float, K: float, r: float, T: float) -> float:
    """
    看涨-看跌平价差值（理论上应接近 0）。
    """
    return float(call_price - put_price - (S0 - K * np.exp(-r * T)))


def greeks(
    S0: float, K: float, r: float, sigma: float, T: float
) -> Tuple[float, float, float, float, float]:
    """
    计算 Greeks（Delta, Gamma, Theta, Vega, Rho）对应看涨期权。
    """
    d1_val = d1(S0, K, r, sigma, T)
    d2_val = d2(S0, K, r, sigma, T)
    delta = _norm_cdf(d1_val)
    gamma = _norm_pdf(d1_val) / (S0 * sigma * np.sqrt(T))
    theta = (
        -(S0 * _norm_pdf(d1_val) * sigma) / (2 * np.sqrt(T))
        - r * K * np.exp(-r * T) * _norm_cdf(d2_val)
    )
    vega = S0 * _norm_pdf(d1_val) * np.sqrt(T)
    rho = K * T * np.exp(-r * T) * _norm_cdf(d2_val)
    return float(delta), float(gamma), float(theta), float(vega), float(rho)

