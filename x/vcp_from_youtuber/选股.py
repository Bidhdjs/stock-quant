# pip install yfinance pandas numpy matplotlib seaborn

"""
================================================================================
项目名称: Python量化多因子选股器 (Quantitative Multi-Factor Stock Screener)
版本: 2.0 Professional
作者: 领域专家 (Domain Expert Persona)
描述:
    本脚本基于技术分析指标（移动平均线、RSI、成交量）构建综合评分系统。
    它利用 yfinance 获取数据，pandas 进行向量化计算，seaborn 进行可视化。
    核心逻辑包括：
    1. 批量数据获取与复权处理。
    2. 计算 SMA, RSI, Volume Ratio 等关键指标。
    3. 使用百分位排名（Percentile Ranking）进行多因子归一化。
    4. 生成综合评分并输出热力图。
================================================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# ==========================================
# 1. 配置参数与标的池定义
# ==========================================
# 在实际应用中，这里可以是S&P 500成分股列表，或者用户自定义的关注列表
# 为了演示，我们选取了美股科技巨头、金融、消费及工业领域的代表性股票
TICKERS =

# 策略参数设置
LOOKBACK_PERIOD = "2y"  # 获取过去2年的数据以计算长周期均线
SMA_SHORT = 50  # 短期均线窗口
SMA_LONG = 200  # 长期均线窗口
RSI_PERIOD = 14  # RSI计算周期
VOL_WINDOW = 20  # 成交量均值窗口


# ==========================================
# 2. 数据获取模块 (Data Ingestion)
# ==========================================
def fetch_market_data(tickers, period):
    """
    使用 yfinance 批量获取历史行情数据。

    参数:
        tickers (list): 股票代码列表
        period (str): 数据周期 (e.g., '1y', '2y')

    返回:
        pandas.DataFrame: 包含所有股票OHLCV数据的多层索引DataFrame
    """
    print(f"\n[系统状态] 正在启动数据下载引擎...")
    print(f"[系统状态] 目标标的数: {len(tickers)} | 数据周期: {period}")

    try:
        # 使用 group_by='ticker' 方便后续按股票处理
        # auto_adjust=True 确保价格已复权（处理分红和拆股）
        # threads=True 开启多线程加速下载
        data = yf.download(
            tickers,
            period=period,
            group_by='ticker',
            auto_adjust=True,
            progress=True,
            threads=True
        )
        print("[系统状态] 数据下载完成。")
        return data
    except Exception as e:
        print(f"[系统错误] 数据下载失败: {e}")
        return None


# ==========================================
# 3. 指标计算引擎 (Calculation Engine)
# ==========================================
def calculate_technical_indicators(data, tickers):
    """
    遍历每只股票，计算技术指标。
    虽然这里用了循环，但每个股票内部的计算是向量化的。
    """
    screener_results =

    print("\n[系统状态] 开始计算技术指标...")

    for ticker in tickers:
        try:
            # 提取单只股票的数据副本
            # 注意：如果下载失败，某些Ticker可能不在列中，需做异常处理
            if ticker not in data.columns.levels:
                continue

            df = data[ticker].copy()

            # 数据清洗：去除空值
            df.dropna(inplace=True)

            if len(df) < SMA_LONG:
                # 如果上市时间不足200天，无法计算200日均线，跳过
                continue

            # --- A. 趋势指标 (Trend) ---
            # 计算50日和200日简单移动平均线
            df = df['Close'].rolling(window=SMA_SHORT).mean()
            df = df['Close'].rolling(window=SMA_LONG).mean()

            # 获取最新一天的数值
            current_close = df['Close'].iloc[-1]
            sma_50_val = df.iloc[-1]
            sma_200_val = df.iloc[-1]

            # 计算乖离率：价格相对于SMA200的偏离程度
            # 正值表示在均线上方（牛市），负值表示在下方（熊市）
            dist_sma_200_pct = (current_close - sma_200_val) / sma_200_val

            # --- B. 动量指标 (Momentum - RSI) ---
            delta = df['Close'].diff()
            # 分离涨跌
            gain = (delta.where(delta > 0, 0))
            loss = (-delta.where(delta < 0, 0))

            # 使用简单移动平均计算RSI (也可改为指数移动平均 ewm)
            avg_gain = gain.rolling(window=RSI_PERIOD).mean()
            avg_loss = loss.rolling(window=RSI_PERIOD).mean()

            rs = avg_gain / avg_loss
            df = 100 - (100 / (1 + rs))

            current_rsi = df.iloc[-1]

            # --- C. 成交量指标 (Volume) ---
            # 计算量比：今日成交量 / 过去20日平均成交量
            df['Vol_Avg'] = df['Volume'].rolling(window=VOL_WINDOW).mean()
            current_vol = df['Volume'].iloc[-1]
            vol_avg = df['Vol_Avg'].iloc[-1]

            vol_ratio = 0
            if vol_avg > 0:
                vol_ratio = current_vol / vol_avg

            # 将结果存入列表
            screener_results.append({
                'Ticker': ticker,
                'Close': round(current_close, 2),
                'SMA_200': round(sma_200_val, 2),
                'Trend_Signal': dist_sma_200_pct,  # 用于排名的原始数据
                'RSI': round(current_rsi, 2),
                'Vol_Ratio': round(vol_ratio, 2)
            })

        except KeyError:
            print(f"警告: 无法找到 {ticker} 的数据")
        except Exception as e:
            print(f"错误: 处理 {ticker} 时发生异常 - {e}")

    # 转换为DataFrame以便后续处理
    return pd.DataFrame(screener_results)


# ==========================================
# 4. 评分与排名模型 (Scoring Model)
# ==========================================
def apply_ranking_system(df):
    """
    核心逻辑：对各项指标进行百分位排名并加权。
    """
    if df.empty:
        return df

    scored_df = df.copy()

    # --- 归一化处理 (Normalization) ---
    # 使用.rank(pct=True) 将绝对数值转换为 0.0 到 1.0 的百分位

    # 1. 趋势得分：价格在200日均线上方越高越好
    scored_df = scored_df.rank(pct=True)

    # 2. 动量得分：RSI 越高代表动能越强 (注意：超买风险需人工二次确认，这里仅做动量筛选)
    scored_df = scored_df.rank(pct=True)

    # 3. 量能得分：放量越多越好
    scored_df = scored_df.rank(pct=True)

    # --- 综合评分 (Composite Score) ---
    # 权重设定：趋势(40%) + 动量(40%) + 量能(20%)
    scored_df = (
                        (0.4 * scored_df) +
                        (0.4 * scored_df) +
                        (0.2 * scored_df)
                ) * 100  # 转换为 0-100 分制

    # 按总分降序排列
    scored_df = scored_df.sort_values(by='Total_Score', ascending=False)

    return scored_df


# ==========================================
# 5. 可视化模块 (Visualization)
# ==========================================
def visualize_results(df):
    """
    绘制前10名和后5名的热力图
    """
    if df.empty:
        print("无数据可绘图。")
        return

    # 选取用于绘图的列
    plot_data = df.set_index('Ticker')]

    # 筛选头部和尾部
    top_10 = plot_data.head(10)
    bottom_5 = plot_data.tail(5)

    # 合并展示
    display_df = pd.concat([top_10, bottom_5])

    # 创建画布
    plt.figure(figsize=(12, 10))

    # 绘制热力图
    # cmap='RdYlGn': 红(低分)-黄(中)-绿(高分)
    sns.heatmap(display_df, annot=True, fmt=".2f", cmap='RdYlGn', linewidths=0.5)

    plt.title('Python智能选股器 - 多因子评分热力图\n(Top 10 Bullish & Bottom 5 Bearish)', fontsize=16)
    plt.ylabel('股票代码')
    plt.xlabel('因子排名得分 (0-1)')

    print("\n[系统状态] 热力图生成中...")
    plt.show()

    # ==========================================
    # 主程序入口
    # ==========================================
    if __name__ == "__main__":
    # 1. 获取数据
        market_data = fetch_market_data(TICKERS, LOOKBACK_PERIOD)

    if market_data is not None and not market_data.empty:
    # 2. 计算指标
        raw_metrics = calculate_technical_indicators(market_data, TICKERS)

    # 3. 评分排序
    final_report = apply_ranking_system(raw_metrics)

    # 4. 文本输出
    print("\n" + "=" * 50)
    print("       TOP 5 强势潜力股 (BULLISH)       ")
    print("=" * 50)
    # 格式化输出
    print(final_report].head(5).to_string(index=False))

    print("\n" + "=" * 50)
    print("       TOP 5 弱势预警股 (BEARISH)       ")
    print("=" * 50)
    print(final_report].tail(5).to_string(index=False))

    # 5. 图形输出
    visualize_results(final_report)

    else:
    print("[错误] 无法执行筛选，数据获取失败。")