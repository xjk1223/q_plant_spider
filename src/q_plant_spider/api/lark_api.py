"""
飞书API模块，负责处理与飞书平台的交互
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.api.drive.v1 import *

logger = logging.getLogger(__name__)

def create_client() -> lark.Client:
    """
    创建飞书客户端
    
    Returns:
        lark.Client: 飞书客户端实例
    """
    app_id = os.getenv("APP_ID")
    app_secret = os.getenv("APP_SECRET")
    
    return lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.ERROR) \
        .build()

class LarkClient:
    """飞书API客户端"""
    
    def __init__(self):
        """初始化飞书客户端"""
        self.client = None
        self.response_template_id = os.getenv("RESPONSE_TEMPLATE_ID")
        self.result_template_id = os.getenv("RESULT_TEMPLATE_ID")
        
    def get_client(self) -> lark.Client:
        """
        获取飞书客户端
        
        Returns:
            lark.Client: 飞书客户端实例
        """
        if not self.client:
            app_id = os.getenv("APP_ID")
            app_secret = os.getenv("APP_SECRET")
            
            self.client = lark.Client.builder() \
                .app_id(app_id) \
                .app_secret(app_secret) \
                .log_level(lark.LogLevel.ERROR) \
                .build()
                
        return self.client
            
    def send_message(self, open_id: str, content: str = None, card_content: Dict = None) -> bool:
        """
        发送消息
        
        Args:
            open_id: 接收者的open_id
            content: 文本内容，如果提供了card_content则忽略此参数
            card_content: 卡片内容，格式为Dict
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 消息类型
            msg_type = "interactive" if card_content else "text"
            
            # 消息内容
            if card_content:
                msg_content = json.dumps(card_content)
            else:
                msg_content = json.dumps({"text": content or "您好！"})
            
            # 创建消息体
            message_body = {
                "receive_id": open_id,
                "msg_type": msg_type,
                "content": msg_content
            }
            
            # 创建请求
            request = CreateMessageRequest.builder() \
                .receive_id_type("open_id") \
                .request_body(message_body) \
                .build()
            
            # 发送请求
            response = self.get_client().im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"发送消息失败: {response.msg}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"发送消息时发生错误: {str(e)}")
            return False
            
    def send_template_message(self, open_id: str, template_id: str = None, template_vars: Dict = None) -> bool:
        """
        发送模板消息
        
        Args:
            open_id: 接收者的open_id
            template_id: 模板ID，默认使用环境变量中的response_template_id
            template_vars: 模板变量
            
        Returns:
            bool: 是否发送成功
        """
        template_id = template_id or self.response_template_id
        
        card_content = {
            "type": "template",
            "data": {
                "template_id": template_id,
            }
        }
        
        # 如果有模板变量，添加
        if template_vars:
            card_content["data"]["template_variable"] = template_vars
            
        return self.send_message(open_id, card_content=card_content)
            
    def update_card(self, message_id: str, data_dict: Dict[str, Any]) -> bool:
        """
        更新卡片消息
        
        Args:
            message_id: 消息ID
            data_dict: 更新内容
            
        Returns:
            bool: 是否更新成功
        """
        try:
            request = PatchMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    PatchMessageRequestBody.builder()
                    .content(json.dumps({"type": "template", "data": data_dict}))
                    .build()
                ) \
                .build()
            
            response = self.get_client().im.v1.message.patch(request)
            
            if not response.success():
                logger.error(f"更新卡片失败: {response.msg}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"更新卡片时发生错误: {str(e)}")
            return False
            
    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            str: 文件token，上传失败返回None
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"文件不存在: {image_path}")
                return None
                
            file_size = os.path.getsize(image_path)
            file_name = os.path.basename(image_path)
            
            # 添加重试机制
            for retry in range(3):
                try:
                    with open(image_path, 'rb') as file:
                        request = UploadAllMediaRequest.builder() \
                            .request_body(UploadAllMediaRequestBody.builder()
                                .file_name(file_name)
                                .parent_type('bitable_image')
                                .parent_node(os.getenv("APP_TOKEN"))
                                .file(file)
                                .size(file_size)
                                .build()) \
                            .build()
                        
                        resp = self.get_client().drive.v1.media.upload_all(request)
                        
                        if resp.success():
                            resp_json = json.loads(lark.JSON.marshal(resp))
                            logger.info(f"成功上传图片: {file_name}")
                            return resp_json['data']['file_token']
                        
                        logger.error(f"上传失败: code: {resp.code}, msg: {resp.msg}")
                        if retry < 2:
                            import time
                            time.sleep(2)
                            continue
                            
                except Exception as e:
                    logger.error(f"上传出错，第{retry+1}次重试: {e}")
                    if retry < 2:
                        import time
                        time.sleep(2)
                    continue
                    
            return None
                
        except Exception as e:
            logger.error(f"上传图片过程中发生错误: {image_path}, 错误: {e}")
            return None

# 全局客户端实例
_lark_client = None

def get_lark_client() -> LarkClient:
    """获取飞书客户端单例"""
    global _lark_client
    if _lark_client is None:
        _lark_client = LarkClient()
    return _lark_client

# 便捷函数，直接调用
def send_message(open_id: str, content: str = None, card_content: Dict = None) -> bool:
    """发送消息便捷函数"""
    return get_lark_client().send_message(open_id, content, card_content)

def send_template_message(open_id: str, template_id: str = None, template_vars: Dict = None) -> bool:
    """发送模板消息便捷函数"""
    return get_lark_client().send_template_message(open_id, template_id, template_vars)

def update_card(message_id: str, data_dict: Dict[str, Any]) -> bool:
    """更新卡片便捷函数"""
    return get_lark_client().update_card(message_id, data_dict)

def upload_image(image_path: str) -> Optional[str]:
    """上传图片便捷函数"""
    return get_lark_client().upload_image(image_path) 