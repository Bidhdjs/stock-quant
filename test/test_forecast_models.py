"""
时间序列预测模型单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import forecast_models as fm


pytestmark = pytest.mark.mock_only


def test_simple_moving_average():
    series = np.array([1, 2, 3, 4, 5], dtype=float)
    result = fm.simple_moving_average(series, window=3)
    assert np.isfinite(result).all()


def test_exponential_smoothing():
    series = np.array([1, 2, 3, 4, 5], dtype=float)
    result = fm.exponential_smoothing(series, alpha=0.3)
    assert np.isfinite(result).all()


def test_linear_regression_forecast():
    series = np.array([1, 2, 3, 4, 5], dtype=float)
    result = fm.linear_regression_forecast(series, steps=2)
    assert len(result) == 2
