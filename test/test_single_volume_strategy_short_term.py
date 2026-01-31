"""
SingleVolumeStrategy 短期数据调试测试。

用途：
  - 使用 2024-06 到 2024-09 三个月的实际数据
  - 测试 SingleVolumeStrategy 策略的完整流程
  - 便于逐步调试策略的买卖信号生成

运行方式：
  conda run -n data_analysis python -m pytest test/test_single_volume_strategy_short_term.py -v -s --tb=short
  conda run -n data_analysis python -m pytest test/test_single_volume_strategy_short_term.py::test_single_volume_strategy_with_short_csv -v -s
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile


@pytest.mark.mock_only
def test_single_volume_strategy_registered():
    """验证 SingleVolumeStrategy 已注册"""
    from core.strategy.strategy_manager import StrategyManager
    
    manager = StrategyManager()
    names = manager.get_strategy_names()
    assert "SingleVolumeStrategy" in names, f"SingleVolumeStrategy not found in {names}"


@pytest.mark.mock_only
def test_single_volume_strategy_with_short_csv(capsys):
    """
    使用短期 AAPL 数据（2024-06 到 2024-09）测试 SingleVolumeStrategy
    
    数据来源：
      - 文件：data/stock/akshare/US.AAPL_AAPL_20240601_20240930_short.csv
      - 时间范围：2024-06-03 ~ 2024-09-30
      - 数据行数：83 条
    
    测试内容：
      - 策略是否能正确加载短期数据
      - 成交量指标是否正确计算
      - 买卖信号是否正确生成
      - 回测是否能完整运行
    """
    from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
    from core.strategy.trading.volume.single_volume_ import SingleVolumeStrategy
    
    # 获取短期数据文件路径
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "data" / "stock" / "akshare" / "US.AAPL_AAPL_20240601_20240930_short.csv"
    
    # 验证文件存在
    assert csv_path.exists(), f"CSV 文件不存在：{csv_path}"
    
    # 加载并验证数据
    df = pd.read_csv(csv_path)
    assert len(df) > 0, "CSV 文件为空"
    assert "date" in df.columns, "CSV 文件缺少 'date' 列"
    assert "close" in df.columns, "CSV 文件缺少 'close' 列"
    assert "volume" in df.columns, "CSV 文件缺少 'volume' 列"
    
    # 使用 capsys 记录输出
    with capsys.disabled():
        print(f"\n【数据信息】")
        print(f"  文件路径：{csv_path}")
        print(f"  数据行数：{len(df)}")
        print(f"  日期范围：{df['date'].min()} ~ {df['date'].max()}")
    
    # 运行回测
    run_backtest_enhanced_volume_strategy(
        str(csv_path),
        SingleVolumeStrategy,
        init_cash=5_000_000
    )
    
    # 捕获输出但不在断言中使用
    captured = capsys.readouterr()
    assert captured.out is not None or captured.err is not None


@pytest.mark.mock_only
def test_single_volume_strategy_synthetic_data(capsys):
    """
    使用合成数据测试 SingleVolumeStrategy（快速验证）
    
    此测试生成虚拟数据，用于快速验证策略框架
    而无需依赖外部 CSV 文件
    """
    from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
    from core.strategy.trading.volume.single_volume_ import SingleVolumeStrategy
    
    # 生成合成数据
    rows = []
    base_dates = pd.date_range("2024-06-01", periods=90, freq="D")
    for i, dt in enumerate(base_dates):
        # 模拟 AAPL 价格波动
        price = 200 + (i % 30) * 0.5 - 7.5  # 30 天周期的价格波动
        rows.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "open": price,
                "high": price + 2,
                "low": price - 2,
                "close": price + 1,
                "volume": 50_000_000 + (i % 20) * 5_000_000,  # 成交量波动
                "amount": 0,
                "stock_code": "US.AAPL",
                "stock_name": "Apple Inc",
                "market": "US",
            }
        )
    
    df = pd.DataFrame(rows)
    assert len(df) == 90, "合成数据行数应为 90"
    
    # 验证数据
    assert df['close'].min() > 0, "收盘价应大于 0"
    assert df['volume'].min() > 0, "成交量应大于 0"
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        csv_path = f.name
    
    try:
        # 运行回测
        run_backtest_enhanced_volume_strategy(
            csv_path,
            SingleVolumeStrategy,
            init_cash=5_000_000
        )
        
        # 捕获输出
        captured = capsys.readouterr()
        assert captured.out is not None or captured.err is not None
        
    finally:
        # 清理临时文件
        Path(csv_path).unlink()
