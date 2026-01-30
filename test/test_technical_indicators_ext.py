"""
技术指标扩展单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import technical_indicators_ext as ti


pytestmark = pytest.mark.mock_only


def test_accumulation_distribution_line(sample_ohlcv_df):
    result = ti.accumulation_distribution_line(sample_ohlcv_df)
    assert len(result) == len(sample_ohlcv_df)


def test_force_index(sample_ohlcv_df):
    result = ti.force_index(sample_ohlcv_df)
    assert len(result) == len(sample_ohlcv_df)


def test_chaikin_oscillator(sample_ohlcv_df):
    result = ti.chaikin_oscillator(sample_ohlcv_df)
    assert len(result) == len(sample_ohlcv_df)


def test_tsi(sample_ohlcv_df):
    result = ti.tsi(sample_ohlcv_df)
    assert len(result) == len(sample_ohlcv_df)
    assert np.isfinite(result.dropna()).all()


def test_heiken_ashi(sample_ohlcv_df):
    result = ti.heiken_ashi(sample_ohlcv_df)
    assert "HA_Close" in result.columns
    assert len(result) == len(sample_ohlcv_df)


def test_parabolic_sar(sample_ohlcv_df):
    result = ti.parabolic_sar(sample_ohlcv_df["High"], sample_ohlcv_df["Low"])
    assert len(result) == len(sample_ohlcv_df)


def test_vwap(sample_ohlcv_df):
    result = ti.vwap(sample_ohlcv_df)
    assert np.isfinite(result)


def test_wma_wsma(sample_ohlcv_df):
    wma = ti.wma(sample_ohlcv_df["Adj Close"], window=3)
    wsma = ti.wsma(sample_ohlcv_df)
    assert len(wma) == len(sample_ohlcv_df)
    assert len(wsma) == len(sample_ohlcv_df)
