"""
分析模块 smoke 测试（mock-only）。
"""

# Front Code X
import pytest


pytestmark = pytest.mark.mock_only


def test_analysis_modules_importable():
    import core.analysis.performance_metrics  # noqa: F401
    import core.analysis.portfolio  # noqa: F401
    import core.analysis.options_pricing  # noqa: F401
    import core.analysis.forecast_metrics  # noqa: F401
    import core.analysis.forecast_models  # noqa: F401
    import core.analysis.technical_indicators_ext  # noqa: F401
    import core.analysis.candlestick_patterns  # noqa: F401
