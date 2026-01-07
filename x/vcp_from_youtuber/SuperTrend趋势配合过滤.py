import pandas_ta as ta

# 计算ATR
df = ta.atr(df['high'], df['low'], df['close'], length=10)

# 计算基准带
df['basic_ub'] = (df['high'] + df['low']) / 2 + (3 * df)
df['basic_lb'] = (df['high'] + df['low']) / 2 - (3 * df)

# 迭代逻辑实现SuperTrend (伪代码逻辑)
# 这一步至关重要，因为pandas的向量化操作难以直接处理递归逻辑
# 必须编写循环或使用numba加速来确定Final Bands

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import datetime


# ==========================================
# 1. 策略参数配置
# ==========================================
class StrategyConfig:
    # Supertrend 参数
    # 常用搭配：(10, 3) 适合波段，(10, 2) 适合激进
    ATR_PERIOD = 10
    ATR_MULTIPLIER = 3.0

    # VCP 识别参数
    LOOKBACK_DAYS = 150  # 扫描过去多少天的形态
    MIN_PRICE = 5.0  # 过滤低价股
    MIN_AVG_VOLUME = 200000  # 流动性过滤

    # 波动率收缩阈值
    CONTRACTION_TOLERANCE = 0.85  # 后一波段振幅需小于前一波段的 85%
    TIGHTNESS_THRESHOLD = 0.6  # 近期波动率需小于长期波动率的 60%
    VOLUME_DRYUP_RATIO = 0.75  # 近期成交量需小于均量的 75%


# ==========================================
# 2. 数据获取模块
# ==========================================
def fetch_stock_data(ticker, start_date, end_date):
    """
    从 Yahoo Finance 获取历史数据，并处理 MultiIndex 问题
    """
    try:
        # progress=False 禁用进度条以保持输出整洁
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df.empty:
            return None

        # 兼容 yfinance 新版本的 MultiIndex 列名 (如: ('Close', 'AAPL') -> 'Close')
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 确保包含必要的列
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            return None

        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


# ==========================================
# 3. 指标计算模块 (Supertrend & Moving Averages)
# ==========================================
def calculate_indicators(df, config):
    """
    计算技术指标：Supertrend, SMA, ATR, Relative Volume
    """
    df = df.copy()

    # 3.1 计算 Supertrend
    # pandas_ta 的 supertrend 函数返回三列：值、方向(1/-1)、及其他
    # 动态获取列名以避免硬编码错误
    st = df.ta.supertrend(length=config.ATR_PERIOD, multiplier=config.ATR_MULTIPLIER)

    if st is None:
        return df

    # 重命名列以方便后续调用
    # pandas_ta 默认列名格式示例: SUPERT_10_3.0, SUPERTd_10_3.0
    st_val_col = f"SUPERT_{config.ATR_PERIOD}_{config.ATR_MULTIPLIER}"
    st_dir_col = f"SUPERTd_{config.ATR_PERIOD}_{config.ATR_MULTIPLIER}"

    df = st[st_val_col]
    df = st[st_dir_col]  # 1 为看涨(绿), -1 为看跌(红)

    # 3.2 计算 趋势均线 (Stage 2 过滤)
    df = ta.sma(df['Close'], length=50)
    df = ta.sma(df['Close'], length=150)
    df = ta.sma(df['Close'], length=200)

    # 3.3 计算 波动率参考 (ATR)
    df = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df = ta.atr(df['High'], df['Low'], df['Close'], length=5)  # 短期波动

    # 3.4 计算 成交量均线
    df = ta.sma(df['Volume'], length=50)

    return df


# ==========================================
# 4. 核心逻辑：VCP形态识别算法
# ==========================================
def check_vcp_setup(df, config):
    """
    分析数据帧，判断是否满足 VCP + Supertrend 的双重条件
    返回: (Boolean, String_Reason)
    """
    # 确保数据长度足够
    if len(df) < 200:
        return False, "数据不足"

    curr = df.iloc[-1]

    # ---------------------------
    # 步骤 1: 趋势过滤 (Supertrend & SMA)
    # ---------------------------

    # Supertrend 必须为看涨 (1)
    if curr != 1:
        return False, "Supertrend为看跌状态"

    # 价格需位于 200日均线之上 (米勒维尼 Stage 2 基础)
    if not (curr['Close'] > curr):
        return False, "价格低于200日均线"

    # ---------------------------
    # 步骤 2: VCP 结构特征 (波动率收缩)
    # ---------------------------

    # 算法逻辑：将最近60天分为两个30天窗口，比较其最高价与最低价的波幅
    # 这是一种简化的VCP检测，实际应用中可用更复杂的波峰波谷识别算法

    window_long = 60
    window_short = 30

    # 过去60-30天的波幅 (Swing 1)
    period_1 = df.iloc[-window_long:-window_short]
    high_1 = period_1['High'].max()
    low_1 = period_1['Low'].min()
    volatility_1 = (high_1 - low_1) / low_1

    # 过去30-0天的波幅 (Swing 2)
    period_2 = df.iloc[-window_short:]
    high_2 = period_2['High'].max()
    low_2 = period_2['Low'].min()
    volatility_2 = (high_2 - low_2) / low_2

    # 检查波动率是否收缩 (后一波段波幅 < 前一波段 * 容忍度)
    if volatility_2 >= (volatility_1 * config.CONTRACTION_TOLERANCE):
        return False, f"波动率未收缩: {volatility_1:.2%} -> {volatility_2:.2%}"

    # ---------------------------
    # 步骤 3: 紧凑性 (Tightness) 与 缩量 (Dry Up)
    # ---------------------------

    # 检查最近5天的紧凑程度
    recent_5 = df.iloc[-5:]
    avg_range_5 = (recent_5['High'] - recent_5['Low']).mean()

    # 如果最近5天平均波幅 < 0.6 * 14天ATR，视为"紧凑"
    if avg_range_5 > (curr * 0.8):  # 放宽一点便于演示
        return False, "近期价格不够紧凑 (Not Tight)"

    # 检查成交量枯竭
    # 最近5天平均成交量 < 50日均量的 75%
    recent_vol_avg = recent_5['Volume'].mean()
    if recent_vol_avg > (curr * config.VOLUME_DRYUP_RATIO):
        return False, "成交量未枯竭"

    # ---------------------------
    # 步骤 4: 枢轴点位置 (Pivot Proximity)
    # ---------------------------

    # 收盘价应接近近期高点 (准备突破)
    dist_to_high = (high_2 - curr['Close']) / curr['Close']
    if dist_to_high > 0.05:  # 距离高点超过5%，可能还在调整底部
        return False, "距离突破点过远"

    return True, "VCP Setup Detected"


# ==========================================
# 5. 主程序：批量扫描
# ==========================================
def run_scanner(ticker_list):
    print(f"开始扫描 {len(ticker_list)} 只股票...")
    print(f"策略: Supertrend({StrategyConfig.ATR_PERIOD}, {StrategyConfig.ATR_MULTIPLIER}) + VCP")

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=365)  # 获取1年数据

    results =

    for ticker in ticker_list:
        # 1. 获取数据
        df = fetch_stock_data(ticker, start_date, end_date)
        if df is None: continue

        # 2. 基础过滤 (价格/流动性)
        if df['Close'].iloc[-1] < StrategyConfig.MIN_PRICE: continue
        if df['Volume'].iloc[-1] * df['Close'].iloc[-1] < 1000000: continue  # 简单成交额过滤

        # 3. 计算指标
        df = calculate_indicators(df, StrategyConfig)

        # 4. 检查策略逻辑
        is_match, reason = check_vcp_setup(df, StrategyConfig)

        if is_match:
            print(f"[发现目标] {ticker}: {reason}")
            results.append({
                'Ticker': ticker,
                'Close': df['Close'].iloc[-1],
                'Supertrend': df.iloc[-1],
                'ATR': df.iloc[-1],
                'Volume_Ratio': df['Volume'].iloc[-1] / df.iloc[-1]
            })

    # 输出结果表格
    if results:
        res_df = pd.DataFrame(results)
        print("\n=== 扫描结果 ===")
        print(res_df.to_markdown(index=False))
    else:
        print("\n未发现符合条件的标的。")


# 示例运行 (需联网)
if __name__ == "__main__":
    # 测试列表 (包含科技巨头和典型成长股)
    sample_tickers =
    run_scanner(sample_tickers)