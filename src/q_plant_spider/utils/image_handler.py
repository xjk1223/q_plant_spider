"""
图片处理模块
"""
import os
import hashlib
import requests
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

class ImageHandler:
    """图片处理器，负责下载和上传图片"""
    
    def __init__(self):
        """初始化图片处理器"""
        self.save_dir = 'downloaded_images'
        self._init_save_dir()
        self.reference_hash = self._get_reference_hash()
        self.max_workers = 4  # 限制最大并发数为4
        self.upload_semaphore = threading.Semaphore(5)  # 限制最大上传并发为5

    def _init_save_dir(self):
        """初始化保存目录"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            logger.info(f"创建图片保存目录: {self.save_dir}")

    def _get_reference_hash(self):
        """获取参考图片哈希值"""
        try:
            ref_file = os.path.join(os.path.dirname(__file__), "../../..", "image.png")
            if os.path.exists(ref_file):
                with open(ref_file, "rb") as f:
                    sha256_hash = hashlib.sha256()
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                return sha256_hash.hexdigest()
            logger.warning(f"参考图片不存在: {ref_file}")
            return None
        except Exception as e:
            logger.error(f"获取参考图片哈希值失败: {e}")
            return None

    def _get_content_hash(self, content):
        """计算内容哈希值"""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(content)
        return sha256_hash.hexdigest()

    def _upload_with_rate_limit(self, image_name):
        """使用信号量限制上传并发"""
        # 导入上传功能
        from ..api.lark_api import upload_image
        
        with self.upload_semaphore:
            try:
                # 首次尝试上传
                file_token = upload_image(os.path.join(self.save_dir, image_name))
                if file_token:
                    logger.debug(f"成功获取file_token: {file_token}")
                    return file_token
                    
                # 如果失败，进行重试
                for retry in range(3):
                    # 遇到频率限制时等待更长时间
                    wait_time = (retry + 1) * 2  # 2秒、4秒、6秒
                    logger.warning(f"上传受限，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    
                    try:
                        file_token = upload_image(os.path.join(self.save_dir, image_name))
                        if file_token:
                            logger.debug(f"重试成功获取file_token: {file_token}")
                            return file_token
                    except Exception as e:
                        logger.error(f"重试时发生错误: {e}")
                        
                logger.error("达到最大重试次数，上传失败")
                return None
                    
            except Exception as e:
                logger.error(f"上传失败: {e}")
                return None

    def _process_single_image(self, args):
        """处理单个图片"""
        attachment_id, cookies, issue_id, number = args
        file_path = None
        try:
            image_url = f'https://qplant.nioint.com/q-plant-admin-front/q-plant-basic/attachmentFmsAndBox/attachmentDownload?attachmentId={attachment_id}&boxToken=null'
            
            # 添加重试机制下载图片
            for retry in range(3):
                try:
                    response = requests.get(image_url, cookies=cookies, timeout=30)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if retry == 2:  # 最后一次重试
                        logger.error(f"下载图片失败 (attachmentId: {attachment_id}): {e}")
                        return None
                    time.sleep(2)  # 重试前等待
                    continue

            if 'application/octet-stream' not in response.headers.get('Content-Type', ''):
                logger.warning(f"警告: attachmentId {attachment_id} 返回的不是图片内容")
                return None

            # 生成文件名
            image_name = f'issue_{issue_id}_{number}.jpg'
            file_path = os.path.join(self.save_dir, image_name)

            # 保存图片内容
            image_content = response.content
            current_hash = self._get_content_hash(image_content)

            if current_hash == self.reference_hash:
                logger.error(f"无内容图片: {image_name}")
                return None

            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(image_content)
                f.flush()
                os.fsync(f.fileno())

            # 确保文件写入完成后再上传
            time.sleep(0.5)

            # 使用限流的上传方法
            file_token = self._upload_with_rate_limit(image_name)
            if file_token:
                logger.debug(f"成功上传图片: {image_name}")
                return file_token

            logger.error(f"获取file_token失败: {image_name}")
            return None

        except Exception as e:
            logger.error(f"处理图片时发生错误 (attachmentId: {attachment_id}): {e}")
            return None
        finally:
            # 清理临时文件
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    def process_images(self, Detail_data, cookies):
        """并发处理多个图片"""
        try:
            attachmentIdS_ = []
            if Detail_data['object'].get('attachmentId'):
                attachmentIdS_.append(Detail_data['object']['attachmentId'])
            if Detail_data['object'].get('attachmentIds'):
                attachmentIdS_.extend(Detail_data['object']['attachmentIds'])

            if not attachmentIdS_:
                logger.debug("没有找到需要处理的图片")
                return []

            issue_id = Detail_data['object']['id']
            logger.debug(f"处理问题ID {issue_id} 的图片")

            # 创建线程池处理图片
            max_workers = min(4, len(attachmentIdS_))  # 限制最大线程数为4
            results = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_aid = {
                    executor.submit(
                        self._process_single_image, 
                        (aid, cookies, issue_id, i+1)
                    ): aid for i, aid in enumerate(attachmentIdS_)
                }
                
                for future in future_to_aid:
                    try:
                        token = future.result()
                        if token:
                            results.append(token)
                    except Exception as e:
                        logger.error(f"图片处理失败: {e}")

            logger.debug(f"处理完成，获取到 {len(results)} 个有效token")
            return results

        except Exception as e:
            logger.error(f"处理图片过程中发生错误: {e}")
            return [] 