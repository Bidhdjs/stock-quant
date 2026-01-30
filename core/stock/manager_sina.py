"""
Sina 实时行情数据源。
提供个股与指数实时行情数据。
"""


import requests

from common.logger import create_log
from core.stock.realtime_types import RealtimeTick

# Front Code X
logger = create_log("manager_sina")

SINA_QUOTE_URL = "http://hq.sinajs.cn/list={symbols}"


def _safe_float(value):
    """安全转换为 float，失败返回 None。"""
    try:
        return float(value)
    except Exception:
        return None


def get_realtime_data(symbol: str, timeout: int = 10) -> RealtimeTick:
    """
    获取 Sina 实时行情

    Args:
        symbol: 股票代码（如 "sh601003"）
        timeout: 请求超时秒数

    Returns:
        RealtimeTick: 统一行情结构
    """
    try:
        response = requests.get(SINA_QUOTE_URL.format(symbols=symbol), timeout=timeout)
        response.raise_for_status()
        text = response.text
        data = text.split(",")
        if len(data) < 30:
            logger.error("Unexpected response for %s: %s", symbol, text[:200])
            return RealtimeTick(symbol=symbol)
        tick = RealtimeTick(symbol=symbol)
        tick.name = data[0].replace('"', "").split("=")[1]
        tick.open = _safe_float(data[1])
        tick.yesterday_close = _safe_float(data[2])
        tick.last = _safe_float(data[3])
        tick.high = _safe_float(data[4])
        tick.low = _safe_float(data[5])
        tick.bid_price = _safe_float(data[6])
        tick.ask_price = _safe_float(data[7])
        tick.volume = _safe_float(data[8])
        tick.amount = _safe_float(data[9])

        tick.bid1_quantity = _safe_float(data[10])
        tick.bid1_price = _safe_float(data[11])
        tick.bid2_quantity = _safe_float(data[12])
        tick.bid2_price = _safe_float(data[13])
        tick.bid3_quantity = _safe_float(data[14])
        tick.bid3_price = _safe_float(data[15])
        tick.bid4_quantity = _safe_float(data[16])
        tick.bid4_price = _safe_float(data[17])
        tick.bid5_quantity = _safe_float(data[18])
        tick.bid5_price = _safe_float(data[19])

        tick.ask1_quantity = _safe_float(data[20])
        tick.ask1_price = _safe_float(data[21])
        tick.ask2_quantity = _safe_float(data[22])
        tick.ask2_price = _safe_float(data[23])
        tick.ask3_quantity = _safe_float(data[24])
        tick.ask3_price = _safe_float(data[25])
        tick.ask4_quantity = _safe_float(data[26])
        tick.ask4_price = _safe_float(data[27])
        tick.ask5_quantity = _safe_float(data[28])
        tick.ask5_price = _safe_float(data[29])

        if symbol.startswith("sh"):
            tick.timestamp = f"{data[-4]} {data[-3]}"
        else:
            tick.timestamp = f"{data[-3]} {data[-2]}"
        return tick
    except Exception as exc:
        logger.error("Fetch sina quote failed for %s: %s", symbol, exc)
        return RealtimeTick(symbol=symbol)


def shenzhen_component_index(timeout: int = 10):
    """
    获取深圳成指实时数据。
    """
    response = requests.get(SINA_QUOTE_URL.format(symbols="s_sz399001"), timeout=timeout)
    response.raise_for_status()
    data = response.text.split(",")
    return {
        "name": data[0].replace('"', "").split("=")[1],
        "price": _safe_float(data[1]),
        "change": _safe_float(data[2]),
        "change_pct": _safe_float(data[3]),
        "volume": _safe_float(data[4]),
        "amount": _safe_float(data[5].split('";')[0]),
    }


def shanghai_component_index(timeout: int = 10):
    """
    获取上证综指实时数据。
    """
    response = requests.get(SINA_QUOTE_URL.format(symbols="s_sh000001"), timeout=timeout)
    response.raise_for_status()
    data = response.text.split(",")
    return {
        "name": data[0].replace('"', "").split("=")[1],
        "price": _safe_float(data[1]),
        "change": _safe_float(data[2]),
        "change_pct": _safe_float(data[3]),
        "volume": _safe_float(data[4]),
        "amount": _safe_float(data[5].split('";')[0]),
    }
