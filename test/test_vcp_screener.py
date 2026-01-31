"""
VCP Screener 逻辑测试。

数学原理：
1. 使用合成价格序列验证极值识别与收缩计算不报错。
2. 验证筛选函数返回结构正确。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.migrations.vcp_screener import screen_universe, vcp, trend_template


@pytest.mark.mock_only
def test_vcp_functions_run():
    periods = 300
    idx = pd.date_range("2024-01-01", periods=periods, freq="D")
    base = np.linspace(100, 130, periods)
    wave = np.sin(np.linspace(0, 12 * np.pi, periods))
    close = base + wave
    data = pd.DataFrame(
        {
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.linspace(1_200_000, 800_000, periods),
        },
        index=idx,
    )

    trend = trend_template(data, df_spx=None)
    assert "Pass" in trend.columns

    result = vcp(data)
    assert isinstance(result, tuple)
    assert len(result) == 5


@pytest.mark.mock_only
def test_screen_universe_basic():
    periods = 260
    idx = pd.date_range("2023-01-01", periods=periods, freq="D")
    close = np.linspace(50, 120, periods)
    data = pd.DataFrame(
        {
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.linspace(2_000_000, 1_500_000, periods),
        },
        index=idx,
    )
    results = screen_universe({"TEST": data}, rs_list=["TEST"])
    assert isinstance(results, pd.DataFrame)
    assert set(results.columns).issuperset(
        {
            "Ticker",
            "Num_of_contraction",
            "Max_contraction",
            "Min_contraction",
            "Weeks_of_contraction",
            "RS_rating",
        }
    )
