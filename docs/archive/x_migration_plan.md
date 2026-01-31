# x/ 迁移清单（Sprint 3）

> 目标：将 `x/` 内可复用脚本迁移到主模块结构，保持可维护与可测试。

## 迁移状态

- [X] `x/demo_tsla.py` → `core/analysis/migrations/ema_demo.py`（EMA 示例与数据抓取封装）
- [X] `x/find_trades.py` → `core/analysis/migrations/trade_scraper.py`（可选 Selenium 抓取）
- [X] `x/vcp_screener.github.io-main/.../vcp_screener.py` → `core/analysis/migrations/vcp_screener.py`（已拆分为可复用模块，默认不联网）
- [X] `x/vcp_from_youtuber/` → `core/analysis/migrations/vcp_tools.py` + `core/analysis/migrations/vcp_from_youtuber/`（提取可复用逻辑，保留说明性模块）
- [X] 交易策略分析基础模块：`core/analysis/trade_schema.py`、`core/analysis/trade_strategy_infer.py`
- [ ] `x/TV代码/*` → `docs/`（仅保留说明性脚本，不进入核心逻辑）

## 说明
- 已迁移的模块均为**可选工具**，默认不影响 CLI 与核心流程。
- 依赖外部数据源的脚本必须保持**懒加载**，避免在未安装依赖时触发异常。
- 迁移完成后再逐步补充 mock-only 测试覆盖。
