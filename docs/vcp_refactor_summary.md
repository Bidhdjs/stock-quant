# VCP 指标重构说明

## 概述
按照项目架构规范，完成了 VCP（Volatility Contraction Pattern）指标的职责划分和代码重构。

## 重构前后对比

### 重构前（不规范）
```
core/analysis/indicators/vcp.py
  └─ evaluate_vcp()  ← 包含所有 VCP 逻辑（数据处理+条件判定+信号触发）【混合了多个职责】

core/strategy/indicator/pattern/vcp_indicator.py
  └─ VCPIndicator
      └─ 直接调用 evaluate_vcp()（缺少信号判定的定制性）
```

### 重构后（符合规范）
```
core/analysis/indicators/vcp.py
  ├─ _resolve_column()         ← 数据列提取
  ├─ _local_extrema()          ← 局部极值点识别
  ├─ _contractions()           ← 收缩幅度计算
  ├─ _num_contractions()       ← 收缩次数统计
  ├─ VCPParams                 ← 参数对象
  ├─ evaluate_vcp()            ← 【已废弃】指向新实现
  └─ evaluate_vcp_legacy()     ← 原始完整实现（备份参考）

core/strategy/indicator/pattern/vcp_indicator.py
  └─ VCPIndicator
      ├─ _evaluate_vcp_conditions()  ← 【核心新增】条件综合判定+信号触发逻辑
      └─ next()                      ← 使用新方法
```

## 职责划分

### core/analysis/indicators/vcp.py
**职责**：基础指标计算与数据清洗
- 从 CSV 数据转换为技术指标（均线、局部极值等）
- 提供底层工具函数供上层使用
- **不涉及**：条件组合、信号触发决策

**函数**：
- `_resolve_column()` - 容错处理列名大小写
- `_local_extrema()` - 识别局部高/低点
- `_contractions()` - 计算波段收缩幅度
- `_num_contractions()` - 统计有效收缩次数

### core/strategy/indicator/pattern/vcp_indicator.py
**职责**：指标判定与信号触发
- 综合判定所有 VCP 条件（Stage 2、收缩、成交量等）
- 生成买入/卖出信号
- 记录信号事件

**方法**：
- `_evaluate_vcp_conditions(df, params)` - 条件综合判定核心逻辑
- `next()` - backtrader 指标循环，触发信号输出

## 关键改动

### 1. 导入优化
```python
# 之前：导入整个 evaluate_vcp
from core.analysis.indicators.vcp import VCPParams, evaluate_vcp

# 之后：只导入工具函数和参数
from core.analysis.indicators.vcp import (
    VCPParams, 
    _resolve_column, 
    _local_extrema, 
    _contractions, 
    _num_contractions
)
```

### 2. 逻辑迁移
完整的条件综合判定逻辑（原在 `evaluate_vcp()` 中）迁移到：
- `VCPIndicator._evaluate_vcp_conditions()`

### 3. evaluate_vcp() 的变化
- **原用途**：完整的 VCP 计算
- **新用途**：废弃函数，输出警告提示使用 VCPIndicator
- **备份**：`evaluate_vcp_legacy()` 保存原始实现供参考

## 优势

✅ **职责清晰**
- 数据处理层 vs 信号决策层分离
- 便于测试和维护

✅ **易于扩展**
- 新的信号判定逻辑在 VCPIndicator 中添加
- 不需要修改基础计算函数

✅ **性能优化**
- VCPIndicator 直接使用工具函数，减少重复计算
- 避免不必要的数据转换

✅ **代码复用**
- 工具函数可被其他指标调用
- 统一的数据处理标准

## 测试覆盖

- ✅ `test_vcp_plus_strategy.py` - VCP+ 策略（2 tests passed）
- ✅ `test_vcp_strategy.py` - VCP 基础策略（2 tests passed）
- ✅ 所有现有测试保持通过

## 向后兼容性

- `VCPParams` 保持不变，现有代码无需修改
- `evaluate_vcp_legacy()` 提供原始实现备份
- VCPIndicator 使用保持一致，透明迁移

## 使用建议

### 标准用法（推荐）
在 backtrader 策略中使用 VCPIndicator：
```python
from core.strategy.indicator.pattern.vcp_indicator import VCPIndicator

class MyStrategy(bt.Strategy):
    def __init__(self):
        self.vcp = VCPIndicator()  # 自动处理所有条件判定
```

### 直接计算用法（如需测试）
仅在特殊场景下调用 `evaluate_vcp_legacy()`：
```python
from core.analysis.indicators.vcp import evaluate_vcp_legacy, VCPParams

result = evaluate_vcp_legacy(df, VCPParams())
```

---

**重构时间**：2026-01-31  
**涉及文件**：
- `core/analysis/indicators/vcp.py`
- `core/strategy/indicator/pattern/vcp_indicator.py`
