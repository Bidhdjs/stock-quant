# LSTM 量化交易策略复现
# pip install numpy pandas yfinance pandas_ta scikit-learn tensorflow matplotlib


# -*- coding: utf-8 -*-
"""
LSTM 量化交易策略复现 - 完整版
基于 EMA, RSI 和 Volume 的深度学习预测模型
"""

import numpy as np
import pandas as pd
import yfinance as yf
import pandas_ta as ta  # 专业的金融技术指标库
import matplotlib.pyplot as plt
import math
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from datetime import datetime, timedelta

# 设置绘图风格
plt.style.use('fivethirtyeight')


class LSTMPredictionStrategy:
    """
    LSTM 深度学习交易策略类
    包含数据获取、特征工程、模型训练、信号生成与回测功能。
    """

    def __init__(self, ticker, start_date, end_date, look_back=60):
        """
        初始化策略对象
        :param ticker: 股票代码 (例如 'NVDA')
        :param start_date: 数据开始日期 (格式 'YYYY-MM-DD')
        :param end_date: 数据结束日期 (格式 'YYYY-MM-DD')
        :param look_back: LSTM的时间窗口大小，即用过去多少天的数据预测下一天
        """
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.look_back = look_back

        # 核心数据容器
        self.df = None  # 原始数据
        self.scaled_data = None  # 归一化后的数据
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None  # LSTM 模型实例

        # 策略超参数
        self.buy_threshold = 0.01  # 开仓阈值：预测涨幅 > 1%
        self.stop_loss_pct = 0.01  # 止损阈值：跌幅 > 1%

    def fetch_and_prepare_data(self):
        """
        步骤 1: 获取数据并计算技术指标
        """
        print(f"[*] 正在获取 {self.ticker} 的历史数据...")
        # 从 Yahoo Finance 下载数据
        self.df = yf.download(self.ticker, start=self.start_date, end=self.end_date)

        if self.df.empty:
            raise ValueError("错误：未获取到数据，请检查股票代码或网络连接。")

        # 仅保留核心列
        self.df = self.df[['Close', 'Volume']].copy()

        # --- 特征工程 (数学原理部分) ---
        print("[*] 计算技术指标 (EMA, RSI)...")

        # 1. 计算 12日 和 26日 EMA
        # 此处使用 pandas_ta 库，它能处理边缘情况
        self.df['EMA_12'] = ta.ema(self.df['Close'], length=12)
        self.df['EMA_26'] = ta.ema(self.df['Close'], length=26)

        # 2. 计算 14日 RSI
        self.df = ta.rsi(self.df['Close'], length=14)

        # 3. 处理缺失值 (由于 EMA 和 RSI 需要历史窗口，前期数据会产生 NaN)
        # 我们直接丢弃前 26 行数据
        self.df.dropna(inplace=True)

        print(f"[*] 数据准备完成。有效数据行数: {len(self.df)}")
        # 打印前几行供检查
        print(self.df.tail())

    def preprocess_for_lstm(self):
        """
        步骤 2: 数据归一化与序列构建
        LSTM 对数值敏感，必须将所有特征缩放到  之间。
        """
        # 选取用于训练的特征列
        # 注意：Close 放在第一列，方便后续反归一化预测值
        feature_columns =
        dataset = self.df[feature_columns].values

        # 归一化
        self.scaled_data = self.scaler.fit_transform(dataset)

        # 构建 X (特征序列) 和 y (目标标签)
        # 目标：利用过去 look_back 天的所有特征，预测下一天的 Close (第0列)
        X, y =,

        for i in range(self.look_back, len(self.scaled_data)):
            # X: 从 i-look_back 到 i 的数据 (不包含 i)
            X.append(self.scaled_data[i - self.look_back:i])
            # y: 第 i 天的 Close 价格 (即我们要预测的目标)
            y.append(self.scaled_data[i, 0])

        X, y = np.array(X), np.array(y)

        # LSTM 需要 3D 输入格式: [样本数, 时间步长, 特征数]
        # X.shape 此时已经是 (samples, look_back, features)
        print(f"[*] 数据集构建完成。输入形状 X: {X.shape}, 标签形状 y: {y.shape}")

        return X, y

    def build_model(self, input_shape):
        """
        步骤 3: 构建 LSTM 神经网络架构
        """
        print("[*] 构建 LSTM 模型架构...")
        model = Sequential()

        # 第一层 LSTM: 50个神经元, 返回序列以供堆叠, 输入维度
        model.add(LSTM(units=50, return_sequences=True, input_shape=input_shape))
        model.add(Dropout(0.2))  # Dropout 防止过拟合 (随机丢弃20%神经元)

        # 第二层 LSTM: 50个神经元, 不再返回序列 (连接全连接层)
        model.add(LSTM(units=50, return_sequences=False))
        model.add(Dropout(0.2))

        # 全连接层 (Dense): 25个神经元
        model.add(Dense(units=25))

        # 输出层: 1个神经元 (预测价格)
        model.add(Dense(units=1))

        # 编译模型: 优化器使用 Adam, 损失函数使用 MSE
        model.compile(optimizer='adam', loss='mean_squared_error')

        self.model = model
        return model

    def train_model(self, X, y, epochs=20, batch_size=32):
        """
        步骤 4: 训练模型
        """
        print(f"[*] 开始训练模型 (Epochs={epochs}, Batch_size={batch_size})...")
        self.model.fit(X, y, batch_size=batch_size, epochs=epochs, verbose=1)
        print("[*] 模型训练完成。")

    def run_strategy_backtest(self):
        """
        步骤 5: 生成信号与回测
        逻辑：使用训练好的模型，对历史数据进行“逐日”预测，并模拟交易。
        注意：为了演示代码逻辑，此处使用的是“样本内”(In-Sample) 测试。
        在严格的生产环境中，应使用“滚动窗口”(Walk-Forward) 方式。
        """
        print("[*] 开始生成交易信号与回测...")

        # 1. 对全量数据进行预测
        # 我们使用 preprocess_for_lstm 生成的 X 来预测
        # 注意：这里我们重新生成一遍 X，覆盖整个数据集
        X_full, _ = self.preprocess_for_lstm()

        # 批量预测
        predicted_scaled = self.model.predict(X_full)

        # 2. 反归一化 (Inverse Transform)
        # 因为 scaler 是针对 5 个特征 fit 的，我们需要构建一个具有 5 列的矩阵来进行逆变换
        # 我们只关心第 1 列 (Close) 的逆变换
        temp_matrix = np.zeros((len(predicted_scaled), self.scaled_data.shape))
        temp_matrix[:, 0] = predicted_scaled.flatten()
        predicted_prices = self.scaler.inverse_transform(temp_matrix)[:, 0]

        # 3. 将预测结果对齐到 DataFrame
        # 预测结果对应的是从第 look_back 天开始的每一天
        # 创建一个新的 DataFrame 用于存储回测结果
        result_df = self.df.iloc[self.look_back:].copy()
        result_df['Predicted_Close'] = predicted_prices

        # --- 交易逻辑实现 ---
        signals =  # 记录买卖操作
        positions =  # 记录持仓状态 (1: 持仓, 0: 空仓)
        portfolio_val =  # 简单的资金曲线 (假设初始资金 10000)

        cash = 10000.0
        shares = 0
        holding = False
        entry_price = 0.0

        # 遍历每一天进行逻辑判断
        # 注意：我们通常基于"今天"的预测来决定"明天"的操作
        # 这里的 Predicted_Close 是模型基于 T-1 及之前的数据预测的 T 日收盘价

        for i in range(len(result_df) - 1):
            current_close = result_df.iloc[i]['Close']  # 今天的实际收盘价

            # 获取模型对"明天"的预测价格
            # 这里的逻辑是：在第 i 天收盘后，我们有了第 i 天的数据，可以运行模型预测 i+1 天的价格
            # 在我们的 result_df 中，Predicted_Close[i+1] 正是利用 i 及之前数据预测的结果
            predicted_tomorrow = result_df.iloc[i + 1]['Predicted_Close']

            action = "HOLD"

            # --- 信号判断 ---

            if not holding:
                # 开仓逻辑: 预测明日涨幅 > 1%
                # 收益率预测 = (预测明日收盘 - 今日收盘) / 今日收盘
                expected_return = (predicted_tomorrow - current_close) / current_close

                if expected_return > self.buy_threshold:
                    # 全仓买入
                    shares = cash / current_close
                    cash = 0
                    entry_price = current_close
                    holding = True
                    action = "BUY"

            else:
                # 平仓逻辑
                # 1. 止损: 当前价格跌破买入价 1% (盘中风控的简化模拟)
                # 2. 信号反转: 预测明日价格低于今日收盘 (即预测下跌)

                is_stop_loss = current_close < entry_price * (1 - self.stop_loss_pct)
                is_reversal = predicted_tomorrow < current_close

                if is_stop_loss:
                    cash = shares * current_close
                    shares = 0
                    holding = False
                    action = "SELL (SL)"
                elif is_reversal:
                    cash = shares * current_close
                    shares = 0
                    holding = False
                    action = "SELL (Signal)"

            signals.append(action)
            positions.append(1 if holding else 0)

            # 计算当日资产总值
            current_value = cash + (shares * current_close)
            portfolio_val.append(current_value)

        # 补齐最后一天的数据
        signals.append("HOLD")
        positions.append(1 if holding else 0)
        portfolio_val.append(cash + (shares * result_df.iloc[-1]['Close']))

        result_df = signals
        result_df['Position'] = positions
        result_df['Portfolio_Value'] = portfolio_val

        return result_df

    def plot_results(self, result_df):
        """
        可视化: 绘制股价对比图和资金曲线
        """
        plt.figure(figsize=(16, 8))

        # 子图 1: 真实价格 vs 预测价格
        plt.subplot(2, 1, 1)
        plt.title(f'{self.ticker} - Real vs Predicted Price')
        plt.plot(result_df.index, result_df['Close'], label='Real Close', linewidth=1)
        plt.plot(result_df.index, result_df['Predicted_Close'], label='AI Predicted', linewidth=1, alpha=0.7)

        # 标记买卖点
        buy_signals = result_df == 'BUY']
        sell_signals = result_df.str.contains('SELL')]

        plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='green', label='Buy Signal', s=100)
        plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='red', label='Sell Signal', s=100)

        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.legend()

        # 子图 2: 策略资金曲线
        plt.subplot(2, 1, 2)
        plt.title('Strategy Portfolio Value')
        plt.plot(result_df.index, result_df['Portfolio_Value'], color='purple', linewidth=1.5)
        plt.xlabel('Date')
        plt.ylabel('Value (USD)')

        plt.tight_layout()
        plt.show()

        # --- 主程序入口 ---
        if __name__ == "__main__":
        # 示例: 分析 NVIDIA 股票
        # 请确保网络通畅以连接 Yahoo Finance
            try:
                # 实例化策略
                strategy = LSTMPredictionStrategy(
                    ticker='NVDA',
                    start_date='2015-01-01',
                    end_date='2021-01-01',
                    look_back=60
                )

                # 执行工作流
                strategy.fetch_and_prepare_data()  # 1. 获取数据
                X, y = strategy.preprocess_for_lstm()  # 2. 数据处理
                strategy.build_model(input_shape=(X.shape, X.shape))  # 3. 构建模型
                strategy.train_model(X, y, epochs=25)  # 4. 训练模型
                backtest_results = strategy.run_strategy_backtest()  # 5. 回测

                # 打印部分交易记录
                print("\n--- 交易记录片段 ---")
                print(backtest_results != 'HOLD']].head(10))

                # 绘图
                # strategy.plot_results(backtest_results)

                except Exception as e:
                print(f"程序运行出错: {e}")