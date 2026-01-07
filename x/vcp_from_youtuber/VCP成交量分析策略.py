import yfinance as yf
import pandas as pd
import numpy as np


# 1. 获取数据函数
def get_data(ticker_symbol):
    """
    使用 yfinance 获取历史数据
    """
    print(f"正在下载 {ticker_symbol} 的数据...")
    # 获取最大周期的历史数据
    stock = yf.Ticker(ticker_symbol)
    df = stock.history(period="max")
    return df


# 2. 计算未来回报函数 (用于回测)
def get_future_return(df):
    """
    计算未来 3天, 7天, 10天 的股价回报率
    """
    # shift(-3) 表示将未来的数据向上平移，从而在当前行看到未来的价格
    # pct_change 计算变化百分比
    df['3day_return'] = df['Close'].pct_change(periods=3).shift(-3)
    df['7day_return'] = df['Close'].pct_change(periods=7).shift(-7)
    df['10day_return'] = df['Close'].pct_change(periods=10).shift(-10)
    return df


# 3. 三种成交量收缩分析模型

def analyze_volume_contraction(df, method=1, x_days=7, y_param=0.3, z_threshold=-1.5):
    """
    根据不同方法分析成交量收缩
    :param df: 数据框
    :param method: 1, 2, 或 3 (对应视频中的三种方法)
    :param x_days: 时间窗口 (X日)
    :param y_param: 百分比参数 (Y%)，用于方法1和3
    :param z_threshold: Z-score 阈值，用于方法2
    """
    df = df.copy()

    # 预先计算未来回报，方便查看结果
    df = get_future_return(df)

    if method == 1:
        # 方法一：低于过去 X 日平均成交量 Y%
        # 逻辑：Current Volume < Moving Average(X) * (1 - Y)

        col_name = f'Vol_MA_{x_days}'
        df[col_name] = df['Volume'].rolling(window=x_days).mean()

        # 筛选条件
        condition = df['Volume'] < (df[col_name] * (1 - y_param))

        print(f"--- 方法一分析 (低于 {x_days} 日均量 {y_param * 100}%) ---")

    elif method == 2:
        # 方法二：标准分 (Z-score) 分析
        # 逻辑：(Current Volume - Mean) / Std Dev < Threshold

        # 计算滚动平均值和滚动标准差
        rolling_mean = df['Volume'].rolling(window=x_days).mean()
        rolling_std = df['Volume'].rolling(window=x_days).std()

        # 计算 Z-score
        df['Vol_Zscore'] = (df['Volume'] - rolling_mean) / rolling_std

        # 筛选条件
        condition = df['Vol_Zscore'] < z_threshold

        print(f"--- 方法二分析 (Z-score < {z_threshold}, 窗口 {x_days} 日) ---")

    elif method == 3:
        # 方法三：较过去 X 日最高成交量下跌 Y%
        # 逻辑：Current Volume < Max_Volume_in_last_X_days * (1 - Y)

        col_name = f'MaxVol_{x_days}'
        df[col_name] = df['Volume'].rolling(window=x_days).max()

        # 筛选条件
        condition = df['Volume'] < (df[col_name] * (1 - y_param))

        print(f"--- 方法三分析 (较 {x_days} 日最高量下跌 {y_param * 100}%) ---")

    else:
        print("无效的方法编号")
        return None

    # 提取满足条件的行
    result_df = df[condition].dropna()

    # 输出统计结果 (Describe)
    print(f"满足条件的天数: {len(result_df)}")
    if len(result_df) > 0:
        print("满足条件后的未来回报统计 (3日, 7日, 10日):")
        print(result_df[['3day_return', '7day_return', '10day_return']].describe())
    else:
        print("未找到满足条件的数据。")

    return result_df


# --- 主程序运行示例 ---

if __name__ == "__main__":
    # 设定股票代码 (例如 Google)
    ticker = "GOOG"

    try:
        # 1. 下载数据
        df = get_data(ticker)

        # 2. 运行三种不同的分析方法

        # 方法一示例：成交量低于过去 7 天平均值的 30%
        analyze_volume_contraction(df, method=1, x_days=7, y_param=0.3)
        print("\n" + "=" * 30 + "\n")

        # 方法二示例：Z-score 低于 -1.5 (统计学上的极低量)，参考过去 30 天
        analyze_volume_contraction(df, method=2, x_days=30, z_threshold=-1.5)
        print("\n" + "=" * 30 + "\n")

        # 方法三示例：成交量较过去 7 天的最高点下跌 20%
        analyze_volume_contraction(df, method=3, x_days=7, y_param=0.2)

    except Exception as e:
        print(f"发生错误: {e}")
        print("请确保已安装 yfinance: pip install yfinance")