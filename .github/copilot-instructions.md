# Stock-Quant Copilot 配置

执行前获取一些最新的当前时间
对任何问题先规划再执行
当执行遇到任何问题把经验教训写回到copilot-instructions.md 文件中
中文描述优先
默认使用虚拟环境 data_analysis
避免中文乱码：此文件必须使用 UTF-8（带 BOM）编码保存，编辑时保持编码一致。

## 项目开发规范（要点）
1. **向量化优先**：处理 DataFrame 时禁止 `for` 遍历，优先 Pandas/NumPy 向量化或 `apply`。
2. **API 规范**：所有 Flask Route 必须包含 try-except，返回统一 JSON：`{'success': bool, 'message': str, 'data': dict|list}`。
3. **中文注释**：关键算法（MACD/RSI/布林带等）必须用中文解释数学原理。
4. **标准化输出**：新增数据源后必须调用 `standardize_stock_data()`。
5. **可视化优先**：优先使用 Plotly 输出 HTML 交互图表。

## 项目结构与约定
- 策略文件：`core/strategy/trading/`，策略类必须继承 `StrategyBase`。
- 指标文件：`core/strategy/indicator/`，指标类必须继承 `bt.Indicator`。
- 配置文件：`settings.py`。
- 时间工具：`common/time_key.py`。

## 工作流程要求
- 收到新任务先查看 Scratchpad，必要时清空旧任务，写出本次任务与步骤。
- 使用 todo 标记进度：
  - `[ ]` 未完成
  - `[X]` 已完成
- 完成阶段性成果及时更新 Scratchpad。
- 任何可复用的经验（尤其是你犯错后修复的经验）写入 `Lessons`。

# Tools

> 项目工具均为 Python 脚本，可用于批处理或自动化。

## Screenshot Verification
```bash
venv/bin/python tools/screenshot_utils.py URL [--output OUTPUT] [--width WIDTH] [--height HEIGHT]
venv/bin/python tools/llm_api.py --prompt "Your verification question" --provider {openai|anthropic} --image path/to/screenshot.png
```

## LLM
```bash
venv/bin/python ./tools/llm_api.py --prompt "Your prompt" --provider "anthropic"
```

## Web Browser
```bash
venv/bin/python ./tools/web_scraper.py --max-concurrent 3 URL1 URL2 URL3
```

## Search Engine
```bash
venv/bin/python ./tools/search_engine.py "your search keywords"
```

# Lessons

## User Specified Lessons
- You have a python venv in ./venv. Use it.
- Include info useful for debugging in the program output.
- Read the file before you try to edit it.
- Due to Cursor's limit, when you use `git` and `gh` and need to submit a multiline commit message, first write the message in a file, and then use `git commit -F <filename>` or similar command to commit. And then remove the file. Include "[Cursor] " in the commit message and PR title.

## Cursor learned
- For search results, ensure proper handling of different character encodings (UTF-8) for international queries
- Add debug information to stderr while keeping the main output clean in stdout for better pipeline integration
- When using seaborn styles in matplotlib, use 'seaborn-v0_8' instead of 'seaborn' as the style name due to recent seaborn version changes
- Use 'gpt-4o' as the model name for OpenAI's GPT-4 with vision capabilities

## Project Lessons
- AGENTS.md 等中文规则文件必须使用 UTF-8（带 BOM）保存，避免 PowerShell/编辑器默认编码导致乱码。
- copilot-instructions.md 必须使用 UTF-8（带 BOM）保存，必要时用 python 直接写入避免乱码。
- 虚拟环境命名为 data_analysis，避免与其他项目冲突。
# Scratchpad

- [X] 任务描述：执行 Sprint 1（数据源稳定 + mock-only 测试补强）
- [X] 计划步骤：1) 评估现有数据源与标准化流程 2) 增强标准化/校验与缺失成交量提示 3) 加 mock-only 测试 4) 运行 mock-only 测试
- [ ] 进度更新：已完成标准化与校验增强、添加测试；等待安装 pytest 后运行 mock-only 测试