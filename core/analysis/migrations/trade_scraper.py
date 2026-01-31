"""
期权/股票交易记录抓取器（可选工具）。

适用场景：
- 迁移自 x/find_trades.py，依赖 Selenium + ChromeDriver。
- 默认不进入核心流程，仅在需要时单独运行。

数学原理：
1. 不涉及量化计算，主要是网页表格解析与分页抓取。
2. 通过 DataFrame 合并实现全量结果拼接。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _require_selenium():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except Exception as exc:
        raise RuntimeError(f"缺少 selenium 依赖，无法抓取: {exc}") from exc
    return webdriver, Service, By, WebDriverWait, EC


def _require_webdriver_manager():
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as exc:
        raise RuntimeError(f"缺少 webdriver_manager 依赖，无法抓取: {exc}") from exc
    return ChromeDriverManager


def _require_bs4():
    try:
        from bs4 import BeautifulSoup
    except Exception as exc:
        raise RuntimeError(f"缺少 bs4 依赖，无法解析: {exc}") from exc
    return BeautifulSoup


def scrape_trades(trade_type: str = "stock", max_pages: int = 0, output_dir: Path | None = None) -> Path | None:
    """
    抓取交易记录并保存 CSV。

    Args:
        trade_type: 'stock' 或 'option'
        max_pages: 0 表示抓取全部页
        output_dir: 输出目录（默认当前目录）

    Returns:
        保存的 CSV 路径；失败时返回 None
    """
    webdriver, Service, By, WebDriverWait, EC = _require_selenium()
    ChromeDriverManager = _require_webdriver_manager()
    BeautifulSoup = _require_bs4()

    config = {
        "stock": {"table_id": "footable_8078", "filename": "stock_trades_all.csv"},
        "option": {"table_id": "footable_8185", "filename": "option_trades_all.csv"},
    }
    if trade_type not in config:
        raise ValueError("不支持的 trade_type，请使用 'stock' 或 'option'。")

    if output_dir is None:
        output_dir = Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    target = config[trade_type]
    table_id = target["table_id"]
    target_path = output_dir / target["filename"]

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = "https://findingyouredge.org/trades/"
    driver.get(url)

    all_data: list[pd.DataFrame] = []
    page_num = 1
    try:
        while True:
            table_element = driver.find_element(By.ID, table_id)
            table_html = table_element.get_attribute("outerHTML")
            soup = BeautifulSoup(table_html, "html.parser")
            if soup.tfoot:
                soup.tfoot.decompose()
            df_current = pd.read_html(str(soup), header=0)[0]

            if isinstance(df_current.columns, pd.MultiIndex):
                df_current.columns = df_current.columns.get_level_values(0)
            df_current.columns = [str(c).strip() for c in df_current.columns]

            first_col = df_current.columns[0]
            df_current = df_current[df_current[first_col].astype(str).str.len() > 3]
            all_data.append(df_current)

            if max_pages > 0 and page_num >= max_pages:
                break

            xpath_next = f'//*[@id="{table_id}"]//tfoot//ul/li/a[contains(text(), "›")]'
            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_next))
                )
                parent_li = next_btn.find_element(By.XPATH, "./..")
                if "disabled" in parent_li.get_attribute("class"):
                    break
                driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                driver.execute_script("arguments[0].click();", next_btn)
                page_num += 1
            except Exception:
                break
    finally:
        driver.quit()

    if not all_data:
        return None
    final_df = pd.concat(all_data, ignore_index=True, sort=False)
    final_df.to_csv(target_path, index=False, encoding="utf-8-sig")
    return target_path


if __name__ == "__main__":
    result = scrape_trades(trade_type="option", max_pages=0, output_dir=Path("x"))
    if result is None:
        raise SystemExit("未抓取到数据")
    print(f"保存文件: {result}")
