#!/usr/bin/env python
"""
项目启动脚本
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 导入主函数并运行
from src.q_plant_spider.main import safe_main

if __name__ == "__main__":
    safe_main() 