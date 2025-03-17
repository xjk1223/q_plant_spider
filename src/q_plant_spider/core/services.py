"""
业务服务模块，处理核心业务逻辑
"""
import logging
from typing import Dict, Any, List
import requests

from .query import QueryManager
from .data_processor import filter_new_data, process_data_batch
from ..api import lark_api
from ..api.bitable_api import get_existing_ids, create_records

logger = logging.getLogger(__name__)

class QueryService:
    """查询服务，封装查询相关业务逻辑"""
    
    def __init__(self):
        """初始化查询服务"""
        self.query_manager = QueryManager()
        
    def perform_query(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """
        执行查询并处理结果
        
        Args:
            query_params: 包含查询参数的字典
                - PVBR: PVBR号
                - time_info: 时间范围
                - modelTypeCode: 车型代码
                
        Returns:
            Dict包含:
                - data: 查询结果数据
                - status: 查询状态
                - issue_length: 问题数量
        """
        try:
            # 执行查询
            result = self.query_manager.query_issue(query_params)
            
            # 如果有数据，处理详情和图片
            if result.get('status') == "更新成功" and result.get('data'):
                try:
                    # 从结果中提取问题数据
                    issues_data = self._extract_issues_data(result['data'])
                    
                    # 处理详情
                    processed_data = self.query_manager.get_issue_details(issues_data)
                    
                    # 更新结果数据
                    result['processed_data'] = processed_data
                    
                except Exception as e:
                    logger.error(f"处理问题详情时发生错误: {e}")
                    
            return result
                
        except Exception as e:
            logger.error(f"执行查询服务时发生错误: {e}")
            return {
                'data': None,
                'status': f"服务错误: {str(e)}",
                'issue_length': 0
            }
    
    def update_database(self, result_data):
        """
        更新数据库
        
        Args:
            result_data: 查询结果数据
            
        Returns:
            Dict: 更新结果
        """
        try:
            # 获取已存在的ID
            existing_ids = get_existing_ids()
            logger.info(f"已存在ID数量: {len(existing_ids)}")
            
            # 检查数据结构
            if 'data' not in result_data or 'object' not in result_data['data']:
                logger.error(f"结果数据格式错误，缺少data或object字段")
                return {'status': '数据格式错误', 'total': 0, 'new': 0, 'updated': 0}
            
            # 从结果中提取原始数据 - 参照exam_lark_use_api.py的结构
            issue_list = result_data['data']['object']['resultList']
            logger.info(f"从查询结果提取出问题列表: {len(issue_list)}条")
            
            # 转换数据格式，将英文字段转为中文字段
            raw_data = []
            from ..core.data_processor import standardize_field_names
            for item in issue_list:
                converted_item = standardize_field_names(item)
                raw_data.append(converted_item)
            
            # 过滤出新数据
            new_data = filter_new_data(raw_data, existing_ids)
            
            # 如果没有新数据，提前返回
            if not new_data:
                logger.info("没有新数据需要添加")
                return {'status': '无新数据', 'total': len(raw_data), 'new': 0, 'updated': 0}
            
            # 处理数据字段
            from ..core.data_processor import process_data_batch
            processed_data = process_data_batch(new_data)
            
            # 获取问题详情和图片
            processed_data = self._get_issue_details(processed_data)
            
            # 创建记录
            update_result = create_records(processed_data)
            
            return {
                'status': '更新成功',
                'total': len(raw_data),
                'new': len(new_data),
                'updated': update_result.get('length', 0)
            }
            
        except Exception as e:
            logger.error(f"更新数据库时发生错误: {e}", exc_info=True)
            return {
                'status': f"更新失败: {str(e)}",
                'total': 0,
                'new': 0,
                'updated': 0
            }
            
    def _extract_issues_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从原始查询数据中提取问题数据
        
        Args:
            data: 原始查询结果数据
            
        Returns:
            List[Dict]: 问题数据列表
        """
        issues = []
        try:
            rows = data.get('object', {}).get('data', [])
            for row in rows:
                issue = {
                    "问题ID": row.get("id"),
                    "问题描述": row.get("issueDesc"),
                    "PVBR": row.get("pvbr"),
                    "问题类型": row.get("issueType"),
                    "问题状态": row.get("issueStatus"),
                    "录入时间": row.get("applyTime"),
                    "分组": row.get("model"),
                    "车型": row.get("modelTypeCode"),
                }
                issues.append(issue)
                
            return issues
            
        except Exception as e:
            logger.error(f"提取问题数据时发生错误: {e}")
            return [] 

    def _get_issue_details(self, issues_data):
        """
        获取问题详情并添加图片信息
        
        Args:
            issues_data: 问题数据列表
            
        Returns:
            List[Dict]: 带有图片信息的问题列表
        """
        if not issues_data:
            return []
        
        try:
            # 导入ImageHandler (需要先实现)
            from ..utils.image_handler import ImageHandler
            image_handler = ImageHandler()
            
            # 获取cookies
            from ..core.auth import AuthManager
            auth_manager = AuthManager()
            cookies_list = auth_manager.load_cookies()
            cookies = auth_manager.cookies_to_dict(cookies_list) if cookies_list else {}
            
            if not cookies:
                logger.error("获取cookies失败，无法获取问题详情")
                return issues_data
            
            # 处理每个问题
            for item in issues_data:
                try:
                    id = item.get('问题ID')
                    if not id:
                        continue
                    
                    logger.info(f"获取问题详情 ID: {id}")
                    Detail_url = 'https://qplant.nioint.com/q-plant-admin-front/q-plant-issue/issueInfo/queryIssueDetail'
                    
                    resp = requests.post(Detail_url, json={'id': id}, cookies=cookies)
                    resp.raise_for_status()
                    Detail_data = resp.json()
                    
                    # 处理图片
                    file_tokens = image_handler.process_images(Detail_data, cookies)
                    item['问题图片'] = [{"file_token": token} for token in file_tokens]
                    
                except Exception as e:
                    logger.error(f"处理问题ID {id} 详情时出错: {e}")
                    item['问题图片'] = []
                
            return issues_data
            
        except Exception as e:
            logger.error(f"获取问题详情过程中发生错误: {e}")
            return issues_data 