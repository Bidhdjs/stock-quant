from pathlib import Path


def get_project_root():
    current_file = Path(__file__).resolve()  # 当前文件的绝对路径
    root_markers = ['README.md', 'requirements-7.txt','requirements-13.txt']  # 根目录标志

    for parent in current_file.parents:
        if any((parent / marker).exists() for marker in root_markers):
            return parent
    raise FileNotFoundError("未找到项目根目录")


project_root = get_project_root()
data_root = project_root / 'data'
stock_data_root = data_root / 'stock'
log_root = project_root / 'log'

html_root = project_root / 'html'
