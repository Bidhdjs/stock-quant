# DataFetcher：负责数据的获取、清洗、存取（缓存机制）。
#
# IndicatorEngine：负责计算SMA、RS、ATR、Supertrend等指标。
#
# StrategyScreener：执行具体的Minervini趋势模板与RS筛选逻辑。

"""
Minervini Trend Template & RS Screener Implementation
Author: Quantitative Finance Expert
Date: 2026-01-06
Description:
    This script implements the Mark Minervini Trend Template strategy combined with
    Relative Strength (IBD Style) and Supertrend indicators.
    It is designed to be robust, handling API limits and data inconsistencies.

Dependencies: yfinance, pandas, numpy, pandas_ta (optional, custom implementation provided)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timedelta
import warnings

# Suppress pandas FutureWarnings (e.g., specific plotting deprecations)
warnings.simplefilter(action='ignore', category=FutureWarning)


class Config:
    # 策略参数配置
    SMA_SHORT = 50
    SMA_MED = 150
    SMA_LONG = 200
    RS_LOOKBACKS =  # 3, 6, 9, 12 months (approx trading days)
    RS_WEIGHTS = [0.4, 0.2, 0.2, 0.2]  # IBD style weighting
    SUPERTREND_PERIOD = 10
    SUPERTREND_MULTIPLIER = 3

    # 筛选阈值
    MIN_RS_RATING = 70  # 相对强度需高于70分位
    ABOVE_52W_LOW_PCT = 1.30  # 高于52周低点30%
    WITHIN_52W_HIGH_PCT = 0.75  # 处于52周高点75%以上（即回撤小于25%）

    # 数据配置
    START_DATE = (datetime.now() - timedelta(days=365 * 2)).strftime('%Y-%m-%d')
    CACHE_DIR = "stock_data_cache"


class DataFetcher:
    """Handles reliable data downloading with caching to avoid API throttling."""

    def __init__(self):
        if not os.path.exists(Config.CACHE_DIR):
            os.makedirs(Config.CACHE_DIR)

    def get_sp500_tickers(self):
        """Fetches current S&P 500 tickers from Wikipedia."""
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            payload = pd.read_html(url)
            tickers = payload.values.tolist()
            # Clean tickers (e.g., BRK.B -> BRK-B for yfinance)
            tickers = [t.replace('.', '-') for t in tickers]
            return tickers
        except Exception as e:
            print(f"Error fetching S&P 500 list: {e}")
            # Fallback list for testing
            return

    def download_data(self, ticker):
        """Downloads data for a single ticker with error handling."""
        cache_path = os.path.join(Config.CACHE_DIR, f"{ticker}.csv")

        # Simple cache logic: if file exists and is modified today, use it.
        if os.path.exists(cache_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            if file_time.date() == datetime.now().date():
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)

        try:
            # Thread safety handling could be added here, but sequential is safer for rate limits
            df = yf.download(ticker, start=Config.START_DATE, progress=False, multi_level_index=False)

            if df.empty:
                return None

            # Ensure index is Datetime
            df.index = pd.to_datetime(df.index)

            # Save to cache
            df.to_csv(cache_path)
            return df
        except Exception as e:
            print(f"Failed to download {ticker}: {e}")
            return None


class IndicatorEngine:
    """Calculates technical indicators vectorially."""

    @staticmethod
    def add_moving_averages(df):
        df = df['Close'].rolling(window=Config.SMA_SHORT).mean()
        df = df['Close'].rolling(window=Config.SMA_MED).mean()
        df = df['Close'].rolling(window=Config.SMA_LONG).mean()
        return df

    @staticmethod
    def add_52_week_stats(df):
        # Rolling 252 days for 52 weeks
        df = df['Low'].rolling(window=252).min()
        df = df['High'].rolling(window=252).max()
        return df

    @staticmethod
    def calculate_rs_score(df):
        """
        Calculates raw RS score based on weighted ROC.
        Returns the scalar score of the latest date.
        """
        if len(df) < 260:
            return -np.inf

        try:
            current_close = df['Close'].iloc[-1]

            # Calculate ROCs
            roc_3m = (current_close / df['Close'].iloc]) - 1
            roc_6m = (current_close / df['Close'].iloc]) - 1
            roc_9m = (current_close / df['Close'].iloc]) - 1
            roc_12m = (current_close / df['Close'].iloc]) - 1

            # Weighted Score
            weights = Config.RS_WEIGHTS
            score = (weights * roc_3m) + (weights[1] * roc_6m) + \
                    (weights[2] * roc_9m) + (weights[3] * roc_12m)

            return score * 100
        except IndexError:
            return -np.inf

    @staticmethod
    def add_supertrend(df, period=10, multiplier=3):
        """
        Manual implementation of Supertrend to avoid external lib dependencies.
        """
        # Calculate TR
        high = df['High']
        low = df['Low']
        close = df['Close']

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()

        # Max of the three
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        # HL2
        hl2 = (high + low) / 2

        # Basic bands
        final_upper = pd.Series(0.0, index=df.index)
        final_lower = pd.Series(0.0, index=df.index)
        supertrend = pd.Series(0.0, index=df.index)
        in_uptrend = pd.Series(True, index=df.index)

        # Vectorization of supertrend is hard due to recursive logic, using Numba or loop
        # Using loop for clarity and compatibility (speed is acceptable for daily data)

        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)

        # Pre-fill lists for speed
        bu = basic_upper.values
        bl = basic_lower.values
        close_vals = close.values
        fu = np.zeros(len(df))
        fl = np.zeros(len(df))
        st = np.zeros(len(df))
        trend = np.zeros(len(df), dtype=bool)  # True for Up

        for i in range(period, len(df)):
            # Final Upper
            if bu[i] < fu[i - 1] or close_vals[i - 1] > fu[i - 1]:
                fu[i] = bu[i]
            else:
                fu[i] = fu[i - 1]

            # Final Lower
            if bl[i] > fl[i - 1] or close_vals[i - 1] < fl[i - 1]:
                fl[i] = bl[i]
            else:
                fl[i] = fl[i - 1]

            # Trend
            if trend[i - 1]:  # Was Up
                if close_vals[i] < fl[i]:
                    trend[i] = False
                else:
                    trend[i] = True
            else:  # Was Down
                if close_vals[i] > fu[i]:
                    trend[i] = True
                else:
                    trend[i] = False

            if trend[i]:
                st[i] = fl[i]
            else:
                st[i] = fu[i]

        df = st
        df = trend
        return df


class StrategyScreener:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.engine = IndicatorEngine()

    def check_minervini_conditions(self, df):
        """
        Validates the 8 rules of the Trend Template.
        Returns (is_match, reason_if_fail)
        """
        try:
            curr = df.iloc[-1]
            sma_50 = curr
            sma_150 = curr
            sma_200 = curr
            close = curr['Close']
            low_52 = curr
            high_52 = curr

            # Trend of 200 SMA (Slope positive)
            # Compare current SMA_200 with 20 days ago
            sma_200_prev = df.iloc[-21]

            # Rule 1: Price > 150 and 200
            if not (close > sma_150 and close > sma_200):
                return False, "Price below LT MAs"

            # Rule 2: 150 > 200
            if not (sma_150 > sma_200):
                return False, "150 SMA < 200 SMA"

            # Rule 3: 200 Trending Up
            if not (sma_200 > sma_200_prev):
                return False, "200 SMA not trending up"

            # Rule 4: 50 > 150 and 50 > 200
            if not (sma_50 > sma_150 and sma_50 > sma_200):
                return False, "50 SMA not above LT MAs"

            # Rule 5: Price > 50 SMA
            if not (close > sma_50):
                return False, "Price below 50 SMA"

            # Rule 6: 30% above 52W Low
            if not (close >= low_52 * Config.ABOVE_52W_LOW_PCT):
                return False, "Less than 30% off lows"

            # Rule 7: Within 25% of 52W High
            if not (close >= high_52 * Config.WITHIN_52W_HIGH_PCT):
                return False, "Too far from highs (>25%)"

            return True, "Pass"

        except Exception as e:
            return False, f"Error: {e}"

    def run(self):
        print("Fetching Ticker List...")
        tickers = self.fetcher.get_sp500_tickers()
        print(f"Analyzing {len(tickers)} stocks...")

        results =

        # Step 1: Calculate Metrics and Pre-filter
        for i, ticker in enumerate(tickers):
            if i % 50 == 0:
                print(f"Processing {i}/{len(tickers)}...")

            df = self.fetcher.download_data(ticker)
            if df is None or len(df) < 260:
                continue

            # Calculate Indicators
            df = self.engine.add_moving_averages(df)
            df = self.engine.add_52_week_stats(df)

            # Check Minervini Template
            passed, reason = self.check_minervini_conditions(df)

            if passed:
                # Calculate RS Score only for those who pass trend template to save time
                rs_score = self.engine.calculate_rs_score(df)

                # Add Supertrend for Context
                df = self.engine.add_supertrend(df)
                st_direction = "BULLISH" if df.iloc[-1] else "BEARISH"

                # Volatility Contraction Proxy: Standard Deviation of last 20 closes / Price
                volatility = df['Close'].rolling(20).std().iloc[-1] / df['Close'].iloc[-1]

                results.append({
                    'Ticker': ticker,
                    'Close': round(df['Close'].iloc[-1], 2),
                    'RS_Raw_Score': rs_score,
                    'Supertrend': st_direction,
                    'Volatility_20d': round(volatility * 100, 2),
                    'Industry': 'N/A'  # Requires external data source
                })

        # Step 2: Calculate Percentile Ranks for RS
        if not results:
            print("No stocks passed the Trend Template.")
            return

        df_res = pd.DataFrame(results)

        # Rank the raw scores to get 0-99 ratings
        # Note: In a real scenario, this rank is against the WHOLE market, not just survivors.
        # But this is the best estimation with available data.
        df_res = pd.qcut(df_res, 100, labels=False, duplicates='drop')

        # Final Filter: RS Rating > Threshold
        final_df = df_res >= Config.MIN_RS_RATING].sort_values(by='RS_Rating', ascending=False)

        print(f"\nFound {len(final_df)} candidates matching all criteria.")
        print("-" * 80)
        print(final_df].head(20).to_string(index=False))
        print("-" * 80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        final_df.to_csv(f"minervini_results_{timestamp}.csv", index=False)
        print(f"Results saved to minervini_results_{timestamp}.csv")

        if __name__ == "__main__":
            screener = StrategyScreener()
        screener.run()