import os
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

from settings import stock_data_root  # 使用项目配置的存储路径


def fetch_tsla(start_date: str, end_date: str) -> pd.DataFrame:
    """
    下载 TSLA 日线数据并计算 EMA12/EMA26（auto_adjust=True）
    返回包含 Close, EMA12, EMA26 的 DataFrame（index = DatetimeIndex）
    """
    df = yf.download("TSLA", start=start_date, end=end_date, progress=False, auto_adjust=True)
    if df.empty:
        return pd.DataFrame()
    df = df[['Close']].copy()
    # 计算 EMA，adjust=False 使用递归形式
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    return df


def save_and_plot(df: pd.DataFrame, out_dir=None):
    if out_dir is None:
        out_dir = stock_data_root / 'yfinance'  # 使用项目配置路径
    os.makedirs(out_dir, exist_ok=True)
    csv_path = out_dir / 'TSLA_yfinance.csv'
    df.to_csv(csv_path, index=True)

    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['Close'], label='Close', linewidth=1)
    plt.plot(df.index, df['EMA12'], label='EMA12', linewidth=1)
    plt.plot(df.index, df['EMA26'], label='EMA26', linewidth=1)
    plt.title('TSLA Close & EMA12/EMA26')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    png_path = out_dir / 'TSLA_EMA.png'
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.show()
    return csv_path, png_path


if __name__ == "__main__":
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    df = fetch_tsla(start, end)
    if df.empty:
        print("未获取到数据")
    else:
        csv_path, img_path = save_and_plot(df)
        print(f"保存 CSV: {csv_path}")
        print(f"保存图片: {img_path}")
