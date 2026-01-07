import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def scrape_trades(trade_type='stock', max_pages=0):
    """
    Args:
        trade_type (str): 'stock' (股票) 或 'option' (期权)
        max_pages (int): 0 表示抓取所有页；大于0 表示抓取指定页数
    """

    # --- 1. 配置区域：ID映射 ---
    # 如果网页更新导致 ID 变了，只需要修改这里
    config = {
        'stock': {
            'table_id': 'footable_8078',  # 股票表格 ID
            'filename': 'stock_trades_all.csv'
        },
        'option': {
            'table_id': 'footable_8185',  # 期权表格 ID (提取自你提供的XPath)
            'filename': 'option_trades_all.csv'
        }
    }

    if trade_type not in config:
        print(f"错误：不支持的类型 '{trade_type}'。请使用 'stock' 或 'option'。")
        return

    current_config = config[trade_type]
    target_table_id = current_config['table_id']
    target_filename = current_config['filename']

    # --- 2. 浏览器设置 ---
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 想要后台静默运行就取消注释
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    print(f"🚀 启动任务：抓取 [{trade_type}] 数据")
    print(f"🎯 目标表格 ID: {target_table_id}")
    print(f"📄 计划页数: {'全部 (无限翻页)' if max_pages == 0 else max_pages}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    url = "https://findingyouredge.org/trades/"
    driver.get(url)

    # 等待页面加载
    time.sleep(5)

    all_data = []
    page_num = 1

    try:
        while True:
            print(f"--- 正在处理第 {page_num} 页 ---")
            # --- 3. 抓取与清洗数据 (已修复乱码页脚) ---
            try:
                # A. 获取表格的 HTML
                table_element = driver.find_element(By.ID, target_table_id)
                table_html = table_element.get_attribute('outerHTML')

                # B. 【新增步骤】使用 BeautifulSoup 剔除 tfoot (翻页条就在这里面)
                soup = BeautifulSoup(table_html, 'html.parser')
                if soup.tfoot:
                    soup.tfoot.decompose()  # 这一刀下去，底部的乱码行就没了

                # C. 读取清洗后的 HTML
                df_current = pd.read_html(str(soup), header=0)[0]

                # D. 处理多级表头 (MultiIndex)
                if isinstance(df_current.columns, pd.MultiIndex):
                    df_current.columns = df_current.columns.get_level_values(0)

                # E. 清洗列名
                df_current.columns = [str(c).strip() for c in df_current.columns]

                # F. 【双重保险】过滤掉没有日期的行 (防止还有漏网之鱼)
                # 假设第一列是“开仓时间”，必须包含数字或 '/'
                first_col = df_current.columns[0]
                df_current = df_current[df_current[first_col].astype(str).str.len() > 3]

                all_data.append(df_current)
                print(f"✅ 第 {page_num} 页抓取成功，本页 {len(df_current)} 条。")

            except Exception as e:
                print(f"❌ 数据抓取失败: {e}")
                break

            # --- 4. 判断是否停止 ---
            # 如果 max_pages 不为 0，且当前页码 >= 目标页码，则停止
            if max_pages > 0 and page_num >= max_pages:
                print(f"已达到设定页数 ({max_pages})，停止抓取。")
                break

            # --- 5. 翻页逻辑 ---
            try:
                # 动态定位：在该表格 ID 内部寻找内容为 '›' 的链接
                # 这种写法比 li[7] 更稳定，无论它在第几个位置都能找到
                xpath_next = f'//*[@id="{target_table_id}"]//tfoot//ul/li/a[contains(text(), "›")]'

                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_next))
                )

                # 检查按钮是否被禁用 (通常父级 li 会有 disabled 类)
                parent_li = next_btn.find_element(By.XPATH, "./..")
                if "disabled" in parent_li.get_attribute("class"):
                    print("🛑 已到达最后一页 (翻页按钮禁用)。")
                    break

                # 执行点击
                driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_btn)

                # 等待加载
                print("⏳ 翻页中，等待数据刷新...")
                time.sleep(4)
                page_num += 1

            except Exception as e:
                print("🛑 未找到下一页按钮，或已是最后一页。")
                break

    finally:
        driver.quit()

    # --- 6. 保存数据 ---
    if all_data:
        try:
            print("正在合并数据...")
            final_df = pd.concat(all_data, ignore_index=True, sort=False)

            # 保存为 CSV (utf-8-sig 防止中文乱码)
            final_df.to_csv(target_filename, index=False, encoding='utf-8-sig')

            print(f"🎉 全部完成！共 {len(final_df)} 条数据。")
            print(f"💾 文件已保存为: {target_filename}")

        except Exception as e:
            print(f"❌ 保存文件时报错: {e}")
    else:
        print("⚠️ 未获取到任何数据。")


# --- 这里是程序的入口 ---
if __name__ == "__main__":
    # 场景 1: 下载【股票】的所有页
    scrape_trades(trade_type='stock', max_pages=0)

    # 场景 2: 下载【期权】的所有页 (根据你的要求，用这个)
    # scrape_trades(trade_type='option', max_pages=0)

    # 场景 3: 只测试下载【期权】的前 2 页
    # scrape_trades(trade_type='option', max_pages=2)