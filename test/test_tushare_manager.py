"""
Tushare 管理器单元测试
验证 token 检查与 pro_api 调用
"""

# Front Code X
import os
import unittest
from unittest.mock import Mock, patch

from core.stock.manager_tushare import TushareManager, new_stock, stock_list


class TestTushareManager(unittest.TestCase):
    def setUp(self):
        """备份环境变量。"""
        self._old_token = os.getenv("TUSHARE_TOKEN")

    def tearDown(self):
        """恢复环境变量。"""
        if self._old_token is None:
            os.environ.pop("TUSHARE_TOKEN", None)
        else:
            os.environ["TUSHARE_TOKEN"] = self._old_token

    def test_requires_token(self):
        """未配置 token 时抛出异常。"""
        os.environ.pop("TUSHARE_TOKEN", None)
        manager = TushareManager()
        with self.assertRaises(ValueError):
            manager.new_stock()

    def test_with_token_calls_pro_api(self):
        """配置 token 后正确调用 pro_api。"""
        os.environ["TUSHARE_TOKEN"] = "test_token"
        mock_pro = Mock()
        mock_pro.new_share.return_value = "new_share"
        mock_pro.query.return_value = "stock_list"
        with patch("core.stock.manager_tushare.ts.pro_api", return_value=mock_pro) as pro_api:
            self.assertEqual(new_stock(), "new_share")
            self.assertEqual(stock_list(), "stock_list")
            pro_api.assert_called_with("test_token")


if __name__ == "__main__":
    unittest.main()
