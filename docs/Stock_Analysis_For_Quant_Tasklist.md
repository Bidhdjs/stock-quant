# Stock_Analysis_For_Quant 迁移任务清单（Python_Stock）

以下任务按“先清单、后逐条执行”的方式设计。每条任务包含**对应提示词**，方便你后续逐条指令执行。  
路径基于本地克隆：`.external/Stock_Analysis_For_Quant_full/Python_Stock/`

---

## 任务 0：建立迁移范围清单（不改代码）
**目标**：生成“将要迁移的策略、风险、评估指标”的总清单（含来源文件）。

**提示词**  
“读取 `Python_Stock` 目录下所有 README 与关键 `.ipynb` 的标题与主要内容（不要执行代码），输出一份**迁移清单**：包含策略类、风险类、评估指标类、时间序列预测类、期权策略类、K线形态类。列出每项对应来源文件路径。”

---

## 任务 1：风险清单与风险定义迁移
**来源**  
- `Portfolio_Strategies/README.md`（风险列表）  
- `Stock_Measurement_Ratio_Chart/README.md`（风险描述）

**目标**：将风险类别与定义迁移到项目文档（不引入策略逻辑）。

**提示词**  
“读取 `Portfolio_Strategies/README.md` 与 `Stock_Measurement_Ratio_Chart/README.md`，提取**风险类别清单与定义**，整理成 `docs/Risk_Taxonomy.md`，并在每一项后注明来源文件路径。”

---

## 任务 2：风险调整绩效指标清单与说明
**来源**  
- `Portfolio_Strategies/README.md`  
- `Stock_Measurement_Ratio_Chart/README.md`

**目标**：提取“风险调整指标”的名称与简要说明，生成指标目录。

**提示词**  
“整理两份 README 中的**风险调整指标列表**（如 Sharpe、Sortino、Calmar、Ulcer 等），输出到 `docs/Performance_Metrics_Catalog.md`，为每个指标补一句话说明（按原文描述），并标注来源文件路径。”

---

## 任务 3：风险与收益指标的实现迁移（代码）
**来源（重点 notebooks）**  
- `Stock_RiskAndReturn.ipynb`  
- `ValueAtRisk.ipynb`  
- `Stock_Alpha_Beta.ipynb`  
- `StockReturnsAnalysis.ipynb`  
- `Annual_Returns.ipynb`  
- `Profit_Loss.ipynb`  
- `Stock_Time_Returns_Analysis.ipynb`

**目标**：把“风险/收益/回撤/波动/Alpha/Beta/VaR”等指标实现为可复用函数模块。

**提示词**  
“逐个阅读上述 notebooks 的代码单元，抽取计算逻辑，整理到 `core/analysis/performance_metrics.py`（新建），每个指标一个函数，包含中文 docstring 与公式说明，禁止执行外部网络；并补对应 mock 测试（不运行）。”

---

## 任务 4：组合策略与资产配置迁移
**来源**  
- `Portfolio_Strategies/*.ipynb`  
- `Portfolio_Analysis.ipynb`  
- `Risk_Returns_Portfolio.ipynb`  
- `Portfolio_Functions.ipynb`

**目标**：梳理组合策略分类，并迁移“组合分析指标/可视化”的共通部分。

**提示词**  
“先输出 `Portfolio_Strategies` 下所有策略笔记本的**策略名称清单**，然后从 `Portfolio_Functions.ipynb` 与 `Portfolio_Analysis.ipynb` 中抽取**组合收益、波动、回撤、权重/再平衡**的公共函数，实现到 `core/analysis/portfolio.py`，并补 mock 测试（不运行）。”

---

## 任务 5：期权策略与Greeks迁移
**来源**  
- `Options_Strategies/README.md`  
- `Options_Strategies/*.ipynb`

**目标**：迁移期权策略名称、Greeks 定义、Black-Scholes 定价逻辑。

**提示词**  
“整理 `Options_Strategies` 目录中的策略与 Greeks 列表，生成 `docs/Options_Strategies.md`。从 `Black_Scholes_*.ipynb` 抽取定价公式实现到 `core/analysis/options_pricing.py`，并添加 mock 测试（不运行）。”

---

## 任务 6：技术指标目录与优先级清单
**来源**  
- `Technical_Indicators/README.md`  
- `Technical_Indicators/*.ipynb`

**目标**：形成“指标目录 + 实现优先级”列表，不立即迁移所有指标实现。

**提示词**  
“读取 `Technical_Indicators/README.md`，生成 `docs/Technical_Indicators_Catalog.md`，并根据项目现有指标体系标注‘已存在/可复用/待迁移’三类。无需实现代码，只做清单与优先级建议。”

---

## 任务 7：K线形态与蜡烛图模式迁移
**来源**  
- `Candlestick_Patterns/README.md`  
- `Candlestick_Patterns/*.ipynb`

**目标**：整理蜡烛图模式清单，并迁移部分检测逻辑。

**提示词**  
“先输出 `Candlestick_Patterns` 下所有形态的名称清单，然后选 3–5 个典型形态（如 Doji / Engulfing 等）将检测逻辑迁移到 `core/analysis/candlestick_patterns.py`，并补 mock 测试（不运行）。”

---

## 任务 8：时间序列预测与误差指标迁移
**来源**  
- `Time_Series_Forecasting/README.md`  
- `Stock_TimeSeries_Forecast.ipynb`

**目标**：迁移误差指标（MAE/MAPE/MSE/RMSE/NRMSE/WAPE/WMAPE）与建模流程框架。

**提示词**  
“从 `Time_Series_Forecasting/README.md` 和 `Stock_TimeSeries_Forecast.ipynb` 抽取误差指标公式，建立 `core/analysis/forecast_metrics.py`；模型部分只保留接口框架与文档说明，不引入重依赖库。”

---

## 任务 9：统一文档整合
**目标**：把迁移完成的指标与策略写入统一文档。

**提示词**  
“将已迁移的风险、指标、策略整理进 `docs/Quant_Analysis_Catalog.md`，分为：风险分类、绩效指标、组合分析、期权分析、蜡烛图形态、时间序列误差指标；并注明来源路径。”

---

## 任务 10：测试统一入口（mock-only）
**目标**：新增一个统一测试入口，仅做 mock。

**提示词**  
“新增 `test/test_analysis_suite.py`，聚合本次迁移的分析模块测试用例（全部 mock，不联网、不运行），并补 README 说明如何执行单测。”
