"""
vcp_from_youtuber 指标测试。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.migrations.vcp_from_youtuber.rsrs_indicator import RsrsConfig, compute_rsrs
from core.analysis.migrations.vcp_from_youtuber.rsi_signal import compute_rsi_signal


@pytest.mark.mock_only
def test_compute_rsrs_columns():
    periods = 200
    idx = pd.date_range("2024-01-01", periods=periods, freq="D")
    base = np.linspace(10, 20, periods)
    data = pd.DataFrame(
        {
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base,
        },
        index=idx,
    )
    result = compute_rsrs(data, config=RsrsConfig(window=10, z_window=30))
    for col in ["beta", "r2", "zscore", "rsrs", "position"]:
        assert col in result.columns


@pytest.mark.mock_only
def test_compute_rsi_signal():
    periods = 50
    idx = pd.date_range("2024-01-01", periods=periods, freq="D")
    close = np.linspace(100, 110, periods)
    data = pd.DataFrame({"close": close}, index=idx)
    result = compute_rsi_signal(data)
    assert "rsi" in result.columns
    assert "rsi_signal" in result.columns
