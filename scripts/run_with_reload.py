#!/usr/bin/env python
"""
开发模式运行脚本，支持代码热重载
"""
import os
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.q_plant_spider.utils.logger import setup_logging

# 配置日志
logger = logging.getLogger(__name__)
setup_logging()

class CodeChangeHandler(FileSystemEventHandler):
    """监控代码变化的事件处理器"""
    
    def __init__(self, callback):
        self.callback = callback
        self.last_modified = time.time()
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # 只处理Python文件
        if not event.src_path.endswith('.py'):
            return
            
        # 防止短时间内重复触发
        current_time = time.time()
        if current_time - self.last_modified < 1:
            return
            
        self.last_modified = current_time
        logger.info(f"检测到文件变化: {event.src_path}")
        self.callback()

def restart_app():
    """重启应用"""
    logger.info("重启应用...")
    
    # 使用os.system执行命令，这样脚本本身不会重启
    os.system("python -m src.q_plant_spider.main")

def main():
    """主函数"""
    logger.info("启动开发模式，监控代码变化...")
    
    # 首次运行
    restart_app()
    
    # 设置文件监控
    event_handler = CodeChangeHandler(restart_app)
    observer = Observer()
    observer.schedule(event_handler, str(ROOT_DIR / "src"), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("停止监控...")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main() 