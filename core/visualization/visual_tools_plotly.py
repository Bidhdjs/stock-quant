"""
Plotly 交易策略回测报告生成
基于行情、信号与交易记录输出可视化 HTML 报告

数学原理：
1. 区间收益：基于总资产序列计算 (期末资产/初始资金 - 1)
2. 最大回撤：总资产序列相对历史峰值的最小回撤
"""
import os
import webbrowser
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common.logger import create_log
from common.util_csv import load_stock_data
from core.visualization.visual_demo import get_sample_signal_records, get_sample_trade_records, get_sample_asset_records
from core.strategy.indicator.common import normalize_signal_type
from settings import stock_data_root, html_root
logger = create_log('visual_tools_plotly')

REPORT_THEME = {
    "bg": "#e2e4e8",
    "panel": "#f0f1f3",
    "panel_soft": "#e8eaee",
    "text": "#1f2328",
    "muted": "#6b7280",
    "grid": "#cfd3d8",
    "accent": "#4b5563",
    "positive": "#2f6b4f",
    "negative": "#9b2c2c",
    "line_blue": "#3f5873",
    "line_orange": "#8a6d3b",
}

SIGNAL_STYLE_CONFIG = [
    {
        "signal_type": "strong_buy",
        "name": "强买入信号",
        "text": "强多",
        "symbol": "circle",
        "color": REPORT_THEME["positive"],
        "text_color": REPORT_THEME["positive"],
        "y_offset": 0.95,
    },
    {
        "signal_type": "normal_buy",
        "name": "买入信号",
        "text": "多",
        "symbol": "circle",
        "color": "#8aa593",
        "text_color": REPORT_THEME["positive"],
        "y_offset": 0.95,
    },
    {
        "signal_type": "strong_sell",
        "name": "强卖出信号",
        "text": "强空",
        "symbol": "circle",
        "color": REPORT_THEME["negative"],
        "text_color": REPORT_THEME["negative"],
        "y_offset": 1.05,
    },
    {
        "signal_type": "normal_sell",
        "name": "卖出信号",
        "text": "空",
        "symbol": "circle",
        "color": "#b07a7a",
        "text_color": REPORT_THEME["negative"],
        "y_offset": 1.05,
    },
    {
        "signal_type": "vcp_buy",
        "name": "VCP 买入信号",
        "text": "VCP",
        "symbol": "diamond",
        "color": "#f59e0b",
        "text_color": "#f59e0b",
        "y_offset": 0.93,
    },
    {
        "signal_type": "vcp_sell",
        "name": "VCP 卖出信号",
        "text": "VCP空",
        "symbol": "triangle-down",
        "color": "#f97316",
        "text_color": "#f97316",
        "y_offset": 1.08,
    },
]

FONT_FAMILY = "IBM Plex Sans, Noto Sans SC, PingFang SC, Microsoft YaHei, sans-serif"
FONT_MONO = "IBM Plex Mono, SFMono-Regular, Menlo, Consolas, monospace"


def prepare_continuous_dates(df):
    """
    创建连续的日期范围，确保K线图不间断显示

    参数:
        df: 原始股票数据DataFrame

    返回:
        包含连续日期的DataFrame
    """
    # 获取数据的最小和最大日期
    min_date = df.index.min()
    max_date = df.index.max()
    # 创建包含所有日期的连续索引（包括周末和节假日）
    continuous_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    # 使用reindex将原始数据填充到连续日期索引中，非交易日数据为NaN
    df_continuous = df.reindex(continuous_dates)
    return df_continuous


def filter_valid_dates(df, records):
    """
    筛选有效的日期，确保记录中的日期在股票数据中存在

    参数:
        df: 股票数据DataFrame
        records: 记录DataFrame（信号或交易）

    返回:
        有效的记录DataFrame
    """
    # 检查records是否为空或是否包含'date'列
    if records is None or records.empty:
        logger.warning("警告：记录为空，无法筛选有效日期")
        return pd.DataFrame()

    if 'date' not in records.columns:
        logger.warning("警告：记录中不包含'date'列，无法筛选有效日期")
        # 尝试查找可能的日期列
        date_like_columns = [col for col in records.columns if 'date' in col.lower()]
        if date_like_columns:
            date_column = date_like_columns[0]
            logger.info(f"使用列'{date_column}'作为日期列")
            valid_dates = df.index  # 股票数据中所有存在的日期
            valid_records = records[records[date_column].isin(valid_dates)].copy()
            return valid_records
        return records  # 如果没有找到类似日期的列，返回原始记录

    valid_dates = df.index  # 股票数据中所有存在的日期
    valid_records = records[records['date'].isin(valid_dates)].copy()

    # 提示缺失的日期
    missing_dates = records[~records['date'].isin(valid_dates)]['date']
    if not missing_dates.empty:
        logger.info(f"警告：以下日期在股票数据中不存在，已跳过：{missing_dates.dt.strftime('%Y-%m-%d').tolist()}")

    return valid_records

def _safe_last(series):
    series = series.dropna()
    if series.empty:
        return None
    return series.iloc[-1]

def _format_number(value, digits=2):
    if value is None or pd.isna(value):
        return "--"
    return f"{value:,.{digits}f}"

def _format_int(value):
    if value is None or pd.isna(value):
        return "--"
    return f"{int(value):,}"

def _format_percent(value, digits=2):
    if value is None or pd.isna(value):
        return "--"
    return f"{value * 100:.{digits}f}%"

def _trend_class(value):
    if value is None or pd.isna(value):
        return ""
    if value > 0:
        return "is-up"
    if value < 0:
        return "is-down"
    return ""

def build_report_payload(stock_info, df_continuous, valid_signals, valid_trades, holdings_data, initial_capital):
    close_series = df_continuous['close'] if 'close' in df_continuous.columns else pd.Series(dtype=float)
    latest_close = _safe_last(close_series)

    prev_close = None
    close_non_na = close_series.dropna()
    if len(close_non_na) >= 2:
        prev_close = close_non_na.iloc[-2]

    price_delta = None
    price_delta_pct = None
    if latest_close is not None and prev_close not in (None, 0):
        price_delta = latest_close - prev_close
        price_delta_pct = price_delta / prev_close

    assets_series = holdings_data['total_assets'] if 'total_assets' in holdings_data.columns else pd.Series(dtype=float)
    latest_assets = _safe_last(assets_series)
    assets_return = None
    if latest_assets is not None and initial_capital not in (None, 0):
        assets_return = latest_assets / initial_capital - 1

    max_drawdown = None
    assets_non_na = assets_series.dropna()
    if not assets_non_na.empty:
        rolling_max = assets_non_na.cummax()
        drawdown = assets_non_na / rolling_max - 1
        max_drawdown = drawdown.min()

    last_holdings = _safe_last(holdings_data['holdings']) if 'holdings' in holdings_data.columns else None
    last_adjusted_cost = _safe_last(holdings_data['adjusted_cost']) if 'adjusted_cost' in holdings_data.columns else None

    trade_count = int(len(valid_trades)) if valid_trades is not None else 0
    buy_count = int((valid_trades['action'] == 'B').sum()) if valid_trades is not None and 'action' in valid_trades.columns else 0
    sell_count = int((valid_trades['action'] == 'S').sum()) if valid_trades is not None and 'action' in valid_trades.columns else 0

    signal_count = int(len(valid_signals)) if valid_signals is not None else 0

    start_date = df_continuous.index.min()
    end_date = df_continuous.index.max()
    date_range = "--"
    if pd.notna(start_date) and pd.notna(end_date):
        date_range = f"{start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}"

    points = int(close_series.notna().sum()) if 'close' in df_continuous.columns else 0

    kpis = [
        {
            "label": "最新价",
            "value": _format_number(latest_close),
            "sub": f"{_format_number(price_delta)} ({_format_percent(price_delta_pct)})" if price_delta is not None else "--",
            "trend": _trend_class(price_delta),
        },
        {
            "label": "区间收益",
            "value": _format_percent(assets_return),
            "sub": f"初始资金 {_format_number(initial_capital)}",
            "trend": _trend_class(assets_return),
        },
        {
            "label": "最大回撤",
            "value": _format_percent(max_drawdown),
            "sub": "基于总资产",
            "trend": _trend_class(max_drawdown),
        },
        {
            "label": "总资产",
            "value": _format_number(latest_assets),
            "sub": "期末资产",
            "trend": _trend_class(assets_return),
        },
        {
            "label": "持仓数量",
            "value": _format_int(last_holdings),
            "sub": f"持仓成本 {_format_number(last_adjusted_cost)}",
            "trend": "",
        },
        {
            "label": "交易次数",
            "value": _format_int(trade_count),
            "sub": f"买入 {buy_count} · 卖出 {sell_count}",
            "trend": "",
        },
    ]

    payload = {
        "stock_info": stock_info or "策略回测报告",
        "date_range": date_range,
        "data_points": points,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal_count": signal_count,
        "kpis": kpis,
    }
    return payload

def build_html_report(fig_html, payload):
    kpi_cards = []
    for kpi in payload.get("kpis", []):
        trend_class = kpi.get("trend", "")
        kpi_cards.append(
            f"""
            <div class="kpi-card {trend_class}">
                <div class="kpi-label">{kpi.get('label', '')}</div>
                <div class="kpi-value">{kpi.get('value', '--')}</div>
                <div class="kpi-sub">{kpi.get('sub', '--')}</div>
            </div>
            """
        )
    kpi_html = "\n".join(kpi_cards)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{payload.get('stock_info')}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: {REPORT_THEME['bg']};
      --panel: {REPORT_THEME['panel']};
      --panel-soft: {REPORT_THEME['panel_soft']};
      --text: {REPORT_THEME['text']};
      --muted: {REPORT_THEME['muted']};
      --grid: {REPORT_THEME['grid']};
      --accent: {REPORT_THEME['accent']};
      --positive: {REPORT_THEME['positive']};
      --negative: {REPORT_THEME['negative']};
      --shadow: 0 16px 50px rgba(17, 24, 39, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: {FONT_FAMILY};
      color: var(--text);
      background: linear-gradient(180deg, #dde0e5 0%, #e8eaee 45%, #eceef1 100%);
      min-height: 100vh;
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(to right, rgba(17, 24, 39, 0.04) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(17, 24, 39, 0.04) 1px, transparent 1px);
      background-size: 24px 24px;
      opacity: 0.35;
      pointer-events: none;
      z-index: 0;
    }}

    .report {{
      position: relative;
      z-index: 1;
      max-width: 1400px;
      margin: 0 auto;
      padding: 28px 28px 48px;
    }}

    .report-header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 24px;
    }}

    .title-block {{
      min-width: 260px;
    }}

    .title-eyebrow {{
      font-size: 12px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
    }}

    h1 {{
      font-size: 28px;
      margin: 0 0 10px;
      font-weight: 600;
    }}

    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .chip {{
      background: rgba(255, 255, 255, 0.5);
      border: 1px solid rgba(15, 23, 42, 0.08);
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      color: var(--muted);
    }}

    .header-stats {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .mini-stat {{
      background: var(--panel);
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      padding: 12px 14px;
      min-width: 150px;
      box-shadow: var(--shadow);
    }}

    .mini-label {{
      font-size: 12px;
      color: var(--muted);
    }}

    .mini-value {{
      font-size: 18px;
      margin-top: 6px;
      font-weight: 600;
      font-family: {FONT_MONO};
    }}

    .mini-sub {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 4px;
    }}

    .section {{
      margin-bottom: 22px;
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }}

    .kpi-card {{
      background: var(--panel);
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 18px;
      padding: 16px 18px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}

    .kpi-card::after {{
      content: "";
      position: absolute;
      inset: auto -40% -40% auto;
      width: 140px;
      height: 140px;
      background: radial-gradient(circle, rgba(15, 23, 42, 0.08) 0%, transparent 60%);
      opacity: 0.6;
    }}

    .kpi-label {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}

    .kpi-value {{
      font-size: 22px;
      margin-top: 6px;
      font-weight: 600;
      font-family: {FONT_MONO};
    }}

    .kpi-sub {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
    }}

    .kpi-card.is-up .kpi-value {{
      color: var(--positive);
    }}

    .kpi-card.is-down .kpi-value {{
      color: var(--negative);
    }}

    .card {{
      background: var(--panel);
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 22px;
      padding: 18px;
      box-shadow: var(--shadow);
    }}

    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }}

    .card-title {{
      font-size: 16px;
      font-weight: 600;
    }}

    .title-with-icon {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}

    .icon {{
      width: 18px;
      height: 18px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
    }}

    .icon svg {{
      width: 100%;
      height: 100%;
    }}

    .card-subtitle {{
      font-size: 12px;
      color: var(--muted);
    }}

    .chart-wrap {{
      background: var(--panel-soft);
      border-radius: 18px;
      padding: 10px;
      border: 1px solid rgba(15, 23, 42, 0.06);
    }}

    .plotly-graph-div {{
      width: 100% !important;
    }}

    .placeholder {{
      padding: 18px;
      border: 1px dashed rgba(15, 23, 42, 0.2);
      border-radius: 16px;
      color: var(--muted);
      font-size: 13px;
    }}

    .footer {{
      font-size: 12px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }}

    @media (max-width: 900px) {{
      .report {{
        padding: 22px 18px 36px;
      }}

      h1 {{
        font-size: 22px;
      }}
    }}
  </style>
</head>
<body>
  <div class="report">
    <header class="report-header">
      <div class="title-block">
        <div class="title-eyebrow">策略回测报告</div>
        <h1>{payload.get('stock_info')}</h1>
        <div class="meta-row">
          <span class="chip">区间 {payload.get('date_range')}</span>
          <span class="chip">数据点 {payload.get('data_points')}</span>
          <span class="chip">信号 {payload.get('signal_count')}</span>
          <span class="chip">生成 {payload.get('generated_at')}</span>
        </div>
      </div>
      <div class="header-stats">
        <div class="mini-stat">
          <div class="mini-label">报告重点</div>
          <div class="mini-value">趋势与回撤</div>
          <div class="mini-sub">成交、持仓与净值</div>
        </div>
        <div class="mini-stat">
          <div class="mini-label">观察窗口</div>
          <div class="mini-value">{payload.get('date_range')}</div>
          <div class="mini-sub">对齐图表与 KPI</div>
        </div>
      </div>
    </header>

    <section class="section kpi-grid">
      {kpi_html}
    </section>

    <section class="section card">
      <div class="card-header">
        <div>
          <div class="card-title title-with-icon">
            <span class="icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M4 18V6" stroke-linecap="round"/>
                <path d="M9 18V9" stroke-linecap="round"/>
                <path d="M14 18V12" stroke-linecap="round"/>
                <path d="M19 18V4" stroke-linecap="round"/>
              </svg>
            </span>
            多维度回测图表
          </div>
          <div class="card-subtitle">K线 · 全景 · 成交量 · 持仓 · 总资产 · 成本</div>
        </div>
        <div class="card-subtitle">交互缩放与悬浮查看</div>
      </div>
      <div class="chart-wrap">
        {fig_html}
      </div>
    </section>

    <section class="section card">
      <div class="card-header">
        <div>
          <div class="card-title title-with-icon">
            <span class="icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M4 6h16" stroke-linecap="round"/>
                <path d="M4 12h16" stroke-linecap="round"/>
                <path d="M4 18h10" stroke-linecap="round"/>
              </svg>
            </span>
            交易与信号列表（预留）
          </div>
          <div class="card-subtitle">后续将展示详细信号与成交记录</div>
        </div>
      </div>
      <div class="placeholder">请在此处填充交易列表、信号列表或分段绩效统计。</div>
    </section>

    <section class="footer">
      <div>数据源：策略回测 · Plotly 报告</div>
      <div>界面风格：灰白终端 · 低饱和度</div>
    </section>
  </div>
</body>
</html>
"""

def calculate_holdings(df_continuous, valid_trades, initial_capital):
    """
    计算持仓量变化、总资产、持仓成本变化

    参数:
        df_continuous: 连续日期的股票数据
        valid_trades: 有效的交易记录
        initial_capital: 初始资金

    返回:
        包含持仓量和总资产和持仓成本的DataFrame
    """
    holdings_data = pd.DataFrame(index=df_continuous.index)
    holdings_data['holdings'] = 0   # 持仓量
    holdings_data['adjusted_cost'] = 0.0  # 持仓成本

    # 检查valid_trades是否为空或不包含'date'列
    if valid_trades is None or valid_trades.empty or 'date' not in valid_trades.columns:
        # 如果没有有效的交易记录，总资产始终为初始资金
        holdings_data['total_assets'] = initial_capital
        return holdings_data

    # 初始化持仓量和资金
    total_holdings = 0  # 当前持仓量
    capital = initial_capital   # 剩余资金
    holdings_value = 0
    total_cost = 0.0  # 总持仓成本
    adjusted_cost = 0.0    # 持仓成本

    # 计算持仓量变化和总资产变化
    holdings_history = []
    asset_history = []
    adjusted_cost_history = []


    for date in df_continuous.index:
        # 检查该日期是否有交易
        day_trades = valid_trades[valid_trades['date'] == date]
        for _, trade in day_trades.iterrows():
            if trade['action'] == 'B':
                # 买入，持仓量增加
                if date in df_continuous.index.dropna():
                    buy_price = trade['price']
                    buy_size = trade['size']
                    commission = trade['commission']
                    current_cost = buy_size * buy_price + commission
                    total_cost += current_cost
                    capital -= current_cost
                    total_holdings += buy_size
                    adjusted_cost = total_cost / total_holdings
            elif trade['action'] == 'S':
                # 卖出，持仓量减少
                if date in df_continuous.index.dropna():
                    sell_price = trade['price']
                    sell_size = trade['size']
                    commission = trade['commission']
                    current_cost = sell_size * sell_price - commission
                    total_cost -= current_cost
                    capital += current_cost
                    total_holdings -= sell_size
                    # 如果全部卖出，重置持仓成本
                    if total_holdings <= 0:
                        adjusted_cost = 0.0
                        total_cost = 0.0
                        total_holdings = 0
                    else:
                        adjusted_cost = total_cost / total_holdings

        # 保存当日持仓量
        holdings_history.append(total_holdings)
        adjusted_cost_history.append(adjusted_cost)

        # 计算总资产（现金+持仓市值）
        if date in df_continuous.index.dropna():
            current_price = df_continuous.loc[date, 'close']
            holdings_value = total_holdings * current_price
        total_assets = capital + holdings_value
        asset_history.append(total_assets)

    # 添加持仓量和总资产数据到DataFrame
    holdings_data['holdings'] = holdings_history
    holdings_data['total_assets'] = asset_history
    holdings_data['adjusted_cost'] = adjusted_cost_history

    return holdings_data


def create_trading_chart(chart_title_prefix, df, valid_signals, valid_trades, holdings_data, initial_capital):
    """
    创建包含K线、信号和交易记录的图表

    参数:
        chart_title_prefix: 图表标题前缀
        df: 原始股票数据处理后得到连续日期的股票数据
        valid_signals: 有效的信号记录
        valid_trades: 有效的交易记录
        holdings_data: 持仓量和总资产数据
        initial_capital: 初始资金

    返回:
        Plotly图表对象
    """
    # 创建五个垂直排列的图表
    fig = make_subplots(
        rows=6, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            'K线图与交易信号',
            '全景K图', # 全景K线视图，用于时间范围选择，方便其他图联动
            '成交量',
            '持仓量变化',
            '总资产变化',
            '持仓成本'
        ),
        row_heights=[0.35, 0.1, 0.15, 0.15, 0.15, 0.15]
    )

    # 1. 添加K线图
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线',
            increasing_line_color=REPORT_THEME['positive'],
            decreasing_line_color=REPORT_THEME['negative']
        ),
        row=1, col=1
    )

    # 2. 添加全景视图占位图（第二行）- 不显示实际数据
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='全景K图',
            marker=dict(
                color=[REPORT_THEME['positive'] if close >= open else REPORT_THEME['negative'] for open, close in zip(df['open'], df['close'])]
            ),
        ),
        row=2, col=1
    )

    # 3. 添加成交量柱状图
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='成交量',
            marker=dict(
                color=[REPORT_THEME['positive'] if close >= open else REPORT_THEME['negative'] for open, close in zip(df['open'], df['close'])],
                opacity=0.75
            ),
        ),
        row=3, col=1
    )

    # 4. 添加持仓量变化曲线
    fig.add_trace(
        go.Scatter(
            x=holdings_data.index,
            y=holdings_data['holdings'],
            mode='lines',
            name='持仓量',
            line=dict(color=REPORT_THEME['line_blue'], width=2)
        ),
        row=4, col=1
    )

    # 5. 添加总资产变化曲线和初始资金参考线
    fig.add_trace(
        go.Scatter(
            x=holdings_data.index,
            y=holdings_data['total_assets'],
            mode='lines',
            name='总资产',
            line=dict(color=REPORT_THEME['accent'], width=2),
            connectgaps=True
        ),
        row=5, col=1
    )

    # 添加初始资金参考线
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color=REPORT_THEME['muted'],
        annotation_text=f"初始资金: {initial_capital}",
        annotation_position="bottom right",
        row=5, col=1
    )

    # 6. 添加持仓成本变化曲线
    fig.add_trace(
        go.Scatter(
            x=holdings_data.index,
            y=holdings_data['adjusted_cost'],
            mode='lines',
            name='持仓成本',
            line=dict(color=REPORT_THEME['line_orange'], width=2)
        ),
        row=6, col=1
    )

    # 6. 添加信号点标记
    # 首先检查valid_signals是否有效
    if valid_signals is not None and not valid_signals.empty and all(col in valid_signals.columns for col in ['date', 'signal_type', 'signal_description']):
        valid_signals = valid_signals.copy()
        valid_signals['signal_type_norm'] = valid_signals['signal_type'].apply(normalize_signal_type)
        for cfg in SIGNAL_STYLE_CONFIG:
            cfg_signals = valid_signals[valid_signals['signal_type_norm'] == cfg['signal_type']]
            if cfg_signals.empty:
                continue
            is_buy = cfg['signal_type'].endswith('buy')
            y_anchor = 'low' if is_buy else 'high'
            y_values = df.loc[cfg_signals['date'], y_anchor] * cfg['y_offset']
            text_position = 'bottom center' if is_buy else 'top center'
            fig.add_trace(
                go.Scatter(
                    x=cfg_signals['date'],
                    y=y_values,
                    mode='markers+text',
                    name=cfg['name'],
                    marker=dict(
                        symbol=cfg['symbol'],
                        color=cfg['color'],
                        size=10,
                        line=dict(width=1, color=REPORT_THEME['text'])
                    ),
                    text=[cfg['text'] for _ in range(len(cfg_signals))],
                    textposition=text_position,
                    texttemplate='%{text}',
                    textfont=dict(family=FONT_FAMILY, size=12, color=cfg['text_color']),
                    hovertemplate='日期: %{x}<br>信号: %{customdata[0]}<extra></extra>',
                    customdata=cfg_signals[['signal_description']].values,
                    showlegend=True
                ), row=1, col=1
            )
    else:
        logger.warning("警告：信号记录为空或不包含必要的列，无法添加信号标记")

    # 7. 添加实际交易点标记
    # 首先检查valid_trades是否有效
    if valid_trades is not None and not valid_trades.empty and all(col in valid_trades.columns for col in ['date', 'action', 'size']):
        # 买入操作（B，上三角形，绿色，K线下方）
        buy_trades = valid_trades[valid_trades['action'] == 'B']
        if not buy_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_trades['date'],
                    y=df.loc[buy_trades['date'], 'close'] * 0.90,
                    mode='markers+text',
                    name='买入操作(B)',
                    marker=dict(
                        symbol='triangle-up',
                        color=REPORT_THEME['positive'],
                        size=12,
                        line=dict(width=1, color=REPORT_THEME['text'])
                    ),
                    text=['B' for _ in range(len(buy_trades))],
                    textposition='bottom center',
                    texttemplate='%{text}',
                    textfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['positive']),
                    hovertemplate='日期: %{x}<br>操作: 买入(B)<br>数量: %{customdata[0]}股<br>价格: %{y:.2f}<extra></extra>',
                    customdata=buy_trades[['size']].values
                ), row=1, col=1
            )

        # 卖出操作（S，下三角形，红色，K线上方）
        sell_trades = valid_trades[valid_trades['action'] == 'S']
        if not sell_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_trades['date'],
                    y=df.loc[sell_trades['date'], 'close'] * 1.10,
                    mode='markers+text',
                    name='卖出操作(S)',
                    marker=dict(
                        symbol='triangle-down',
                        color=REPORT_THEME['negative'],
                        size=12,
                        line=dict(width=1, color=REPORT_THEME['text'])
                    ),
                    text=['S' for _ in range(len(sell_trades))],
                    textposition='top center',
                    texttemplate='%{text}',
                    textfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['negative']),
                    hovertemplate='日期: %{x}<br>操作: 卖出(S)<br>数量: %{customdata[0]}股<br>价格: %{y:.2f}<extra></extra>',
                    customdata=sell_trades[['size']].values
                ), row=1, col=1
            )
    else:
        logger.warning("警告：交易记录为空或不包含必要的列，无法添加交易标记")

    # 8. 设置图表布局
    fig.update_layout(
        title=dict(
            text=f'{chart_title_prefix} - 股票交易策略回测分析',
            font=dict(family=FONT_FAMILY, size=20, color=REPORT_THEME['text']),
            x=0.5,
            y=0.99,
            xanchor='center',
            yanchor='top'  # 设置yanchor为top，确保y值从标题顶部开始计算
        ),
        height=1500,
        autosize=True,
        margin=dict(l=80, r=50, t=90, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted'])
        ),
        hovermode='x unified',
        font=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['text']),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="white", font=dict(color=REPORT_THEME['text']))
    )

    # 设置X轴
    fig.update_xaxes(
        title_text="日期",
        showgrid=True,
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted'])
    )

    # 设置Y轴
    # K线图Y轴
    fig.update_yaxes(
        title_text="价格",
        showgrid=True,
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted']),
        row=1, col=1
    )

    # 全景视图Y轴 - 隐藏Y轴标签和刻度
    fig.update_yaxes(
        title_text="全景K图",
        showgrid=True,
        showticklabels=False,  # 隐藏刻度标签
        showline=False,  # 隐藏轴线
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted']),
        row=2, col=1
    )

    # 成交量Y轴
    fig.update_yaxes(
        title_text="成交量",
        showgrid=True,
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted']),
        row=3, col=1
    )

    # 持仓量Y轴
    fig.update_yaxes(
        title_text="持仓量(股)",
        showgrid=True,
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted']),
        row=4, col=1
    )

    # 总资产Y轴
    fig.update_yaxes(
        title_text="总资产",
        showgrid=True,
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted']),
        row=5, col=1
    )

    # 添加持仓成本Y轴
    fig.update_yaxes(
        title_text="持仓成本",
        showgrid=True,
        gridwidth=1,
        gridcolor=REPORT_THEME['grid'],
        tickfont=dict(family=FONT_FAMILY, size=12, color=REPORT_THEME['muted']),
        row=6, col=1
    )

    return fig


def save_and_show_chart(fig, file_name, output_dir=None, report_payload=None):
    """
    保存图表并在浏览器中显示

    参数:
        fig: Plotly图表对象
        output_dir: 输出目录路径（可选）
        report_payload: 报告元数据

    返回:
        保存的文件路径
    """

    # 如果指定了输出目录，则使用该目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, file_name)
    else:
        file_path = file_name

    fig_html = fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={
            "responsive": True,
            "displaylogo": False,
            "scrollZoom": True
        }
    )

    if report_payload is None:
        report_payload = {
            "stock_info": "策略回测报告",
            "date_range": "--",
            "data_points": 0,
            "signal_count": 0,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kpis": []
        }

    html_content = build_html_report(fig_html, report_payload)
    Path(file_path).write_text(html_content, encoding="utf-8")

    # 在浏览器中显示图表
    try:
        webbrowser.open(Path(file_path).resolve().as_uri())
    except Exception as exc:
        logger.warning(f"浏览器打开失败：{exc}")

    return file_path


def plotly_draw(kline_csv_path, strategy, initial_capital, html_file_name,html_file_path):
    signal_record_manager = strategy.indicator.signal_record_manager
    signals_df = signal_record_manager.transform_to_dataframe()
    trade_record_manager = strategy.trade_record_manager
    trades_df = trade_record_manager.transform_to_dataframe()
    # 1. 加载股票数据
    df = load_stock_data(kline_csv_path)

    # 2. 准备连续日期数据
    df_continuous = prepare_continuous_dates(df)

    # 3. 获取信号记录和交易记录和资产记录
    if signals_df is None:
        signals_df = get_sample_signal_records()
    if trades_df is None:
        trades_df = get_sample_trade_records()
    logger.debug(f"买/卖信号记录：")
    logger.debug(f"\n{signals_df}")
    logger.debug(f"交易记录：")
    logger.debug(f"\n{trades_df}")

    # 4. 筛选有效的日期
    valid_signals = filter_valid_dates(df, signals_df)
    valid_trades = filter_valid_dates(df, trades_df)

    # 5. 计算持仓量和资产变化
    holdings_data = calculate_holdings(df_continuous, valid_trades, initial_capital)

    # 6. 创建图表
    # 从CSV路径中提取股票代码和名称
    file_name = os.path.basename(str(kline_csv_path))
    parts = file_name.split('_')
    stock_info = ""
    if len(parts) >= 2:
        stock_code = parts[0]
        stock_name = parts[1]
        stock_info = f"{stock_code} {stock_name}"

    fig = create_trading_chart(stock_info, df_continuous, valid_signals, valid_trades, holdings_data, initial_capital)
    report_payload = build_report_payload(stock_info, df_continuous, valid_signals, valid_trades, holdings_data, initial_capital)
    # 7. 保存和显示图表
    output_path = save_and_show_chart(fig, html_file_name, html_file_path, report_payload)

    return output_path
