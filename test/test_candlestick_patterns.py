"""
蜡烛图形态检测单元测试（mock-only）。
"""

# Front Code X
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from core.analysis import candlestick_patterns as cp


pytestmark = pytest.mark.mock_only


def test_detect_patterns_returns_expected_keys(monkeypatch, capsys):
    fake_talib = Mock()
    fake_talib.CDLDOJI.return_value = np.array([1, 0])
    fake_talib.CDLMORNINGSTAR.return_value = np.array([0, 1])
    fake_talib.CDLDARKCLOUDCOVER.return_value = np.array([0, 0])
    fake_talib.CDLABANDONEDBABY.return_value = np.array([0, 0])
    fake_talib.CDLBELTHOLD.return_value = np.array([1, -1])

    monkeypatch.setattr(cp, "_require_talib", lambda: fake_talib)

    df = pd.DataFrame(
        {
            "Open": [1.0, 1.1],
            "High": [1.2, 1.3],
            "Low": [0.9, 1.0],
            "Close": [1.05, 1.2],
        }
    )

    result = cp.detect_patterns(df)
    with capsys.disabled():
        print(result)
    assert set(result.keys()) == {
        "Doji",
        "MorningStar",
        "DarkCloudCover",
        "AbandonedBaby",
        "BeltHold",
    }
    for series in result.values():
        assert len(series) == len(df)
