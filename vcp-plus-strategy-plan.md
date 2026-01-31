# Plan: VCPPlusStrategy 重构

**Generated**: 2026-01-31
**Estimated Complexity**: High

## Overview
将 `core/analysis/migrations/vcp_screener很全的一个项目.py` 中的 VCP 筛选与信号生成逻辑，抽象为新的交易策略 `VCPPlusStrategy`，并保持与现有 `VCPStrategy` 同级别、同结构的分层设计。策略仅替换指标/信号生成方法，其余回测流程、策略基类行为保持一致。

## Prerequisites
- 熟悉现有策略结构：`StrategyBase`、`VCPStrategy` 与 `VCPStrategyLoose`
- 了解指标/信号注册方式（`set_indicator` / indicator lines）
- 明确数据字段标准化流程与列名要求

## Sprint 1: 现状调研与设计对齐
**Goal**: 明确 VCPPlusStrategy 的结构边界与可复用组件，完成新指标/信号接口设计。
**Demo/Validation**:
- 能用伪数据或单元测试调用新指标的信号输出
- 文档或注释中清晰写出信号产生条件

### Task 1.1: 梳理现有策略与指标结构
- **Location**: `core/strategy/trading/pattern/vcp_strategy.py`, `core/strategy/trading/pattern/vcp_strategy_loose.py`, `core/strategy/indicator/pattern/`
- **Description**: 总结现有策略的分层结构（策略类/指标类/信号线），确认需要保持的一致性（方法、字段、命名、注册方式）。
- **Complexity**: 3
- **Dependencies**: 无
- **Acceptance Criteria**:
  - 输出结构对齐清单（策略类接口、指标输出线、日志与计数）
- **Validation**:
  - 手动检查结构一致性

### Task 1.2: 拆解迁移脚本的核心指标与信号逻辑
- **Location**: `core/analysis/migrations/vcp_screener很全的一个项目.py`
- **Description**: 抽取趋势模板、局部高低点、收缩幅度、RS 评级、成交量收缩等核心计算，明确哪些进入指标、哪些进入策略。
- **Complexity**: 5
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 列出 VCPPlus 的指标计算清单与信号判定流程
- **Validation**:
  - 人工复核逻辑映射

### Task 1.3: 设计 VCPPlus 指标接口与策略调用方式
- **Location**: `core/strategy/indicator/pattern/`（新文件）, `core/strategy/trading/pattern/`（新文件）
- **Description**: 设计新的 indicator 输出线（如 vcp_plus_signal / vcp_plus_sell_signal 或等价命名），并定义策略类中 `next()` 与买卖策略的调用逻辑。
- **Complexity**: 6
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - 明确指标输出线与策略判断关系
- **Validation**:
  - 设计评审（人工）

## Sprint 2: 指标实现与策略落地
**Goal**: 完成 VCPPlus 指标与策略类实现，保持与现有 VCPStrategy 同级别结构。
**Demo/Validation**:
- 策略注册可被 CLI 列出
- 基于样例 CSV 运行回测无报错并产出买卖信号日志

### Task 2.1: 新建 VCPPlus 指标类
- **Location**: `core/strategy/indicator/pattern/vcp_plus_indicator.py`
- **Description**: 将迁移脚本中的趋势模板、局部极值、收缩判定与成交量收缩等计算向量化实现；统一列名与数据标准化；输出信号线。
- **Complexity**: 7
- **Dependencies**: Task 1.3
- **Acceptance Criteria**:
  - 指标可独立实例化并产出信号线
  - 无 for 循环遍历 DataFrame
- **Validation**:
  - 单元测试或最小回测样例验证

### Task 2.2: 新建 VCPPlus 策略类
- **Location**: `core/strategy/trading/pattern/vcp_plus_strategy.py`
- **Description**: 继承 `StrategyBase`，结构对齐 `VCPStrategy`；调用新指标并在 `next()` 中使用新的信号判断买卖。
- **Complexity**: 5
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 策略可被策略注册器发现
  - 运行日志包含买卖信号触发信息
- **Validation**:
  - 运行最小回测用例

### Task 2.3: 策略注册与文档更新
- **Location**: `core/strategy/trading/registry.py`（若存在）, `docs/`相关文档
- **Description**: 注册新策略名称 `VCPPlusStrategy`，更新策略说明与示例命令。
- **Complexity**: 4
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - CLI 可识别 `VCPPlusStrategy`
- **Validation**:
  - CLI 列表检查

## Sprint 3: 测试与回归
**Goal**: 确保新策略符合测试规范且不影响现有策略。
**Demo/Validation**:
- pytest mock-only 通过
- 对比 VCPStrategy / VCPPlusStrategy 输出无报错

### Task 3.1: 增加 VCPPlusStrategy 测试
- **Location**: `test/test_vcp_plus_strategy.py`
- **Description**: 参照现有 VCPStrategy 测试结构，增加策略注册测试与最小样例回测测试。
- **Complexity**: 5
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - 测试标记 `@pytest.mark.mock_only`
- **Validation**:
  - `conda run -n data_analysis python -m pytest -m mock_only test/test_vcp_plus_strategy.py`

### Task 3.2: 回归现有 VCP 策略测试
- **Location**: `test/test_vcp_strategy.py`, `test/test_vcp_strategy_short_term.py`
- **Description**: 确认新增策略不会影响现有 VCP 策略逻辑。
- **Complexity**: 3
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - 现有测试通过
- **Validation**:
  - 运行相关 pytest 用例

## Testing Strategy
- 新增策略测试以 mock-only 为默认
- 重点验证指标信号线是否正确生成
- 回测链路可执行且无异常

## Potential Risks & Gotchas
- 迁移脚本内含外部数据源（Finviz / yfinance / pandas_datareader），策略内需移除网络调用
- 指标计算需向量化，避免 for 循环
- 数据列名差异（脚本使用 Close/High/Low/Volume，策略需统一为小写列名）
- 局部极值与收缩计算的索引边界，可能触发空序列或索引越界
- RS 评级逻辑依赖大盘指数数据，需在策略中替换为可注入或移除

## Rollback Plan
- 删除新增 `vcp_plus_indicator.py` 与 `vcp_plus_strategy.py`
- 移除策略注册与文档更新
- 回退新增测试文件
