# Plan: Plotly HTML 报告视觉重构

**Generated**: 2026-01-31
**Estimated Complexity**: Medium

## Overview
将 core/visualization/visual_tools_plotly.py 的 Plotly 报告输出改为自定义 HTML 模板，参考券商终端（Futu）与 TradingView 的信息层级和视觉语言，提升可读性、性能与直观性。重点在：布局分区、KPI 速览、图表容器皮肤化、图标系统与响应式。

## Prerequisites
- 了解当前 plotly_draw() 数据来源（行情/信号/交易/持仓）
- 可在本机打开输出的 HTML 进行人工验收

## Sprint 1: 现状审计与视觉方向
**Goal**: 明确当前输出结构与数据可用性，确定视觉方向与布局草图。
**Demo/Validation**:
- 记录现有 HTML 输出构成（Plotly 默认模板）
- 产出简要布局草图（头部/KPI/图表/表格/附注）

### Task 1.1: 审计当前 HTML 输出
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 梳理 save_and_show_chart、plotly_draw 现有输出方式与可用数据字段
- **Complexity**: 2
- **Dependencies**: 无
- **Acceptance Criteria**:
  - 明确需要改造的函数与数据接口
- **Validation**:
  - 阅读代码并记录结论

### Task 1.2: 选择视觉方向与排版体系
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 选择 清爽专业终端风（浅色石墨+高对比强调）或深色终端风，确定字体、色板、密度
- **Complexity**: 3
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 输出明确的色板、字体与层级
- **Validation**:
  - 在计划文档补充设计基调

### Task 1.3: 定义信息区块与KPI清单
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 规划头部与KPI卡片的指标（如区间收益、最大回撤、最新价、持仓市值等），标注数据来源
- **Complexity**: 4
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 指标列表明确、可计算
- **Validation**:
  - 在计划文档列出计算口径

## Sprint 2: HTML 模板与样式实现
**Goal**: 自定义 HTML 结构与 CSS，使报告像交易终端界面。
**Demo/Validation**:
- 生成 HTML 文件并能在浏览器正常打开
- 视觉层级清晰、图表融入整体 UI

### Task 2.1: 引入自定义 HTML 模板
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 用 ig.to_html() 注入图表，包裹在自定义 HTML/CSS 模板中
- **Complexity**: 5
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 仍能完整显示 Plotly 图表
  - 模板结构包含头部、KPI区、图表区、说明区
- **Validation**:
  - 打开 HTML 验证结构

### Task 2.2: KPI 与摘要信息渲染
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 计算并渲染核心指标（例如最新价、区间收益、最大回撤、交易次数）
- **Complexity**: 5
- **Dependencies**: Task 1.3
- **Acceptance Criteria**:
  - KPI 数据与图表时间范围一致
- **Validation**:
  - 对比数据源抽查 1-2 个指标

### Task 2.3: 图标系统与视觉细节
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 使用内联 SVG 图标为区块标题与 KPI 卡片增强视觉识别
- **Complexity**: 3
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 不引入外部图标依赖
- **Validation**:
  - HTML 中正确展示 SVG

### Task 2.4: Plotly 皮肤化
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 调整 Plotly 主题色、网格线、字体与背景，以匹配整体设计
- **Complexity**: 4
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 图表与页面主题一致，阅读更清晰
- **Validation**:
  - 目视检查

## Sprint 3: 性能与体验优化
**Goal**: 确保 HTML 体积与加载性能可控，布局在不同屏幕可用。
**Demo/Validation**:
- 本地打开无卡顿
- 桌面/移动端布局不崩

### Task 3.1: 体积与加载策略
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 根据需求选择 include_plotlyjs 策略（内联或 CDN）并压缩非必要样式
- **Complexity**: 3
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 文件体积与加载速度有改善
- **Validation**:
  - 比较文件大小与首屏渲染

### Task 3.2: 响应式细节优化
- **Location**: core/visualization/visual_tools_plotly.py
- **Description**: 使用 CSS Grid/Flex 实现自适应布局与小屏折叠
- **Complexity**: 4
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 320px 宽度不溢出
- **Validation**:
  - 浏览器缩放检查

## Testing Strategy
- 生成样例报告并打开 HTML
- 对比图表与 KPI 数据一致性
- 小屏/宽屏快速检查

## Potential Risks & Gotchas
- Plotly 自带样式覆盖自定义样式
- 使用 CDN 导致离线不可用
- KPI 指标口径与现有数据不一致
- 大数据量下 HTML 体积膨胀

## Rollback Plan
- 恢复 ig.write_html 默认输出
- 保留旧模板作为 legacy 分支或可切换参数
