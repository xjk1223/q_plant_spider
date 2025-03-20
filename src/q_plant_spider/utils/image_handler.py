"""
图片处理模块 - 兼容层

该模块是从core/image.py导入的兼容包装，
以确保使用最新的qplant-f3版本的代码，
同时保持向后兼容性。
"""
import logging
from ..core.image import ImageHandler

# 设置模块级别的日志记录器
logger = logging.getLogger(__name__)

# 使用__all__导出ImageHandler类
__all__ = ['ImageHandler'] 