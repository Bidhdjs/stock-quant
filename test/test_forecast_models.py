"""
时间序列预测模型单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import forecast_models as fm


pytestmark = pytest.mark.mock_only


def test_naive_forecast():
    series = np.array([1, 2, 3, 4, 5], dtype=float)
    model = fm.NaiveForecast().fit(series)
    result = model.predict(2)
    assert result == [5.0, 5.0]


def test_moving_average_forecast():
    series = np.array([1, 2, 3, 4, 5], dtype=float)
    model = fm.MovingAverageForecast(window=3).fit(series)
    result = model.predict(2)
    assert len(result) == 2
    assert np.isfinite(result).all()


def test_moving_average_value():
    series = np.array([1, 2, 3, 4, 5], dtype=float)
    model = fm.MovingAverageForecast(window=3).fit(series)
    result = model.predict(1)
    assert result[0] == np.mean([3.0, 4.0, 5.0])
