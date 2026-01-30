"""
Pytest 公共配置与 fixture。
"""

# Front Code X

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_prices():
    return pd.Series([100, 102, 101, 105, 103], name="price")


@pytest.fixture
def sample_returns_df():
    return pd.DataFrame(
        {
            "A": [0.01, -0.005, 0.02, -0.01],
            "B": [0.015, 0.0, -0.01, 0.005],
            "C": [0.0, 0.01, 0.005, -0.002],
        }
    )


@pytest.fixture
def sample_ohlcv_df():
    return pd.DataFrame(
        {
            "Open": [10, 11, 12, 11],
            "High": [11, 12, 13, 12],
            "Low": [9, 10, 11, 10],
            "Close": [10.5, 11.5, 12.0, 11.2],
            "Adj Close": [10.5, 11.5, 12.0, 11.2],
            "Volume": [100, 120, 140, 110],
        }
    )


@pytest.fixture(autouse=True)
def fixed_seed():
    np.random.seed(1)
    yield
