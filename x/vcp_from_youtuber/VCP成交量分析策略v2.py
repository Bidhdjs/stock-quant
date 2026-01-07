# -*- coding: utf-8 -*-
"""
Mark Minervini VCP (波动收缩模式) 成交量枯竭分析脚本
基于视频逻辑：https://www.youtube.com/watch?v=ZfwbKhzjH1M

功能：
1. 获取股票历史数据 (yfinance)
2. 计算三种成交量枯竭指标 (Absolute, Relative, Tightness)
3. 可视化 K 线图与信号点 (mplfinance)
"""



import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import datetime


def fetch_stock_data(ticker, period="2y", interval="1d"):
    """
    获取股票历史数据。

    参数:
        ticker (str): 股票代码 (如 'AAPL', '0700.HK')
        period (str): 数据时长 (默认 '2y' 即两年)
        interval (str): 数据周期 (默认 '1d' 即日线)

    返回:
        pd.DataFrame: 包含 OHLCV 数据的 DataFrame
    """
    try:
        # 使用 yfinance 下载数据
        df = yf.download(ticker, period=period, interval=interval, progress=False)

        # 数据清洗：处理空值
        df.dropna(inplace=True)

        # 确保索引是 Datetime 类型
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        print(f"成功获取 {ticker} 数据，共 {len(df)} 行。")
        return df
    except Exception as e:
        print(f"获取数据失败: {e}")
        return pd.DataFrame()


def identify_vcp_setup(df):
    """
    结合价格趋势和成交量信号，识别潜在的 VCP 买点前兆。
    """
    # 确保已运行过 analyze_vcp_volume
    if 'Vol_Dry_Consecutive' not in df.columns:
        df = analyze_vcp_volume(df)

    # 定义趋势条件:
    # 1. 股价高于 200 日均线 (长期上升趋势)
    # 2. 股价高于 50 日均线 (中期上升趋势) - 可选
    condition_trend = df['Close'] > df['Price_MA200']

    # 定义成交量条件:
    # 连续 3 天成交量低于 MA50
    condition_vol = df

    # 定义价格波动收缩 (Price Contraction) 的简化逻辑:
    # 过去 3 天的振幅 (High - Low) / Close 处于极低水平 (例如小于 3%)
    # 这也是视频中隐含的"Tight"概念
    df = (df['High'] - df['Low']) / df['Close']
    df = df.rolling(window=3).max() < 0.03

    # 综合信号
    df = condition_trend & condition_vol & df

    return df


def analyze_vcp_volume(df, ma_window=50, tight_window=3):
    """
    对 DataFrame 进行 VCP 成交量逻辑分析。

    参数:
        df (pd.DataFrame): 股票数据
        ma_window (int): 移动平均线窗口 (默认 50)
        tight_window (int): 判定连续缩量的窗口 (默认 3天)

    返回:
        pd.DataFrame: 包含分析指标的新 DataFrame
    """
    data = df.copy()

    # ==============================================================================
    # 1. 基础指标计算
    # ==============================================================================
    # 计算 50日成交量均线
    data['Vol_MA50'] = data['Volume'].rolling(window=ma_window).mean()

    # 计算 200日价格均线 (用于趋势过滤，Minervini 强调 VCP 需在上升趋势中)
    data['Price_MA200'] = data['Close'].rolling(window=200).mean()

    # ==============================================================================
    # 2. 视频逻辑一：绝对量收缩 (Absolute Contraction)
    # 逻辑：今日成交量 < 昨日成交量
    # ==============================================================================
    data = data['Volume'] < data['Volume'].shift(1)

    # ==============================================================================
    # 3. 视频逻辑二：相对均线收缩 (Below Average)
    # 逻辑：今日成交量 < 50日成交量均线
    # ==============================================================================
    data = data['Volume'] < data['Vol_MA50']

    # ==============================================================================
    # 4. 视频逻辑三：滚动窗口内的持续紧缩 (Tightness / Dry-Up)
    # 逻辑：在过去 N 天内，每天的成交量都低于 50日均线
    # 技术点：使用 rolling().min() 或 rolling().apply()
    # ==============================================================================
    # 由于 'Vol_Below_MA50' 是布尔值 (True=1, False=0)
    # 我们可以计算滚动窗口内的最小值。如果最小值为 1，说明窗口内全是 1 (即全是 True)
    data = (
        data
        .rolling(window=tight_window)
        .min()
    ).fillna(0).astype(bool)

    # ==============================================================================
    # 5. 增强逻辑：极度枯竭 (Extreme Dry-Up)
    # 逻辑：今日成交量 < 50日均线的 50% (更加严格的筛选)
    # ==============================================================================
    data = data['Volume'] < (data['Vol_MA50'] * 0.5)

    return data

def plot_vcp_analysis(df, ticker_name):
    """
    绘制带有 VCP 信号的 K 线图。
    """
    # 截取最近 6 个月的数据以便观察
    plot_data = df.tail(126).copy()

    # 创建信号标记
    # 我们将在满足 VCP_Signal 的那一天，在最低价下方画一个紫色三角形
    signal_points =[]
    for date, row in plot_data.iterrows():
        if row:
            signal_points.append(row['Low'] * 0.98)  # 标记在最低价下方 2% 处
        else:
            signal_points.append(np.nan)

    apd = [
        mpf.make_addplot(plot_data['Vol_MA50'], panel=1, color='orange', width=1.5),  # 成交量均线
        mpf.make_addplot(signal_points, type='scatter', markersize=100, marker='^', color='purple', panel=0)  # 信号点
    ]

    # 设置绘图风格
    s = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size': 10})

    mpf.plot(
        plot_data,
        type='candle',
        volume=True,
        title=f"\n{ticker_name} - VCP Volume & Tightness Analysis",
        addplot=apd,
        style=s,
        figsize=(12, 8),
        panel_ratios=(2, 1)  # 价格图占 2/3，成交量占 1/3
    )


# 示例调用 (假设环境可联网)
# df = fetch_stock_data('NVDA')
# df_analyzed = identify_vcp_setup(df)
# plot_vcp_analysis(df_analyzed, 'NVIDIA Corp')



# ==========================================
# 4. 主程序入口
# ==========================================
if __name__ == "__main__":
    # 在这里修改你想分析的股票代码
    # 美股直接输入代码 (如 'NVDA', 'AAPL')
    # 港股需加后缀 (如 '0700.HK')
    # 台股需加后缀 (如 '2330.TW')
    target_ticker = 'NVDA'

    # 1. 获取数据
    df = fetch_stock_data(target_ticker)

    if df is not None:
        df_analyzed = identify_vcp_setup(df)
        plot_vcp_analysis(df_analyzed, 'NVIDIA Corp')

        print("\n注意：紫色三角形标记表示'价格紧凑'且'成交量连续3天低于均线'的潜在 VCP 关注点。")