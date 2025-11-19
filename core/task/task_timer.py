import requests
import json
import time
import logging
from datetime import datetime, timedelta
import os
import schedule
from common.logger import create_log
from common.util_html import signals_to_html, save_clean_html
from core.task.task_config import load_tasks
from settings import signals_root

logger = create_log('task_timer')

# API基础URL
BASE_URL = "http://localhost:5000"
# 全局任务列表和调度器
current_tasks = []
scheduled_jobs = {}

# 任务函数映射表
TASK_FUNCTIONS = {
    "daily_task": "daily_task",
    "get_stock_data_task": "get_stock_data_for_all",
    "run_backtest_task": "run_backtest_for_all",
    "check_signals_task": "check_recent_signals"
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

# 修改任务执行函数，传入任务特定的配置
def get_stock_data_for_all(target_stocks):
    """为指定的目标股票获取数据"""
    logger.info("开始为所有目标股票获取数据")
    success_count = 0
    for stock in target_stocks:
        if get_stock_data(stock):
            success_count += 1
    logger.info(f"股票数据获取完成，成功: {success_count}/{len(target_stocks)}")
    return success_count == len(target_stocks)


def run_backtest_for_stocks(target_stocks, backtest_config):
    """
    通过接口运行回测，使用TARGET_STOCKS中的数据源和股票信息
    """
    logger.info("开始为所有目标股票运行回测")
    # 使用TARGET_STOCKS中配置的股票和数据源
    success_count = 0
    for stock in target_stocks:
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
                "init_cash": backtest_config["init_cash"],
                "strategy": backtest_config["strategy"]
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


def check_yesterday_signals(target_stocks,days=365):
    """
    检查昨天买入信号
    """
    logger.info("开始检查昨天信号")

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_day = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
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
            for stock in target_stocks:
                data_source = stock["data_source"]
                stock_file = stock["filename"]
                if data_source in signal_file and stock_file.replace('.csv', '') in signal_file:
                    target_signal_file.append(signal_file)
        if len(target_signal_file) == 0:
            for stock in target_stocks:
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

def daily_task(target_stocks, backtest_config):
    """
    每日定时任务主函数
    """
    logger.info("===== 开始执行每日定时任务 =====")

    # 1. 获取股票数据
    for stock in target_stocks:
        if not get_stock_data(stock):
            return

    # 2. 运行回测
    if not run_backtest_for_stocks(target_stocks, backtest_config):
        return
    #
    # 3. 检查当天信号
    check_yesterday_signals(target_stocks)
    logger.info("===== 每日定时任务执行完毕 =====")


def execute_task(task_id, task_name, task_config):
    """
    执行指定的任务
    """
    logger.info(f"执行任务: {task_id} - {task_name}")

    # 获取任务特定的配置
    target_stocks = task_config.get("target_stocks", [])
    backtest_config = task_config.get("backtest_config", {})
    params = task_config.get("params", {})

    if not target_stocks:
        logger.error(f"任务 {task_id} 没有配置目标股票")
        return False

    try:
        # 根据任务名称执行相应的函数
        if task_name == "daily_task":
            daily_task(target_stocks, backtest_config)
        elif task_name == "get_stock_data_task":
            get_stock_data_for_all(target_stocks)
        elif task_name == "run_backtest_task":
            run_backtest_for_stocks(target_stocks, backtest_config)
        elif task_name == "check_signals_task":
            days = params.get("days", 1)
            check_yesterday_signals(target_stocks, days)
        else:
            logger.error(f"未知任务类型: {task_name}")
            return False

        logger.info(f"任务执行成功: {task_id}")
        return True
    except Exception as e:
        logger.error(f"执行任务时出错: {task_id}, 错误: {str(e)}", exc_info=True)
        return False


def update_schedule():
    """
    更新定时任务调度
    """
    global current_tasks

    # 加载最新的任务配置
    tasks = load_tasks()
    current_tasks = tasks

    # 清除现有的所有调度任务
    for job in schedule.jobs:
        schedule.cancel_job(job)
    scheduled_jobs.clear()

    # 添加新的调度任务
    enabled_tasks_count = 0
    for task in tasks:
        if task.get("enabled", False):
            enabled_tasks_count += 1
            task_id = task["id"]
            task_name = task.get("function", "daily_task")
            task_time = task.get("time", "19:00")
            params = task.get("params", {})

            # 创建一个闭包来确保每个任务使用正确的参数
            def create_task_handler(task_id, task_name, task_config):
                def task_handler():
                    execute_task(task_id, task_name, task_config)

                return task_handler

            # 设置定时任务
            job = schedule.every().day.at(task_time).do(create_task_handler(task_id, task_name, task))
            scheduled_jobs[task_id] = job
            logger.info(f"已添加任务调度: {task_id} - {task_name}，时间: {task_time}")

    logger.info(f"任务调度更新完成，已启用 {enabled_tasks_count}/{len(tasks)} 个任务")


def schedule_tasks():
    """
    设置定时任务
    """
    logger.info("启动定时任务调度器")
    # 初始更新调度
    update_schedule()
    # 每小时重新加载一次配置，以便及时响应配置更改
    schedule.every(1).hour.do(update_schedule)

    # 持续运行定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


def get_current_tasks():
    """
    获取当前加载的任务列表
    """
    return current_tasks

if __name__ == "__main__":
    # 可以选择立即执行一次任务，或者直接启动定时任务
    # daily_task()  # 立即执行一次
    schedule_tasks()  # 启动定时任务
