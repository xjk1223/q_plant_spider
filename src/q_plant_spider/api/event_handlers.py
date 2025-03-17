"""
飞书事件处理模块
"""
import logging
import threading
import re
from typing import Dict, Any
from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger, 
    P2CardActionTriggerResponse
)
import lark_oapi as lark
import os

from ..core.services import QueryService
from . import lark_api

logger = logging.getLogger(__name__)

# 从环境变量获取模板ID
response_template_id = os.getenv("RESPONSE_TEMPLATE_ID")
result_template_id = os.getenv("RESULT_TEMPLATE_ID")

def do_p2_application_bot_menu_v6(data: lark.application.v6.P2ApplicationBotMenuV6) -> None:
    """处理机器人菜单事件"""
    lark_api.send_template_message(data.event.operator.operator_id.open_id)

def process_query_and_update(data: P2CardActionTrigger):
    """
    后台处理查询和更新操作
    
    该函数在独立线程中运行，处理查询请求并更新卡片内容
    """
    try:
        # 获取表单数据
        form_value = data.event.action.form_value
        message_id = data.event.context.open_message_id
        
        # 处理日期和时间格式
        pvbr = form_value.get("PVBR", "")
        start_time = re.sub(r'\s+\+\d{4}$', '', form_value.get("start_time", ""))
        end_time = re.sub(r'\s+\+\d{4}$', '', form_value.get("end_time", ""))  
        time_info = f"{start_time}~{end_time}"
        model_type_code = "~".join(form_value.get("modelTypeCode", [""]))
        
        # 构建查询参数
        query_params = {
            "PVBR": pvbr, 
            "time_info": time_info, 
            "modelTypeCode": model_type_code
        }

        # 初始化查询服务
        query_service = QueryService()
        
        # 1. 执行查询
        logger.info(f"开始查询 - PVBR: {pvbr}, 时间: {time_info}, 车型: {model_type_code}")
        result = query_service.perform_query(query_params)
        logger.info(f"获取到数据条数: {result.get('issue_length', 0)}")

        # 2. 根据结果状态处理数据更新
        if result.get('status') == "更新成功":
            logger.info("查询成功，开始更新数据库")
            color = 'blue'
            
            # 更新数据库
            update_result = query_service.update_database(result)
            
            # 记录详细日志
            total_rows = result.get('issue_length', 0)
            new_rows = update_result.get('new', 0)
            updated_rows = update_result.get('updated', 0)
            logger.info(f"更新结果: 共{total_rows}条数据，新增{new_rows}条，更新{updated_rows}条")
            
            # 状态和总行数
            base_status = "更新成功"
            totalRows = updated_rows
            
        elif result.get('status') == "未获取到数据":
            # 无数据情况
            color = 'yellow' 
            base_status = '未获取到数据,文档未更新'
            totalRows = 0
            
        else:
            # 查询失败
            color = 'red'
            base_status = '更新失败'
            totalRows = 0
            logger.error(f"查询失败: {result.get('status')}")

        # 3. 完全匹配exam_main.py的卡片更新格式
        data_dict = {
            "template_id": result_template_id,
            "template_variable": {
                "PVBR": pvbr, 
                "TIME_INFO": time_info,  
                "modelTypeCode": model_type_code,
                "status": result.get('status', "更新状态未知"),
                "totalRows": totalRows,
                "color": color,
                "base_status": base_status,
            }
        }

        logger.info("开始更新卡片内容")
        lark_api.update_card(message_id, data_dict)

    except Exception as e:
        logger.error(f"处理查询更新失败: {str(e)}")
        # 更新卡片显示错误，严格匹配exam_main.py的格式
        error_data = {
            "template_id": result_template_id,
            "template_variable": {
                "status": "处理失败",
                "color": "red",
                "base_status": str(e),
                "totalRows": 0
            }
        }
        lark_api.update_card(message_id, error_data)

def do_card_action_trigger(data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
    """卡片回调处理函数"""
    # 返回即时响应，让用户知道请求已接收
    resp = {
        "toast": {
            "type": "success",
            "content": "请求已提交，正在处理..."
        },
        'card':{
            'type':'template',
            'data':{
                'template_id': response_template_id,
                'template_variable':{
                    'disabled': True,
                }
            }
        }
    }
    
    # 启动后台线程处理实际查询
    thread = threading.Thread(target=process_query_and_update, args=(data,))
    thread.daemon = True
    thread.start()
    
    return P2CardActionTriggerResponse(resp)

class EventHandler:
    """自定义事件处理器"""
    
    def __init__(self, encrypt_key, verification_token, log_level=lark.LogLevel.ERROR):
        # 使用 builder 模式创建基类
        self.handler = lark.EventDispatcherHandler.builder(
            encrypt_key, 
            verification_token, 
            log_level
        ) \
            .register_p2_application_bot_menu_v6(do_p2_application_bot_menu_v6) \
            .register_p2_card_action_trigger(do_card_action_trigger) \
            .build()
        
    def handle_request(self, request):
        """处理请求"""
        # 记录请求信息
        client_host = request.headers.get('X-Real-IP') or request.remote_addr
        logger.info(f"接收到请求: {client_host}, 方法: {request.method}")
        return self.handler.handle_request(request) 