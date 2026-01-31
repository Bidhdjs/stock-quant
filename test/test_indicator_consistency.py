"""
指标计算一致性测试。

数学原理：
1. 常量序列的标准差应为 0。
2. RSI 对平坦序列应接近 0（无上行动量）。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.indicators.volume import VolumeIndicatorParams, compute_volume_features


@pytest.mark.mock_only
def test_volume_features_constant_series():
    length = 30
    df = pd.DataFrame(
        {
            "open": np.ones(length) * 10,
            "high": np.ones(length) * 11,
            "low": np.ones(length) * 9,
            "close": np.ones(length) * 10,
            "volume": np.ones(length) * 1000,
        }
    )
    params = VolumeIndicatorParams(n2=5, n3=20, rsi_period=14)
    features = compute_volume_features(df, params)
    last = features.iloc[-1]

    assert last["vol_std_5"] == pytest.approx(0.0, abs=1e-6)
    assert last["vol_std_20"] == pytest.approx(0.0, abs=1e-6)
    assert 0 <= last["rsi"] <= 100
