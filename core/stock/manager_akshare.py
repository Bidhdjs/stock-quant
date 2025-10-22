import os
import akshare as ak
import pandas as pd
from pandas import DataFrame

from common.logger import create_log
from common.util_csv import save_to_csv
from core.stock.manager_common import standardize_stock_data
from settings import stock_data_root

logger = create_log('manage_akshare')

def get_hk_stock_history(stock_code: str, start_date: str, end_date: str, adjust_type: str = 'qfq') -> DataFrame:
    """
    获取港股历史数据
    """
    try:
        logger.info(f"开始获取({stock_code}.HK)历史数据...")

        # 尝试获取港股历史数据
        df = ak.stock_hk_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust_type  # 前复权
        )

        if df.empty:
            logger.warning("未能获取到数据，尝试备用方法...")
            # 尝试备用方法
            df = ak.stock_hk_daily(symbol=stock_code)
            # 日期过滤
            if not df.empty and '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                mask = (df['日期'] >= start_date) & (df['日期'] <= end_date)
                df = df.loc[mask]

        if not df.empty:
            # 使用简单的股票名称格式
            stock_name = f"港股{stock_code}"

            # 标准化数据格式
            df = standardize_stock_data(df, stock_code, stock_name, 'HK')

            logger.info(f"成功获取{stock_name}历史数据，共 {len(df)} 条记录")
            if not df.empty:
                logger.info(f"数据时间范围: {df['date'].min()} 至 {df['date'].max()}")

            return df
        else:
            logger.warning(f"无法获取{stock_code}历史数据")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"获取港股 {stock_code} 数据时出错: {str(e)}")
        return pd.DataFrame()


def get_single_hk_stock_history(stock_code: str, start_date: str, end_date: str,
                                adjust_type: str = 'qfq', output_dir: str = 'akshare') -> bool:
    """
    获取单只港股的历史数据并保存到CSV
    """
    # 获取历史数据
    df = get_hk_stock_history(stock_code, start_date, end_date, adjust_type)

    if not df.empty:
        try:
            # 获取股票名称
            stock_name = df['stock_name'].iloc[0]

            # 获取日期范围并格式化
            start_date_formatted = df['date'].min().strftime('%Y%m%d')
            end_date_formatted = df['date'].max().strftime('%Y%m%d')

            # 确保输出目录存在
            output_path = os.path.join(stock_data_root, output_dir)
            os.makedirs(output_path, exist_ok=True)

            # 保存到CSV
            filename = os.path.join(output_path,
                                    f"{stock_code}_{stock_name}_{start_date_formatted}_{end_date_formatted}.csv")
            save_to_csv(df.round(2), filename)

            logger.info(f"数据已成功保存至: {filename}")
            return True
        except Exception as e:
            logger.error(f"保存港股 {stock_code} 数据时出错: {str(e)}")
            return False
    else:
        logger.warning(f"未能获取港股 {stock_code} 的数据")
        return False


if __name__ == "__main__":
    # 示例：获取单只港股数据
    get_single_hk_stock_history(
        stock_code="00700",  # 腾讯控股
        start_date="2021-01-01",
        end_date="2025-10-13",
        adjust_type='qfq'
    )
