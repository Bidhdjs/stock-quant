# config.py
"""
市场宽度分析系统配置文件
包含市场成分股列表、数据存储路径及API设置
"""
import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'market_data'
CACHE_DIR = DATA_DIR / 'parquet_store'

# 确保目录存在
os.makedirs(CACHE_DIR, exist_ok=True)

# 市场成分股全集 (Universe Definitions)
# 在实际生产中，这些列表应通过API动态获取以避免偏差。
# 这里为了演示，列举了代表性股票。
MARKET_UNIVERSES = {
    'US_TECH_GIANTS':,
    'HK_BLUE_CHIPS': [
        '0700.HK', '09988.HK', '03690.HK', '01299.HK', '00005.HK',
        '00388.HK', '00939.HK', '00941.HK', '01810.HK', '02318.HK'
    ],
    'JP_NIKKEI_SAMPLE':,
    # 使用ETF作为行业代理，避免个股幸存者偏差
    'US_SECTORS':
}

# 指标参数
PARAMS = {
    'SMA_SHORT': 50,
    'SMA_LONG': 200,
    'MCO_FAST': 19,
    'MCO_SLOW': 39,
    'TRIN_WINDOW': 14
}

# data_engine.py
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from config import CACHE_DIR


class DataEngine:
    def __init__(self, tickers, start_date, end_date=None, refresh_cache=False):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.today().strftime('%Y-%m-%d')
        self.refresh_cache = refresh_cache

    def _get_cache_path(self, ticker):
        """生成标准化的缓存文件路径"""
        # 清理Ticker名称中的特殊字符（如 ^GSPC -> GSPC）
        safe_ticker = ticker.replace('^', '').replace('.', '_')
        return CACHE_DIR / f"{safe_ticker}.parquet"

    def fetch_data(self):
        """
        主数据获取逻辑：
        1. 检查本地Parquet缓存。
        2. 如果缓存存在且覆盖了所需时间段，直接读取。
        3. 否则，通过yfinance API下载增量或全量数据。
        4. 保存回缓存。
        """
        data_store = {}
        missing_tickers =

        print(f"[*] Starting data ingestion for {len(self.tickers)} tickers...")

        for ticker in self.tickers:
            cache_path = self._get_cache_path(ticker)
            df = pd.DataFrame()
            loaded_from_cache = False

            if cache_path.exists() and not self.refresh_cache:
                try:
                    df = pd.read_parquet(cache_path)
                    # 检查数据是否覆盖了请求的结束日期
                    if not df.empty and df.index[-1].strftime('%Y-%m-%d') >= self.end_date:
                        # 截取所需时间段
                        mask = (df.index >= self.start_date) & (df.index <= self.end_date)
                        data_store[ticker] = df.loc[mask]
                        loaded_from_cache = True
                except Exception as e:
                    print(f"[!] Cache read error for {ticker}: {e}")

            if not loaded_from_cache:
                missing_tickers.append(ticker)

        # 批量下载缺失数据 (Batch Downloading)
        if missing_tickers:
            print(f"[*] Downloading {len(missing_tickers)} tickers from API...")
            try:
                # yfinance 批量下载通过空格分隔Ticker字符串
                tickers_str = " ".join(missing_tickers)
                # 使用 threads=True 开启多线程加速
                download_data = yf.download(
                    tickers_str,
                    start=self.start_date,
                    end=self.end_date,
                    group_by='ticker',
                    auto_adjust=True,
                    threads=True,
                    progress=False
                )

                # 处理批量下载的数据结构
                if len(missing_tickers) == 1:
                    # 单个Ticker的情况
                    ticker = missing_tickers
                    df = download_data
                    if not df.empty:
                        self._save_to_cache(ticker, df)
                        data_store[ticker] = df
                else:
                    # 多个Ticker的情况，yfinance返回MultiIndex
                    for ticker in missing_tickers:
                        try:
                            df = download_data[ticker].copy()
                            # 清除全NaN行（例如停牌日）
                            df.dropna(how='all', inplace=True)
                            if not df.empty:
                                self._save_to_cache(ticker, df)
                                data_store[ticker] = df
                            else:
                                print(f"[!] No data found for {ticker}")
                        except KeyError:
                            print(f"[!] Ticker {ticker} parsing failed.")

            except Exception as e:
                print(f"[!!] Critical API Error: {e}")

        print(f"[*] Data ingestion complete. Loaded {len(data_store)} tickers.")
        return data_store

    def _save_to_cache(self, ticker, df):
        """将数据保存为Parquet格式"""
        try:
            cache_path = self._get_cache_path(ticker)
            df.to_parquet(cache_path)
        except Exception as e:
            print(f"[!] Failed to write cache for {ticker}: {e}")

    def get_aligned_prices(self, data_store):
        """
        数据对齐：将所有股票的收盘价合并到一个DataFrame。
        处理不同股票停牌导致的日期不一致问题。
        """
        close_prices = pd.DataFrame()
        volume_data = pd.DataFrame()

        for ticker, df in data_store.items():
            if 'Close' in df.columns:
                close_prices[ticker] = df['Close']
            if 'Volume' in df.columns:
                volume_data[ticker] = df['Volume']

        # 前向填充（Forward Fill）：假设停牌期间价格不变
        close_prices.fillna(method='ffill', inplace=True)
        # 后向填充作为兜底
        close_prices.fillna(method='bfill', inplace=True)

        # 再次丢弃仍有NaN的行（通常是最初始的日期）
        close_prices.dropna(inplace=True)

        # 对齐成交量数据，缺失填充为0
        volume_data = volume_data.reindex(close_prices.index).fillna(0)

        return close_prices, volume_data


# breadth_analyzer.py
import pandas as pd
import numpy as np
from config import PARAMS


class BreadthAnalyzer:
    def __init__(self, close_df, volume_df):
        self.close_df = close_df
        self.volume_df = volume_df
        self.results = pd.DataFrame(index=close_df.index)

    def compute_basic_stats(self):
        """计算基础的涨跌家数"""
        # 计算日收益率
        daily_returns = self.close_df.pct_change()

        # 统计上涨、下跌、平盘家数
        # axis=1 表示按行（每天）统计
        self.results['Advances'] = daily_returns.apply(lambda x: (x > 0).sum(), axis=1)
        self.results = daily_returns.apply(lambda x: (x < 0).sum(), axis=1)
        self.results['Unchanged'] = daily_returns.apply(lambda x: (x == 0).sum(), axis=1)
        self.results = self.results['Advances'] + self.results + self.results['Unchanged']

        # 1. 腾落线 (AD Line)
        self.results['Net_Advances'] = self.results['Advances'] - self.results
        self.results = self.results['Net_Advances'].cumsum()

        return self.results

    def compute_mcclellan_indicators(self):
        """计算麦克莱伦振荡器与求和指数"""
        # 防止除以零
        total = self.results.replace(0, np.nan)

        # Ratio Adjusted Net Advances
        rana = (self.results['Net_Advances'] / total) * 1000
        rana = rana.fillna(0)

        # EMA Calculation
        ema_fast = rana.ewm(span=PARAMS, adjust=False).mean()
        ema_slow = rana.ewm(span=PARAMS, adjust=False).mean()

        # 2. McClellan Oscillator
        self.results['McClellan_Oscillator'] = ema_fast - ema_slow

        # 3. McClellan Summation Index (累积振荡器)
        self.results = self.results['McClellan_Oscillator'].cumsum()

        return self.results

    def compute_trin(self):
        """计算阿姆斯指数 (TRIN)"""
        # 计算上涨股总成交量和下跌股总成交量
        # 我们需要知道哪些股票是涨的，哪些是跌的
        daily_returns = self.close_df.pct_change()

        up_vol = pd.Series(0.0, index=self.close_df.index)
        down_vol = pd.Series(0.0, index=self.close_df.index)

        # 这里的向量化处理稍显复杂，为了清晰使用循环，
        # 在生产环境中可用 numpy.where 进行优化
        up_mask = (daily_returns > 0)
        down_mask = (daily_returns < 0)

        # 利用Pandas的乘法对齐特性
        up_vol = (self.volume_df * up_mask).sum(axis=1)
        down_vol = (self.volume_df * down_mask).sum(axis=1)

        # AD Ratio
        ad_ratio = self.results['Advances'] / self.results.replace(0, 1)

        # Volume Ratio
        vol_ratio = up_vol / down_vol.replace(0, 1)

        # 4. TRIN
        self.results = ad_ratio / vol_ratio

        # 平滑处理TRIN（通常看10日均线）
        self.results = self.results.rolling(window=10).mean()

        return self.results

    def compute_ma_breadth(self):
        """计算均线宽度 (% Above MA)"""
        # 50日均线宽度
        sma50 = self.close_df.rolling(window=PARAMS).mean()
        above50 = (self.close_df > sma50).sum(axis=1)
        pct_above50 = (above50 / self.close_df.shape[1]) * 100
        self.results = pct_above50

        # 200日均线宽度
        sma200 = self.close_df.rolling(window=PARAMS).mean()
        above200 = (self.close_df > sma200).sum(axis=1)
        pct_above200 = (above200 / self.close_df.shape[1]) * 100
        self.results = pct_above200

        return self.results


# main.py
import matplotlib.pyplot as plt
import pandas as pd
from data_engine import DataEngine
from breadth_analyzer import BreadthAnalyzer
from config import MARKET_UNIVERSES


def main():
    # --- 1. 设置与数据获取 ---
    # 选择要分析的市场，这里以港股蓝筹为例
    # 用户可以切换为 'US_TECH_GIANTS' 或 'US_SECTORS'
    target_universe = 'HK_BLUE_CHIPS'
    tickers = MARKET_UNIVERSES[target_universe]

    start_date = "2022-01-01"

    print(f"--- Market Breadth Analysis System ---")
    print(f"Target Universe: {target_universe}")

    engine = DataEngine(tickers, start_date)
    data_store = engine.fetch_data()

    if not data_store:
        print("No data loaded. Exiting.")
        return

    # 对齐数据
    close_df, vol_df = engine.get_aligned_prices(data_store)
    print(f"Data aligned. Shape: {close_df.shape}")

    # --- 2. 指标计算 ---
    analyzer = BreadthAnalyzer(close_df, vol_df)
    analyzer.compute_basic_stats()
    analyzer.compute_mcclellan_indicators()
    analyzer.compute_trin()
    metrics = analyzer.compute_ma_breadth()

    # --- 3. 可视化报告 ---
    print("Generating Dashboard...")

    # 创建一个风格化的仪表盘
    plt.style.use('bmh')  # 使用一种专业的金融图表风格
    fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(14, 20), sharex=True)

    # 图表 1: 腾落线 (ADL) vs 指数 (使用成分股的平均值作为指数代理)
    # 在实际中，应下载对应的指数数据 (如 ^HSI) 进行对比
    proxy_index = close_df.mean(axis=1)

    ax1 = axes
    ax1.set_title(f'{target_universe} - Advance/Decline Line vs Equal-Weight Index', fontsize=14)
    ax1.plot(metrics.index, metrics, label='AD Line (Breadth)', color='#1f77b4', linewidth=2)

    ax1_twin = ax1.twinx()
    ax1_twin.plot(proxy_index.index, proxy_index, label='Equal-Weight Index (Price)', color='#d62728', linestyle='--',
                  alpha=0.7)

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')

    # 图表 2: McClellan Oscillator
    ax2 = axes[1]
    ax2.set_title('McClellan Oscillator (Momentum)', fontsize=14)
    ax2.bar(metrics.index, metrics['McClellan_Oscillator'], color='gray', alpha=0.8, label='Oscillator')
    # 绘制阈值线
    ax2.axhline(0, color='black', linewidth=1)
    ax2.axhline(50, color='red', linestyle=':', label='Overbought zone')  # 阈值因市场而异，这里取50演示
    ax2.axhline(-50, color='green', linestyle=':', label='Oversold zone')
    ax2.legend(loc='upper left')

    # 图表 3: TRIN (Arms Index)
    ax3 = axes
    ax3.set_title('TRIN / Arms Index (Volume Sentiment)', fontsize=14)
    # TRIN通常是倒置看的，或者 >1 看空。为了方便，我们画10日均线
    ax3.plot(metrics.index, metrics, color='purple', label='TRIN (10-day SMA)')
    ax3.axhline(1.0, color='black', linestyle='-')
    ax3.fill_between(metrics.index, metrics, 1.0, where=(metrics > 1), facecolor='red', alpha=0.3, label='Bearish Vol')
    ax3.fill_between(metrics.index, metrics, 1.0, where=(metrics < 1), facecolor='green', alpha=0.3,
                     label='Bullish Vol')
    ax3.set_ylim(0.5, 2.0)  # 限制Y轴防止极端值破坏图表
    ax3.legend(loc='upper left')

    # 图表 4: 均线体制 (% Above SMA200)
    ax4 = axes
    ax4.set_title('Market Regime: % Stocks Above SMA 200', fontsize=14)
    ax4.plot(metrics.index, metrics, color='orange', linewidth=2)
    ax4.axhline(50, color='black', linestyle='-', linewidth=1.5)
    ax4.axhline(80, color='red', linestyle='--', label='Overheated (>80%)')
    ax4.axhline(20, color='green', linestyle='--', label='Oversold (<20%)')
    ax4.fill_between(metrics.index, metrics, 50, where=(metrics >= 50), facecolor='gold', alpha=0.2,
                     label='Bull Regime')
    ax4.legend(loc='upper left')
    ax4.set_ylim(0, 100)

    plt.tight_layout()
    plt.show()
    print("Dashboard generated successfully.")


if __name__ == "__main__":
    main()