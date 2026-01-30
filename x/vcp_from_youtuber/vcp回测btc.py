import ccxt
import pandas as pd
import numpy as np
import datetime
import time
import matplotlib.pyplot as plt

# 设置Pandas显示选项，确保打印输出时能看到所有列，方便调试
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
pd.set_option('display.width', 1000)

def initialize_exchange():
    """
    初始化CCXT交易所实例。
    这里使用Bybit作为示例，实际使用时可根据需求配置API Key（仅用于交易，回测仅需公开数据）。
    """
    exchange = ccxt.bybit({
        'timeout': 30000,
        'enableRateLimit': True,  # 启用内置的速率限制处理，防止IP被封
    })
    return exchange


def fetch_ohlcv_data(exchange, symbol, timeframe='1d', start_date='2020-01-01'):
    """
    从交易所获取指定交易对的历史K线数据。

    参数:
        exchange: CCXT交易所对象
        symbol: 交易对名称，如 'BTC/USDT'
        timeframe: 时间周期，如 '1d' (日线)
        start_date: 起始日期字符串 'YYYY-MM-DD'

    返回:
        pd.DataFrame: 包含 timestamp, open, high, low, close, volume 的数据框
    """
    # 将日期字符串转换为毫秒级时间戳
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    since = int(start_dt.timestamp() * 1000)

    all_candles =
    limit = 1000  # Bybit通常允许的最大单次请求量

    print(f"开始下载 {symbol} 数据，起始时间: {start_date}...")

    while True:
        try:
            # 调用ccxt的fetch_ohlcv方法
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

            if not candles:
                break

            all_candles.extend(candles)

            # 更新since变量：取最后一条K线的时间戳 + 1毫秒，作为下次请求的起点
            last_timestamp = candles[-1]
            since = last_timestamp + 1

            # 如果获取的数据少于limit，说明已经到达最新数据，退出循环
            if len(candles) < limit:
                break

            # 简单的进度反馈
            print(f"已获取至: {datetime.datetime.fromtimestamp(last_timestamp / 1000)}")

        except Exception as e:
            print(f"数据下载出错: {e}")
            # 出错时稍作休眠后重试，或退出
            time.sleep(5)
            break

    # 将列表转换为DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # 处理时间戳：转换为datetime对象并设为索引
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # 数据清洗：去重（防止分页边界重复）
    df = df[~df.index.duplicated(keep='first')]

    print(f"下载完成，共 {len(df)} 条K线数据。")
    return df


def calculate_trend_template(df):
    """
    计算技术指标并应用Minervini趋势模板过滤条件。

    逻辑复现:
    1. 计算 MA50, MA150, MA200
    2. 计算 52周新高/新低 (在加密货币中通常使用365天作为一年)
    3. 判断 MA200 的趋势方向
    4. 生成布尔信号
    """
    # 1. 计算移动平均线
    df = df['close'].rolling(window=50).mean()
    df = df['close'].rolling(window=150).mean()
    df = df['close'].rolling(window=200).mean()

    # 2. 计算52周（365天）最高价和最低价
    # 注意：shift(1)是为了避免前视偏差，即计算当天的信号时，应基于昨天及之前的High/Low
    # 但Trend Template通常比较的是当前价格与过去一年的High/Low，所以包含当天是可以接受的，
    # 或者是使用截至昨天的High/Low。这里我们使用包含当天的滚动窗口。
    window_year = 365
    df['52_week_low'] = df['close'].rolling(window=window_year).min()
    df['52_week_high'] = df['close'].rolling(window=window_year).max()

    # 3. 计算 MA200 的斜率趋势
    # 视频中提到 MA200 必须上涨至少1个月。
    # 我们检查当天的 MA200 是否大于 20个交易日（约1个月）前的 MA200。
    df = df.shift(20)
    df = df > df

    # 4. 应用六大过滤条件 (Minervini Stage 2 Criteria)

    # 条件1: 价格 > MA150 和 MA200
    c1 = (df['close'] > df) & (df['close'] > df)

    # 条件2: MA150 > MA200
    c2 = df > df

    # 条件3: MA200 处于上升趋势
    c3 = df

    # 条件4: MA50 > MA150 和 MA200 (多头排列)
    c4 = (df > df) & (df > df)

    # 条件5: 当前价格 >= 52周最低价的 125% (即上涨了至少25%)
    c5 = df['close'] >= (1.25 * df['52_week_low'])

    # 条件6: 当前价格 >= 52周最高价的 75% (即处于距离新高25%的范围内)
    c6 = df['close'] >= (0.75 * df['52_week_high'])

    # 综合所有条件
    df = c1 & c2 & c3 & c4 & c5 & c6

    return df


def run_backtest_strategy(df):
    """
    执行回测逻辑：
    - 入场：当 'Trend_Template_Met' 为 True，且价格出现突破迹象（这里简化为收盘价站稳）
    - 出场：固定止损 5%，固定止盈 10%
    """

    # 初始资金配置
    initial_capital = 10000
    balance = initial_capital
    position = 0  # 持仓数量
    entry_price = 0
    in_trade = False

    trades =  # 记录交易日志

    # 策略参数
    stop_loss_pct = 0.05
    take_profit_pct = 0.10

    # 遍历每一行数据
    # 注意：从第200天开始，因为前期数据用于计算MA200
    for i in range(365, len(df)):
        curr_date = df.index[i]
        curr_close = df['close'].iloc[i]
        curr_high = df['high'].iloc[i]
        curr_low = df['low'].iloc[i]
        trend_met = df.iloc[i]

        # --- 1. 持仓管理逻辑 (检查是否触发止盈止损) ---
        if in_trade:
            # 计算止损价和止盈价
            sl_price = entry_price * (1 - stop_loss_pct)
            tp_price = entry_price * (1 + take_profit_pct)

            # 检查当日最低价是否击穿止损
            if curr_low <= sl_price:
                # 止损离场
                exit_price = sl_price  # 假设在止损价成交（实际可能有滑点）
                pnl = (exit_price - entry_price) * position
                balance += pnl
                trades.append({
                    'Entry_Date': entry_date,
                    'Exit_Date': curr_date,
                    'Type': 'Stop Loss',
                    'Entry_Price': entry_price,
                    'Exit_Price': exit_price,
                    'PnL': pnl,
                    'Balance': balance
                })
                in_trade = False
                position = 0
                continue  # 结束当日逻辑

            # 检查当日最高价是否触及止盈
            elif curr_high >= tp_price:
                # 止盈离场
                exit_price = tp_price
                pnl = (exit_price - entry_price) * position
                balance += pnl
                trades.append({
                    'Entry_Date': entry_date,
                    'Exit_Date': curr_date,
                    'Type': 'Take Profit',
                    'Entry_Price': entry_price,
                    'Exit_Price': exit_price,
                    'PnL': pnl,
                    'Balance': balance
                })
                in_trade = False
                position = 0
                continue

        # --- 2. 开仓逻辑 (寻找买入信号) ---
        if not in_trade:
            if trend_met:
                # 视频中提到的 "Cheat Area" 是一个形态学概念，
                # 在代码中，我们可以进一步要求波动率处于低位，
                # 或者简单地在趋势模板满足时，视为潜在买点。
                # 为了复现视频的简单回测，我们假设满足趋势模板即买入。

                # 全仓买入 (简化模型)
                entry_price = curr_close
                position = balance / entry_price
                entry_date = curr_date
                in_trade = True

                # 注意：实际交易中不会在产生信号的当根K线收盘买入，
                # 而是在次日开盘买入，或者在当日突破时买入。
                # 这里为了简化，假设以当日收盘价买入。

    # 整理回测结果
    trades_df = pd.DataFrame(trades)
    return trades_df, balance