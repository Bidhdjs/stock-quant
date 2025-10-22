import os
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common.logger import create_log
from settings import stock_data_root, html_root
logger = create_log('visual_tools_plotly')


def load_stock_data(csv_path):
    """
    加载股票数据并设置日期索引

    参数:
        csv_path: 股票数据CSV文件路径

    返回:
        加载好的DataFrame
    """
    df = pd.read_csv(
        csv_path,
        parse_dates=['date'],  # 解析date列为datetime类型
        index_col='date'  # 将date列设为索引，方便按日期查询
    )
    return df


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


def get_sample_signal_records():
    """
    获取示例信号记录

    返回:
        信号记录DataFrame
    """
    signal_records = pd.DataFrame([
        {'date': '2024-01-15', 'signal_type': 'normal_buy', 'signal_description': '多'},  # 仅信号，未操作
        {'date': '2024-01-17', 'signal_type': 'normal_buy', 'signal_description': '多(执行)'},  # 信号+操作
        {'date': '2024-02-18', 'signal_type': 'strong_buy', 'signal_description': '强多'},  # 仅信号，未操作
        {'date': '2024-02-20', 'signal_type': 'strong_buy', 'signal_description': '强多(执行)'},  # 信号+操作
        {'date': '2024-03-18', 'signal_type': 'normal_sell', 'signal_description': '空'},  # 仅信号，未操作
        {'date': '2024-03-20', 'signal_type': 'normal_sell', 'signal_description': '空(执行)'},  # 信号+操作
        {'date': '2024-04-13', 'signal_type': 'strong_sell', 'signal_description': '强空'},  # 仅信号，未操作
        {'date': '2024-04-15', 'signal_type': 'strong_sell', 'signal_description': '强空(执行)'},  # 信号+操作
        {'date': '2024-05-06', 'signal_type': 'normal_buy', 'signal_description': '多'},  # 仅信号，未操作
        {'date': '2024-05-08', 'signal_type': 'normal_buy', 'signal_description': '多(执行)'},  # 信号+操作
        {'date': '2024-06-10', 'signal_type': 'strong_buy', 'signal_description': '强多'},  # 仅信号，未操作
        {'date': '2024-06-12', 'signal_type': 'strong_buy', 'signal_description': '强多(执行)'},  # 信号+操作
        {'date': '2024-07-28', 'signal_type': 'normal_sell', 'signal_description': '空'},  # 仅信号，未操作
        {'date': '2024-07-30', 'signal_type': 'normal_sell', 'signal_description': '空(执行)'},  # 信号+操作
        {'date': '2024-08-23', 'signal_type': 'strong_sell', 'signal_description': '强空'},  # 仅信号，未操作
        {'date': '2024-08-25', 'signal_type': 'strong_sell', 'signal_description': '强空(执行)'},  # 信号+操作
    ])
    # 将日期转换为datetime类型
    signal_records['date'] = pd.to_datetime(signal_records['date'])
    return signal_records


def get_sample_trade_records():
    """
    获取示例交易记录

    返回:
        交易记录DataFrame
    """
    trade_records = pd.DataFrame([
        {'date': '2024-01-17', 'action': 'B', 'signal_type': 'normal_buy', 'shares': 200},
        {'date': '2024-02-20', 'action': 'B', 'signal_type': 'strong_buy', 'shares': 300},
        {'date': '2024-03-20', 'action': 'S', 'signal_type': 'normal_sell', 'shares': 200},
        {'date': '2024-04-15', 'action': 'S', 'signal_type': 'strong_sell', 'shares': 100},
        {'date': '2024-05-08', 'action': 'B', 'signal_type': 'normal_buy', 'shares': 200},
        {'date': '2024-06-12', 'action': 'B', 'signal_type': 'strong_buy', 'shares': 250},
        {'date': '2024-07-30', 'action': 'S', 'signal_type': 'normal_sell', 'shares': 200},
        {'date': '2024-08-25', 'action': 'S', 'signal_type': 'strong_sell', 'shares': 250},
    ])
    # 将日期转换为datetime类型
    trade_records['date'] = pd.to_datetime(trade_records['date'])
    return trade_records

def get_sample_asset_records():
    asset_records = pd.DataFrame([
        {'date': '2024-01-15', 'total_assets': 1000000},  # 初始资金
        {'date': '2024-01-17', 'total_assets': 799800},
        {'date': '2024-02-20', 'total_assets': 409400},
        {'date': '2024-03-20', 'total_assets': 1200200},
        {'date': '2024-04-15', 'total_assets': 2000300}
    ])
    # 将日期转换为datetime类型
    asset_records['date'] = pd.to_datetime(asset_records['date'])
    return asset_records


def filter_valid_dates(df, records):
    """
    筛选有效的日期，确保记录中的日期在股票数据中存在

    参数:
        df: 股票数据DataFrame
        records: 记录DataFrame（信号或交易）

    返回:
        有效的记录DataFrame
    """
    valid_dates = df.index  # 股票数据中所有存在的日期
    valid_records = records[records['date'].isin(valid_dates)].copy()

    # 提示缺失的日期
    missing_dates = records[~records['date'].isin(valid_dates)]['date']
    if not missing_dates.empty:
        logger.info(f"警告：以下日期在股票数据中不存在，已跳过：{missing_dates.dt.strftime('%Y-%m-%d').tolist()}")

    return valid_records


def calculate_holdings(df_continuous, valid_trades, initial_capital=1000000):
    """
    计算持仓量变化和总资产变化

    参数:
        df_continuous: 连续日期的股票数据
        valid_trades: 有效的交易记录
        initial_capital: 初始资金

    返回:
        包含持仓量和总资产的DataFrame
    """
    holdings_data = pd.DataFrame(index=df_continuous.index)
    holdings_data['holdings'] = 0

    # 初始化持仓量和资金
    total_holdings = 0
    capital = initial_capital
    holdings_value = 0

    # 计算持仓量变化和总资产变化
    holdings_history = []
    asset_history = []

    for date in df_continuous.index:
        # 检查该日期是否有交易
        day_trades = valid_trades[valid_trades['date'] == date]
        for _, trade in day_trades.iterrows():
            if trade['action'] == 'B':
                # 买入，持仓量增加
                total_holdings += trade['shares']
                # 从资金中扣除买入金额
                if date in df_continuous.index.dropna():
                    buy_price = df_continuous.loc[date, 'close']
                    capital -= trade['shares'] * buy_price
            elif trade['action'] == 'S':
                # 卖出，持仓量减少
                total_holdings -= trade['shares']
                # 资金增加卖出金额
                if date in df_continuous.index.dropna():
                    sell_price = df_continuous.loc[date, 'close']
                    capital += trade['shares'] * sell_price

        # 保存当日持仓量
        holdings_history.append(total_holdings)

        # 计算总资产（现金+持仓市值），这样算会忽略手续费和滑点，实际情况中会有这些成本，舍弃
        if date in df_continuous.index.dropna():
            current_price = df_continuous.loc[date, 'close']
            holdings_value = total_holdings * current_price
        total_assets = capital + holdings_value
        asset_history.append(total_assets)

    # 添加持仓量和总资产数据到DataFrame
    holdings_data['holdings'] = holdings_history
    holdings_data['total_assets'] = asset_history

    return holdings_data


def create_trading_chart(df_continuous, df, valid_signals, valid_trades, holdings_data, valid_assets, initial_capital):
    """
    创建包含K线、信号和交易记录的图表

    参数:
        df_continuous: 连续日期的股票数据
        df: 原始股票数据
        valid_signals: 有效的信号记录
        valid_trades: 有效的交易记录
        holdings_data: 持仓量和总资产数据
        initial_capital: 初始资金

    返回:
        Plotly图表对象
    """
    # 创建四个垂直排列的图表
    fig = make_subplots(
        rows=4, cols=1,  # 四行一列的布局
        shared_xaxes=True,  # 共享X轴（日期）
        vertical_spacing=0.03,  # 图表间垂直间距
        row_heights=[0.4, 0.2, 0.2, 0.2],  # 调整各图表高度比例
        subplot_titles=('K线与交易信号', '成交量', '持仓量', '总资产变化')  # 子图表标题
    )

    # 添加K线图到第一个子图
    fig.add_trace(
        go.Candlestick(
            x=df_continuous.index,  # 使用连续日期索引作为x轴
            open=df_continuous['open'],
            high=df_continuous['high'],
            low=df_continuous['low'],
            close=df_continuous['close'],
            name='K线'
        ),
        row=1, col=1  # 指定放在第一行第一列
    )

    # 添加信号标记
    # 多信号（K线下方，绿色文字）
    normal_buy_signals = valid_signals[valid_signals['signal_type'] == 'normal_buy']
    if not normal_buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=normal_buy_signals['date'],
            y=df.loc[normal_buy_signals['date'], 'low'] * 0.98,
            mode='text',
            name='多信号',
            text=['多' for _ in range(len(normal_buy_signals))],
            textposition='middle center',
            texttemplate='%{text}',
            textfont=dict(family="SimHei, Arial", size=12, color="green", weight="bold"),
            hovertemplate='日期: %{x}<br>信号: %{customdata[0]}<extra></extra>',
            customdata=normal_buy_signals[['signal_description']].values,
            showlegend=True
        ), row=1, col=1)

    # 强多信号（K线下方，深绿色文字，更大字号）
    strong_buy_signals = valid_signals[valid_signals['signal_type'] == 'strong_buy']
    if not strong_buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=strong_buy_signals['date'],
            y=df.loc[strong_buy_signals['date'], 'low'] * 0.95,
            mode='text',
            name='强多信号',
            text=['强多' for _ in range(len(strong_buy_signals))],
            textposition='middle center',
            texttemplate='%{text}',
            textfont=dict(family="SimHei, Arial", size=14, color="darkgreen", weight="bold"),
            hovertemplate='日期: %{x}<br>信号: %{customdata[0]}<extra></extra>',
            customdata=strong_buy_signals[['signal_description']].values,
            showlegend=True
        ), row=1, col=1)

    # 空信号（K线上方，橙色文字）
    normal_sell_signals = valid_signals[valid_signals['signal_type'] == 'normal_sell']
    if not normal_sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=normal_sell_signals['date'],
            y=df.loc[normal_sell_signals['date'], 'high'] * 1.02,
            mode='text',
            name='空信号',
            text=['空' for _ in range(len(normal_sell_signals))],
            textposition='middle center',
            texttemplate='%{text}',
            textfont=dict(family="SimHei, Arial", size=12, color="orange", weight="bold"),
            hovertemplate='日期: %{x}<br>信号: %{customdata[0]}<extra></extra>',
            customdata=normal_sell_signals[['signal_description']].values,
            showlegend=True
        ), row=1, col=1)

    # 强空信号（K线上方，红色文字，更大字号）
    strong_sell_signals = valid_signals[valid_signals['signal_type'] == 'strong_sell']
    if not strong_sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=strong_sell_signals['date'],
            y=df.loc[strong_sell_signals['date'], 'high'] * 1.05,
            mode='text',
            name='强空信号',
            text=['强空' for _ in range(len(strong_sell_signals))],
            textposition='middle center',
            texttemplate='%{text}',
            textfont=dict(family="SimHei, Arial", size=14, color="red", weight="bold"),
            hovertemplate='日期: %{x}<br>信号: %{customdata[0]}<extra></extra>',
            customdata=strong_sell_signals[['signal_description']].values,
            showlegend=True
        ), row=1, col=1)

    # 添加实际交易点标记
    # 买入操作（B，上三角形，绿色，K线下方）
    buy_trades = valid_trades[valid_trades['action'] == 'B']
    if not buy_trades.empty:
        fig.add_trace(go.Scatter(
            x=buy_trades['date'],
            y=df.loc[buy_trades['date'], 'close'] * 0.90,
            mode='markers+text',
            name='买入操作(B)',
            marker=dict(
                symbol='triangle-up',
                color='green',
                size=12,
                line=dict(width=1, color='black')
            ),
            text=['B' for _ in range(len(buy_trades))],
            textposition='bottom center',
            texttemplate='%{text}',
            textfont=dict(family="SimHei, Arial", size=12, color="darkgreen", weight="bold"),
            hovertemplate='日期: %{x}<br>操作: 买入(B)<br>数量: %{customdata[0]}股<br>价格: %{y:.2f}<extra></extra>',
            customdata=buy_trades[['shares']].values
        ), row=1, col=1)

    # 卖出操作（S，下三角形，红色，K线上方）
    sell_trades = valid_trades[valid_trades['action'] == 'S']
    if not sell_trades.empty:
        fig.add_trace(go.Scatter(
            x=sell_trades['date'],
            y=df.loc[sell_trades['date'], 'close'] * 1.10,
            mode='markers+text',
            name='卖出操作(S)',
            marker=dict(
                symbol='triangle-down',
                color='red',
                size=12,
                line=dict(width=1, color='black')
            ),
            text=['S' for _ in range(len(sell_trades))],
            textposition='top center',
            texttemplate='%{text}',
            textfont=dict(family="SimHei, Arial", size=12, color="darkred", weight="bold"),
            hovertemplate='日期: %{x}<br>操作: 卖出(S)<br>数量: %{customdata[0]}股<br>价格: %{y:.2f}<extra></extra>',
            customdata=sell_trades[['shares']].values
        ), row=1, col=1)

    # 添加成交量图表到第二个子图
    volume_continuous = df_continuous['volume'].fillna(0)
    fig.add_trace(go.Bar(
        x=df_continuous.index,
        y=volume_continuous,
        name='成交量',
        marker_color='blue',
        opacity=0.5
    ), row=2, col=1)

    # 添加持仓量图表到第三个子图
    fig.add_trace(go.Scatter(
        x=holdings_data.index,
        y=holdings_data['holdings'],
        mode='lines',
        name='持仓量',
        line=dict(color='purple', width=2),
        hovertemplate='日期: %{x}<br>持仓量: %{y}股<extra></extra>'
    ), row=3, col=1)

    # # 添加总资产变化图表到第四个子图，这里不准，没有计算手续费和滑点，只是简单的累加，计算总资产有误差，暂时不使用
    # fig.add_trace(go.Scatter(
    #     x=holdings_data.index,
    #     y=holdings_data['total_assets'],
    #     mode='lines',
    #     name='总资产',
    #     line=dict(color='gold', width=2),
    #     hovertemplate='日期: %{x}<br>总资产: %.2f<extra></extra>'
    # ), row=4, col=1)

    # 添加总资产变化图表到第四个子图
    assets_filled = pd.Series(index=df_continuous.index)

    # 首先，用valid_assets中的实际值填充对应日期
    for date, value in valid_assets.set_index('date')['total_assets'].items():
        if date in assets_filled.index:
            assets_filled.loc[date] = value
    # 然后，使用线性插值填充缺失的日期
    assets_filled = assets_filled.interpolate(method='linear')
    # 如果开头有缺失值，用第一个有效值向前填充
    assets_filled = assets_filled.ffill()
    # 如果结尾有缺失值，用最后一个有效值向后填充
    assets_filled = assets_filled.bfill()
    fig.add_trace(go.Scatter(
        x=df_continuous.index,
        y=assets_filled.values,
        mode='lines',
        name='总资产',
        line=dict(color='gold', width=2),
        hovertemplate='日期: %{x}<br>总资产: %{y:.2f}<extra></extra>'
    ), row=4, col=1)

    # 添加初始资金参考线到总资产图表
    fig.add_hline(
        y=initial_capital,
        line=dict(color='gray', width=1, dash='dash'),
        annotation_text=f'初始资金: {initial_capital}',
        annotation_font=dict(size=10),
        row=4, col=1
    )

    # 美化图表布局
    fig.update_layout(
        title='股票K线与交易信号标记',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        template='plotly_white',
        height=1200,
        margin=dict(l=50, r=50, t=100, b=50),
    )

    # 设置Y轴标题和样式
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_yaxes(title_text="持仓量(股)", row=3, col=1)
    fig.update_yaxes(title_text="总资产", row=4, col=1)

    return fig


def save_and_show_chart(fig, output_dir=None):
    """
    保存图表并在浏览器中显示

    参数:
        fig: Plotly图表对象
        output_dir: 输出目录路径（可选）

    返回:
        保存的文件路径
    """
    # 获取当前时间作为文件名的一部分
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"stock_with_trades_{current_time}.html"

    # 如果指定了输出目录，则使用该目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, file_name)
    else:
        file_path = file_name

    # 保存图表
    fig.write_html(file_path)

    # 在浏览器中显示图表
    fig.show()

    return file_path


def plotly_draw(kline_csv_path=None, signal_records=None, trade_records=None, asset_records=None, initial_capital=1000000):
    """
    主函数，整合所有功能步骤

    参数:
        kline_csv_path: 股票数据CSV文件路径
        signal_records: 信号记录DataFrame（可选）
        trade_records: 交易记录DataFrame（可选）
        asset_records: 资产记录DataFrame（可选）
        initial_capital: 初始资金
    """
    # 如果未提供CSV路径，则使用默认路径
    if kline_csv_path is None:
        kline_csv_path = stock_data_root / 'futu/HK.00700_腾讯控股_20230103_20251013.csv'

    # 1. 加载股票数据
    df = load_stock_data(kline_csv_path)

    # 2. 准备连续日期数据
    df_continuous = prepare_continuous_dates(df)

    # 3. 获取信号记录和交易记录和资产记录
    if signal_records is None:
        signal_records = get_sample_signal_records()
    if trade_records is None:
        trade_records = get_sample_trade_records()
    if asset_records is None:
        asset_records = get_sample_asset_records()
    logger.info(f"买/卖信号记录：")
    logger.info(f"\n{signal_records}")
    logger.info(f"交易记录：")
    logger.info(f"\n{trade_records}")
    logger.info(f"资产记录：")
    logger.info(f"\n{asset_records}")

    # 4. 筛选有效的日期
    valid_signals = filter_valid_dates(df, signal_records)
    valid_trades = filter_valid_dates(df, trade_records)
    valid_assets = filter_valid_dates(df, asset_records)

    # 5. 计算持仓量和资产变化
    holdings_data = calculate_holdings(df_continuous, valid_trades, initial_capital)

    # 6. 创建图表
    fig = create_trading_chart(df_continuous, df, valid_signals, valid_trades, holdings_data, valid_assets, initial_capital)

    # 7. 保存和显示图表
    relative_path = str(kline_csv_path).replace(str(stock_data_root) + '/', '')
    html_file_path = html_root /relative_path.rsplit('.', 1)[0]
    logger.info(f"回测可视化图表将保存至：{html_file_path}，对应股票数据：{kline_csv_path}")
    output_path = save_and_show_chart(fig,html_file_path)

    return output_path


if __name__ == "__main__":
    CSV_PATH = stock_data_root / "futu/HK.00700_腾讯控股_20210104_20240112.csv"
    plotly_draw(CSV_PATH)
    # plotly_draw()