"""
yfinance 数据源管理器
支持美股、港股、台股等全球市场数据获取

数学原理：
1. 复权处理：使用 auto_adjust=True 自动调整价格，消除分红和拆股对历史价格序列的影响
2. 数据对齐：处理不同市场交易日历差异，使用前向填充(ffill)处理缺失值
"""

import os
import datetime
from typing import Tuple, Optional, List
from pathlib import Path

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from common.logger import create_log
from common.util_csv import save_to_csv
from core.stock.manager_common import standardize_stock_data
from settings import stock_data_root

logger = create_log('manager_yfinance')

# yfinance 市场代码后缀映射
MARKET_SUFFIX_MAP = {
    'US': '',           # 美股无后缀
    'HK': '.HK',        # 港股
    'TW': '.TW',        # 台股
    'JP': '.T',         # 日本东京证券交易所
    'UK': '.L',         # 伦敦证券交易所
    'DE': '.DE',        # 德国法兰克福
    'SG': '.SI',        # 新加坡
    'AU': '.AX',        # 澳大利亚
}

# 市场名称映射
MARKET_NAME_MAP = {
    'US': '美股',
    'HK': '港股',
    'TW': '台股',
    'JP': '日股',
    'UK': '英股',
    'DE': '德股',
    'SG': '新加坡股',
    'AU': '澳股',
}


class YFinanceManager:
    """
    yfinance 数据管理器
    
    特性：
    1. 支持全球多市场数据获取
    2. 自动处理 yfinance 新版本的 MultiIndex 列名问题
    3. 统一输出格式，与项目其他数据源兼容
    """
    
    def __init__(self):
        """初始化管理器"""
        pass
    
    def _get_yf_ticker(self, stock_code: str, market: str) -> str:
        """
        转换股票代码为 yfinance 格式
        
        Args:
            stock_code: 原始股票代码 (如 '00700', 'AAPL')
            market: 市场代码 (如 'HK', 'US')
        
        Returns:
            yfinance 格式的股票代码 (如 '0700.HK', 'AAPL')
        """
        market = market.upper()
        suffix = MARKET_SUFFIX_MAP.get(market, '')
        
        # 港股需要去掉前导零并补足4位
        if market == 'HK':
            # 移除可能的前缀
            code = stock_code.replace('HK.', '').lstrip('0')
            # 港股代码需要4位数字
            code = code.zfill(4)
            return f"{code}{suffix}"
        
        # 美股移除可能的前缀
        if market == 'US':
            code = stock_code.replace('US.', '')
            return f"{code}{suffix}"
        
        # 其他市场直接拼接
        return f"{stock_code}{suffix}"
    
    def _handle_multiindex_columns(self, df: DataFrame) -> DataFrame:
        """
        处理 yfinance 新版本返回的 MultiIndex 列名
        
        数学原理：
        yfinance >= 0.2.0 版本在下载单只股票时可能返回 MultiIndex 列，
        如 ('Close', 'AAPL')，需要展平为单层列名 'Close'
        
        Args:
            df: 原始 DataFrame
        
        Returns:
            处理后的 DataFrame
        """
        if isinstance(df.columns, pd.MultiIndex):
            # 取第一层列名
            df.columns = df.columns.get_level_values(0)
        return df
    
    def get_stock_data(
        self, 
        stock_code: str, 
        market: str,
        start_date: str, 
        end_date: str,
        auto_adjust: bool = True
    ) -> DataFrame:
        """
        获取单只股票的历史数据
        
        数学原理：
        1. auto_adjust=True: 价格 = 原始价格 × 调整因子
           调整因子考虑了分红除息和股票拆分，使得历史价格可比
        2. 成交量也会相应调整，确保量价关系一致性
        
        Args:
            stock_code: 股票代码
            market: 市场代码 ('US', 'HK', 'TW' 等)
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            auto_adjust: 是否自动复权，默认 True
        
        Returns:
            标准化后的 DataFrame
        """
        yf_ticker = self._get_yf_ticker(stock_code, market)
        logger.info(f"开始获取 {market}.{stock_code} ({yf_ticker}) 历史数据...")
        
        try:
            # 下载数据
            df = yf.download(
                yf_ticker,
                start=start_date,
                end=end_date,
                auto_adjust=auto_adjust,
                progress=False,  # 关闭进度条
                threads=False    # 单线程更稳定
            )
            
            if df.empty:
                logger.warning(f"未获取到 {yf_ticker} 的数据")
                return pd.DataFrame()
            
            # 处理 MultiIndex 列名
            df = self._handle_multiindex_columns(df)
            
            # 重置索引，将日期从索引变为列
            df = df.reset_index()
            
            # 重命名列为小写，与项目标准一致
            column_map = {
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Adj Close': 'adj_close'
            }
            df = df.rename(columns=column_map)
            
            # 确保日期格式正确
            df['date'] = pd.to_datetime(df['date'])
            
            # 获取股票名称
            stock_name = self._get_stock_name(yf_ticker)
            market_name = MARKET_NAME_MAP.get(market.upper(), market)
            display_name = f"{market_name}{stock_name}"
            
            # 标准化数据格式
            df = standardize_stock_data(
                df=df,
                stock_code=stock_code,
                stock_name=display_name,
                market=market.upper()
            )
            
            logger.info(f"成功获取 {market}.{stock_code} 数据，共 {len(df)} 条记录")
            if not df.empty:
                logger.info(f"数据时间范围: {df['date'].min()} 至 {df['date'].max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"获取 {yf_ticker} 数据失败: {str(e)}")
            return pd.DataFrame()
    
    def _get_stock_name(self, yf_ticker: str) -> str:
        """
        获取股票名称
        
        Args:
            yf_ticker: yfinance 格式的股票代码
        
        Returns:
            股票名称，获取失败则返回代码本身
        """
        try:
            ticker_obj = yf.Ticker(yf_ticker)
            info = ticker_obj.info
            # 优先使用 shortName，其次 longName
            return info.get('shortName') or info.get('longName') or yf_ticker
        except Exception as e:
            logger.warning(f"获取 {yf_ticker} 名称失败: {e}")
            return yf_ticker
    
    def get_batch_data(
        self,
        ticker_list: List[str],
        market: str,
        start_date: str,
        end_date: str
    ) -> dict:
        """
        批量获取多只股票数据
        
        数学原理：
        yfinance 支持批量下载，通过空格分隔的 ticker 字符串一次性请求
        减少 API 调用次数，提高效率
        
        Args:
            ticker_list: 股票代码列表
            market: 市场代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            dict: {stock_code: DataFrame}
        """
        # 转换所有代码为 yfinance 格式
        yf_tickers = [self._get_yf_ticker(code, market) for code in ticker_list]
        tickers_str = ' '.join(yf_tickers)
        
        logger.info(f"批量获取 {len(ticker_list)} 只 {market} 股票数据...")
        
        try:
            # 批量下载
            data = yf.download(
                tickers_str,
                start=start_date,
                end=end_date,
                group_by='ticker',
                auto_adjust=True,
                threads=True,
                progress=False
            )
            
            result = {}
            
            # 单只股票的情况
            if len(ticker_list) == 1:
                df = self._handle_multiindex_columns(data)
                if not df.empty:
                    result[ticker_list[0]] = self._process_single_df(
                        df, ticker_list[0], market
                    )
            else:
                # 多只股票的情况，遍历处理
                for code, yf_ticker in zip(ticker_list, yf_tickers):
                    try:
                        df = data[yf_ticker].copy()
                        df = df.dropna(how='all')  # 移除全空行
                        if not df.empty:
                            result[code] = self._process_single_df(df, code, market)
                    except KeyError:
                        logger.warning(f"未找到 {yf_ticker} 的数据")
                        continue
            
            logger.info(f"批量获取完成，成功 {len(result)}/{len(ticker_list)} 只")
            return result
            
        except Exception as e:
            logger.error(f"批量获取数据失败: {str(e)}")
            return {}
    
    def _process_single_df(
        self, 
        df: DataFrame, 
        stock_code: str, 
        market: str
    ) -> DataFrame:
        """
        处理单只股票的 DataFrame
        
        Args:
            df: 原始数据
            stock_code: 股票代码
            market: 市场代码
        
        Returns:
            标准化后的 DataFrame
        """
        df = df.reset_index()
        column_map = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        df = df.rename(columns=column_map)
        df['date'] = pd.to_datetime(df['date'])
        
        market_name = MARKET_NAME_MAP.get(market.upper(), market)
        
        return standardize_stock_data(
            df=df,
            stock_code=stock_code,
            stock_name=f"{market_name}{stock_code}",
            market=market.upper()
        )


# ============================================================
# 便捷函数：与其他数据源管理器保持一致的接口
# ============================================================

def get_stock_history(
    stock_code: str,
    market: str,
    start_date: str,
    end_date: str
) -> DataFrame:
    """
    获取股票历史数据（便捷函数）
    
    Args:
        stock_code: 股票代码
        market: 市场代码 ('US', 'HK', 'TW' 等)
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        标准化的 DataFrame
    """
    manager = YFinanceManager()
    return manager.get_stock_data(stock_code, market, start_date, end_date)


def get_single_stock_history(
    stock_code: str,
    market: str,
    start_date: str,
    end_date: str,
    output_dir: str = 'yfinance'
) -> Tuple[bool, Optional[str]]:
    """
    获取单只股票历史数据并保存到 CSV
    
    与 manager_akshare.get_single_hk_stock_history 保持一致的接口
    
    Args:
        stock_code: 股票代码
        market: 市场代码
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
    
    Returns:
        Tuple[bool, str]: (是否成功, CSV文件名)
    """
    try:
        manager = YFinanceManager()
        df = manager.get_stock_data(stock_code, market, start_date, end_date)
        
        if df.empty:
            return False, None
        
        # 获取股票名称
        stock_name = df['stock_name'].iloc[0] if 'stock_name' in df.columns else stock_code
        
        # 构建文件名
        date_min = df['date'].min()
        date_max = df['date'].max()
        
        # 处理日期格式
        if hasattr(date_min, 'strftime'):
            start_fmt = date_min.strftime('%Y%m%d')
            end_fmt = date_max.strftime('%Y%m%d')
        else:
            start_fmt = str(date_min).replace('-', '')[:8]
            end_fmt = str(date_max).replace('-', '')[:8]
        
        # 清理股票代码中的前缀
        clean_code = stock_code.replace('US.', '').replace('HK.', '')
        csv_name = f"{clean_code}_{stock_name}_{start_fmt}_{end_fmt}.csv"
        
        # 保存文件
        output_path = os.path.join(stock_data_root, output_dir)
        os.makedirs(output_path, exist_ok=True)
        
        filename = os.path.join(output_path, csv_name)
        save_to_csv(df.round(2), filename)
        
        logger.info(f"数据已保存至: {filename}")
        return True, csv_name
            
    except Exception as e:
        logger.error(f"保存 {market}.{stock_code} 数据失败: {str(e)}")
        return False, None


def get_us_stock_history(
    stock_code: str,
    start_date: str,
    end_date: str,
    output_dir: str = 'yfinance'
) -> Tuple[bool, Optional[str]]:
    """
    获取美股历史数据并保存（便捷函数）
    
    Args:
        stock_code: 美股代码 (如 'AAPL', 'MSFT')
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
    
    Returns:
        Tuple[bool, str]: (是否成功, CSV文件名)
    """
    return get_single_stock_history(stock_code, 'US', start_date, end_date, output_dir)


def get_hk_stock_history(
    stock_code: str,
    start_date: str,
    end_date: str,
    output_dir: str = 'yfinance'
) -> Tuple[bool, Optional[str]]:
    """
    获取港股历史数据并保存（便捷函数）
    
    Args:
        stock_code: 港股代码 (如 '00700', '09988')
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
    
    Returns:
        Tuple[bool, str]: (是否成功, CSV文件名)
    """
    return get_single_stock_history(stock_code, 'HK', start_date, end_date, output_dir)


def get_index_data(
    index_code: str,
    start_date: str,
    end_date: str
) -> DataFrame:
    """
    获取指数数据（用于 RS Rating 计算）
    
    常用指数代码：
    - ^GSPC: 标普500
    - ^DJI: 道琼斯
    - ^IXIC: 纳斯达克
    - ^HSI: 恒生指数
    - ^TWII: 台湾加权指数
    
    Args:
        index_code: 指数代码 (含 ^ 前缀)
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        DataFrame
    """
    logger.info(f"获取指数 {index_code} 数据...")
    
    try:
        df = yf.download(
            index_code,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False
        )
        
        if df.empty:
            logger.warning(f"未获取到 {index_code} 的数据")
            return pd.DataFrame()
        
        # 处理 MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df.reset_index()
        df.columns = [col.lower() for col in df.columns]
        
        logger.info(f"成功获取 {index_code} 数据，共 {len(df)} 条")
        return df
        
    except Exception as e:
        logger.error(f"获取 {index_code} 数据失败: {str(e)}")
        return pd.DataFrame()


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    # 设置日期范围
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=365*2)).strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("yfinance 数据源管理器测试")
    print("=" * 60)
    
    # 测试1：获取美股数据
    print("\n[测试1] 获取美股 AAPL 数据")
    success, filename = get_us_stock_history(
        stock_code="AAPL",
        start_date=start_date,
        end_date=end_date
    )
    print(f"结果: {'成功' if success else '失败'}, 文件: {filename}")
    
    # 测试2：获取港股数据
    print("\n[测试2] 获取港股 00700 数据")
    success, filename = get_hk_stock_history(
        stock_code="00700",
        start_date=start_date,
        end_date=end_date
    )
    print(f"结果: {'成功' if success else '失败'}, 文件: {filename}")
    
    # 测试3：获取指数数据
    print("\n[测试3] 获取标普500指数数据")
    index_df = get_index_data("^GSPC", start_date, end_date)
    if not index_df.empty:
        print(f"成功获取 {len(index_df)} 条记录")
        print(index_df.head())
    
    # 测试4：批量获取数据
    print("\n[测试4] 批量获取美股数据")
    manager = YFinanceManager()
    batch_result = manager.get_batch_data(
        ticker_list=['AAPL', 'MSFT', 'GOOGL'],
        market='US',
        start_date=start_date,
        end_date=end_date
    )
    print(f"成功获取 {len(batch_result)} 只股票数据")
    for code, df in batch_result.items():
        print(f"  - {code}: {len(df)} 条记录")
