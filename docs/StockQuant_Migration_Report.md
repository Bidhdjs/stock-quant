# StockQuant 迁移变更清单

本文件汇总本次对话中从 https://github.com/Gary-Hertel/StockQuant 迁移的功能点，以及在当前项目内产生的代码改动与测试补充。

## 一、迁移的功能点

### 1) 实时行情数据源
- Sina 实时行情
  - 个股行情解析（含买卖盘）
  - 指数行情（上证/深证）
- 网易实时行情（money.126）
  - 个股行情解析（含买卖盘）
  - 指数行情（上证/深证）

对应实现：
- `core/stock/manager_sina.py`
- `core/stock/manager_money.py`
- 统一行情结构：`core/stock/realtime_types.py`

### 2) Tushare 基础数据
- 新股上市列表
- 股票基础信息列表

对应实现：
- `core/stock/manager_tushare.py`
- 通过环境变量 `TUSHARE_TOKEN` 配置 token

### 3) 技术指标（TA-Lib 封装）
实现并对齐接口调用方式（支持 `kline` 列表或 DataFrame）：
- ATR / BOLL / CCI / HIGHEST / MA / MACD / EMA / KAMA / KDJ / LOWEST
- OBV / RSI / ROC / STOCHRSI / SAR / STDDEV / TRIX / VOLUME
- `CurrentBar(kline)` 返回 k 线长度

对应实现：
- `core/strategy/indicator/talib_indicators.py`

## 二、测试补充（全 mock、不联网、不运行）

### 1) 实时行情测试
- `test/test_realtime_sources.py`
  - Sina 行情解析
  - 网易行情解析
  - 指数解析（上证/深证）

### 2) Tushare 管理器测试
- `test/test_tushare_manager.py`
  - token 必填校验
  - `pro_api` 调用路径验证（mock）

### 3) TA-Lib 指标测试
- `test/test_talib_indicators.py`
  - 拆分逻辑与依赖缺失行为
- `test/test_talib_indicator_api.py`
  - 全量指标接口与返回结构验证（mock）

### 4) 数据源管理器测试（mock 外部服务）
- `test/test_data_sources_mock.py`
  - akshare / baostock / futu / yfinance 分支路径验证

## 三、依赖更新

已新增依赖（仅写入 requirements，未安装）：
- `requests`
- `tushare`
- `TA-Lib`

对应文件：
- `requirements-13.txt`
- `requirements-7.txt`

## 四、文档更新

- `docs/QuickStart.md` 增加“外部数据源与指标（StockQuant 集成）”说明

## 五、标记说明

所有新增功能文件均添加了 `Front Code X` 标记，便于你后续统一注释或回滚：
- `core/stock/realtime_types.py`
- `core/stock/manager_sina.py`
- `core/stock/manager_money.py`
- `core/stock/manager_tushare.py`
- `core/strategy/indicator/talib_indicators.py`
- 所有新增测试文件

## 六、额外说明

- 本次迁移仅实现单点功能与 mock 测试，不涉及调度与前端页面接入
- 外部依赖均未执行联网测试，避免引入外部不稳定因素
- 本地克隆参考仓库路径：`.external/StockQuant`（仅供参考，不参与运行）

