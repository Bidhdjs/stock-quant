import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# 设置专业的绘图风格
sns.set_theme(style="darkgrid")
plt.rcParams['figure.figsize'] = [1, 2]
plt.rcParams['font.sans-serif'] =  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


class MeanReversionBacktester:
    """
    均值回归回测器类：
    实现基于每日跌幅排名的“最大输家”买入策略。
    """

    def __init__(self, tickers, start_date, end_date, top_n=10, holding_period=1):
        """
        初始化回测器参数。

        参数:
        tickers (list): 股票代码列表。
        start_date (str): 回测开始日期 'YYYY-MM-DD'。
        end_date (str): 回测结束日期 'YYYY-MM-DD'。
        top_n (int): 每日买入的股票数量（跌幅最大的前N只）。
        holding_period (int): 持仓天数（默认为1，即持有至次日）。
        """
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.top_n = top_n
        self.holding_period = holding_period

        # 内部数据存储
        self.data = None
        self.returns = None
        self.positions = None
        self.strategy_returns = None
        self.benchmark_returns = None
        self.metrics = {}

    def download_data(self):
        """
        从Yahoo Finance下载历史调整后收盘价（Adj Close）。
        使用调整后收盘价至关重要，因为它剔除了分红和拆股的影响。
        """
        print(f"正在下载 {len(self.tickers)} 只股票的历史数据...")
        try:
            # 批量下载以提高效率
            data = yf.download(
                self.tickers,
                start=self.start_date,
                end=self.end_date,
                group_by='ticker',
                progress=True
            )
            # 提取Adj Close，处理多层索引
            if len(self.tickers) > 1:
                self.data = data.xs('Adj Close', level=1, axis=1)
            else:
                self.data = data['Adj Close']

            # 清洗数据：删除全为空的列
            self.data.dropna(axis=1, how='all', inplace=True)
            print("数据下载完成。")
        except Exception as e:
            print(f"数据下载失败: {e}")

    def prepare_data(self):
        """
        计算每日收益率。
        """
        if self.data is None:
            raise ValueError("数据未下载，请先调用 download_data()")

        # 计算百分比收益率
        self.returns = self.data.pct_change()

    def generate_signals(self):
        """
        核心逻辑：生成交易信号。
        识别每日跌幅最大的前N只股票。
        """
        print("正在生成交易信号...")

        # 使用Pandas的rank方法进行横向排名（axis=1）
        # method='min' 处理平局，ascending=True 表示从小到大排序（跌幅最大的排在前面）
        # 排名为 1 的股票即为跌幅最大的股票
        daily_ranks = self.returns.rank(axis=1, method='min', ascending=True)

        # 生成信号矩阵：若排名 <= top_n，则标记为True（买入信号）
        # 注意：这个信号是基于当日收盘价计算的
        self.signals = (daily_ranks <= self.top_n)

    def backtest(self):
        """
        执行回测逻辑，计算资金曲线。
        处理前视偏差：
        T日的信号基于T日的跌幅，我们在T日收盘后才知道谁是输家。
        因此，我们在T+1日持有这些股票。
        逻辑上，我们将信号向后移动1天（shift(1)）。
        """
        print("正在执行回测计算...")

        # 将信号下移一天，代表T日的信号在T+1日生效（产生T+1日的收益）
        # 假设：T日收盘买入（或T+1开盘买入），持有至T+1收盘。
        # 这里使用的是T+1日的 Close-to-Close 收益率。
        positions = self.signals.shift(1).fillna(False)

        # 每日持仓数量可能少于 top_n（例如某些股票停牌或数据缺失）
        # 计算每日实际持仓数，用于等权重分配资金
        daily_counts = positions.sum(axis=1)

        # 避免除以零
        weights = positions.div(daily_counts, axis=0).fillna(0)

        # 策略每日收益率 = sum(个股收益率 * 权重)
        self.strategy_daily_returns = (weights * self.returns).sum(axis=1)

        # 计算基准收益率（这里简单使用股票池的等权重平均作为基准）
        # 在实际应用中，可以下载SPY数据作为基准
        self.benchmark_daily_returns = self.returns.mean(axis=1)

        # 计算累积净值
        self.strategy_cumulative = (1 + self.strategy_daily_returns).cumprod()
        self.benchmark_cumulative = (1 + self.benchmark_daily_returns).cumprod()

    def calculate_metrics(self):
        """
        计算关键绩效指标：CAGR, Sharpe, Max Drawdown
        """
        # 年化收益率 (CAGR)
        total_days = (
                    datetime.strptime(self.end_date, "%Y-%m-%d") - datetime.strptime(self.start_date, "%Y-%m-%d")).days
        years = total_days / 365.25
        total_return = self.strategy_cumulative.iloc[-1] - 1
        cagr = (self.strategy_cumulative.iloc[-1]) ** (1 / years) - 1

        # 夏普比率 (假设无风险利率为2%)
        rf = 0.02
        volatility = self.strategy_daily_returns.std() * np.sqrt(252)
        sharpe = (cagr - rf) / volatility if volatility != 0 else 0

        # 最大回撤
        rolling_max = self.strategy_cumulative.cummax()
        drawdown = (self.strategy_cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        self.metrics = {
            '总收益率': f"{total_return:.2%}",
            '年化收益率 (CAGR)': f"{cagr:.2%}",
            '年化波动率': f"{volatility:.2%}",
            '夏普比率': f"{sharpe:.2f}",
            '最大回撤': f"{max_drawdown:.2%}"
        }
        return self.metrics

    def plot_results(self):
        """
        绘制包含累积收益与回撤的专业图表。
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 4]}, sharex=True)

        # 上图：净值曲线
        ax1.plot(self.strategy_cumulative.index, self.strategy_cumulative, label=f'最大跌幅策略 (Top {self.top_n})',
                 color='#1f77b4', linewidth=2)
        ax1.plot(self.benchmark_cumulative.index, self.benchmark_cumulative, label='基准 (等权重)', color='gray',
                 linestyle='--', alpha=0.7)
        ax1.set_title(f"策略绩效回测: 买入每日跌幅最大的 {self.top_n} 只股票", fontsize=16, fontweight='bold')
        ax1.set_ylabel("净值增长 (初始=1)", fontsize=12)
        ax1.legend(loc='upper left', fontsize=12)
        ax1.grid(True, alpha=0.3)

        # 下图：回撤区域
        rolling_max = self.strategy_cumulative.cummax()
        drawdown = (self.strategy_cumulative - rolling_max) / rolling_max

        ax2.fill_between(drawdown.index, drawdown, 0, color='#d62728', alpha=0.3, label='回撤幅度')
        ax2.plot(drawdown.index, drawdown, color='#d62728', linewidth=1)
        ax2.set_title("策略最大回撤 (Drawdown)", fontsize=14)
        ax2.set_ylabel("回撤百分比", fontsize=12)
        ax2.set_xlabel("日期", fontsize=12)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()


# --- 策略执行示例 ---

# 定义股票池：这里为了演示，选取了纳斯达克100的部分高流动性科技股
# 在真实生产环境中，应该动态获取历史时刻的指数成分股以避免幸存者偏差
universe =

# 实例化回测器
backtester = MeanReversionBacktester(
    tickers=universe,
    start_date='2020-01-01',
    end_date='2023-12-31',
    top_n=5  # 每日买入跌幅最大的5只
)

# 运行流程
backtester.download_data()
backtester.prepare_data()
backtester.generate_signals()
backtester.backtest()

# 输出指标
metrics = backtester.calculate_metrics()
print("\n--------- 策略回测报告 ---------")
for k, v in metrics.items():
    print(f"{k}: {v}")

# 绘图
backtester.plot_results()   