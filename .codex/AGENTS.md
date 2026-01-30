执行前获取一些最新的当前时间
对任何问题先规划再执行
当执行遇到任何问题把经验教训写回到AGENTS.md 文件中
中文描述优先
默认使用虚拟环境 data_analysis
避免中文乱码：此文件必须使用 UTF-8（带 BOM）编码保存，编辑时保持编码一致。

# Stock-Quant Codex 代码生成规范

## 1. 文件结构与导入规范

### 1.1 导入顺序（强制遵守）
```python
# 第一组：Python 标准库
import os
import sys
import datetime
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path

# 第二组：第三方库（按字母排序）
import pandas as pd
import numpy as np
import backtrader as bt
from flask import Flask, request, jsonify
from pandas import DataFrame

# 第三组：项目内部导入
from common.logger import create_log
from common.util_csv import save_to_csv
from settings import stock_data_root, INIT_CASH
```

### 1.2 文件头部注释（必须包含）
```python
"""
模块功能简述（一句话）
详细说明或使用场景说明

数学原理：（如涉及量化策略/指标计算，必须添加）
1. 原理1：公式推导或计算逻辑（用中文解释）
2. 原理2：数据处理方法说明
"""
```

## 2. 命名规范

### 2.1 文件命名
- 全部小写，单词间用下划线分隔：`manager_yfinance.py`
- Manager类文件：`manager_<数据源>.py`
- 策略文件：`<策略功能>.py`（位于 `core/strategy/trading/`）
- 指标文件：`<指标名>.py`（位于 `core/strategy/indicator/`）

### 2.2 类命名
- 大驼峰（PascalCase）：`YFinanceManager`, `StrategyBase`
- Manager类命名模式：`<Source>Manager`
- 策略类必须继承：`StrategyBase` (from `core.strategy.trading.common`)
- 指标类必须继承：`bt.Indicator`

### 2.3 函数/方法命名
- 小写+下划线：`get_stock_data()`, `standardize_stock_data()`
- 私有方法以单下划线开头：`_get_yf_ticker()`
- 双下划线开头的方法禁止使用（除魔术方法外）

### 2.4 变量命名
- 小写+下划线：`stock_code`, `market_name`
- 常量全大写：`MIN_ORDER_SIZE`, `HK_COMMISSION`
- DataFrame 变量名：`df`, `data`, `stock_df`（禁止用 `dataframe`）

### 2.5 常量定义位置
- 全局通用常量：定义在 `settings.py`
- 模块级常量：定义在文件顶部（导入之后）
```python
# 示例
MARKET_SUFFIX_MAP = {
    'US': '',
    'HK': '.HK',
}

MARKET_NAME_MAP = {
    'US': '美股',
    'HK': '港股',
}
```

## 3. 注释规范

### 3.1 函数文档字符串（Docstring）
```python
def get_stock_data(self, stock_code: str, start_date: str, end_date: str, market: str = 'US') -> DataFrame:
    """
    获取股票历史数据（一句话功能描述）
    
    Args:
        stock_code: 股票代码 (如 'AAPL', '00700')
        start_date: 开始日期 (格式: 'YYYY-MM-DD')
        end_date: 结束日期 (格式: 'YYYY-MM-DD')
        market: 市场代码 (默认: 'US', 可选: 'HK', 'TW')
    
    Returns:
        DataFrame: 标准化的股票数据，包含列：
            - date: 日期
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - stock_code: 股票代码
            - stock_name: 股票名称
            - market: 市场
    
    Raises:
        ValueError: 当市场代码不支持时
        DataSourceError: 当数据源请求失败时
    
    Example:
        >>> df = manager.get_stock_data('AAPL', '2024-01-01', '2024-12-31', 'US')
    """
```

### 3.2 行内注释规则
- **中文注释**：用于解释业务逻辑、数学原理、复杂算法
- **英文注释**：仅在与国际化库/API交互时使用
- 关键算法必须注释（MACD, RSI, 布林带等）

```python
# 计算 MACD 指标：基于 EMA(12) - EMA(26)，信号线为 MACD 的 EMA(9)
df['macd'] = df['ema12'] - df['ema26']
df['signal'] = df['macd'].ewm(span=9).mean()

# 港股需要去掉前导零并补足4位
if market == 'HK':
    stock_code = stock_code.lstrip('0').zfill(4)
```

### 3.3 类注释规范
```python
class YFinanceManager:
    """
    yfinance 数据管理器
    
    特性：
    1. 支持全球多市场数据获取
    2. 自动处理 yfinance 新版本的 MultiIndex 列名问题
    3. 统一输出格式，与项目其他数据源兼容
    
    支持市场：
        - US: 美股
        - HK: 港股
        - TW: 台股
    """
```

## 4. 数据处理规范（核心）

### 4.1 向量化处理（强制）
**严禁使用 for 循环遍历 DataFrame！**

❌ **错误示例：**
```python
# 禁止这样写！
for index, row in df.iterrows():
    df.at[index, 'sma'] = df.loc[:index, 'close'].mean()
```

✅ **正确示例：**
```python
# 使用向量化操作
df['sma'] = df['close'].rolling(window=20).mean()

# 使用 apply（仅在必须时）
df['custom'] = df.apply(lambda row: complex_function(row), axis=1)

# 使用向量化条件
df['signal'] = np.where(df['close'] > df['sma'], 1, 0)
```

### 4.2 数据标准化流程
所有数据源获取的数据必须调用 `standardize_stock_data()`：

```python
from core.stock.manager_common import standardize_stock_data

# 获取原始数据后
raw_df = yf.download(ticker, start=start_date, end=end_date)

# 立即标准化
df = standardize_stock_data(
    df=raw_df,
    stock_code=stock_code,
    stock_name=stock_name,
    market=market
)
```

### 4.3 DataFrame 列名要求
- **统一使用英文小写列名**：`open`, `close`, `high`, `low`, `volume`
- **必需列**：`['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'stock_code', 'stock_name', 'market']`
- **日期列处理**：
```python
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')  # 必须按日期升序排序
```

## 5. Flask API 规范

### 5.1 统一返回格式
**所有 API 必须返回此格式：**
```python
{
    'success': bool,      # True/False
    'message': str,       # 描述性信息（中文）
    'data': dict or list  # 实际数据
}
```

### 5.2 路由定义模板
```python
@app.route('/api/stock/data', methods=['GET', 'POST'])
def get_stock_data():
    """获取股票数据 API"""
    try:
        # 1. 获取参数
        stock_code = request.args.get('stock_code') or request.json.get('stock_code')
        market = request.args.get('market', 'US')
        
        # 2. 参数校验
        if not stock_code:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: stock_code',
                'data': {}
            }), 400
        
        # 3. 业务逻辑
        manager = YFinanceManager()
        df = manager.get_stock_data(stock_code, start_date, end_date, market)
        
        # 4. 返回结果
        return jsonify({
            'success': True,
            'message': '数据获取成功',
            'data': {
                'stock_code': stock_code,
                'records': df.to_dict('records')
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'参数错误: {str(e)}',
            'data': {}
        }), 400
        
    except Exception as e:
        logger.error(f'获取股票数据失败: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}',
            'data': {}
        }), 500
```

### 5.3 日志记录
```python
from common.logger import create_log

logger = create_log('module_name')  # 使用模块名

# 使用场景
logger.info(f'处理请求: stock_code={stock_code}')
logger.warning(f'数据缺失: {missing_columns}')
logger.error(f'操作失败: {error_msg}', exc_info=True)  # 错误时打印堆栈
```

## 6. 策略开发规范

### 6.1 策略类结构
```python
# 文件位置: core/strategy/trading/<策略名>.py
import backtrader as bt
from core.strategy.trading.common import StrategyBase

class MyStrategy(StrategyBase):
    """
    策略说明
    
    交易逻辑：
    - 买入信号：条件1 AND 条件2
    - 卖出信号：条件3 OR 条件4
    
    参数说明：
    - period: 移动平均周期（默认20）
    - threshold: 阈值参数（默认0.02）
    """
    
    params = (
        ('period', 20),
        ('threshold', 0.02),
    )
    
    def __init__(self):
        super().__init__()
        # 初始化指标
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.period)
    
    def trading_strategy_buy(self):
        """
        买入策略逻辑
        
        Returns:
            bool: True表示触发买入信号
        """
        if self.data.close[0] > self.sma[0] * (1 + self.p.threshold):
            return True
        return False
    
    def trading_strategy_sell(self):
        """
        卖出策略逻辑
        
        Returns:
            bool: True表示触发卖出信号
        """
        if self.data.close[0] < self.sma[0] * (1 - self.p.threshold):
            return True
        return False
```

### 6.2 指标开发规范
```python
# 文件位置: core/strategy/indicator/<指标名>.py
import backtrader as bt

class MyIndicator(bt.Indicator):
    """
    自定义指标
    
    计算公式：
    1. 步骤1的数学描述
    2. 步骤2的数学描述
    
    参数：
    - period: 计算周期
    """
    
    lines = ('signal',)  # 定义输出线
    params = (
        ('period', 14),
    )
    
    def __init__(self):
        # 使用向量化操作
        self.lines.signal = bt.indicators.SMA(self.data.close, period=self.p.period)
```

## 7. 配置与路径管理

### 7.1 使用 settings.py 配置
```python
from settings import stock_data_root, INIT_CASH, HK_COMMISSION

# 构建路径
data_file = stock_data_root / f'{stock_code}.csv'

# 使用费率常量
commission_fee = trade_amount * HK_COMMISSION
```

### 7.2 路径处理
```python
from pathlib import Path

# 优先使用 Path 对象
data_dir = Path('data/stock')
data_dir.mkdir(parents=True, exist_ok=True)

# 拼接路径
file_path = data_dir / f'{stock_code}_{market}.csv'
```

## 8. 时间处理规范

### 8.1 优先使用项目工具
```python
from common.time_key import get_current_date, format_date

# 获取当前日期
today = get_current_date()

# 格式化日期
date_str = format_date(datetime_obj)
```

### 8.2 时区处理
```python
# 统一使用 UTC 或项目配置的时区
df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)  # 移除时区
```

## 9. 可视化规范

### 9.1 优先使用 Plotly
```python
from core.visualization.visual_tools_plotly import create_candlestick_chart

# 使用项目封装的 Plotly 工具
fig = create_candlestick_chart(df, title='股价走势')
fig.write_html('output.html')
```

### 9.2 禁止使用 Matplotlib
除非有明确的静态图需求，否则一律使用 Plotly 生成交互式图表。

## 10. 代码风格检查清单

在生成代码前，确认：

- [ ] 导入顺序符合规范（标准库 → 第三方 → 项目内部）
- [ ] 文件头部包含中文文档字符串
- [ ] 所有函数都有详细的 Docstring（中文）
- [ ] DataFrame 操作全部使用向量化（无 for 循环）
- [ ] 数据源输出调用了 `standardize_stock_data()`
- [ ] Flask API 包含 try-except 并返回统一 JSON 格式
- [ ] 策略类继承 `StrategyBase`
- [ ] 指标类继承 `bt.Indicator`
- [ ] 关键算法添加中文数学原理注释
- [ ] 使用 `settings.py` 中的配置常量
- [ ] 日志使用 `create_log()` 创建
- [ ] 路径使用 `Path` 对象处理
- [ ] 可视化优先使用 Plotly

## 11. 示例：完整文件模板

```python
"""
新数据源管理器
支持从 XXX 平台获取股票数据

数学原理：
1. 复权计算：price_adjusted = price_raw * adj_factor
2. 缺失值处理：使用前向填充法（forward fill）
"""

import os
from typing import Optional
from pathlib import Path

import pandas as pd
from pandas import DataFrame

from common.logger import create_log
from core.stock.manager_common import standardize_stock_data
from settings import stock_data_root

logger = create_log('manager_newsource')


class NewSourceManager:
    """
    新数据源管理器
    
    特性：
    1. 支持多市场数据
    2. 自动缓存机制
    """
    
    def __init__(self):
        """初始化管理器"""
        self.data_dir = stock_data_root / 'newsource'
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def get_stock_data(self, stock_code: str, start_date: str, 
                      end_date: str, market: str = 'US') -> DataFrame:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (格式: 'YYYY-MM-DD')
            end_date: 结束日期
            market: 市场代码
        
        Returns:
            DataFrame: 标准化的股票数据
        """
        try:
            # 1. 获取原始数据
            raw_df = self._fetch_raw_data(stock_code, start_date, end_date, market)
            
            # 2. 标准化数据（必须调用）
            df = standardize_stock_data(
                df=raw_df,
                stock_code=stock_code,
                stock_name=self._get_stock_name(stock_code),
                market=market
            )
            
            logger.info(f'成功获取 {stock_code} 数据，共 {len(df)} 条记录')
            return df
            
        except Exception as e:
            logger.error(f'获取数据失败: {stock_code}, {str(e)}', exc_info=True)
            raise
    
    def _fetch_raw_data(self, stock_code: str, start_date: str, 
                       end_date: str, market: str) -> DataFrame:
        """
        从数据源获取原始数据（内部方法）
        
        Returns:
            DataFrame: 原始数据
        """
        # 实现逻辑...
        pass
```

---

**核心要点总结：**
1. ✅ 中文注释 + 向量化处理 + API 规范
2. ✅ 继承 `StrategyBase` / `bt.Indicator`
3. ✅ 调用 `standardize_stock_data()`
4. ✅ 使用 `settings.py` 配置
5. ✅ Plotly 绘图优先

## 12. Pytest Testing Rules

- Use pytest for all tests; do not use unittest.
- Test files live in `test/` and follow `test_*.py` naming.
- Default to `@pytest.mark.mock_only`; do not hit external network.
- Use `@pytest.mark.network` for real external services and document it.
- Use `@pytest.mark.slow` for long-running tests.
- Shared fixtures live in `test/conftest.py`.
- Use pytest `assert` instead of `self.assert*`.
- 需要在不改命令行参数的情况下输出调试信息时，使用 `capsys`：
  `with capsys.disabled(): print(value)`

Example:
```python
import pytest


@pytest.mark.mock_only
def test_example():
    assert 1 + 1 == 2
```
# Tools

> 项目工具均为 Python 脚本，可用于批处理或自动化。

## Screenshot Verification
```bash
python tools/screenshot_utils.py URL [--output OUTPUT] [--width WIDTH] [--height HEIGHT]
python tools/llm_api.py --prompt "Your verification question" --provider {openai|anthropic} --image path/to/screenshot.png
```

## LLM
```bash
python ./tools/llm_api.py --prompt "Your prompt" --provider "anthropic"
```

## Web Browser
```bash
python ./tools/web_scraper.py --max-concurrent 3 URL1 URL2 URL3
```

## Search Engine
```bash
python ./tools/search_engine.py "your search keywords"
```

# Lessons
- 新增测试后必须在 data_analysis 环境跑 mock-only（conda run -n data_analysis python -m pytest -m mock_only test/xxx.py），如失败需当场修复并复跑。
- 运行 pytest 时必须使用 conda 环境 data_analysis（推荐: conda run -n data_analysis python -m pytest -m mock_only）。



## Project Lessons
- AGENTS.md 等中文规则文件必须使用 UTF-8（带 BOM）保存，避免 PowerShell/编辑器默认编码导致乱码。
- 虚拟环境使用 conda data_analysis，避免与系统 Python 包冲突。

- copilot-instructions.md 必须使用 UTF-8（带 BOM）保存，必要时用 python 直接写入避免乱码。
# Scratchpad

- [ ] 任务描述：
- [ ] 计划步骤：
- [ ] 进度更新：
