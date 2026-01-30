"""
期权定价与 Greeks 单元测试（mock-only）。
"""

# Front Code X
import numpy as np
import pytest

pytest.importorskip("scipy")

from core.analysis import options_pricing as op


pytestmark = pytest.mark.mock_only


def test_black_scholes_call_put():
    call = op.black_scholes_call(100, 100, 0.05, 0.2, 1.0)
    put = op.black_scholes_put(100, 100, 0.05, 0.2, 1.0)
    assert np.isfinite(call)
    assert np.isfinite(put)


def test_greeks():
    delta, gamma, theta, vega, rho = op.greeks(100, 100, 0.05, 0.2, 1.0)
    assert np.isfinite(delta)
    assert np.isfinite(gamma)
    assert np.isfinite(theta)
    assert np.isfinite(vega)
    assert np.isfinite(rho)
