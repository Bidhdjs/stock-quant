"""
技术指标扩展单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import technical_indicators_ext as ti


pytestmark = pytest.mark.mock_only


def test_sma():
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    result = ti.simple_moving_average(data, 3)
    assert np.isfinite(result).all()


def test_ema():
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    result = ti.exponential_moving_average(data, 3)
    assert np.isfinite(result).all()


def test_rsi():
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    result = ti.rsi(data, 3)
    assert np.isfinite(result).all()


def test_macd():
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    result = ti.macd(data, 3, 6, 3)
    assert "macd" in result
    assert "signal" in result
    assert "hist" in result


def test_bollinger_bands():
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    result = ti.bollinger_bands(data, 3)
    assert "upper" in result
    assert "middle" in result
    assert "lower" in result


def test_obv(sample_ohlcv_df):
    result = ti.on_balance_volume(sample_ohlcv_df)
    assert len(result) == len(sample_ohlcv_df)


def test_atr(sample_ohlcv_df):
    result = ti.average_true_range(sample_ohlcv_df, 3)
    assert np.isfinite(result).all()
