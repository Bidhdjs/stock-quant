"""
时间序列基础预测模型模块。
包含简单移动平均、指数平滑、线性回归预测。

数学原理：
1. 移动平均平滑。
2. 指数平滑衰减权重。
3. 线性回归拟合趋势。
"""


from __future__ import annotations

# Front Code X

# 第一组：Python 标准库
from typing import Iterable, List

# 第二组：第三方库（按字母排序）
import numpy as np

# 第三组：项目内部导入

class ForecastModel:
    """
    预测模型接口（抽象）。
    """

    def fit(self, series: Iterable[float]) -> "ForecastModel":
        raise NotImplementedError

    def predict(self, horizon: int) -> List[float]:
        raise NotImplementedError


class NaiveForecast(ForecastModel):
    """
    Naive 预测：使用最后一个值。
    """

    def __init__(self):
        self._last_value: float | None = None

    def fit(self, series: Iterable[float]) -> "NaiveForecast":
        values = np.asarray(list(series), dtype=float)
        if values.size == 0:
            raise ValueError("series is empty")
        self._last_value = float(values[-1])
        return self

    def predict(self, horizon: int) -> List[float]:
        if self._last_value is None:
            raise ValueError("model is not fitted")
        return [self._last_value] * horizon


class MovingAverageForecast(ForecastModel):
    """
    Moving Average 预测：使用窗口均值。
    """

    def __init__(self, window: int = 5):
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self._mean: float | None = None

    def fit(self, series: Iterable[float]) -> "MovingAverageForecast":
        values = np.asarray(list(series), dtype=float)
        if values.size < self.window:
            raise ValueError("series length must be >= window")
        self._mean = float(values[-self.window :].mean())
        return self

    def predict(self, horizon: int) -> List[float]:
        if self._mean is None:
            raise ValueError("model is not fitted")
        return [self._mean] * horizon

