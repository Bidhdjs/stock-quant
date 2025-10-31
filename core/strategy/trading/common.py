import datetime

import pandas as pd

from common.logger import create_log

logger = create_log("trade_strategy_common")


class TradeRecordManager:
    def __init__(self):
        self.trade_records = []

    def add_signal_record(self, date, action, signal_type, shares):
        self.trade_records.append(TradeRecord(date, action, signal_type, shares))

    def transform_to_dataframe(self):
        return pd.DataFrame([record.__dict__ for record in self.trade_records])


class TradeRecord:
    def __init__(self, date, action, signal_type, shares):
        if type(date) is datetime.date:
            # 将datetime.date转换为pandas Timestamp
            self.date = pd.Timestamp(date)
            # self.date = date.strftime('%Y-%m-%d')
        elif type(date) is str:
            # 将字符串转换为pandas Timestamp
            self.date = pd.Timestamp(date)
            # self.date = date
        else:
            raise ValueError('date must be datetime.date or str')
        self.action = action
        self.signal_type = signal_type
        self.shares = shares


class AssetRecordManager:
    def __init__(self):
        self.asset_records = []

    def add_asset_record(self, date, total_assets):
        self.asset_records.append(AssetRecord(date, total_assets))

    def transform_to_dataframe(self):
        return pd.DataFrame([record.__dict__ for record in self.asset_records])


class AssetRecord:
    def __init__(self, date, total_assets):
        if type(date) is datetime.date:
            # 将datetime.date转换为pandas Timestamp
            self.date = pd.Timestamp(date)
        elif type(date) is str:
            # 将字符串转换为pandas Timestamp
            self.date = pd.Timestamp(date)
        else:
            raise ValueError('date must be datetime.date or str')
        self.total_assets = total_assets
