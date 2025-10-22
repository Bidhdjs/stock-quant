import os
from common.logger import create_log
logger = create_log("util_csv")


def save_to_csv(df, filename):
    """将数据保存到CSV文件"""
    if not df.empty:
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 保存到CSV
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"数据已保存到 {filename}")
    else:
        logger.warning("无数据可保存")