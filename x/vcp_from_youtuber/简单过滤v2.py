import pandas as pd
import numpy as np
import yfinance as yf
import datetime
import time

# 设置显示选项，方便查看 DataFrame
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)


def get_rs_rating(tickers_list, benchmark_ticker="^GSPC"):
    """
    计算股票列表的相对强度评级 (RS Rating) 代理值。
    逻辑：计算过去一年的加权收益率，然后在股票池内进行百分位排序。
    """
    rs_data =  None  #todo 自己维护标普500数据池
    end_date = datetime.datetime.now()
    # 获取一年前的日期，多取几天以确保有数据
    start_date = end_date - datetime.timedelta(days=400)

    print(f"正在计算 {len(tickers_list)} 只股票的相对强度...")

    for ticker in tickers_list:
        try:
            # 下载数据，progress=False 关闭进度条以减少杂乱输出
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            # 确保数据长度足够（至少252个交易日）
            if len(df) < 252:
                continue

            # 获取关键时间点的收盘价（使用Adj Close以包含股息影响）
            # 注意：yfinance 新版下载的数据列名可能是多层索引，需注意处理
            if 'Adj Close' in df.columns:
                series = df['Adj Close']
            else:
                series = df['Close']

            current_price = series.iloc[-1]
            price_3m_ago = series.iloc[-63]  # 约3个月前
            price_6m_ago = series.iloc[-126]  # 约6个月前
            price_9m_ago = series.iloc[-189]  # 约9个月前
            price_12m_ago = series.iloc[-252]  # 约1年前

            # 计算各周期收益率
            ret_3m = (current_price - price_3m_ago) / price_3m_ago
            ret_6m = (current_price - price_6m_ago) / price_6m_ago
            ret_9m = (current_price - price_9m_ago) / price_9m_ago
            ret_12m = (current_price - price_12m_ago) / price_12m_ago

            # 计算加权分数 (IBD 给予近况更高权重)
            # 权重分配：近3个月(40%), 近6个月(20%), 近9个月(20%), 近12个月(20%)
            weighted_score = (0.4 * ret_3m) + (0.2 * ret_6m) + (0.2 * ret_9m) + (0.2 * ret_12m)

            rs_data.append({
                'Ticker': ticker,
                'RS_Score': weighted_score
            })

        except Exception as e:
            # 实际生产中应记录日志
            continue

    # 创建 DataFrame
    df_rs = pd.DataFrame(rs_data)

    if df_rs.empty:
        return pd.DataFrame()

    # 计算百分位排名 (0 到 100)
    df_rs = df_rs.rank(pct=True) * 100
    df_rs = df_rs.round(2)

    # 按照排名降序排列
    return df_rs.sort_values(by='RS_Rating', ascending=False)


def check_minervini_criteria(ticker, rs_rating):
    """
    检查单只股票是否符合 Mark Minervini 的趋势模板八大准则。
    参数:
        ticker: 股票代码
        rs_rating: 预先计算好的 RS 评级
    返回:
        字典: 包含检查结果和关键数据；若不符合返回 None 或包含失败原因。
    """
    try:
        # 下载过去 2 年的数据，以便计算 200 日均线及其趋势
        df = yf.download(ticker, period="2y", progress=False)

        if len(df) < 250:  # 数据不足
            return None

        # 处理列名（兼容性）
        if 'Close' in df.columns:
            close = df['Close']
        elif 'Adj Close' in df.columns:
            close = df['Adj Close']
        else:
            return None

        # --- 计算移动平均线 ---
        sma_50 = close.rolling(window=50).mean()
        sma_150 = close.rolling(window=150).mean()
        sma_200 = close.rolling(window=200).mean()

        # --- 计算 52 周高低点 ---
        # 252 个交易日约为 1 年
        low_52week = close.rolling(window=252).min()
        high_52week = close.rolling(window=252).max()

        # --- 获取最新数据点 ---
        current_close = close.iloc[-1]
        curr_sma_50 = sma_50.iloc[-1]
        curr_sma_150 = sma_150.iloc[-1]
        curr_sma_200 = sma_200.iloc[-1]
        curr_low_52 = low_52week.iloc[-1]
        curr_high_52 = high_52week.iloc[-1]

        # --- 200日均线趋势检测 ---
        # 检查 20 日前（约1个月）的 200SMA
        sma_200_1mo_ago = sma_200.iloc[-22]
        trending_up_200 = curr_sma_200 > sma_200_1mo_ago

        # --- 准则判定 ---

        # 准则 1: 股价 > 150SMA 和 200SMA
        c1 = current_close > curr_sma_150 and current_close > curr_sma_200

        # 准则 2: 150SMA > 200SMA
        c2 = curr_sma_150 > curr_sma_200

        # 准则 3: 200SMA 处于上升趋势
        c3 = trending_up_200

        # 准则 4: 50SMA > 150SMA 和 200SMA
        c4 = curr_sma_50 > curr_sma_150 and curr_sma_50 > curr_sma_200

        # 准则 5: 股价 > 50SMA
        c5 = current_close > curr_sma_50

        # 准则 6: 股价高于 52 周低点 30%
        c6 = current_close >= (1.30 * curr_low_52)

        # 准则 7: 股价处于 52 周高点的 25% 范围内 (即 > 75% 的高点价格)
        c7 = current_close >= (0.75 * curr_high_52)

        # 准则 8: RS Rating >= 70
        c8 = rs_rating >= 70

        # 综合判断
        is_stage_2 = c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8

        if is_stage_2:
            return {
                'Ticker': ticker,
                'Price': round(current_close, 2),
                'RS_Rating': rs_rating,
                'SMA_50': round(curr_sma_50, 2),
                'SMA_150': round(curr_sma_150, 2),
                'SMA_200': round(curr_sma_200, 2),
                '52W_High': round(curr_high_52, 2),
                'Pct_off_High': round((current_close / curr_high_52 - 1) * 100, 2)
            }
        else:
            return None

    except Exception as e:
        print(f"Error checking {ticker}: {e}")
        return None


def run_screener(tickers_list):
    """
    主执行函数
    """
    # 1. 首先计算 RS Rating，因为这需要全市场数据且可以作为第一道过滤器
    df_rs = get_rs_rating(tickers_list)

    if df_rs.empty:
        print("无数据或计算失败。")
        return pd.DataFrame()

    # 只保留 RS Rating >= 70 的股票进入下一轮，减少网络请求
    # 注意：如果市场极度低迷，可能没有任何股票 RS > 70，此时应灵活调整阈值
    potential_candidates = [df_rs >= 70].tolist()  #todo 取大于70

    print(f"通过 RS 筛选的股票数量: {len(potential_candidates)}")

    final_results =[]

    # 2. 逐个检查技术形态
    for ticker in potential_candidates:
    # 获取该股票的 RS 值
        rs_val = df_rs.loc == [ticker, 'RS_Rating'].values

    result = check_minervini_criteria(ticker, rs_val)
    if result:
        final_results.append(result)
    print(f"发现符合条件股票: {ticker}")

    # 3. 输出结果
    return pd.DataFrame(final_results)


# --- 示例运行 ---
# 在实际使用中，请替换为完整的股票代码列表，例如从 CSV 读取
sample_tickers = []
# 真正的列表应该包含几百上千只股票才能体现 RS 的意义

# df_winners = run_screener(sample_tickers)
# print(df_winners)