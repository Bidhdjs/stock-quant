from common.logger import create_log
import datetime

logger = create_log("util_html")


def signals_to_html(signals_data, filters=None, summary=None):
    """将信号数据转换为HTML报告

    参数:
        signals_data: 信号数据列表，每个元素是包含信号信息的字典
        filters: 筛选条件字典
        summary: 统计信息字典

    返回:
        HTML格式的报告字符串
    """
    try:
        # 设置默认筛选条件和统计信息
        if filters is None:
            filters = {}
        if summary is None:
            summary = {
                'total_signals': len(signals_data),
                'buy_signals': len([s for s in signals_data if s.get('signal_type') and 'buy' in s.get('signal_type')]),
                'sell_signals': len(
                    [s for s in signals_data if s.get('signal_type') and 'sell' in s.get('signal_type')]),
                'unique_stocks': len(set([s.get('stock_info', '') for s in signals_data]))
            }

        # 获取筛选条件
        strategy_filter = filters.get('strategy_name', '')
        stock_filter = filters.get('stock_code', '')
        signal_type_filter = filters.get('signal_type', '')
        start_date = filters.get('start_date', '')
        end_date = filters.get('end_date', '')

        # 获取统计信息
        total_signals = summary.get('total_signals', 0)
        buy_signals = summary.get('buy_signals', 0)
        sell_signals = summary.get('sell_signals', 0)
        unique_stocks = summary.get('unique_stocks', 0)

        # 生成信号表格行
        table_rows = []
        for signal in signals_data:
            signal_type_class = ''
            if signal.get('signal_type') and 'buy' in signal.get('signal_type'):
                signal_type_class = 'price-up'
            elif signal.get('signal_type') and 'sell' in signal.get('signal_type'):
                signal_type_class = 'price-down'

            table_row = f"                <tr>\n"
            table_row += f"                    <td>{signal.get('date', '-')}</td>\n"
            table_row += f"                    <td class='{signal_type_class}'>{signal.get('signal_type', '-')}</td>\n"
            table_row += f"                    <td>{signal.get('description', '-')}</td>\n"
            table_row += f"                    <td>{signal.get('stock_info', '-')}</td>\n"
            table_row += f"                    <td>{signal.get('data_source', '-')}</td>\n"
            table_row += f"                    <td>{signal.get('strategy_name', '-')}</td>\n"
            table_row += f"                </tr>"
            table_rows.append(table_row)

        # 创建HTML内容
        html_content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>信号分析报告 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #2a2a2a; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .stats-container {{ display: flex; justify-content: space-around; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{
            text-align: center;
            padding: 15px;
            background: #3a3a3a;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            margin: 10px;
            flex: 1;
            min-width: 200px;
            color: #e0e0e0;
        }}
        .stat-value {{ font-size: 1.8rem; font-weight: bold; margin: 5px 0; }}
        .price-up {{ color: #ff6b6b; }}
        .price-down {{ color: #4ecdc4; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #3a3a3a;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            color: #e0e0e0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #555;
        }}
        th {{
            background-color: #4a4a4a;
            color: #fff;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #404040;
        }}
        .filters {{
            background: #3a3a3a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            color: #e0e0e0;
        }}
        .timestamp {{ text-align: right; color: #999; margin-top: 10px; font-size: 0.9rem; }}
        h1, h2, h3 {{ color: #fff; }}
        strong {{ color: #ccc; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>信号分析报告</h1>
            <p>此报告包含根据筛选条件分析的信号数据</p>
        </div>

        <div class="filters">
            <h3>筛选条件</h3>
            <div class="row">
                <div class="col-md-4">
                    <strong>策略：</strong>{strategy_filter or '全部策略'}
                </div>
                <div class="col-md-4">
                    <strong>股票：</strong>{stock_filter or '全部股票'}
                </div>
                <div class="col-md-4">
                    <strong>信号类型：</strong>{signal_type_filter or '全部类型'}
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-6">
                    <strong>起始时间：</strong>{start_date or '不限制'}
                </div>
                <div class="col-md-6">
                    <strong>结束时间：</strong>{end_date or '不限制'}
                </div>
            </div>
        </div>

        <div class="stats-container">
            <div class="stat-box">
                <div>总信号数</div>
                <div class="stat-value">{total_signals}</div>
            </div>
            <div class="stat-box">
                <div>买入信号</div>
                <div class="stat-value price-up">{buy_signals}</div>
            </div>
            <div class="stat-box">
                <div>卖出信号</div>
                <div class="stat-value price-down">{sell_signals}</div>
            </div>
            <div class="stat-box">
                <div>涉及股票数</div>
                <div class="stat-value">{unique_stocks}</div>
            </div>
        </div>

        <h2>信号详情</h2>
        <table>
            <thead>
                <tr>
                    <th>日期</th>
                    <th>信号类型</th>
                    <th>描述</th>
                    <th>股票信息</th>
                    <th>数据源</th>
                    <th>策略</th>
                </tr>
            </thead>
            <tbody>
{chr(10).join(table_rows)}
            </tbody>
        </table>

        <div class="timestamp">
            报告生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
'''

        logger.info(f"成功生成HTML报告，包含{len(signals_data)}条信号")
        return html_content

    except Exception as e:
        logger.error(f"生成HTML报告失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 示例用法
    sample_signals = [
        {
            'date': '2023-10-01',
            'signal_type': 'buy',
            'description': '买入信号',
            'stock_info': '腾讯控股(00700)',
            'data_source': 'futu',
            'strategy_name': 'EnhancedVolumeStrategy'
        },
        {
            'date': '2023-10-02',
            'signal_type': 'sell',
            'description': '卖出信号',
            'stock_info': '阿里巴巴(09988)',
            'data_source': 'futu',
            'strategy_name': 'SingleVolumeStrategy'
        }
    ]

    html = signals_to_html(sample_signals)
    print(html)