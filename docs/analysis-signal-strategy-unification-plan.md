# Plan: 指标-信号-策略分层整合

**Generated**: 2026-01-31
**Estimated Complexity**: High

## Overview
目标是统一“指标 → 信号 → 策略”的分层结构，**以 `core/analysis` 为指标计算权威来源**，`core/strategy/indicator` 仅负责**基于指标值的信号规则**，`core/strategy/trading` 负责**执行交易**。要求：
- 覆盖所有策略（含未来扩展）
- 代码层面实改并保持 CLI/API 兼容
- 每一层 + 链路都要有测试
- 功能正常后更新文档（旧文档可弱化/替换）

## Prerequisites
- 熟悉 Backtrader 指标/策略结构
- 保持兼容现有 CLI / StrategyManager / IndicatorManager
- 测试使用 `data_analysis` 环境（mock-only 为主）

## Sprint 1: 指标层统一（core/analysis 作为唯一指标计算源）
**Goal**：明确指标计算边界与接口，形成可复用的指标计算模块。
**Demo/Validation**：
- 能在 `core/analysis` 生成结构化指标输出
- 与现有策略指标计算结果保持一致（数值对齐或误差在可接受范围内）

### Task 1.1: 指标清单与接口约定
- **Location**: `core/analysis/*`, `core/strategy/indicator/*`, `core/strategy/trading/*`
- **Description**:
  - 盘点所有策略使用的指标（含 Enhanced/Single/VCP 以及后续扩展）
  - 设计统一指标输出结构（例如返回 DataFrame / dict / numpy 数组）
  - 明确“指标计算”与“信号规则”边界
- **Dependencies**: None
- **Acceptance Criteria**:
  - 形成指标清单（映射到 core/analysis 模块）
  - 明确每个指标的输入字段与输出字段
- **Validation**:
  - 文档化结果写入计划日志或新文档附录
- **Status**: Completed
- **Log**:
  - Volume 指标（Enhanced/Single）统一到 `core/analysis/indicators/volume.py`
  - VCP 指标统一到 `core/analysis/indicators/vcp.py`
  - 现有分析类指标继续保留在 `core/analysis/*`，作为信号层可复用来源

### Task 1.2: 指标计算迁移与模块化
- **Location**:
  - 新增：`core/analysis/indicators/`（建议）
  - 现有：`core/analysis/technical_indicators_ext.py`
- **Description**:
  - 将 Enhanced/Single/VCP 相关计算逻辑整理到 core/analysis 中
  - VCP 需输出“进度/强度”型指标（例如 0~1 或百分比）
  - 指标计算与阈值判断分离
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - core/analysis 中提供可复用的函数（支持策略/信号层调用）
  - 保持输入列与当前数据结构一致
- **Validation**:
  - 为每个指标函数补充单元测试（最小样本 + 可重复断言）
- **Status**: Completed
- **Log**:
  - 新增 `core/analysis/indicators/` 模块
  - 新增 `core/analysis/indicators/volume.py` 与 `core/analysis/indicators/vcp.py`

### Task 1.3: 指标一致性回归测试
- **Location**: `test/`（新增测试）
- **Description**:
  - 对比“旧计算逻辑”与“core/analysis 新逻辑”的数值一致性
  - 对关键指标（量能/均线/RSI/BOLL/KDJ/VCP核心值）做断言
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - 核心指标数值偏差在可接受范围内
- **Validation**:
  - `conda run -n data_analysis python -m pytest -m mock_only test/test_indicator_consistency.py`
- **Status**: Completed
- **Log**:
  - 新增 `test/test_indicator_consistency.py`
  - 新增基础指标单测：`test/test_analysis_volume_indicators.py`、`test/test_analysis_vcp.py`

## Sprint 2: 信号层改造（core/strategy/indicator 只做规则判断）
**Goal**：信号层只消费 `core/analysis` 指标输出，不再自行计算指标。
**Demo/Validation**：
- Enhanced/Single/VCP 信号输出一致或更可控
- 策略回测可正常执行

### Task 2.1: Enhanced/Single 信号重构
- **Location**:
  - `core/strategy/indicator/volume/enhanced_volume.py`
  - `core/strategy/indicator/volume/single_volume.py`
- **Description**:
  - 替换内部计算为 core/analysis 指标函数输出
  - 保留信号规则逻辑（主信号 vs 增强信号）
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - 不在 indicator 中重复实现指标计算
  - 信号输出字段不变（保持策略兼容）
- **Validation**:
  - mock-only 回测/单元测试通过
- **Status**: Completed
- **Log**:
  - 重构 `core/strategy/indicator/volume/enhanced_volume.py`
  - 重构 `core/strategy/indicator/volume/single_volume.py`
  - 信号规则保留，仅从 `core/analysis/indicators/volume.py` 取指标值

### Task 2.2: VCP 信号重构（支持进度型指标）
- **Location**:
  - `core/strategy/indicator/pattern/vcp_indicator.py`
  - `core/analysis/indicators/vcp.py`（建议）
- **Description**:
  - VCP 指标计算与阈值判断拆分
  - core/analysis 提供 VCP 进度/强度值
  - indicator 只负责“达到阈值即出信号”
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - VCP 进度值可被信号规则配置/调整
  - 输出的信号记录机制保持不变
- **Validation**:
  - `test/test_vcp_strategy.py` 保持通过或增强断言
- **Status**: Completed
- **Log**:
  - 新增 `core/analysis/indicators/vcp.py` 输出进度分值
  - `core/strategy/indicator/pattern/vcp_indicator.py` 使用进度阈值触发信号

### Task 2.3: 信号层统一接口与注册
- **Location**: `core/strategy/indicator_manager.py`, `core/strategy/indicator/__init__.py`
- **Description**:
  - 确保新/改造后的 indicator 可以被自动发现与注册
  - 统一命名与输出字段规范（主/增强/强度）
- **Dependencies**: Task 2.1, Task 2.2
- **Acceptance Criteria**:
  - IndicatorManager 能正确发现所有 indicator
- **Validation**:
  - 新增测试覆盖 indicator discovery
- **Status**: Completed
- **Log**:
  - IndicatorManager 改为 walk_packages 自动发现所有子模块
  - 新增 `test/test_indicator_discovery.py`

## Sprint 3: 策略层兼容 + 测试链路 + 文档更新
**Goal**：策略层保持兼容，链路测试通过，文档完成更新。
**Demo/Validation**：
- CLI 回测可以正常运行
- 文档说明“指标→信号→策略”结构

### Task 3.1: 策略层适配与兼容验证
- **Location**:
  - `core/strategy/trading/*`
  - `core/quant/quant_manage.py`
  - `core/cli.py`
- **Description**:
  - 确保策略类对信号字段访问不变
  - 保持 CLI 参数与 StrategyManager 行为不变
- **Dependencies**: Sprint 2
- **Acceptance Criteria**:
  - Backtest CLI 可正常运行
  - 策略执行逻辑与订单流程不变
- **Validation**:
  - `conda run -n data_analysis python tools/cli_smoke.py`
- **Status**: Completed
- **Log**:
  - CLI smoke 已验证 EnhancedVolumeStrategy / VCPStrategy 回测正常

### Task 3.2: 分层链路测试补齐
- **Location**: `test/`
- **Description**:
  - 增加“指标层 → 信号层 → 策略层”链路测试
  - 覆盖至少 Enhanced / Single / VCP 三个路径
- **Dependencies**: Sprint 2
- **Acceptance Criteria**:
  - 每条链路可验证信号输出与策略执行
- **Validation**:
  - `conda run -n data_analysis python -m pytest -m mock_only`
- **Status**: Completed
- **Log**:
  - 新增/覆盖 mock-only 测试：指标层、VCP/策略注册、IndicatorManager 发现
  - 已执行 mock-only 子集验证通过

### Task 3.3: 文档更新（替换旧文档）
- **Location**:
  - `docs/策略回测流程说明.md`
  - `docs/项目功能说明.md`
  - 可新增：`docs/指标-信号-策略分层说明.md`
- **Description**:
  - 按新架构更新流程、调用链与职责边界
  - 旧文档仅保留必要信息
- **Dependencies**: Sprint 3
- **Acceptance Criteria**:
  - 文档能够清晰解释分层职责与调用路径
- **Validation**:
  - 手动检查与示例 CLI 一致
- **Status**: Completed
- **Log**:
  - 更新 `docs/策略回测流程说明.md`，补充指标计算层说明
  - 更新 `docs/项目功能说明.md`，明确指标/信号/策略分层结构

## Testing Strategy
- 指标层：单元测试（输出数值一致性）
- 信号层：规则触发测试（主信号/增强信号）
- 策略层：mock-only 回测 smoke + CLI smoke
- 链路：至少 3 条策略全链路测试

## Potential Risks & Gotchas
- 指标计算从 Backtrader 迁到 pandas/numpy 可能出现数值偏差
- VCP 进度型指标的阈值需要校准
- 旧策略对字段名敏感，需保持兼容
- 数据列名差异（Open/High/Low/Close vs open/high/low/close）

## Rollback Plan
- 保留旧 indicator 实现分支（或临时开关）
- 每次迁移一个策略，确保回测可运行后再继续
