## Content input and output
- Always use 'chcp 65001' before running shell commands that produce text output on Windows to ensure UTF-8 encoding and avoid garbled characters.

# Agent 命令执行环境规范

- 执行命令请始终优先选择 **PowerShell 7（pwsh.exe）**，而不是旧版的 **powershell.exe**。
- 这样能保证命令执行全部采用 UTF-8 编码，避免中文乱码问题及 BOM 错误。
- 请勿使用 powershell.exe，确保兼容新特性和中文无乱码。

# Agent 执行前准备

- 执行前获取最新当前时间
- 对任何问题先规划再执行
- 默认使用虚拟环境 data_analysis
- 中文描述优先
- 执行遇到问题将经验教训写回本文件 Lessons
- 避免中文乱码：本文件必须使用 UTF-8 编码保存，编辑时保持编码一致。

# Stock-Quant Codex 代码生成规范

## 1. 文件头部注释（必须包含）
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
- Manager 类文件：`manager_<数据源>.py`
- 策略文件：`<策略功能>.py`（位于 `core/strategy/trading/`）
- 指标文件：`<指标名>.py`（位于 `core/strategy/indicator/`）

### 2.2 类命名
- 大驼峰（PascalCase）：`YFinanceManager`, `StrategyBase`
- Manager 类命名模式：`<Source>Manager`
- 策略类必须继承：`StrategyBase`（from `core.strategy.trading.common`）
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

## 3. 数据处理规范（核心）

### 3.1 向量化处理（强制）
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

### 3.2 数据标准化流程
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

### 3.3 DataFrame 列名要求
- **统一使用英文小写列名**：`open`, `close`, `high`, `low`, `volume`
- **必需列**：`['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'stock_code', 'stock_name', 'market']`
- **日期列处理**：
```python
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')  # 必须按日期升序排序
```

## 4. 策略开发规范

### 4.1 策略类结构
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

### 4.2 指标开发规范
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

---

**核心要点总结：**
1. ✅ 中文注释 + 向量化处理 + API 规范
2. ✅ 继承 `StrategyBase` / `bt.Indicator`
3. ✅ 调用 `standardize_stock_data()`
4. ✅ 使用 `settings.py` 配置
5. ✅ Plotly 绘图优先

## 5. Pytest Testing Rules

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

## 6. 项目结构与约定

- 策略文件：`core/strategy/trading/`，策略类必须继承 `StrategyBase`。
- 指标文件：`core/strategy/indicator/`，指标类必须继承 `bt.Indicator`。
- 配置文件：`settings.py`。
- 时间工具：`common/time_key.py`。

## 7. 工具

> 项目工具均为 Python 脚本，可用于批处理或自动化。

### Screenshot Verification
```bash
python tools/screenshot_utils.py URL [--output OUTPUT] [--width WIDTH] [--height HEIGHT]
python tools/llm_api.py --prompt "Your verification question" --provider {openai|gemini} --image path/to/screenshot.png
```

### LLM
```bash
python ./tools/llm_api.py --prompt "Your prompt" --provider {openai|gemini}
```

### Web Browser
```bash
python ./tools/web_scraper.py --max-concurrent 3 URL1 URL2 URL3
```

### Search Engine
```bash
python ./tools/search_engine.py "your search keywords"
```

## 8. 工作流程要求

- 收到新任务先查看 Scratchpad，必要时清空旧任务，写出本次任务与步骤。
- 使用 todo 标记进度：
  - `[ ]` 未完成
  - `[X]` 已完成
- 完成阶段性成果及时更新 Scratchpad。
- 任何可复用的经验（尤其是你犯错后修复的经验）写入 `Lessons`。

## Scratchpad
## Scratchpad

- [X] 任务描述：回答 PowerShell 7 如何设置环境变量
- [X] 计划步骤：1) 区分临时/持久与用户/系统范围 2) 给出常用 pwsh 命令 3) 补充查看/生效说明
- [X] 进度更新：已给出 PowerShell 7 环境变量设置方法

## Lessons

- After generating Chinese text, verify files for mojibake ("?", "?", "?", "?") and re-save as UTF-8 using Python if needed.

- web_scraper.py 使用 response.body + charset 解析后仍可能乱码；需检查是否被二次转码或改用 response.text()/requests+chardet 专门处理 GBK。

- Windows 下 git filter-branch 可能因脚本执行/路径问题报 "cd: write error: No error" 并超时，必要时改用交互式 rebase 移除敏感文件。

- web_scraper.py 抓取到的中文可能乱码（站点为 GBK/GB2312）；需按页面 charset 转码或用 chardet 检测后再解析。

- conda run 在 GBK 控制台输出包含特殊字符时可能触发 UnicodeEncodeError；可尝试设置 OutputEncoding 为 UTF-8 或用 CONDA_NO_PLUGINS=true。
- 运行 pytest/cli_smoke 如遇 conda UnicodeEncodeError，建议设置 CONDA_NO_PLUGINS=true 与 PYTHONIOENCODING=utf-8 后重试。

- web_scraper.py 依赖 Playwright；未安装会报 ModuleNotFoundError: playwright。

- Installing google-generativeai upgraded protobuf to 5.x, which conflicts with futu-api (requires protobuf 3.x).
- llm_api.py imports google.generativeai at module load; if it is missing, even OpenAI calls fail. Install google-generativeai or make the import lazy.
- Running tools/screenshot_utils.py requires Playwright (and browser drivers); otherwise it fails with ModuleNotFoundError: playwright.
- 新增测试后必须在 data_analysis 环境跑 mock-only（conda run -n data_analysis python -m pytest -m mock_only test/xxx.py），如失败需当场修复并复跑。
- 运行 pytest 时必须使用 conda 环境 data_analysis（推荐: conda run -n data_analysis python -m pytest -m mock_only）。
- 写回的内容如果是乱码就用英文写回。

- 通过 PowerShell 管道传入含中文的脚本可能被系统代码页替换为问号；写文件时先设置 OutputEncoding 为 UTF-8。


- AGENTS.md 等中文规则文件必须使用 UTF-8 保存，避免 PowerShell/编辑器默认编码导致乱码。
- copilot-instructions.md 必须使用 UTF-8 保存，必要时用 python 直接写入避免乱码。
- 虚拟环境命名为 data_analysis，避免与其他项目冲突。

- On Windows, conda run can crash printing stdout with Unicode (GBK encoding); sanitize output or force UTF-8.
- 更新 CLI 或测试后，先用 data_analysis 环境运行 tools/cli_smoke.py 验证（conda run -n data_analysis python tools/cli_smoke.py）。
- tools/search_engine.py uses duckduckgo_search (now renamed to ddgs) and may return no results; also non-ASCII queries can appear garbled in PowerShell.
- tools/search_engine.py requires duckduckgo_search; missing package causes ModuleNotFoundError.
- Gemini API call failed with PERMISSION_DENIED: API key reported as leaked; rotate to a new key.
- Context7 API key (CONTEXT7_API_KEY) is not set, so docs lookup via context7 is unavailable.
- Gemini call via google-generativeai can warn deprecation (use google.genai) and fail with WinError 10060 (connection timeout).
- 更新 CLI 或测试后，先用 data_analysis 环境运行 tools/cli_smoke.py 验证（conda run -n data_analysis python tools/cli_smoke.py）。
- 生成中文相关的内容之后都需要自己检查一遍是否有出现乱码全是?的问题，发现后修正
