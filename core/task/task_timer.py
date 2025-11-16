import requests
import json
import time
import logging
from datetime import datetime, timedelta
import os
import schedule
from common.logger import create_log
from common.util_html import signals_to_html, save_clean_html
from settings import signals_root

logger = create_log('task_timer')

# API基础URL
BASE_URL = "http://localhost:5000"

# 配置目标股票列表
TARGET_STOCKS = [
    # 港股示例
    # {"market": "hk", "data_source": "akshare", "stock_code": "HK.09988", "adjust_type": "qfq"},  # 腾讯控股
    # 美股示例
    {"market": "us", "data_source": "akshare", "stock_code": "US.IVV", "adjust_type": "qfq"},  # 标普500 ETF
    # A股示例
    {"market": "cn", "data_source": "baostock", "stock_code": "SH.600519", "adjust_type": "qfq"}  # 贵州茅台
]

# 配置回测参数
BACKTEST_CONFIG = {
    "strategy": "EnhancedVolumeStrategy",
    "init_cash": 5000000
}


def get_stock_data(stock_config):
    """
    通过接口获取股票数据
    """
    logger.info(f"开始获取股票数据: {stock_config['stock_code']}")

    # 计算日期范围（最近365天）
    data_pattern = '%Y-%m-%d'
    end_date = datetime.now().strftime(data_pattern)
    start_date = (datetime.now() - timedelta(days=365*4)).strftime(data_pattern)
    adjust_type = stock_config["adjust_type"]

    url = f"{BASE_URL}/acquire_stock_data"
    payload = {
        "market": stock_config["market"],
        "data_source": stock_config["data_source"],
        "stock_code": stock_config["stock_code"],
        "start_date": start_date,
        "end_date": end_date,
        "adjust_type": adjust_type
    }

    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()

        if result.get('success'):
            filename = result.get('data', {}).get('filename')
            logger.info(f"股票数据获取成功: {stock_config['stock_code']}, 文件名: {filename}")
            if filename:
                logger.info(f"股票数据文件: {filename}")
                # 保存数据文件名到配置中
                stock_config["filename"] = filename
            return True
        else:
            logger.error(f"股票数据获取失败: {stock_config['stock_code']}, 错误: {result.get('message')}")
            return False
    except Exception as e:
        logger.error(f"获取股票数据时发生异常: {stock_config['stock_code']}, 异常: {str(e)}")
        return False


def run_backtest_for_stocks():
    """
    通过接口运行回测，使用TARGET_STOCKS中的数据源和股票信息
    """
    logger.info("开始运行回测")

    # 使用TARGET_STOCKS中配置的股票和数据源
    success_count = 0
    for stock in TARGET_STOCKS:
        stock_code = stock["stock_code"]
        data_source = stock["data_source"]
        stock_file = stock["filename"]

        try:
            if not stock_file:
                logger.error(f"未找到股票文件: {stock_code} in {data_source}")
                continue

            logger.info(f"找到股票文件: {stock_file}, 开始回测")

            # 运行回测
            url = f"{BASE_URL}/run_backtest"
            payload = {
                "source": data_source,
                "stock_file": stock_file,
                "is_batch": False,
                "init_cash": BACKTEST_CONFIG["init_cash"],
                "strategy": BACKTEST_CONFIG["strategy"]
            }

            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            backtest_result = response.json()

            if backtest_result.get('success'):
                logger.info(f"回测成功: {stock_code} in {data_source}")
                success_count += 1
            else:
                logger.error(f"回测失败: {stock_code} in {data_source}, 错误: {backtest_result.get('message')}")

            # 避免请求过于频繁
            time.sleep(5)
        except Exception as e:
            logger.error(f"运行回测时发生异常: {stock_code} in {data_source}, 异常: {str(e)}")
            return False

    logger.info(f"回测完成，成功: {success_count}/{len(TARGET_STOCKS)}")
    return True


def check_yesterday_signals():
    """
    检查昨天买入信号
    """
    logger.info("开始检查昨天信号")

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_day = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    try:
        # 获取所有信号文件
        response = requests.get(f"{BASE_URL}/get_signal_files")
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            logger.error(f"获取信号文件失败: {result.get('message')}")
            return

        signal_files = result.get('data', {}).get('signal_files', [])
        logger.info(f"获取到 {len(signal_files)} 个信号文件")

        url = f"{BASE_URL}/analyze_signals"
        all_signal_files = []
        target_signal_file = []
        for signal_file in signal_files:
            all_signal_files.append(signal_file['file_path'])
        for signal_file in all_signal_files:
            for stock in TARGET_STOCKS:
                data_source = stock["data_source"]
                stock_file = stock["filename"]
                if data_source in signal_file and stock_file.replace('.csv', '') in signal_file:
                    target_signal_file.append(signal_file)
        if len(target_signal_file) == 0:
            for stock in TARGET_STOCKS:
                stock_file = stock["filename"]
                logger.error(f"没有信号文件包含股票 {stock_file.replace('.csv', '')}")
            return
        else:
            logger.info(f"找到 {len(target_signal_file)} 个信号文件包含目标股票")

        payload = {
            "file_paths": target_signal_file,
            "filters": {
                "start_date": start_day,
                "end_date": yesterday,
                "strategy_name": "",
                "stock_code": "",
                "signal_type": ""
            }
        }

        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        analyze_result = response.json()

        if analyze_result.get('success'):
            signals = analyze_result.get('data', {}).get('signals', [])
            total_signals_count = analyze_result.get('data', {}).get('summary', {}).get('total_signals', 0)

            logger.info(f"昨天共有 {total_signals_count} 个信号")

            # 打印每个信号
            for signal in signals:
                logger.debug(f"信号: 股票={signal.get('stock_info')}, 日期={signal.get('date')}, "
                            f"信号类型={signal.get('signal_type')}, 策略={signal.get('strategy_name')}")

            summary = analyze_result.get('data', {}).get('summary', {})
            filters = analyze_result.get('data', {}).get('filters', {})
            html = signals_to_html(signals, filters, summary)
            save_clean_html(html)
            logger.info("成功检查昨天信号，并下载信号HTML完成")
            return True
        else:
            logger.error(f"分析信号失败: {analyze_result.get('message')}")
            return False

    except Exception as e:
        logger.error(f"检查信号过程中发生异常: {str(e)}")
        return False

def daily_task():
    """
    每日定时任务主函数
    """
    logger.info("===== 开始执行每日定时任务 =====")

    # 1. 获取股票数据
    for stock in TARGET_STOCKS:
        if not get_stock_data(stock):
            return

    # 2. 运行回测
    if not run_backtest_for_stocks():
        return
    #
    # 3. 检查当天信号
    check_yesterday_signals()



    logger.info("===== 每日定时任务执行完毕 =====")


def schedule_tasks():
    """
    设置定时任务
    """
    # 设置每天15:00执行
    time_pattern = "19:04"
    schedule.every().day.at(time_pattern).do(daily_task)

    logger.info(f"定时任务已设置，每天{time_pattern}执行")

    # 持续运行定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    # 可以选择立即执行一次任务，或者直接启动定时任务
    # daily_task()  # 立即执行一次
    schedule_tasks()  # 启动定时任务
