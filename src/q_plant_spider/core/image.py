"""
图片处理模块，负责下载、处理和上传图片
"""
import os
import hashlib
import requests
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class ImageHandler:
    """图片处理器"""
    
    def __init__(self, save_dir: str = 'downloaded_images'):
        """
        初始化图片处理器
        
        Args:
            save_dir: 图片保存目录
        """
        self.save_dir = Path(save_dir)
        self._init_save_dir()
        self.reference_hash = self._get_reference_hash()
        self.max_workers = 4
        self.upload_semaphore = threading.Semaphore(5)

    def _init_save_dir(self) -> None:
        """初始化保存目录"""
        self.save_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建图片保存目录: {self.save_dir}")

    def _get_reference_hash(self) -> Optional[str]:
        """获取参考图片哈希值"""
        try:
            ref_image = Path("image.png")
            if not ref_image.exists():
                logger.warning("参考图片不存在")
                return None
                
            with ref_image.open("rb") as f:
                sha256_hash = hashlib.sha256()
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"获取参考图片哈希值失败: {e}")
            return None

    def _get_content_hash(self, content: bytes) -> str:
        """计算内容哈希值"""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(content)
        return sha256_hash.hexdigest()

    def _upload_with_rate_limit(self, image_path: Path) -> Optional[str]:
        """使用信号量限制上传并发"""
        from ..api.lark_api import upload_image  # 延迟导入避免循环引用
        
        with self.upload_semaphore:
            try:
                for retry in range(3):
                    try:
                        file_token = upload_image(str(image_path))
                        if file_token:
                            logger.debug(f"成功获取file_token: {file_token}")
                            return file_token
                    except Exception as e:
                        wait_time = (retry + 1) * 2
                        if retry < 2:  # 最后一次失败不需要等待
                            logger.warning(f"上传失败，等待 {wait_time} 秒后重试: {e}")
                            time.sleep(wait_time)
                            
                logger.error("达到最大重试次数，上传失败")
                return None
                    
            except Exception as e:
                logger.error(f"上传失败: {e}")
                return None

    def _process_single_image(self, args: tuple) -> Optional[str]:
        """处理单个图片"""
        attachment_id, cookies, issue_id, number = args
        temp_file = None
        
        try:
            image_url = (
                f'https://qplant-f3.nioint.com/q-plant-admin-front/q-plant-basic/attachmentFmsAndBox/attachmentDownload?attachmentId={attachment_id}&boxToken=null'
            )
            
            # 下载图片(带重试)
            for retry in range(3):
                try:
                    response = requests.get(image_url, cookies=cookies, timeout=30)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if retry == 2:
                        logger.error(f"下载图片失败 (attachmentId: {attachment_id}): {e}")
                        return None
                    time.sleep(2)
                    continue

            # 验证响应类型
            if 'application/octet-stream' not in response.headers.get('Content-Type', ''):
                logger.warning(f"警告: attachmentId {attachment_id} 返回的不是图片内容")
                return None

            # 处理图片内容
            image_content = response.content
            if self._get_content_hash(image_content) == self.reference_hash:
                logger.error(f"无内容图片: issue_{issue_id}_{number}.jpg")
                return None

            # 保存临时文件
            temp_file = self.save_dir / f'issue_{issue_id}_{number}.jpg'
            temp_file.write_bytes(image_content)
            
            # 确保文件写入完成
            time.sleep(0.5)

            # 上传图片
            file_token = self._upload_with_rate_limit(temp_file)
            if file_token:
                logger.debug(f"成功上传图片: {temp_file.name}")
                return file_token

            logger.error(f"获取file_token失败: {temp_file.name}")
            return None

        except Exception as e:
            logger.error(f"处理图片时发生错误 (attachmentId: {attachment_id}): {e}")
            return None
            
        finally:
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.error(f"删除临时文件失败: {e}")

    def process_images(self, detail_data: Dict[str, Any], cookies: Dict[str, str]) -> List[str]:
        """并发处理多个图片
        
        Args:
            detail_data: 问题详情数据
            cookies: 请求cookies
            
        Returns:
            List[str]: 上传成功的图片token列表
        """
        try:
            # 收集所有附件ID
            attachment_ids = []
            if detail_data['object'].get('attachmentId'):
                attachment_ids.append(detail_data['object']['attachmentId'])
            if detail_data['object'].get('attachmentIds'):
                attachment_ids.extend(detail_data['object']['attachmentIds'])

            if not attachment_ids:
                logger.debug("没有找到需要处理的图片")
                return []

            issue_id = detail_data['object']['id']
            logger.debug(f"处理问题ID {issue_id} 的图片")

            # 并发处理图片
            max_workers = min(self.max_workers, len(attachment_ids))
            results = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_aid = {
                    executor.submit(
                        self._process_single_image, 
                        (aid, cookies, issue_id, i+1)
                    ): aid for i, aid in enumerate(attachment_ids)
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
        
