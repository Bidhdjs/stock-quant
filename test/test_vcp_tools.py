"""
VCP 工具集测试。

数学原理：
1. 确保滚动均线与信号列能正常生成。
2. 使用模拟数据验证输出列一致性。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.migrations.vcp_tools import VcpConfig, build_vcp_signal_frame


@pytest.mark.mock_only
def test_build_vcp_signal_frame_columns():
    periods = 260
    dates = pd.date_range("2024-01-01", periods=periods, freq="D")
    base = np.linspace(100, 130, periods)
    data = pd.DataFrame(
        {
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base,
            "volume": np.linspace(1_000_000, 800_000, periods),
        },
        index=dates,
    )

    config = VcpConfig(ma_window=10, tight_window=3, price_ma_window=20)
    result = build_vcp_signal_frame(data, config=config)

    expected_cols = {
        "vol_ma",
        "price_ma",
        "vol_below_prev",
        "vol_below_ma",
        "vol_dry_consecutive",
        "vol_extreme_dry",
        "price_tight",
        "vcp_signal",
    }
    assert expected_cols.issubset(result.columns)
    assert result["vcp_signal"].dtype == bool
