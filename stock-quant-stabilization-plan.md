# 计划：Stock-Quant 稳定性、CLI 迁移、数据源与策略分析

**生成日期**：2026-01-30  
**复杂度**：高

## 概述
目标优先级：先稳定数据源与测试体系，再提供可运行的简化 CLI（输出 CSV/HTML 为主），同时迁移 `x/` 的新代码进入主项目模块。前端与定时任务代码保留但默认不参与执行，不影响整体运行。

## 前置约束（已确认）
- 外部项目：`StockQuant` 与 `Stock_Analysis_For_Quant` 已预处理，不重复阅读。
- 前端/定时任务：保留代码但不改动逻辑，不作为默认执行路径；兼容不报错为主。
- CLI：尽量简单；输出为 CSV 和 HTML（网页图表为主）。
- 数据源：稳定优先，可扩展；主要面向美股；成交量缺失可用 0 兜底并提示。
- 测试：继续 `mock_only`，避免联网波动。
- 历史交易字段：由我判断并统一成稳定 schema。
- `x/` 目录是新代码，需要迁移到主模块。

## Sprint 1：数据源稳定 + 测试体系补强（最高优先）
**目标**：数据源输出一致、可用；所有关键路径有 mock-only 测试支撑。  
**验收/演示**：
- `python -m pytest -m mock_only`
- `python -m core.cli data fetch ...`（输出符合统一 schema）

### [X] 任务 1.1：统一数据输出 schema 与校验器
- **位置**：`core/stock/manager_common.py`（新增或扩展），`docs/`
- **说明**：定义统一字段：`date, open, high, low, close, volume, amount, stock_code, stock_name, market`；提供校验/归一化函数。
- **依赖**：无
- **验收标准**：
  - 所有数据源都通过统一校验器输出一致列。
  - 缺失成交量时自动填 0 并输出提示日志。
- **验证**：`test/test_data_sources_mock.py` 新增用例。

### [X] 任务 1.2：数据源稳定性与回退策略
- **位置**：`core/stock/manager_akshare.py`, `core/stock/manager_yfinance.py`, `core/stock/manager_sina.py`, `core/stock/manager_tushare.py`, `core/stock/manager_baostock.py`
- **说明**：定义稳定优先的回退顺序；当某数据源失败时自动降级到下一数据源。
- **依赖**：任务 1.1
- **验收标准**：
  - 回退顺序可配置（默认稳定优先）。
  - 明确日志记录（含数据源名与原因）。
- **验证**：mock-only 失败模拟测试。

### [X] 任务 1.3：成交量缺失提示与补齐策略
- **位置**：`core/stock/manager_common.py`，`core/stock/realtime_types.py`
- **说明**：美股为主，缺失成交量填 0，并写明“成交量缺失”提示；为后续补齐预留接口。
- **依赖**：任务 1.1
- **验收标准**：
  - 统一行为：缺失则填 0 + log 提示。
- **验证**：mock-only 测试覆盖。

### [X] 任务 1.4：数据缓存与本地存储规范
- **位置**：`settings.py`, `data/`
- **说明**：规范数据存储路径；重复抓取可重用本地 CSV。
- **依赖**：任务 1.1
- **验收标准**：
  - 数据落盘路径一致、可复用。
- **验证**：手动运行并检查生成文件。

## Sprint 2：CLI 最小可用（CSV + HTML）
**目标**：在不依赖前端/定时任务的情况下运行核心流程（数据抓取、回测、结果输出）。  
**验收/演示**：
- `python -m core.cli data fetch ...`
- `python -m core.cli backtest ...`（输出 CSV + HTML）

### [X] 任务 2.1：设计 CLI 命令与参数
- **位置**：`core/cli.py`（新增），`README.md`
- **说明**：最小命令集：`data fetch`、`backtest`、`signals analyze`（可选）、`strategy list`。
- **依赖**：Sprint 1
- **验收标准**：
  - CLI 参数清晰，尽量少必填项。
- **验证**：README 用法示例。

### [X] 任务 2.2：实现 CLI 入口与输出
- **位置**：`core/cli.py`, `core/quant/quant_manage.py`, `core/visualization/visual_tools_plotly.py`
- **说明**：调用现有回测逻辑，输出 CSV/HTML；HTML 用于网页图表展示。
- **依赖**：任务 2.1
- **验收标准**：
  - CLI 不依赖前端和定时任务。
- **验证**：CLI 命令成功运行并生成输出文件。

### [X] 任务 2.3：前端/定时任务兼容性隔离
- **位置**：`frontend/frontend_app.py`, `core/task/task_timer.py`, `core/task/task_timer_script.py`
- **说明**：保留代码，确保不作为默认入口；必要时做懒加载或隔离导入。
- **依赖**：任务 2.2
- **验收标准**：
  - CLI 运行不触发前端/定时任务相关报错。
- **验证**：CLI 运行通过。

## Sprint 3：迁移 `x/` 新代码到主模块
**目标**：将 `x/` 的新代码迁移到主模块结构中，保持可维护与可测试。  
**验收/演示**：
- `python -m core.cli ...` 可调用迁移后的功能
- 单元测试通过（mock-only）

### [X] 任务 3.1：梳理 `x/` 代码与目标归属
- **位置**：`x/`, `core/`
- **说明**：按功能分类（策略/指标/分析/工具），确定迁移目标模块。
- **依赖**：Sprint 2
- **验收标准**：
  - 明确每个脚本迁移去向清单。
- **验证**：迁移清单文档或内部记录。

### [X] 任务 3.2：迁移与模块化
- **位置**：`core/analysis/`, `core/strategy/`, `core/quant/`, `core/visualization/`
- **说明**：将 `x/` 中可复用逻辑抽到主模块，并统一接口。
- **依赖**：任务 3.1
- **验收标准**：
  - 主模块可直接调用迁移功能。
- **验证**：mock-only 单元测试与 CLI 试跑。

### [X] 任务 3.3：补齐迁移代码的测试
- **位置**：`test/`
- **说明**：新增 mock-only 测试覆盖迁移功能。
- **依赖**：任务 3.2
- **验收标准**：
  - 关键逻辑有测试覆盖。
- **验证**：`python -m pytest -m mock_only`

## Sprint 4：历史交易策略分析（延后）
**目标**：分析历史交易，推断策略类型特征（持仓周期、趋势/反转、量价关系）。  
**验收/演示**：
- `python -m core.cli trades analyze --input ...`
- 输出 CSV + HTML 报告

### 任务 4.1：定义交易数据 schema 与解析器
- **位置**：`core/analysis/trade_schema.py`（新增）
- **说明**：统一字段（symbol, time, side, qty, price, fee, pnl 等）。
- **依赖**：Sprint 3
- **验收标准**：
  - 多个交易 CSV 均可解析。
- **验证**：mock-only 测试。

### 任务 4.2：策略推断启发式规则
- **位置**：`core/analysis/trade_strategy_infer.py`（新增）
- **说明**：用持有期、波动、量价结构推断策略特征。
- **依赖**：任务 4.1
- **验收标准**：
  - 输出策略画像 + 置信度。
- **验证**：用历史交易样本验证。

### 任务 4.3：CLI 报告输出
- **位置**：`core/cli.py`, `core/visualization/`
- **说明**：输出 CSV + HTML，HTML 展示图表。
- **依赖**：任务 4.2
- **验收标准**：
  - CLI 可产出完整报告。
- **验证**：手动运行。

## 测试策略
- 保持 `mock_only` 标签，避免真实联网。
- 新增 CLI “烟雾测试”用本地 CSV 运行。

## 风险与注意事项
- 前端/定时任务与核心逻辑耦合时需谨慎隔离，避免引入破坏性变更。
- 数据源受限时需要良好的降级策略与日志提示。
- `x/` 迁移可能存在隐含依赖或路径假设，需要逐个验证。
- 历史交易数据字段可能不完整，必须先统一 schema。

## 回滚方案
- 前端/定时任务保持原逻辑，仅隔离导入。
- 数据源改动以新增/包裹为主，避免破坏原函数签名。
- 迁移新代码时保留原脚本备份路径。
