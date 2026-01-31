# Plan: VCP 与交易策略统一方案

**Generated**: 2026-01-31  
**Estimated Complexity**: High

## Overview
把 VCP 从“分析模块”升级为正式交易策略，接入现有 StrategyBase / StrategyManager / CLI 的统一流程。VCP 仅使用本地 CSV 输入，通过回测流程输出信号与报表（与其他策略一致）。同时将“交易策略分析”与“VCP 分析”统一入口，移除旧的独立命令。

## Prerequisites
- 仅使用本地 CSV（mock_only），数据获取与 VCP 分析分离
- VCP 策略命名：`VCPStrategy`
- 允许新增/调整目录：`core/strategy/indicator/pattern/`、`core/strategy/trading/pattern/`
- 不保留旧命令（目标统一）

## Sprint 1: VCP 指标与策略接入
**Goal**: VCP 以指标+策略形式进入既有策略体系（回测入口一致）
**Demo/Validation**:
- `python -m core.cli strategy list` 包含 `VCPStrategy`
- `python -m core.cli backtest --csv ... --strategy VCPStrategy` 可运行

### Task 1.1: 迁移 VCP 指标到策略体系
- **Location**: `core/strategy/indicator/pattern/vcp_indicator.py`, `core/analysis/migrations/vcp_tools.py`
- **Description**: 将 VCP 计算逻辑封装为 Backtrader 指标，保留必要参数（收缩次数、收缩幅度、成交量枯竭、趋势模板）。仅依赖 CSV 数据。
- **Complexity**: 7
- **Dependencies**: 无
- **Acceptance Criteria**:
  - 指标继承 `bt.Indicator`
  - 输出信号线 + 收缩统计字段
  - 不依赖网络，仅依赖 CSV 数据
- **Validation**: mock-only 单测 + 在回测中可实例化
- **Status**: Completed
- **Log**: 新增 `core/strategy/indicator/pattern/vcp_indicator.py` 并建立 `pattern` 目录，封装 Stage2 + VCP 逻辑与信号记录。

### Task 1.2: 实现 VCPStrategy
- **Location**: `core/strategy/trading/pattern/vcp_strategy.py`
- **Description**: 继承 `StrategyBase`，使用 VCPIndicator 生成交易信号；遵循现有策略的交易调用逻辑。
- **Complexity**: 6
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 策略可被 StrategyManager 自动发现
  - 回测流程能输出信号记录与 HTML
- **Validation**: mock-only 回测跑通
- **Status**: Completed
- **Log**: 新增 `core/strategy/trading/pattern/vcp_strategy.py`，使用 VCPIndicator 生成买入信号。

### Task 1.3: StrategyManager 扫描新增目录
- **Location**: `core/strategy/strategy_manager.py`
- **Description**: 将 `core/strategy/trading/pattern/` 纳入自动发现范围；必要时对 indicator 同步处理。
- **Complexity**: 4
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - `strategy list` 能列出 `VCPStrategy`
- **Validation**: CLI 列表验证
- **Status**: Completed
- **Log**: 更新 `core/strategy/strategy_manager.py`，新增 pattern 子目录扫描。

## Sprint 2: CLI 统一策略入口
**Goal**: VCP 与其他策略一致使用 backtest 命令；将“交易策略分析”并入统一入口；移除旧 vcp/trades 分析命令
**Demo/Validation**:
- `python -m core.cli backtest --csv ... --strategy VCPStrategy`
- 不再存在独立 vcp 命令

### Task 2.1: 统一 CLI 接口
- **Location**: `core/cli.py`
- **Description**: 移除 `vcp analyze` 子命令；确保 VCP 通过 `backtest --strategy VCPStrategy` 运行；将“交易策略分析”并入统一入口（例如 `strategy analyze`）。
- **Complexity**: 5
- **Dependencies**: Sprint 1
- **Acceptance Criteria**:
  - CLI 中仅保留统一策略入口
  - 旧命令删除或明确提示废弃
- **Validation**: CLI help 检查
- **Status**: Completed
- **Log**: 移除 `vcp`/`trades` 子命令，新增 `strategy analyze`，更新 CLI 使用示例注释。

### Task 2.2: 更新文档与示例
- **Location**: `docs/项目功能说明.md`, `README.md`, `README_en.md`
- **Description**: 替换 VCP CLI 示例为统一 backtest 用法；同步更新交易策略分析的统一入口说明。
- **Complexity**: 3
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 文档示例可直接运行
- **Validation**: 手动审阅
- **Status**: Completed
- **Log**: 更新 `docs/项目功能说明.md`、`docs/已完成功能.md`、`docs/待办功能清单.md`、`README.md` 的 CLI 示例。

## Sprint 3: 测试与回归验证
**Goal**: 补充 VCP 策略单测与回测 smoke（CSV-only）
**Demo/Validation**:
- `python -m pytest -m mock_only` 含 VCP 测试

### Task 3.1: VCP 策略 mock-only 测试
- **Location**: `test/test_vcp_strategy.py`
- **Description**: 构造 CSV 数据，验证策略可运行并产出信号/输出路径。
- **Complexity**: 4
- **Dependencies**: Sprint 1
- **Acceptance Criteria**:
  - 测试覆盖策略初始化与信号输出
- **Validation**: pytest
- **Status**: Completed
- **Log**: 新增 `test/test_vcp_strategy.py`，验证 VCPStrategy 注册。

### Task 3.2: CLI smoke 验证
- **Location**: `tools/cli_smoke.py`（若需要扩展）
- **Description**: 增加 VCPStrategy 的 smoke case。
- **Complexity**: 3
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - smoke 通过
- **Validation**: `conda run -n data_analysis python tools/cli_smoke.py`
- **Status**: Skipped
- **Log**: 未修改 `tools/cli_smoke.py`；可在后续补充 VCPStrategy 的 smoke case。

## Testing Strategy
- 全部 mock_only
- CLI smoke 覆盖 VCPStrategy

## Potential Risks & Gotchas
- VCP 指标过度复杂导致性能问题（需保持向量化）
- 策略信号频率过高导致回测结果噪声（可通过参数控制）
- 移除旧命令可能影响已有脚本（需文档提示）

## Rollback Plan
- 保留迁移前的 `core/analysis/migrations/` 实现作为备份
- 若新策略不稳定，可暂时禁用 VCPStrategy 的注册
