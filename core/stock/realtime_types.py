"""
实时行情数据结构。
用于统一不同实时数据源的输出格式。
"""


from dataclasses import dataclass
from typing import Optional

# Front Code X


@dataclass
class RealtimeTick:
    """统一实时行情数据结构。"""
    symbol: str
    name: Optional[str] = None
    timestamp: Optional[str] = None
    last: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    yesterday_close: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None

    bid1_quantity: Optional[float] = None
    bid1_price: Optional[float] = None
    bid2_quantity: Optional[float] = None
    bid2_price: Optional[float] = None
    bid3_quantity: Optional[float] = None
    bid3_price: Optional[float] = None
    bid4_quantity: Optional[float] = None
    bid4_price: Optional[float] = None
    bid5_quantity: Optional[float] = None
    bid5_price: Optional[float] = None

    ask1_quantity: Optional[float] = None
    ask1_price: Optional[float] = None
    ask2_quantity: Optional[float] = None
    ask2_price: Optional[float] = None
    ask3_quantity: Optional[float] = None
    ask3_price: Optional[float] = None
    ask4_quantity: Optional[float] = None
    ask4_price: Optional[float] = None
    ask5_quantity: Optional[float] = None
    ask5_price: Optional[float] = None
