# Stock-Quant 项目开发规范

## 核心原则
1. **向量化优先**：处理 DataFrame 时严禁使用 for 循环，必须使用 Pandas/NumPy 的内置方法或 apply。
2. **API 规范**：所有 Flask Route 必须包含 try-except 块，返回统一的 JSON 格式 {'success': bool, 'message': str, 'data': dict}。
3. **中文注释**：关键算法（如 MACD, 均线策略）必须用中文解释数学原理。

## 项目结构感知
- 策略文件位于 `core/strategy/trading/`，必须继承 `StrategyBase`。
- 数据清洗逻辑在 `core/stock/manager_common.py`，获取新数据源后必须调用 `standardize_stock_data`。
- 配置文件是 `settings.py`，涉及费率和路径时优先读取此文件。

## 库使用偏好
- 绘图优先使用 Plotly (HTML交互)，而非 Matplotlib (静态)。
- 时间处理优先使用 `common/time_key.py` 中的工具。