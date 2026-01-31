# Plan: Neon 信号落库 + 回测报告指标展示

**Generated**: 2026-01-31  
**Estimated Complexity**: High

## Overview
目标是将每次产生的交易信号写入 Neon 数据库，并保存当时各指标的数值与触发条件说明；回测 HTML 报告页面通过后端接口读取 Neon 中的信号数据，在图中/表中展示信号详情，便于复盘“为什么出这个信号”。

## Prerequisites
- 提供 Neon Data API 访问配置（API 方式，不直连 Postgres）
- 仅回测写入（离线回测），触发时记录
- 信号展示为悬浮提示（hover）
- 保留 CSV（CSV 与 Neon 并行）
- 需要 Flask 服务支持访问 Neon

## Sprint 1: Neon 数据库基础与配置
**Goal**: 建立 DB 连接与表结构，提供最小可用的写入/查询能力。  
**Demo/Validation**:
- 执行初始化脚本创建表
- 插入一条模拟信号并查询验证

### Task 1.1: 增加 Neon API 配置项与特性开关
- **Location**: `settings.py`
- **Description**: 新增 Neon API 配置读取（例如 `NEON_API_URL`、`NEON_API_KEY`、`NEON_ENABLED`），默认关闭以保证兼容。
- **Complexity**: 3
- **Dependencies**: None
- **Acceptance Criteria**:
  - 未配置时不影响现有回测流程
  - 可通过环境变量启用 Neon 写入
- **Validation**:
  - 启动回测时确认日志提示“Neon 未启用/启用”

### Task 1.2: 新增 Neon API 访问模块
- **Location**: `core/db/neon_client.py`（新增），可能新增 `core/db/__init__.py`
- **Description**: 提供 API 请求封装、批量写入与查询的轻量封装。
- **Complexity**: 6
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - 提供 `insert_signals()` / `fetch_signals()` 等接口
  - 失败时输出可读日志，不抛出不可控异常
- **Validation**:
  - 本地调用模块方法，返回可用连接与数据

### Task 1.3: 定义信号落库表结构
- **Location**: `docs/neon-signal-schema.sql`（新增）或 `core/db/neon_client.py` 内置 SQL
- **Description**: 设计 `signal_events`（可选 `backtest_runs`）表，存储 run_id、策略、股票、信号类型、指标快照 JSON、触发条件等字段；由外部初始化，应用内仅写入与查询。
- **Complexity**: 5
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - JSONB 字段可保存任意指标值
  - 支持按 run_id/日期/信号类型过滤查询
- **Validation**:
  - 执行建表 SQL，插入/查询成功

### Task 1.4: 新增依赖并记录安装说明
- **Location**: `requirements-13.txt`, `README.md` 或 `docs/项目功能说明.md`
- **Description**: 选择并加入 HTTP 客户端库（如 `requests` 已存在则复用），补充环境配置说明。
- **Complexity**: 4
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - 依赖可安装且不影响现有功能
- **Validation**:
  - `pip` 安装后可在 Python 中导入模块

## Sprint 2: 信号记录增强与写入 Neon
**Goal**: 信号产生时记录指标值与触发条件，并落库。  
**Demo/Validation**:
- 运行一次回测后，Neon 中新增对应信号行
- CSV 仍然生成且字段兼容

### Task 2.1: 扩展信号记录结构
- **Location**: `core/strategy/indicator/common.py`
- **Description**: 扩展 `SignalRecord` 增加 `indicator_values` 与 `trigger_conditions`（JSON/文本），`SignalRecordManager.add_signal_record` 支持可选参数。
- **Complexity**: 4
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - 旧调用不改也能运行
  - `transform_to_dataframe()` 输出新增字段
- **Validation**:
  - 单元测试验证字段存在与序列化正确

### Task 2.2: VCP 指标记录指标快照
- **Location**: `core/strategy/indicator/pattern/vcp_indicator.py`
- **Description**: 在产生 VCP 信号时写入 `vcp_result`、关键阈值与阶段信息，生成可读触发说明。
- **Complexity**: 5
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 每次信号记录包含完整 VCP 参数与计算结果
- **Validation**:
  - 打印/断言一条信号记录字段完整

### Task 2.3: 成交量指标记录指标快照
- **Location**: `core/strategy/indicator/volume/single_volume.py`, `core/strategy/indicator/volume/enhanced_volume.py`
- **Description**: 在买卖信号触发时记录 RSI/BOLL/KDJ/成交量等关键数值与布尔条件。
- **Complexity**: 6
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - 每条信号包含数值快照与触发条件列表
- **Validation**:
  - 回测时导出的信号 DataFrame 包含新增字段

### Task 2.4: 回测流程落库（仅回测）
- **Location**: `core/quant/quant_manage.py`
- **Description**: 在信号 CSV 保存后，追加 Neon 写入流程；补充 run_id、strategy_name、stock_info、data_source 等元信息，仅回测触发时写入。
- **Complexity**: 6
- **Dependencies**: Task 1.2, Task 2.1
- **Acceptance Criteria**:
  - Neon 可见本次回测的信号行
  - 未启用 Neon 时流程不报错
- **Validation**:
  - 查询 DB 与 CSV 行数一致（允许过滤差异）

## Sprint 3: 回测 HTML 报告展示信号详情
**Goal**: 报告页面通过 API 读取 Neon 信号数据并展示指标值/触发条件。  
**Demo/Validation**:
- 打开回测结果页面，看到信号详情面板
- 点击/悬停信号可查看指标值

### Task 3.1: 新增查询接口
- **Location**: `frontend/frontend_app.py`
- **Description**: 增加 `/api/signals`（或类似）接口，按 run_id/日期/信号类型查询 Neon 并返回 JSON。
- **Complexity**: 6
- **Dependencies**: Task 1.2, Task 2.4
- **Acceptance Criteria**:
  - API 返回包含指标快照与触发说明
  - 错误时返回可读提示（不泄露连接信息）
- **Validation**:
  - Postman/浏览器访问接口返回正确 JSON

### Task 3.2: HTML 报告注入 run_id 元信息
- **Location**: `core/visualization/visual_tools_plotly.py`
- **Description**: 在 `build_report_payload` 增加 run_id/strategy/stock 信息，并在 `build_html_report` 中输出为 data-* 属性或全局变量。
- **Complexity**: 5
- **Dependencies**: Task 2.4
- **Acceptance Criteria**:
  - 生成的 HTML 中包含可解析的 run_id
- **Validation**:
  - 打开 HTML 源码可找到 run_id 信息

### Task 3.3: 报告页面展示信号详情（悬浮）
- **Location**: `core/visualization/visual_tools_plotly.py`（模板 HTML 部分），必要时 `frontend/templates/result_viewer.html`
- **Description**: 在 Plotly 信号点 hover 中追加指标值与触发条件展示；加载时通过后端 API 获取信号详情并注入自定义 hover data。
- **Complexity**: 7
- **Dependencies**: Task 3.1, Task 3.2
- **Acceptance Criteria**:
  - 页面可看到信号详情列表
  - 无数据时显示友好占位信息
- **Validation**:
  - 浏览器打开结果页面进行交互验证

## Sprint 4: 测试与文档
**Goal**: 覆盖核心逻辑的单测与文档说明。  
**Demo/Validation**:
- 运行 mock-only 测试通过

### Task 4.1: 单元测试
- **Location**: `test/test_signal_record_manager.py`（新增）
- **Description**: 测试 SignalRecordManager 新字段、序列化结果与兼容性。
- **Complexity**: 4
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - pytest mock-only 通过
- **Validation**:
  - `conda run -n data_analysis python -m pytest -m mock_only test/test_signal_record_manager.py`

### Task 4.2: 文档与使用说明
- **Location**: `docs/项目功能说明.md`, `docs/待办功能清单.md`
- **Description**: 记录 Neon 配置方式、HTML 展示入口、故障排查提示。
- **Complexity**: 3
- **Dependencies**: Task 3.3
- **Acceptance Criteria**:
  - 文档包含配置与访问路径
- **Validation**:
  - 人工审阅

## Testing Strategy
- 以 mock-only 为主（不访问真实 Neon）
- DB 层使用 mock 连接或 monkeypatch
- 浏览器验证通过前端页面手动检查

## Potential Risks & Gotchas
- Neon 连接失败导致回测流程中断（需降级/容错）
- 指标快照 JSON 过大影响写入性能
- run_id 与 HTML 文件名不一致导致查不到数据
- HTML 直接打开时无后端服务，无法访问 Neon API
- 时间戳/时区不一致导致信号匹配错位

## Rollback Plan
- 通过 `NEON_ENABLED=false` 回退为仅 CSV 存储
- 保留现有 CSV 生成逻辑作为兜底
