# Plan: 项目文档整合与归档

**Generated**: 2026-01-31  
**Estimated Complexity**: Medium

## Overview
把现有需求/迁移/功能整理文档合并为 2–3 个中文文档（项目功能说明、已完成功能、待办功能列表），其余文档归档到 `docs/archive/`。需要基于**实际代码与现状**判定已完成/未完成。

## Prerequisites
- 读取并理解以下文档：`README.md`、`docs/QuickStart.md`、`docs/二次开发规划.md`、`docs/解释.md`、`docs/Quant_Analysis_Catalog.md`、`docs/Risk_Taxonomy.md`、`docs/Stock_Analysis_For_Quant_Tasklist.md`、`docs/StockQuant_Migration_Report.md`、`docs/x_migration_plan.md`、`docs/Testing.md`、`stock-quant-stabilization-plan.md`、`TODO.md`
- 结合代码现状与测试内容确认“已完成/未完成”
- 输出全部中文，存放在 `docs/`

## Sprint 1: 基础盘点与清单构建
**Goal**: 形成统一“项目功能说明/已完成/待办”三类清单草稿，并标明来源  
**Demo/Validation**:
- 草稿包含项目结构、核心功能、迁移模块、CLI、测试方式
- 已完成/待办与代码现状一致

### Task 1.1: 汇总项目结构与功能范围
- **Location**: `docs/QuickStart.md`, `docs/二次开发规划.md`, `docs/解释.md`, `README.md`
- **Description**: 提炼项目结构、核心流程、CLI/前端/任务/数据源/策略/回测/可视化现状，形成“项目功能说明”草稿大纲
- **Dependencies**: 无
- **Acceptance Criteria**:
  - 输出明确模块结构
  - 列出核心入口（CLI/前端/任务）
  - 说明数据格式与测试方式
- **Validation**: 草稿可直接编写成最终文档

### Task 1.2: 已完成与未完成对比清单
- **Location**: `stock-quant-stabilization-plan.md`, `TODO.md`, `docs/x_migration_plan.md`, `docs/StockQuant_Migration_Report.md`, `docs/Quant_Analysis_Catalog.md`
- **Description**: 对照代码现状，明确“已完成功能”与“待办功能”
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 已完成清单不含“尚未实现”的模块
  - 待办清单包含 TODO 中的未完成条目
  - 迁移成果被正确标注
- **Validation**: 与代码/测试结果一致

## Sprint 2: 文档合并与归档
**Goal**: 输出 2–3 个最终文档，并归档其余文件  
**Demo/Validation**:
- `docs/` 仅保留 2–3 个新文档 + 归档目录
- 新文档内容完整、结构清晰、中文

### Task 2.1: 生成三类最终文档
- **Location**: `docs/`
- **Description**: 
  - `docs/项目功能说明.md`：项目结构、核心流程、CLI/前端、数据源、策略、回测、可视化、测试
  - `docs/已完成功能.md`：以模块+功能点列出已完成内容
  - `docs/待办功能清单.md`：基于 TODO/规划列出后续需求（含优先级）
- **Dependencies**: Sprint 1
- **Acceptance Criteria**:
  - 内容来自现有文档且已去重
  - 已完成/待办与代码现状一致
- **Validation**: 人工审阅

### Task 2.2: 归档旧文档
- **Location**: `docs/archive/`
- **Description**: 将除新文档外的旧文档移动到归档目录，保留历史记录
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - `docs/` 仅保留 2–3 个新文档 + `archive/`
  - 原文件不丢失
- **Validation**: 目录结构检查

## Testing Strategy
- 无代码测试；仅做内容完整性与一致性检查

## Potential Risks & Gotchas
- 现有文档存在重复/不一致信息，需要以代码为准校验
- 归档移动可能影响引用链接，需要在新文档中改为统一引用

## Rollback Plan
- 归档前保留原文件副本；必要时恢复 `docs/archive/` 中内容
