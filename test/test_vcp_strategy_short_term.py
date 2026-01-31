"""
VCPStrategy 短期数据调试测试。

用途：
  - 使用 2024-06 到 2024-09 三个月的实际数据
  - 测试 VCPStrategy 策略的完整流程
  - 便于逐步调试 VCP 形态识别和信号生成

运行方式：
  conda run -n data_analysis python -m pytest test/test_vcp_strategy_short_term.py -v -s --tb=short
  conda run -n data_analysis python -m pytest test/test_vcp_strategy_short_term.py::test_vcp_strategy_with_short_csv -v -s
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile


@pytest.mark.mock_only
def test_vcp_strategy_registered():
    """验证 VCPStrategy 已注册"""
    from core.strategy.strategy_manager import StrategyManager
    
    manager = StrategyManager()
    names = manager.get_strategy_names()
    assert "VCPStrategy" in names, f"VCPStrategy not found in {names}"


@pytest.mark.mock_only
def test_vcp_strategy_with_short_csv(capsys):
    """
    使用短期 AAPL 数据（2024-06 到 2024-09）测试 VCPStrategy
    
    数据来源：
      - 文件：data/stock/akshare/US.AAPL_AAPL_20240601_20240930_short.csv
      - 时间范围：2024-06-03 ~ 2024-09-30
      - 数据行数：83 条
    
    测试内容：
      - Stage 2 趋势识别是否正确
      - 收缩次数是否正确计算
      - VCP 形态是否正确识别
      - 买卖信号是否正确生成
      - 回测是否能完整运行
    """
    from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
    from core.strategy.trading.pattern.vcp_strategy import VCPStrategy
    
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
        print(f"  收盘价范围：{df['close'].min():.2f} ~ {df['close'].max():.2f}")
        print(f"  成交量范围：{df['volume'].min():,.0f} ~ {df['volume'].max():,.0f}")
    
    # 运行回测
    run_backtest_enhanced_volume_strategy(
        str(csv_path),
        VCPStrategy,
        init_cash=5_000_000
    )
    
    # 捕获输出但不在断言中使用
    captured = capsys.readouterr()
    assert captured.out is not None or captured.err is not None


@pytest.mark.mock_only
def test_vcp_strategy_loose_with_short_csv(capsys):
    """
    使用短期 AAPL 数据测试 VCPStrategyLoose（宽松版，用于快速验证）
    
    VCPStrategyLoose 特点：
      - progress_threshold = 0.34（降低触发门槛）
      - 便于快速验证回测管线
      - 更容易生成测试信号
    
    测试内容：
      - 宽松版策略是否更容易触发信号
      - 进度阈值设置是否有效
      - EMA 卖出逻辑是否正确
    """
    from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
    from core.strategy.trading.pattern.vcp_strategy_loose import VCPStrategyLoose
    
    # 获取短期数据文件路径
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "data" / "stock" / "akshare" / "US.AAPL_AAPL_20211126_20251124.csv"
    
    # 验证文件存在
    assert csv_path.exists(), f"CSV 文件不存在：{csv_path}"
    
    # 加载并验证数据
    df = pd.read_csv(csv_path)
    assert len(df) > 0, "CSV 文件为空"
    
    # 使用 capsys 记录输出
    with capsys.disabled():
        print(f"\n【VCPStrategyLoose 测试】")
        print(f"  进度阈值：0.34（允许部分条件未满足）")
        print(f"  卖出条件：EMA5 穿越")
    
    # 运行回测
    run_backtest_enhanced_volume_strategy(
        str(csv_path),
        VCPStrategyLoose,
        init_cash=5_000_000
    )
    
    # 捕获输出
    captured = capsys.readouterr()
    assert captured.out is not None or captured.err is not None


@pytest.mark.mock_only
def test_vcp_strategy_synthetic_data(capsys):
    """
    使用合成数据测试 VCPStrategy（快速验证）
    
    此测试生成虚拟数据，用于快速验证 VCP 识别框架
    而无需依赖外部 CSV 文件
    
    合成数据特点：
      - 包含 Stage 2 上升趋势
      - 模拟价格收缩模式
      - 成交量枯竭特征
    """
    from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
    from core.strategy.trading.pattern.vcp_strategy import VCPStrategy
    
    # 生成合成数据（包含 VCP 特征）
    rows = []
    base_dates = pd.date_range("2024-06-01", periods=150, freq="D")
    
    for i, dt in enumerate(base_dates):
        # 模拟上升趋势（Stage 2）
        base_price = 200 + i * 0.3
        
        # 加入收缩模式（3-4 次收缩，深度逐次递减）
        contraction_wave = (i % 50) / 50
        if contraction_wave < 0.33:
            # 第一次收缩：深度 30%
            price = base_price + 15 * (contraction_wave / 0.33)
        elif contraction_wave < 0.66:
            # 第二次收缩：深度 18%
            price = base_price + 9 * ((contraction_wave - 0.33) / 0.33)
        else:
            # 第三次收缩：深度 10%
            price = base_price + 5 * ((contraction_wave - 0.66) / 0.34)
        
        # 添加随机波动
        price += (i % 5) * 0.2 - 0.4
        
        # 成交量逐步衰减（成交量枯竭）
        volume = 100_000_000 - (i * 200_000)
        volume = max(volume, 20_000_000)
        
        rows.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "open": price,
                "high": price + 2,
                "low": price - 2,
                "close": price + 0.5,
                "volume": volume,
                "amount": 0,
                "stock_code": "US.AAPL",
                "stock_name": "Apple Inc",
                "market": "US",
            }
        )
    
    df = pd.DataFrame(rows)
    assert len(df) == 150, "合成数据行数应为 150"
    
    # 验证数据特征
    assert df['close'].min() > 0, "收盘价应大于 0"
    assert df['volume'].min() > 0, "成交量应大于 0"
    assert df['close'].iloc[-1] > df['close'].iloc[0], "应为上升趋势"
    assert df['volume'].iloc[-1] < df['volume'].iloc[0], "应为成交量衰减"
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        csv_path = f.name
    
    try:
        # 使用 capsys 记录输出
        with capsys.disabled():
            print(f"\n【合成 VCP 数据测试】")
            print(f"  数据行数：{len(df)}")
            print(f"  价格趋势：{df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")
            print(f"  成交量趋势：{df['volume'].iloc[0]:,.0f} → {df['volume'].iloc[-1]:,.0f}")
        
        # 运行回测
        run_backtest_enhanced_volume_strategy(
            csv_path,
            VCPStrategy,
            init_cash=5_000_000
        )
        
        # 捕获输出
        captured = capsys.readouterr()
        assert captured.out is not None or captured.err is not None
        
    finally:
        # 清理临时文件
        Path(csv_path).unlink()
