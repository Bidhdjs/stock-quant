"""
实时数据源单元测试
验证 Sina/网易 解析逻辑与输出结构
"""

# Front Code X
import unittest
from unittest.mock import Mock, patch

from core.stock import manager_sina, manager_money


class TestRealtimeSources(unittest.TestCase):
    def test_sina_realtime_parsing(self):
        """验证 Sina 行情解析字段。"""
        sample_fields = [
            'var hq_str_sh601003="TestName',
            "10", "9.5", "10.2", "10.5", "9.3", "10.1", "10.2",
            "1000", "2000",
            "10", "10.1", "20", "10.2", "30", "10.3", "40", "10.4", "50", "10.5",
            "60", "10.6", "70", "10.7", "80", "10.8", "90", "10.9", "100", "11.0",
            "2026-01-30", "15:00:00", '";'
        ]
        text = ",".join(sample_fields)
        response = Mock()
        response.text = text
        response.raise_for_status = Mock()
        with patch("core.stock.manager_sina.requests.get", return_value=response):
            tick = manager_sina.get_realtime_data("sh601003")
        self.assertEqual(tick.symbol, "sh601003")
        self.assertEqual(tick.name, "TestName")
        self.assertEqual(tick.open, 10.0)
        self.assertEqual(tick.last, 10.2)
        self.assertEqual(tick.volume, 1000.0)
        self.assertEqual(tick.amount, 2000.0)
        self.assertEqual(tick.timestamp, "2026-01-30 15:00:00")

    def test_money_realtime_parsing(self):
        """验证网易行情解析字段。"""
        payload = {
            "0601003": {
                "name": "TestName",
                "time": "2026-01-30 15:00:00",
                "open": 10,
                "yestclose": 9.5,
                "price": 10.2,
                "high": 10.5,
                "low": 9.3,
                "bid1": 10.1,
                "ask1": 10.2,
                "volume": 1000,
                "turnover": 2000,
                "bidvol1": 10,
                "bidvol2": 20,
                "bidvol3": 30,
                "bidvol4": 40,
                "bidvol5": 50,
                "askvol1": 60,
                "askvol2": 70,
                "askvol3": 80,
                "askvol4": 90,
                "askvol5": 100,
                "bid2": 10.2,
                "bid3": 10.3,
                "bid4": 10.4,
                "bid5": 10.5,
                "ask2": 10.3,
                "ask3": 10.4,
                "ask4": 10.5,
                "ask5": 10.6,
            }
        }
        text = f"_ntes_quote_callback({payload});"
        response = Mock()
        response.text = text
        response.raise_for_status = Mock()
        with patch("core.stock.manager_money.requests.get", return_value=response):
            tick = manager_money.get_realtime_data("sh601003")
        self.assertEqual(tick.symbol, "sh601003")
        self.assertEqual(tick.name, "TestName")
        self.assertEqual(tick.last, 10.2)
        self.assertEqual(tick.volume, 1000.0)
        self.assertEqual(tick.amount, 2000.0)

    def test_sina_index_parsing(self):
        """验证 Sina 指数解析字段。"""
        text = 'var hq_str_s_sh000001="上证指数,3000,10,0.3,1000,2000";'
        response = Mock()
        response.text = text
        response.raise_for_status = Mock()
        with patch("core.stock.manager_sina.requests.get", return_value=response):
            result = manager_sina.shanghai_component_index()
        self.assertEqual(result["name"], "上证指数")
        self.assertEqual(result["price"], 3000.0)
        self.assertEqual(result["amount"], 2000.0)

    def test_money_index_parsing(self):
        """验证网易指数解析字段。"""
        payload = {"1399001": {"name": "深证成指", "price": 100, "yestclose": 90, "percent": 1.2, "volume": 1000, "turnover": 2000}}
        text = f"_ntes_quote_callback({payload});"
        response = Mock()
        response.text = text
        response.raise_for_status = Mock()
        with patch("core.stock.manager_money.requests.get", return_value=response):
            result = manager_money.shenzhen_component_index()
        self.assertEqual(result["name"], "深证成指")
        self.assertEqual(result["price"], 100.0)
        self.assertEqual(result["change"], 10.0)
        self.assertEqual(result["change_pct"], 1.2)
        self.assertEqual(result["amount"], 2000.0)


if __name__ == "__main__":
    unittest.main()
