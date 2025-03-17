"""
日志配置模块
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Optional

def setup_logging(log_level: int = logging.INFO, 
                  log_file: Optional[str] = None,
                  console_level: int = logging.INFO) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_level: 文件日志级别
        log_file: 日志文件名，默认为'app_日期.log'
        console_level: 控制台日志级别
        
    Returns:
        logging.Logger: 配置好的根日志记录器
    """
    # 创建日志格式器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    # 自定义日志处理器，支持按日期滚动
    class DailyRotatingHandler(RotatingFileHandler):
        def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None):
            self.date = datetime.now().date()
            # 添加日期后缀
            if not filename.endswith('.log'):
                filename = f"{filename}.log"
            filename_with_date = f"{filename.rsplit('.', 1)[0]}_{self.date.strftime('%Y-%m-%d')}.log"
            super().__init__(filename_with_date, mode, maxBytes, backupCount, encoding=encoding)
            
        def emit(self, record):
            try:
                current_date = datetime.now().date()
                if current_date != self.date:
                    self.date = current_date
                    base_name = self.baseFilename.rsplit('_', 1)[0]
                    self.baseFilename = f"{base_name}_{self.date.strftime('%Y-%m-%d')}.log"
                    if self.stream:
                        self.stream.close()
                        self.stream = None
                super().emit(record)
            except Exception:
                self.handleError(record)
    
    # 创建logs目录
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # 确定日志文件名
    if log_file is None:
        log_file = 'app'
    log_path = log_dir / log_file
    
    # 创建文件处理器
    file_handler = DailyRotatingHandler(
        str(log_path),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    
    # 过滤器，减少控制台详细日志
    class ProcessLogFilter(logging.Filter):
        def filter(self, record):
            return not any(msg in record.getMessage() for msg in [
                '处理ID:',
                '处理问题ID',
                '成功上传图片:',
                '成功获取file_token:',
                '处理完成，获取到'
            ])
    
    console_handler.addFilter(ProcessLogFilter())
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # 添加新处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('lark_oapi').setLevel(logging.WARNING)
    
    return root_logger 