#!/usr/bin/env python
# coding: utf-8
"""
VCP（Volatility Contraction Pattern，波动收缩形态）股票筛选器

VCP 是由 Mark Minervini 提出的一种技术分析形态，用于识别潜在的突破性股票。
该形态的特点是：
1. 股票处于上升趋势（Stage 2 阶段）
2. 价格波动幅度逐渐收窄（形成一系列收缩）
3. 成交量随着盘整而萎缩
4. 等待突破买入点

本脚本的主要功能：
1. 从 Finviz 获取符合初步条件的股票列表
2. 使用趋势模板筛选处于 Stage 2 的股票
3. 检测 VCP 形态
4. 计算相对强度（RS）评级
5. 生成最终的观察名单
"""

# In[ ]:


# ==================== 导入必要的库 ====================
import pandas as pd          # 数据处理库
import numpy as np           # 数值计算库
import yfinance as yf        # Yahoo Finance 数据接口
from datetime import date as dt  # 日期处理
from pandas_datareader import data as pdr  # 金融数据读取器
import time                  # 时间处理
import finviz               # Finviz 股票筛选工具
from finviz.screener import Screener  # Finviz 筛选器
from finvizfinance.quote import finvizfinance  # Finviz 金融数据
import matplotlib.pyplot as plt  # 绑图库
from scipy.signal import argrelextrema  # 用于寻找局部极值点


# In[ ]:


# ==================== 趋势斜率计算函数 ====================
# 判断 MA200 是否处于上升趋势
# 使用线性回归的斜率来判断趋势方向
def trend_value(nums:list):
    """
    计算一组数据的线性回归斜率
    
    参数:
        nums: 数值列表（如 MA200 的值）
    
    返回:
        斜率值（正值表示上升趋势，负值表示下降趋势）
    
    原理: 使用最小二乘法计算线性回归斜率
    斜率公式: slope = (n * Σ(x*y) - Σx * Σy) / (n * Σ(x²) - (Σx)²)
    """
    summed_nums = sum(nums)        # Σy: 所有数值的总和
    multiplied_data = 0            # Σ(x*y): 索引与数值乘积的总和
    summed_index = 0               # Σx: 所有索引的总和
    squared_index = 0              # Σ(x²): 索引平方的总和

    for index, num in enumerate(nums):
        index += 1                 # 索引从1开始
        multiplied_data += index * num   # 累加 x*y
        summed_index += index            # 累加 x
        squared_index += index**2        # 累加 x²

    # 计算斜率的分子和分母
    numerator = (len(nums) * multiplied_data) - (summed_nums * summed_index)
    denominator = (len(nums) * squared_index) - summed_index**2
    if denominator != 0:
        return numerator/denominator
    else:
        return 0


# ==================== 趋势模板筛选函数（Stage 2 判断）====================
# 基于 Mark Minervini 的趋势模板条件，判断股票是否处于 Stage 2（上升阶段）
def trend_template(df):
    """
    使用 Minervini 趋势模板筛选处于 Stage 2 的股票
    
    Stage 2 是股票生命周期中最佳的买入阶段，特点是：
    - 价格在关键均线之上
    - 均线呈多头排列
    - 200日均线呈上升趋势
    
    参数:
        df: 股票历史数据 DataFrame
    
    返回:
        添加了条件判断列的 DataFrame
    """
    # ---------- 计算移动平均线 ----------
    df['MA_50'] = round(df['Close'].rolling(window=50).mean(),2)    # 50日均线
    df['MA_150'] = round(df['Close'].rolling(window=150).mean(),2)  # 150日均线
    df['MA_200'] = round(df['Close'].rolling(window=200).mean(),2)  # 200日均线
    
    # ---------- 计算52周最高价和最低价 ----------
    if len(df.index) > 5*52:  # 如果数据超过52周（约260个交易日）
        df['52_week_low'] = df['Low'].rolling(window = 5*52).min()   # 52周最低价
        df['52_week_high'] = df['High'].rolling(window = 5*52).max()  # 52周最高价
    else:  # 数据不足52周，使用全部数据
        df['52_week_low'] = df['Low'].rolling(window = len(df.index)).min()
        df['52_week_high'] = df['High'].rolling(window = len(df.index)).max()
    
    # ---------- 条件1&5: 价格在 50MA、150MA 和 200MA 之上 ----------
    # 这表明股票处于强势上升趋势中
    df['condition_1'] = (df['Close'] > df['MA_150']) & (df['Close'] > df['MA_200']) & (df['Close'] > df['MA_50'])
    
    # ---------- 条件2&4: 均线多头排列（50MA > 150MA > 200MA）----------
    # 短期均线在长期均线之上是上升趋势的特征
    df['condition_2'] = (df['MA_150'] > df['MA_200']) & (df['MA_50'] > df['MA_150'])
    
    # ---------- 条件3: 200日均线至少上升1个月（20个交易日）----------
    # 确保长期趋势是向上的
    slope = df['MA_200'].rolling(window = 20).apply(trend_value)
    df['condition_3'] = slope > 0.0
    
    # ---------- 条件6: 价格至少比52周最低价高30% ----------
    # 确保股票已经从底部上涨了一定幅度
    df['condition_6'] = df['Low'] > (df['52_week_low']*1.3)
    
    # ---------- 条件7: 价格在52周最高价的25%范围内 ----------
    # 确保股票接近新高，而不是远离高点
    df['condition_7'] = df['High'] > (df['52_week_high']*0.75)
    
    # ---------- 条件8（附加）: 相对强度线向上 ----------
    # 相对强度线(RS Line)比较股票与S&P500的表现
    # 上升的RS线表明股票跑赢大盘
    df['RS'] = df['Close']/df_spx['Close']  # 计算相对强度
    slope_rs = df['RS'].rolling(window = 20).apply(trend_value)
    df['condition_8'] = slope > 0.0  # RS线斜率为正
    
    # ---------- 综合判断: 所有条件都满足才通过 ----------
    df['Pass'] = df[['condition_1','condition_2','condition_3','condition_6','condition_7','condition_8']].all(axis='columns')
    
    return df


# ==================== 局部高点和低点检测函数 ====================
def local_high_low(df):
    """
    检测价格的局部极值点（波峰和波谷）
    
    这些极值点用于识别 VCP 形态中的收缩点
    
    参数:
        df: 股票历史数据 DataFrame
    
    返回:
        adjusted_local_high: 调整后的局部高点索引列表
        adjusted_local_low: 调整后的局部低点索引列表
    """
    # 使用 scipy 的 argrelextrema 函数找出局部极值点
    # order=10 表示在前后各10个点的范围内寻找极值
    local_high = argrelextrema(df['High'].to_numpy(),np.greater,order=10)[0]  # 局部高点
    local_low = argrelextrema(df['Low'].to_numpy(),np.less,order=10)[0]       # 局部低点
    
    # ---------- 消除连续的高点或低点 ----------
    # VCP 形态需要高低点交替出现
    # 以下代码确保高点和低点交替排列
    i = 0
    j = 0
    local_high_low = []
    adjusted_local_high = []
    adjusted_local_low = []
    
    # 遍历并调整高低点，确保交替出现
    while i < len(local_high) and j < len(local_low):
        if local_high[i] < local_low[j]:
            # 如果高点在低点之前，找到该低点之前的最后一个高点
            while i < len(local_high):
                if local_high[i] < local_low[j]:
                    i+=1
                else:
                    adjusted_local_high.append(local_high[i-1])
                    break
        elif local_high[i] > local_low[j]:
            # 如果低点在高点之前，找到该高点之前的最后一个低点
            while j < len(local_low):
                if local_high[i] > local_low[j]:
                    j+=1
                else:
                    adjusted_local_low.append(local_low[j-1])
                    break
        else:
            i+=1
            j+=1
    
    # 处理剩余的高点或低点
    if i < len(local_high):
        adjusted_local_high.pop(-1)
        while i < len(local_high):
            if local_high[i] > local_low[j-1]:
                i+=1
            else:
                adjusted_local_high.append(local_high[i-1])
                break
        adjusted_local_high.append(local_high[-1])
        adjusted_local_low.append(local_low[j-1])
    
    if j < len(local_low):
        adjusted_local_low.pop(-1)
        while j < len(local_low):
            if local_high[i-1] > local_low[j]:
                j+=1
            else:
                adjusted_local_low.append(local_low[j-1])
                break
        adjusted_local_low.append(local_low[-1])
        adjusted_local_high.append(local_high[i-1])
    return adjusted_local_high, adjusted_local_low


# ==================== 收缩幅度计算函数 ====================
def contractions(df,local_high,local_low):
    """
    计算每次收缩的深度（百分比）
    
    收缩深度 = (波峰价格 - 波谷价格) / 波峰价格 * 100
    
    参数:
        df: 股票历史数据 DataFrame
        local_high: 局部高点索引列表
        local_low: 局部低点索引列表
    
    返回:
        contraction: 收缩幅度列表（从最近到最早）
    """
    # 反转列表，从最近的高低点开始计算
    local_high = local_high[::-1]
    local_low = local_low[::-1]
    
    i = 0
    j = 0
    contraction = []
    
    # 计算每个高点到低点的收缩幅度
    while i < len(local_low) and j < len(local_high):
        if local_low[i] > local_high[j]:
            # 收缩幅度 = (高点价格 - 低点价格) / 高点价格 * 100
            contraction.append(round((df['High'][local_high][j] - df['Low'][local_low][i]) / df['High'][local_high][j] * 100,2))
            i+=1
            j+=1
        else:
            j+=1
    return contraction


# ==================== 收缩次数计算函数 ====================
def num_of_contractions(contraction):
    """
    计算有效的收缩次数
    
    VCP 形态的特点是收缩幅度逐渐递减
    此函数计算连续递减的收缩次数
    
    参数:
        contraction: 收缩幅度列表
    
    返回:
        num_of_contraction: 有效收缩次数
    """
    new_c = 0
    num_of_contraction = 0
    for c in contraction:
        if c > new_c:  # 如果当前收缩比前一个大（从最近往回看，收缩应该越来越大）
            num_of_contraction+=1
            new_c = c
        else:
            break  # 一旦不满足递增条件，停止计数
    return num_of_contraction


# ==================== 最大和最小收缩幅度计算函数 ====================
def max_min_contraction(contraction,num_of_contractions):
    """
    获取最大收缩幅度和最小收缩幅度
    
    参数:
        contraction: 收缩幅度列表
        num_of_contractions: 有效收缩次数
    
    返回:
        max_contraction: 最大收缩幅度（最早的那次）
        min_contraction: 最小收缩幅度（最近的那次）
    """
    max_contraction = contraction[num_of_contractions-1]  # 最大收缩（第一次）
    min_contraction = contraction[0]  # 最小收缩（最后一次）
    return max_contraction, min_contraction


# ==================== 收缩周数计算函数 ====================
def weeks_of_contraction(df,local_high,num_of_contractions):
    """
    计算 VCP 形态持续的周数
    
    参数:
        df: 股票历史数据 DataFrame
        local_high: 局部高点索引列表
        num_of_contractions: 有效收缩次数
    
    返回:
        week_of_contraction: VCP 形态持续的周数
    """
    # 从第一个收缩高点到最新数据的天数，除以5得到周数
    week_of_contraction = (len(df.index) - local_high[::-1][num_of_contractions-1]) / 5
    return week_of_contraction


# ==================== VCP 形态判断主函数 ====================
def vcp(df):
    """
    判断股票是否符合 VCP（波动收缩形态）
    
    VCP 的标准条件：
    1. 收缩次数: 2-4 次
    2. 最大收缩幅度: 不超过 50%
    3. 最小收缩幅度: 不超过 15%
    4. 持续时间: 至少 2 周
    5. 成交量收缩: 近5日平均成交量 < 近30日平均成交量
    6. 尚未突破: 当前价格仍在盘整区间内
    
    参数:
        df: 股票历史数据 DataFrame
    
    返回:
        num_of_contraction: 收缩次数
        max_c: 最大收缩幅度
        min_c: 最小收缩幅度
        week_of_contraction: 收缩周数
        flag_final: 是否符合 VCP (1=是, 0=否)
    """
    # ---------- 准备收缩测量数据 ----------
    [local_high, local_low] = local_high_low(df)
    contraction = contractions(df,local_high,local_low)
    
    # ---------- 条件1: 计算收缩次数（理想值: 2-4 次）----------
    num_of_contraction = num_of_contractions(contraction)
    if 2 <= num_of_contraction <= 4:
        flag_num = 1
    else:
        flag_num = 0
    
    # ---------- 条件2&3: 计算收缩深度 ----------
    [max_c, min_c] = max_min_contraction(contraction,num_of_contraction)
    # 最大收缩不应超过50%（否则跌幅太大，可能是弱势股）
    if max_c > 50:
        flag_max = 0
    else:
        flag_max = 1
    # 最小收缩应在15%以内（表明波动在收敛）
    if min_c <= 15:
        flag_min = 1
    else:
        flag_min = 0
    
    # ---------- 条件4: 计算收缩周数（至少2周）----------
    week_of_contraction = weeks_of_contraction(df,local_high,num_of_contraction)
    if week_of_contraction >= 2:
        flag_week = 1
    else:
        flag_week = 0
    
    # ---------- 条件5: 成交量收缩 ----------
    # 计算30日和5日平均成交量
    df['30_day_avg_volume'] = round(df['Volume'].rolling(window = 30).mean(),2)
    df['5_day_avg_volume'] = round(df['Volume'].rolling(window = 5).mean(),2)
    # 5日均量应小于30日均量（表明成交量在萎缩，等待突破）
    df['vol_contraction'] = df['5_day_avg_volume'] < df['30_day_avg_volume']
    if df['vol_contraction'][-1] == 1:
        flag_vol = 1
    else:
        flag_vol = 0
        
    # ---------- 条件6: 尚未突破（仍在盘整中）----------
    # 当前最高价应低于最近的局部高点（未突破）
    if df['High'][-1] < df['High'][local_high][-1]:
        flag_consolidation = 1
    else:
        flag_consolidation = 0
    
    # ---------- 综合判断 ----------
    if flag_num == 1 & flag_max == 1 & flag_min == 1 & flag_week == 1 & flag_vol == 1 & flag_consolidation == 1:
        flag_final = 1
    else:
        flag_final = 0
    
    return num_of_contraction,max_c,min_c,week_of_contraction,flag_final


# ==================== RS（相对强度）评级计算函数 ====================
def rs_rating(ticker,rs_list):
    """
    计算股票的相对强度评级
    
    RS Rating 衡量股票相对于其他股票的表现
    评级范围: 0-100，越高表示表现越好
    
    参数:
        ticker: 股票代码
        rs_list: 按52周表现排序的股票列表
    
    返回:
        rs: RS 评级（0-100）
    """
    ticker_index = rs_list.index(ticker)  # 找到股票在排名中的位置
    rs = round(ticker_index / len(rs_list) * 100,0)  # 转换为百分位数
    return rs


# In[ ]:


# ==================== 第一步: 从 Finviz 获取初步筛选的股票列表 ====================
"""
使用 Finviz 的筛选器获取符合以下条件的股票:
- cap_smallover: 市值大于小盘股（排除微型股）
- sh_avgvol_o100: 平均成交量 > 10万股（确保流动性）
- sh_price_o2: 股价 > $2（排除低价股/仙股）
- ta_sma200_sb50: 50日均线在200日均线之上（上升趋势）
- ta_sma50_pa: 价格在50日均线之上
"""
filters = ['cap_smallover','sh_avgvol_o100','sh_price_o2','ta_sma200_sb50','ta_sma50_pa']
stock_list = Screener(filters = filters, table = 'Performance' , order = 'asc')
ticker_table = pd.DataFrame(stock_list.data)
ticker_list = ticker_table['Ticker'].to_list()  # 获取股票代码列表
# print(ticker_list)


# In[ ]:


# ==================== 第二步: 准备 RS 评级数据和大盘基准数据 ====================
"""
RS（Relative Strength，相对强度）评级筛选条件:
- RS 评级应大于 70（即表现超过 70% 的股票）
- RS 评级追踪股票过去52周的价格表现，并与其他所有股票进行比较
"""
# 获取按52周表现排序的所有股票，用于计算 RS 评级
performance_table = Screener(table='Performance', order='perf52w')
rs_table = pd.DataFrame(performance_table.data)
rs_list = rs_table['Ticker'].to_list()  # 按表现排序的股票列表

# 下载 S&P 500 指数数据，用于计算相对强度（趋势模板的条件9）
# 相对强度线用于判断股票是否跑赢大盘
df_spx = yf.download(tickers = '^GSPC', period = '2y')  # 获取2年数据


# In[ ]:


# ==================== 第三步: 主筛选循环 ====================
"""
遍历所有初步筛选的股票，进行以下检查:
1. 趋势模板筛选（判断是否处于 Stage 2）
2. VCP 形态检测
3. RS 评级筛选
"""

# 注意: ticker.info 方法处理时间太长，不使用
yf.pdr_override()  # 使用 pandas_datareader 覆盖 yfinance

# 创建 DataFrame 存储筛选结果
radar = pd.DataFrame({
    'Ticker': [],              # 股票代码
    'Num_of_contraction': [],  # 收缩次数
    'Max_contraction': [],     # 最大收缩幅度
    'Min_contraction': [],     # 最小收缩幅度
    'Weeks_of_contraction': [],# 收缩周数
    'RS_rating': []            # RS 评级
})

fail = 0  # 记录处理失败的股票数量

# 遍历每只股票进行分析
for ticker_string in ticker_list:
    try:
        # 获取股票过去2年的历史数据
        ticker_history = pdr.get_data_yahoo(tickers = ticker_string, period = '2y')
        
        # 步骤3.1: 使用趋势模板判断股票是否处于 Stage 2（上升阶段）
        trend_template_screener = trend_template(ticker_history)
        
        if trend_template_screener['Pass'][-1] == 1:
            # 股票通过趋势模板筛选，处于 Stage 2
            print(f'{ticker_string} is in Stage 2')  
            
            # 步骤3.2: 检测 VCP 形态
            vcp_screener = list(vcp(ticker_history))
            
            # 步骤3.3: 计算 RS 评级
            rs = rs_rating(ticker_string,rs_list)
            
            # 步骤3.4: 最终筛选 - VCP 形态成立且 RS >= 70
            if (vcp_screener[-1] == 1) & (rs >= 70):
                # 将结果存入 DataFrame
                vcp_screener.insert(0,ticker_string)  # 插入股票代码
                vcp_screener.insert(-1,rs)            # 插入 RS 评级
                radar.loc[len(radar)] = vcp_screener[0:6]  # 存储到结果表
                print(f'{ticker_string} has a VCP')
            else:
                print(f'{ticker_string} does not have a VCP')
        else:
            # 股票不在 Stage 2，跳过
            print(f'{ticker_string} is not in Stage 2')
    except:
        # 处理异常（数据获取失败等）
        fail+=1
        
print('Finished!!!')  # 筛选完成
print(f'{fail} stocks fail to analyze')  # 输出失败的股票数量


# In[ ]:


# ==================== 第四步: 输出筛选结果 ====================
print(f'{len(radar)} stocks pass')  # 输出通过筛选的股票数量
# print(radar)  # 可取消注释查看详细结果


# In[ ]:


# ==================== 第五步: 可视化 - 绑制符合条件股票的图表 ====================
"""
为每只通过筛选的股票绑制价格图表:
- 显示收盘价走势
- 标记局部高点（波峰）
- 标记局部低点（波谷）
"""
for ticker in radar['Ticker']:
    # 重新获取股票数据
    ticker_history = pdr.get_data_yahoo(tickers = ticker, period = '2y')
    
    # 获取局部高低点
    [local_high, local_low] = local_high_low(ticker_history)
    contraction = contractions(ticker_history,local_high,local_low)
    num_of_contraction = num_of_contractions(contraction)
    
    # 只保留有效收缩区间内的高低点
    local_high = local_high[::-1][0:num_of_contraction]
    local_low = local_low[::-1][0:num_of_contraction]
    
    # 绑制图表
    plt.plot(range(len(ticker_history.index)),ticker_history['Close'])  # 收盘价曲线
    plt.plot(local_high,ticker_history['High'][local_high],'o')  # 高点用圆圈标记
    plt.plot(local_low,ticker_history['Low'][local_low],'x')     # 低点用X标记
    
    plt.title(ticker)       # 图表标题（股票代码）
    plt.xlabel('Days')      # X轴标签
    plt.ylabel('Close Price')  # Y轴标签
    plt.show()


# In[ ]:


# ==================== 第六步: 保存结果到 Excel 文件 ====================
"""
将筛选结果保存到 Excel 文件:
- 每天的结果保存为单独的 sheet（以日期命名）
- 支持追加到现有文件
"""
# 定义 Excel 文件路径（需要根据实际情况修改）
filename = 'C:/Users/marco/Desktop/Trade Resources/Watchlist/vcp_screener.xlsx'

# 获取今天的日期作为 sheet 名称
today = dt.today().strftime("%Y_%m_%d")

# 尝试读取现有的 Excel 文件（如果存在）
try:
    database = pd.read_excel(filename, sheet_name=None)  # 读取所有 sheet
except FileNotFoundError:
    database = {}  # 文件不存在则创建空字典

# 将今天的筛选结果添加到数据库
database[today] = radar

# 将更新后的数据写入 Excel 文件
with pd.ExcelWriter(filename) as writer:
    for sheet_name, df in database.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)

