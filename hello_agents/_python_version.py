"""运行时的版本建议，仅作提示，不限制版本。"""
import sys


def show_recommendation():
    if sys.version_info[:2] == (3, 12):
        print("提示：推荐安装 Python 3.13；当前 Python 3.12 可以继续运行。", file=sys.stderr)
