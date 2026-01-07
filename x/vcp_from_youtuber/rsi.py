
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import matplotlib.pyplot as plt

# 视频逻辑重现
data = yf.download('0005.HK', start='2020-01-01', end='2023-01-01')

data = data.ta.rsi(length=14)

# 正确示范
data = 0
# [data.loc < 30, 'Signal'] = 1
# 信号下移一格，代表明日执行
data = data.shift(1) * data['Pct_Change']

data['MA200'] = data.ta.sma(length=200)
# 仅在长牛趋势中做多
# data.loc < 30) & (data['Close'] > data['MA200']), 'Signal'] = 1

commission = 0.001  # 万分之十的手续费
slippage = 0.001    # 万分之十的滑点估计
# 净收益 = 策略名义收益 - 进场成本 - 出场成本
data = data - (commission + slippage) * 2