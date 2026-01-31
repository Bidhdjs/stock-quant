"""
信号指标自动发现测试。

数学原理：
1. 指标类应被自动注册到管理器。
"""

import pytest

from core.strategy.indicator_manager import IndicatorManager


@pytest.mark.mock_only
def test_indicator_manager_discovers_volume_and_pattern_indicators():
    manager = IndicatorManager()
    names = manager.get_indicator_names()
    assert "EnhancedVolumeIndicator" in names
    assert "SingleVolumeIndicator" in names
    assert "VCPIndicator" in names
