"""
网易实时行情数据源
提供个股与指数实时行情数据
"""

import json

import requests

from common.logger import create_log
from core.stock.realtime_types import RealtimeTick

# Front Code X
logger = create_log("manager_money")

MONEY_QUOTE_URL = "http://api.money.126.net/data/feed/{code},money.api"


def _safe_float(value):
    """安全转换为 float，失败返回 None。"""
    try:
        return float(value)
    except Exception:
        return None


def _symbol_to_code(symbol: str) -> str:
    """转换股票代码为网易接口使用的 code。"""
    if symbol.startswith("sh"):
        return f"0{symbol.lstrip('sh')}"
    if symbol.startswith("sz"):
        return f"1{symbol.lstrip('sz')}"
    return symbol


def _safe_change(price, yestclose):
    """安全计算涨跌额，无法计算则返回 None。"""
    price_value = _safe_float(price)
    yestclose_value = _safe_float(yestclose)
    if price_value is None or yestclose_value is None:
        return None
    return price_value - yestclose_value


def get_realtime_data(symbol: str, timeout: int = 10) -> RealtimeTick:
    """
    获取网易实时行情

    Args:
        symbol: 股票代码（如 "sh601003"）
        timeout: 请求超时秒数

    Returns:
        RealtimeTick: 统一行情结构
    """
    try:
        code = _symbol_to_code(symbol)
        response = requests.get(MONEY_QUOTE_URL.format(code=code), timeout=timeout)
        response.raise_for_status()
        text = response.text.lstrip("_ntes_quote_callback(").rstrip(");")
        data = json.loads(text)
        payload = data.get(code, {})
        tick = RealtimeTick(symbol=symbol)
        tick.name = payload.get("name")
        tick.timestamp = payload.get("time")
        tick.open = _safe_float(payload.get("open"))
        tick.yesterday_close = _safe_float(payload.get("yestclose"))
        tick.last = _safe_float(payload.get("price"))
        tick.high = _safe_float(payload.get("high"))
        tick.low = _safe_float(payload.get("low"))
        tick.bid_price = _safe_float(payload.get("bid1"))
        tick.ask_price = _safe_float(payload.get("ask1"))
        tick.volume = _safe_float(payload.get("volume"))
        tick.amount = _safe_float(payload.get("turnover"))

        tick.bid1_quantity = _safe_float(payload.get("bidvol1"))
        tick.bid1_price = _safe_float(payload.get("bid1"))
        tick.bid2_quantity = _safe_float(payload.get("bidvol2"))
        tick.bid2_price = _safe_float(payload.get("bid2"))
        tick.bid3_quantity = _safe_float(payload.get("bidvol3"))
        tick.bid3_price = _safe_float(payload.get("bid3"))
        tick.bid4_quantity = _safe_float(payload.get("bidvol4"))
        tick.bid4_price = _safe_float(payload.get("bid4"))
        tick.bid5_quantity = _safe_float(payload.get("bidvol5"))
        tick.bid5_price = _safe_float(payload.get("bid5"))

        tick.ask1_quantity = _safe_float(payload.get("askvol1"))
        tick.ask1_price = _safe_float(payload.get("ask1"))
        tick.ask2_quantity = _safe_float(payload.get("askvol2"))
        tick.ask2_price = _safe_float(payload.get("ask2"))
        tick.ask3_quantity = _safe_float(payload.get("askvol3"))
        tick.ask3_price = _safe_float(payload.get("ask3"))
        tick.ask4_quantity = _safe_float(payload.get("askvol4"))
        tick.ask4_price = _safe_float(payload.get("ask4"))
        tick.ask5_quantity = _safe_float(payload.get("askvol5"))
        tick.ask5_price = _safe_float(payload.get("ask5"))
        return tick
    except Exception as exc:
        logger.error("Fetch money.126 quote failed for %s: %s", symbol, exc)
        return RealtimeTick(symbol=symbol)


def shenzhen_component_index(timeout: int = 10):
    """获取深圳成指实时数据。"""
    response = requests.get(MONEY_QUOTE_URL.format(code="1399001"), timeout=timeout)
    response.raise_for_status()
    text = response.text.lstrip("_ntes_quote_callback(").rstrip(");")
    data = json.loads(text).get("1399001", {})
    return {
        "name": data.get("name"),
        "price": _safe_float(data.get("price")),
        "change": _safe_change(data.get("price"), data.get("yestclose")),
        "change_pct": _safe_float(data.get("percent")),
        "volume": _safe_float(data.get("volume")),
        "amount": _safe_float(data.get("turnover")),
    }


def shanghai_component_index(timeout: int = 10):
    """获取上证综指实时数据。"""
    response = requests.get(MONEY_QUOTE_URL.format(code="0000001"), timeout=timeout)
    response.raise_for_status()
    text = response.text.lstrip("_ntes_quote_callback(").rstrip(");")
    data = json.loads(text).get("0000001", {})
    return {
        "name": data.get("name"),
        "price": _safe_float(data.get("price")),
        "change": _safe_change(data.get("price"), data.get("yestclose")),
        "change_pct": _safe_float(data.get("percent")),
        "volume": _safe_float(data.get("volume")),
        "amount": _safe_float(data.get("turnover")),
    }
