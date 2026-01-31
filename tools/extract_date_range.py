"""
从股票CSV文件中提取指定日期范围的数据

使用场景：
  从长期数据中截取短期数据用于快速测试

数学原理：
1. 日期范围筛选：使用 pandas to_datetime 和布尔索引实现高效筛选
2. 数据完整性：保留原始列结构和数据类型
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def extract_date_range(
    input_csv: str,
    output_csv: str,
    start_date: str,
    end_date: str
) -> bool:
    """
    从CSV文件中提取指定日期范围的数据

    Args:
        input_csv: 输入CSV文件路径
        output_csv: 输出CSV文件路径
        start_date: 开始日期 (YYYY-MM-DD 格式)
        end_date: 结束日期 (YYYY-MM-DD 格式)

    Returns:
        bool: 是否成功提取
    """
    try:
        # 1. 读取原始数据
        print(f"[*] 读取文件: {input_csv}")
        df = pd.read_csv(input_csv)

        # 2. 检查日期列
        if 'date' not in df.columns:
            print("错误: 未找到 'date' 列")
            return False

        # 3. 转换日期列类型
        df['date'] = pd.to_datetime(df['date'])

        # 4. 按日期范围筛选
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        mask = (df['date'] >= start) & (df['date'] <= end)
        df_filtered = df[mask].copy()

        # 5. 检查是否有数据
        if df_filtered.empty:
            print(f"警告: 在 {start_date} 到 {end_date} 范围内未找到数据")
            return False

        # 6. 保存到新文件
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_filtered.to_csv(output_csv, index=False)

        # 7. 打印统计信息
        print(f"[✓] 成功提取数据")
        print(f"    日期范围: {df_filtered['date'].min()} 至 {df_filtered['date'].max()}")
        print(f"    数据行数: {len(df_filtered)}")
        print(f"    列数: {len(df_filtered.columns)}")
        print(f"[✓] 输出文件: {output_csv}")

        return True

    except Exception as e:
        print(f"[✗] 提取失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 设置文件路径
    repo_root = Path(__file__).resolve().parents[1]
    input_file = repo_root / "data" / "stock" / "akshare" / "US.AAPL_AAPL_20211126_20251124.csv"
    output_file = repo_root / "data" / "stock" / "akshare" / "US.AAPL_AAPL_20240601_20240930_short.csv"

    # 执行提取
    success = extract_date_range(
        str(input_file),
        str(output_file),
        start_date="2024-06-01",
        end_date="2024-09-30"
    )

    if not success:
        exit(1)