# Quant Analysis Catalog（迁移汇总）

本文件汇总从 `Stock_Analysis_For_Quant` 迁移到本项目的代码模块与功能点，便于后续扩展与维护。

---

## 1. 绩效与风险指标

**模块**：`core/analysis/performance_metrics.py`  
**覆盖功能**：
- 日收益率、年化收益/波动  
- Sharpe、Sortino  
- 最大回撤  
- 实现波动/方差  
- Alpha/Beta/R^2  
- VaR（历史、正态、t 分布、蒙特卡洛）  
- 盈亏与总回报  

---

## 2. 组合分析与资产配置

**模块**：`core/analysis/portfolio.py`  
**覆盖功能**：
- 日对数收益、月/年收益  
- 组合收益序列与累计收益  
- 组合方差/标准差/协方差矩阵  
- 组合预期收益、Sharpe、Sortino  
- 滚动最大回撤  
- 风险收益表  

---

## 3. 期权定价与 Greeks

**模块**：`core/analysis/options_pricing.py`  
**覆盖功能**：
- Black‑Scholes d1/d2  
- 欧式看涨/看跌定价  
- 看涨‑看跌平价  
- Greeks（Delta/Gamma/Theta/Vega/Rho）  

---

## 4. 时间序列误差指标

**模块**：`core/analysis/forecast_metrics.py`  
**覆盖功能**：
- MAE / MAPE / MSE / RMSE  
- NRMSE（mean/range）  
- WAPE / WMAPE  

---

## 5. 时间序列预测模型（基础）

**模块**：`core/analysis/forecast_models.py`  
**覆盖功能**：
- ForecastModel 抽象接口  
- NaiveForecast  
- MovingAverageForecast  

---

## 6. 技术指标扩展（非 TA‑Lib）

**模块**：`core/analysis/technical_indicators_ext.py`  
**覆盖功能**：
- ADL、ADXVMA、EVM、ForceIndex、Chaikin  
- TSI、Fishy Turbo、Guppy EMA  
- Heiken Ashi  
- Parabolic SAR  
- PMO  
- Pring Special K  
- RS Ratio/Momentum  
- TMA、VWMA、VWAP  
- WMA、WSMA  

---

## 7. 蜡烛图形态检测（TA‑Lib CDL）

**模块**：`core/analysis/candlestick_patterns.py`  
**覆盖功能**：
- Doji  
- Morning Star  
- Dark Cloud Cover  
- Abandoned Baby  
- Belt Hold  
- 批量检测 `detect_patterns`  

---

## 8. 测试覆盖（mock-only）

**新增测试文件**：  
- `test/test_performance_metrics.py`  
- `test/test_portfolio_analysis.py`  
- `test/test_options_pricing.py`  
- `test/test_forecast_metrics.py`  
- `test/test_forecast_models.py`  
- `test/test_technical_indicators_ext.py`  
- `test/test_candlestick_patterns.py`  

说明：所有测试均为 mock / 本地数据，不联网、不运行。

