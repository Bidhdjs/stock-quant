"""
成交量指标计算测试。

数学原理：
1. 滚动均值/标准差应在样本量足够时输出有限值。
2. RSI 输出应处于 0~100。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.indicators.volume import VolumeIndicatorParams, compute_volume_features


@pytest.mark.mock_only
def test_volume_features_basic():
    length = 60
    base = np.linspace(100, 120, length)
    df = pd.DataFrame(
        {
            "open": base,
            "high": base + 1,
            "low": base - 1,
            "close": base + 0.5,
            "volume": np.linspace(1000, 2000, length),
        }
    )
    params = VolumeIndicatorParams()
    features = compute_volume_features(df, params)
    last = features.iloc[-1]

    assert np.isfinite(last["ma_vol_5"])
    assert np.isfinite(last["ma_vol_20"])
    assert 0 <= last["rsi"] <= 100
    assert isinstance(last["is_3_down"], (bool, np.bool_))
    assert isinstance(last["is_3_up"], (bool, np.bool_))
