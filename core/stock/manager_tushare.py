"""
Tushare 数据源管理器。
提供基础数据获取能力（如新股列表、股票基础信息）。
"""


import os

import tushare as ts

from common.logger import create_log

# Front Code X
logger = create_log("manager_tushare")


class TushareManager:
    """
    Tushare 数据管理器

    说明：
    - 通过环境变量 TUSHARE_TOKEN 配置 Token
    """
    def __init__(self, token: str | None = None):
        self.token = token or self._get_token()
        if not self.token:
            logger.warning("Tushare token not found. Set TUSHARE_TOKEN env var.")

    @staticmethod
    def _get_token() -> str | None:
        """从环境变量读取 TUSHARE_TOKEN。"""
        return os.getenv("TUSHARE_TOKEN")

    def _pro(self):
        """构造 Tushare Pro 客户端。"""
        if not self.token:
            raise ValueError("Tushare token is required. Set TUSHARE_TOKEN env var.")
        return ts.pro_api(self.token)

    def new_stock(self):
        """获取新股上市列表。"""
        return self._pro().new_share()

    def stock_list(self):
        """获取股票基础信息列表。"""
        return self._pro().query(
            "stock_basic",
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,list_date",
        )


def new_stock():
    """便捷函数：获取新股上市列表。"""
    return TushareManager().new_stock()


def stock_list():
    """便捷函数：获取股票基础信息列表。"""
    return TushareManager().stock_list()
