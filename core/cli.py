"""
CLI 入口：提供最小可用的 data fetch / backtest / strategy list / strategy analyze。

使用示例：
  python -m core.cli data fetch --market US --code AAPL --start 2026-01-01 --end 2026-01-30
  python -m core.cli backtest --csv data/stock/akshare/US.AAPL_AAPL_20260101_20260130.csv --strategy EnhancedVolumeStrategy
  python -m core.cli backtest --csv data/stock/akshare/US.AAPL_AAPL_20260101_20260130.csv --strategy VCPStrategy
  python -m core.cli strategy list
  python -m core.cli strategy analyze --input x/option_trades_all.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd

from common.logger import create_log
from core.analysis.trade_schema import normalize_trades
from core.analysis.trade_strategy_infer import infer_strategy, profile_to_frame
from core.quant.quant_manage import run_backtest_enhanced_volume_strategy
from core.stock.data_source_router import fetch_history_with_fallback
from core.stock.manager_common import write_cached_history
from core.strategy.strategy_manager import StrategyManager
import settings


logger = create_log("cli")


def _parse_preferred(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def cmd_data_fetch(args: argparse.Namespace) -> int:
    preferred = _parse_preferred(args.preferred)
    df, source = fetch_history_with_fallback(
        market=args.market,
        stock_code=args.code,
        start_date=args.start,
        end_date=args.end,
        preferred=preferred,
    )
    if df.empty:
        logger.error("数据获取失败：market=%s code=%s", args.market, args.code)
        return 1
    stock_name = df["stock_name"].iloc[0] if "stock_name" in df.columns else args.code
    cache_path = write_cached_history(
        df,
        source=source or (preferred[0] if preferred else "unknown"),
        market=args.market,
        stock_code=args.code,
        stock_name=stock_name,
        start_date=args.start,
        end_date=args.end,
    )
    logger.info("数据获取成功：source=%s rows=%s", source, len(df))
    if cache_path:
        logger.info("缓存文件：%s", cache_path)
        print(cache_path)
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv) if args.csv else None
    if not csv_path:
        if not all([args.market, args.code, args.start, args.end]):
            logger.error("缺少参数：请提供 --csv 或 (market/code/start/end)")
            return 1
        preferred = _parse_preferred(args.preferred)
        df, source = fetch_history_with_fallback(
            market=args.market,
            stock_code=args.code,
            start_date=args.start,
            end_date=args.end,
            preferred=preferred,
        )
        if df.empty:
            logger.error("数据获取失败：market=%s code=%s", args.market, args.code)
            return 1
        stock_name = df["stock_name"].iloc[0] if "stock_name" in df.columns else args.code
        cache_path = write_cached_history(
            df,
            source=source or (preferred[0] if preferred else "unknown"),
            market=args.market,
            stock_code=args.code,
            stock_name=stock_name,
            start_date=args.start,
            end_date=args.end,
        )
        if cache_path:
            csv_path = Path(cache_path)
        else:
            logger.error("无法写入缓存 CSV，回测终止")
            return 1

    manager = StrategyManager()
    strategy_class = manager.get_strategy(args.strategy)
    if not strategy_class:
        logger.error("未找到策略：%s", args.strategy)
        logger.info("可用策略：%s", ", ".join(manager.get_strategy_names()))
        return 1

    init_cash = args.cash if args.cash is not None else settings.INIT_CASH
    run_backtest_enhanced_volume_strategy(csv_path, strategy_class, init_cash=init_cash)
    return 0


def cmd_strategy_list() -> int:
    manager = StrategyManager()
    names = manager.get_strategy_names()
    for name in names:
        print(name)
    return 0


def _write_html_table(df: pd.DataFrame, html_path: Path, title: str) -> None:
    html = [
        "<html><head><meta charset='utf-8'>",
        f"<title>{title}</title>",
        "<style>body{font-family:Arial,Helvetica,sans-serif;margin:24px;}table{border-collapse:collapse;width:100%;}",
        "th,td{border:1px solid #ddd;padding:8px;text-align:right;}th{text-align:center;background:#f5f5f5;}</style>",
        "</head><body>",
        f"<h2>{title}</h2>",
        df.to_html(index=False, escape=False),
        "</body></html>",
    ]
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text("\n".join(html), encoding="utf-8")


def cmd_trades_analyze(args: argparse.Namespace) -> int:
    csv_path = Path(args.input)
    if not csv_path.exists():
        logger.error("输入 CSV 不存在：%s", csv_path)
        return 1
    trades = pd.read_csv(csv_path)
    normalized = normalize_trades(trades)
    profile = infer_strategy(normalized)
    summary_df = profile_to_frame(profile)

    output_dir = Path(args.output_dir) if args.output_dir else csv_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / f"{csv_path.stem}_strategy_profile.csv"
    out_html = output_dir / f"{csv_path.stem}_strategy_profile.html"
    summary_df.to_csv(out_csv, index=False)
    _write_html_table(summary_df, out_html, title="Strategy Profile")
    logger.info("策略画像输出：%s", out_csv)
    logger.info("策略画像报告：%s", out_html)
    print(out_csv)
    print(out_html)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stock-Quant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    data_parser = subparsers.add_parser("data", help="数据相关命令")
    data_sub = data_parser.add_subparsers(dest="data_cmd", required=True)
    fetch = data_sub.add_parser("fetch", help="拉取历史数据并缓存")
    fetch.add_argument("--market", required=True, help="市场（US/HK/CN）")
    fetch.add_argument("--code", required=True, help="股票代码")
    fetch.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    fetch.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")
    fetch.add_argument("--preferred", help="数据源优先级（逗号分隔）")
    fetch.set_defaults(func=cmd_data_fetch)

    backtest = subparsers.add_parser("backtest", help="回测")
    backtest.add_argument("--csv", help="本地 CSV 路径")
    backtest.add_argument("--market", help="市场（US/HK/CN）")
    backtest.add_argument("--code", help="股票代码")
    backtest.add_argument("--start", help="开始日期 YYYY-MM-DD")
    backtest.add_argument("--end", help="结束日期 YYYY-MM-DD")
    backtest.add_argument("--preferred", help="数据源优先级（逗号分隔）")
    backtest.add_argument("--strategy", default="EnhancedVolumeStrategy", help="策略类名")
    backtest.add_argument("--cash", type=float, default=None, help="初始资金")
    backtest.set_defaults(func=cmd_backtest)

    strategy = subparsers.add_parser("strategy", help="策略相关")
    strategy_sub = strategy.add_subparsers(dest="strategy_cmd", required=True)
    list_cmd = strategy_sub.add_parser("list", help="列出策略")
    list_cmd.set_defaults(func=lambda args: cmd_strategy_list())
    analyze_trades = strategy_sub.add_parser("analyze", help="交易策略推断（CSV -> CSV/HTML）")
    analyze_trades.add_argument("--input", required=True, help="交易 CSV 路径")
    analyze_trades.add_argument("--output-dir", help="输出目录（默认 CSV 同级）")
    analyze_trades.set_defaults(func=cmd_trades_analyze)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return int(args.func(args))
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
