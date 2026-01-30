"""
时间序列误差指标单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import forecast_metrics as fm


pytestmark = pytest.mark.mock_only


def test_mae():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 1.9, 3.2])
    value = fm.mae(y_true, y_pred)
    assert np.isfinite(value)


def test_mse():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 1.9, 3.2])
    value = fm.mse(y_true, y_pred)
    assert np.isfinite(value)


def test_rmse():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 1.9, 3.2])
    value = fm.rmse(y_true, y_pred)
    assert np.isfinite(value)


def test_mape():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 1.9, 3.2])
    value = fm.mape(y_true, y_pred)
    assert np.isfinite(value)


def test_smape():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.1, 1.9, 3.2])
    value = fm.smape(y_true, y_pred)
    assert np.isfinite(value)
