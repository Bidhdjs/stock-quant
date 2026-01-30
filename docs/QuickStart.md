# 快速上手（整理版）

本文基于当前仓库已存在的文档与代码结构整理而成，目标是帮助你快速跑通“数据获取 → 回测 → 结果查看”的最小闭环，并明确“数据源整合 + 成交量字段”的落点。

## 1. 项目核心流程（最小闭环）

1) 获取历史K线数据（CSV）
2) 回测引擎读取CSV并运行策略
3) 输出信号与图表

对应入口：
- 数据获取：`frontend/frontend_app.py` 或 `core/task/task_timer.py`
- 回测执行：`core/quant/quant_manage.py`
- 结果输出：`signals/`、`html/`、`log/`

## 2. 快速运行（推荐路径）

1) 创建虚拟环境并安装依赖（推荐 Python 3.13）
2) 启动前端：`python frontend/frontend_app.py`
3) 在页面中选择数据源与市场，拉取数据并回测

## 3. CSV 数据格式（强制字段）

必须包含以下字段：
- `date, open, high, low, close, volume, amount, stock_code, stock_name, market`

样例见：
- `README_en.md`（英文说明）
- `README.md`（中文说明）

注意：
- `volume`（成交量）是策略与指标关键字段，缺失会导致策略信号不可用或失真
- `amount`（成交额）可为空，但建议尽量填充

## 4. 数据源现状与整合计划

### 已集成的数据源（可直接使用）
- akshare：`core/stock/manager_akshare.py`
- baostock：`core/stock/manager_baostock.py`
- futu：`core/stock/manager_futu.py`

### 已实现但未完全打通
- yfinance：`core/stock/manager_yfinance.py`
  - 前端接口已有分支（`frontend/frontend_app.py`）
  - 任务调度仍缺少 yfinance 入口（`core/task/task_timer.py` / `core/task/task_timer_script.py`）
  - 前端下拉与市场联动需要补齐（`frontend/templates/index.html` / `frontend/templates/schedule.html`）

## 5. 成交量字段（volume）落点

成交量在以下模块被直接使用：
- 回测读取CSV：`core/quant/quant_manage.py`
- 指标/策略：`core/strategy/indicator/volume/`、`core/strategy/trading/volume/`

建议的统一处理入口：
- `core/stock/manager_common.py` 的 `standardize_stock_data()` 负责字段统一与补齐
- 如果某数据源返回“成交量(手)”等列名，可在映射中补充对应关系，确保标准化后一定有 `volume`

## 6. 第一阶段（数据源整合 + 成交量）

建议优先完成以下三件事：
1) 任务调度支持 yfinance（`core/task/task_timer.py`、`core/task/task_timer_script.py`）
2) 前端支持 yfinance 选择与市场限制（`frontend/templates/index.html`、`frontend/templates/schedule.html`）
3) 成交量字段兜底校验（在 `standardize_stock_data()` 或读取CSV后增加告警）

## 7. 常见文件入口索引

- 任务配置：`config/scheduled_tasks.json`
- 数据目录：`data/stock/`
- 回测主入口：`core/quant/quant_manage.py`
- 前端页面：`frontend/templates/index.html`
- 说明文档：`README.md`、`README_en.md`、`docs/解释.md`、`docs/二次开发规划.md`

## 8. 新增外部数据源与指标（StockQuant 集成）

- 实时行情（新浪/网易）：
  - `core/stock/manager_sina.py`
  - `core/stock/manager_money.py`
  - 统一输出 `RealtimeTick`：`core/stock/realtime_types.py`

- Tushare 基础数据：
  - `core/stock/manager_tushare.py`
  - 使用环境变量 `TUSHARE_TOKEN`

- TA-Lib 指标封装：
  - `core/strategy/indicator/talib_indicators.py`
  - 依赖 `TA-Lib`（已加入 requirements）
