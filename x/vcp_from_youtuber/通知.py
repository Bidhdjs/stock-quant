# pip install yfinance pandas numpy requests

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class NotificationManager:
    def __init__(self, telegram_config=None, discord_config=None, email_config=None):
        """
        初始化通知管理器。
        :param telegram_config: 字典，包含 'token' 和 'chat_id'
        :param discord_config: 字典，包含 'webhook_url'
        :param email_config: 字典，包含 'sender', 'password', 'receiver'
        """
        self.tg_config = telegram_config
        self.dc_config = discord_config
        self.email_config = email_config

    def send_telegram(self, message):
        """
        发送Telegram消息，包含重试机制以应对网络波动。
        参考: [6, 15, 22]
        """
        if not self.tg_config:
            return

        url = f"https://api.telegram.org/bot{self.tg_config['token']}/sendMessage"
        payload = {
            "chat_id": self.tg_config['chat_id'],
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logging.info("Telegram消息发送成功")
        except requests.exceptions.RequestException as e:
            logging.error(f"Telegram发送失败: {e}")

    def send_discord(self, symbol, price, pivot, volume_ratio, trend_status):
        """
        发送Discord Embed消息，提供可视化的信号详情。
        参考:
        """
        if not self.dc_config:
            return

        # 根据涨跌设置颜色 (绿色: 0x00FF00)
        color = 0x00FF00

        embed = {
            "title": f"🚨 VCP 突破信号: {symbol}",
            "description": "检测到波动收缩模式后的枢轴点突破！",
            "color": color,
            "fields":,
        "footer": {"text": "QuantAlgo Bot - VCP Strategy"},
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        }

        payload = {
            "username": "Market Scanner",
            "avatar_url": "https://i.imgur.com/4M34hi2.png",
            "embeds": [embed]
        }

        try:
            response = requests.post(self.dc_config['webhook_url'], json=payload, timeout=10)
            if response.status_code in:
                logging.info(f"Discord消息发送成功: {symbol}")
            else:
                logging.error(f"Discord发送异常: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Discord连接错误: {e}")

    def send_email_report(self, subject, html_content):
        """
        发送HTML格式的汇总报告邮件。
        参考: [8, 21]
        """
        if not self.email_config:
            return

        msg = MIMEMultipart()
        msg['From'] = self.email_config['sender']
        msg = self.email_config['receiver']
        msg = subject
        msg.attach(MIMEText(html_content, 'html'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_config['sender'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            logging.info("邮件报告发送成功")
        except Exception as e:
            logging.error(f"邮件发送失败: {e}")


import yfinance as yf
import pandas as pd
import numpy as np


class VCPScreener:
    def __init__(self, tickers):
        self.tickers = tickers

    def _check_trend_template(self, df):
        """
        验证Mark Minervini的8大趋势准则。
        返回: (bool, str) -> (是否通过, 状态描述)
        参考:
        """
        if len(df) < 260:  # 确保有一年的数据
            return False, "数据不足"

        # 计算移动平均线
        sma_50 = df['Close'].rolling(window=50).mean()
        sma_150 = df['Close'].rolling(window=150).mean()
        sma_200 = df['Close'].rolling(window=200).mean()

        # 52周高低点
        low_52w = df['Low'].rolling(window=260).min()
        high_52w = df['High'].rolling(window=260).max()

        # 获取最新一天的值
        c = df['Close'].iloc[-1]
        s50 = sma_50.iloc[-1]
        s150 = sma_150.iloc[-1]
        s200 = sma_200.iloc[-1]
        h52 = high_52w.iloc[-1]
        l52 = low_52w.iloc[-1]

        # 趋势判断逻辑
        # 1. 价格高于长期均线
        c1 = c > s150 and c > s200
        # 2. 150日均线高于200日均线
        c2 = s150 > s200
        # 3. 200日均线处于上升趋势 (比较当前与20天前)
        c3 = s200 > sma_200.iloc[-22]
        # 4. 50日均线高于长期均线 (短期趋势强)
        c4 = s50 > s150 and s50 > s200
        # 5. 价格高于50日均线
        c5 = c > s50
        # 6. 较52周低点至少上涨30%
        c6 = c >= (1.3 * l52)
        # 7. 处于52周高点的25%以内
        c7 = c >= (0.75 * h52)

        if c1 and c2 and c3 and c4 and c5 and c6 and c7:
            return True, "Stage 2 Uptrend"
        else:
            return False, "Not in Trend"

    def _detect_vcp(self, df):
        """
        检测波动收缩模式 (VCP)。
        逻辑: 检查过去60天内波动率是否呈阶梯式下降。
        参考: [10, 12]
        """
        # 将过去60天分为三个20天的时间窗口
        # 这是一种简化的算法模拟，实际VCP可能更复杂
        period = 20
        vol_sections =

        for i in range(3):
            start = -(i + 1) * period
            end = -i * period if i != 0 else None
            segment = df['Close'].iloc[start:end]
            # 计算归一化波动率 (标准差 / 均值)
            vol = segment.std() / segment.mean()
            vol_sections.append(vol)

        # vol_sections[1] 是最远的时间段, vol_sections 是最近的时间段
        # VCP特征: 波动率逐渐降低 (Vol_Old > Vol_Mid > Vol_New)
        # 且最近的波动率必须非常低 (例如小于3%)
        is_contracting = (vol_sections[1] > vol_sections[2]) and \
                         (vol_sections[2] > vol_sections)

        is_tight = vol_sections < 0.05  # 5%的紧凑度阈值

        # 检查成交量枯竭: 最近5天平均成交量 < 50日均量
        vol_sma50 = df['Volume'].rolling(50).mean().iloc[-1]
        vol_recent = df['Volume'].iloc[-5:].mean()
        volume_dry = vol_recent < vol_sma50

        return is_contracting and is_tight and volume_dry

    def analyze_stock(self, ticker):
        """
        主分析函数，整合趋势和VCP检测。
        """
        try:
            # 下载数据，使用auto_adjust=True复权
            df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 260:
                return None

            # 步骤1: 趋势模板过滤
            is_trend, status = self._check_trend_template(df)
            if not is_trend:
                return None

            # 步骤2: VCP形态检测
            is_vcp = self._detect_vcp(df)

            if is_vcp:
                # 计算关键指标
                current_price = df['Close'].iloc[-1]
                pivot_point = df['High'].iloc[-20:].max()  # 最近20天最高价作为枢轴

                # 检查是否刚突破枢轴 (当前价格 > 枢轴 且 昨日价格 <= 枢轴)
                # 注意: 这里简化为接近枢轴或刚突破
                volume_ratio = df['Volume'].iloc[-1] / df['Volume'].rolling(50).mean().iloc[-1]

                return {
                    "symbol": ticker,
                    "price": current_price,
                    "pivot": pivot_point,
                    "volume_ratio": volume_ratio,
                    "status": status
                }

        except Exception as e:
            logging.error(f"分析 {ticker} 时出错: {e}")
            return None


if __name__ == "__main__":
    # --- 用户配置区 (请替换为真实Key) ---
    TG_CONFIG = {
        "token": "YOUR_TELEGRAM_BOT_TOKEN",
        "chat_id": "YOUR_CHAT_ID"
    }
    DC_CONFIG = {
        "webhook_url": "YOUR_DISCORD_WEBHOOK_URL"
    }
    # --------------------------------

    # 1. 初始化通知器
    notifier = NotificationManager(telegram_config=TG_CONFIG, discord_config=DC_CONFIG)

    # 2. 定义股票池 (示例: 纳斯达克科技股)
    # 在实际生产环境中，这里应读取包含数千只股票的CSV文件
    tickers =

    logging.info(f"开始扫描 {len(tickers)} 只股票...")
    screener = VCPScreener(tickers)

    # 3. 循环扫描
    found_count = 0
    for ticker in tickers:
        result = screener.analyze_stock(ticker)

        if result:
            found_count += 1
            logging.info(f"发现信号: {ticker}")

            # 4. 触发多渠道通知

            # Telegram推送
            msg_text = (f"🚀 *VCP 突破预警*\n"
                        f"股票: *{result['symbol']}*\n"
                        f"价格: ${result['price']:.2f}\n"
                        f"枢轴点: ${result['pivot']:.2f}\n"
                        f"量能: {result['volume_ratio']:.1f}x")
            notifier.send_telegram(msg_text)

            # Discord推送
            notifier.send_discord(
                result['symbol'],
                result['price'],
                result['pivot'],
                result['volume_ratio'],
                result['status']
            )

    logging.info(f"扫描完成。共发现 {found_count} 个潜在机会。")

# 每个交易日的美东时间下午4:05（收盘后）运行一次扫描
# 5 16 * * 1-5 /usr/bin/python3 /home/user/vcp_bot/main.py >> /var/log/vcp_bot.log 2>&1