"""
主程序入口，负责初始化和启动飞书机器人服务
"""
import time
import asyncio
import signal
import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT_DIR))

# 加载环境变量
env_path = ROOT_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# 内部模块导入 - 使用绝对导入
from src.q_plant_spider.utils.logger import setup_logging

# 初始化日志
logger = setup_logging()

# 全局变量
cli = None
loop = None

def signal_handler(signum, frame):
    """处理退出信号"""
    logger.info("接收到退出信号，正在关闭服务...")
    try:
        if loop and loop.is_running():
            # 获取所有任务
            pending = asyncio.all_tasks(loop)
            
            # 取消所有任务
            for task in pending:
                task.cancel()
            
            # 停止事件循环
            loop.stop()
            
            # 等待所有任务完成
            try:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            except:
                pass
            
            # 现在可以安全地关闭事件循环
            try:
                loop.close()
            except:
                pass
            
        logger.info("服务已安全退出")
    except Exception as e:
        logger.error(f"关闭服务时发生错误: {e}")
    finally:
        # 禁用错误输出
        sys.stderr = open(os.devnull, 'w')
        os._exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)    # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)   # 终止信号

def check_environment():
    """检查环境变量是否设置"""
    required_vars = [
        "APP_ID", "APP_SECRET", 
        "ENCRYPT_KEY", "VERIFICATION_TOKEN",
        "RESPONSE_TEMPLATE_ID", "RESULT_TEMPLATE_ID"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(f"缺少必要的环境变量: {', '.join(missing)}")
        logger.info("请在.env文件中设置这些变量，参考.env.example")
        return False
    return True

def main():
    """主函数"""
    start_time = time.time()
    
    try:
        global cli, loop
        
        # 检查环境变量
        if not check_environment():
            logger.info("服务启动失败: 环境变量配置不完整")
            # 在开发环境中返回而不是退出，这样run_with_reload可以继续监控
            return
            
        try:
            # 这部分可能会出错的导入放在这里，以便更好地处理可能的异常
            import lark_oapi as lark
            from src.q_plant_spider.api.event_handlers import EventHandler
            
            # 从环境变量获取配置
            app_id = os.getenv("APP_ID")
            app_secret = os.getenv("APP_SECRET")
            encrypt_key = os.getenv("ENCRYPT_KEY")
            verification_token = os.getenv("VERIFICATION_TOKEN")
            
            # 创建事件处理器
            event_handler = EventHandler(encrypt_key, verification_token, lark.LogLevel.ERROR)
            
            # 创建客户端
            cli = lark.ws.Client(
                app_id=app_id,
                app_secret=app_secret,
                event_handler=event_handler.handler,
                log_level=lark.LogLevel.ERROR
            )

            
            # 获取事件循环
            loop = asyncio.get_event_loop()
            
            # 启动客户端
            cli.start()
            logger.info("飞书机器人服务启动成功")
            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f'服务启动耗时: {elapsed_time:.2f}秒')
            
        except ImportError as e:
            logger.error(f"导入模块失败: {str(e)}")
            logger.info("请确保已安装所有依赖: pip install -r requirements/base.txt")
            return
            
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        return

def safe_main():
    """安全的主函数入口"""
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户手动停止服务")
    except Exception as e:
        logger.error(f"程序异常退出: {str(e)}")
        
if __name__ == "__main__":
    safe_main() 