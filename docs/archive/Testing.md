# pytest 测试指南

## 1. 推荐命令

```bash
python -m pytest
```

精确指定 mock-only 测试：

```bash
python -m pytest -m mock_only
```

跳过网络测试：

```bash
python -m pytest -m "not network"
```

## 2. 标记（markers）

- `mock_only`：仅使用 mock，不触发外部网络
- `network`：需要真实外部服务
- `slow`：耗时较长的测试

## 3. Fixture

公共 fixture 位于 `test/conftest.py`，当前包含：

- `sample_prices`
- `sample_returns_df`
- `sample_ohlcv_df`
- `fixed_seed`

## 4. 模板

```python
import pytest


@pytest.mark.mock_only
def test_example():
    assert 1 + 1 == 2
```
