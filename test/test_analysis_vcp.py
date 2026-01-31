"""
VCP 指标计算测试。

数学原理：
1. 进度值应在 0~1 之间。
2. 输出结构包含关键字段。
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.indicators.vcp import VCPParams, evaluate_vcp


@pytest.mark.mock_only
def test_vcp_progress_range():
    length = 260
    close = np.linspace(50, 100, length)
    df = pd.DataFrame(
        {
            "close": close,
            "high": close + 1,
            "low": close - 1,
            "volume": np.linspace(1000, 800, length),
        }
    )
    result = evaluate_vcp(df, VCPParams())
    assert 0.0 <= result["progress"] <= 1.0
    assert {"stage2_pass", "is_vcp", "num_contractions", "max_contraction", "min_contraction"}.issubset(
        result.keys()
    )
