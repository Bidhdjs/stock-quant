"""
期权定价与 Greeks 单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

from core.analysis import options_pricing as op


pytestmark = pytest.mark.mock_only


def test_black_scholes_call_put():
    call, put = op.black_scholes(100, 100, 1.0, 0.05, 0.2)
    assert np.isfinite(call)
    assert np.isfinite(put)


def test_greeks():
    greeks = op.greeks(100, 100, 1.0, 0.05, 0.2)
    assert "delta" in greeks
    assert "gamma" in greeks
    assert "theta" in greeks
    assert "vega" in greeks
    assert "rho" in greeks
