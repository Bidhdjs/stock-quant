"""
Tushare 管理器单元测试。
验证 token 检查与 pro_api 调用。
"""

# Front Code X
import os
from unittest.mock import Mock, patch

import pytest

pytest.importorskip("tushare")

from core.stock.manager_tushare import TushareManager, new_stock, stock_list


pytestmark = pytest.mark.mock_only


def _restore_token(old_token):
    if old_token is None:
        os.environ.pop("TUSHARE_TOKEN", None)
    else:
        os.environ["TUSHARE_TOKEN"] = old_token


def test_requires_token():
    """未配置 token 时抛出异常。"""
    old_token = os.getenv("TUSHARE_TOKEN")
    os.environ.pop("TUSHARE_TOKEN", None)
    try:
        manager = TushareManager()
        with pytest.raises(ValueError):
            manager.new_stock()
    finally:
        _restore_token(old_token)


def test_with_token_calls_pro_api():
    """配置 token 后正确调用 pro_api。"""
    old_token = os.getenv("TUSHARE_TOKEN")
    os.environ["TUSHARE_TOKEN"] = "test_token"
    mock_pro = Mock()
    mock_pro.new_share.return_value = "new_share"
    mock_pro.query.return_value = "stock_list"
    try:
        with patch("core.stock.manager_tushare.ts.pro_api", return_value=mock_pro) as pro_api:
            assert new_stock() == "new_share"
            assert stock_list() == "stock_list"
            pro_api.assert_called_with("test_token")
    finally:
        _restore_token(old_token)
