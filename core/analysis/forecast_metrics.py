"""
时间序列预测误差指标模块。
包含 MAE/MSE/RMSE/MAPE/SMAPE。

数学原理：
1. 误差度量：真实值与预测值差异。
"""


from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Iterable

# 第二组：第三方库（按字母排序）
import numpy as np

# 第三组：项目内部导入

def _to_array(values: Iterable[float]) -> np.ndarray:
    """转换为 numpy 数组并去除 NaN。"""
    arr = np.asarray(list(values), dtype=float)
    return arr[~np.isnan(arr)]


def mae(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Mean Absolute Error."""
    yt = _to_array(y_true)
    yp = _to_array(y_pred)
    return float(np.mean(np.abs(yp - yt)))


def mape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Mean Absolute Percentage Error."""
    yt = _to_array(y_true)
    yp = _to_array(y_pred)
    denom = np.where(yt == 0, np.nan, yt)
    return float(np.nanmean(np.abs((yp - yt) / denom)) * 100)


def mse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Mean Squared Error."""
    yt = _to_array(y_true)
    yp = _to_array(y_pred)
    return float(np.mean((yp - yt) ** 2))


def rmse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(mse(y_true, y_pred)))


def nrmse(y_true: Iterable[float], y_pred: Iterable[float], method: str = "mean") -> float:
    """
    Normalized RMSE.

    Args:
        method: "mean" 或 "range"
    """
    yt = _to_array(y_true)
    rms = rmse(yt, y_pred)
    if method == "range":
        denom = np.max(yt) - np.min(yt)
    else:
        denom = np.mean(yt)
    return float(rms / denom) if denom != 0 else np.nan


def wape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """Weighted Absolute Percentage Error."""
    yt = _to_array(y_true)
    yp = _to_array(y_pred)
    denom = np.sum(np.abs(yt))
    return float(np.sum(np.abs(yp - yt)) / denom) if denom != 0 else np.nan


def wmape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """
    Weighted Mean Absolute Percentage Error.
    与 WAPE 形式一致，保留命名差异以便兼容。
    """
    return wape(y_true, y_pred) * 100

