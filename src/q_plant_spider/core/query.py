"""
查询模块，负责处理问题数据的查询和处理
"""
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .auth import AuthManager
from .image import ImageHandler

logger = logging.getLogger(__name__)

class QueryManager:
    """查询管理器"""
    
    def __init__(self):
        """初始化查询管理器"""
        self.auth_manager = AuthManager()
        self.image_handler = ImageHandler()
        
    def _check_cookies(self) -> Dict[str, str]:
        """检查并获取有效的cookies"""
        cookies_list = self.auth_manager.load_cookies()
        if not cookies_list:
            return {}
            
        for cookie in cookies_list:
            if cookie.get('name') == 'qplant.sid':
                if cookie.get('expiry'):
                    expiry_time = datetime.fromtimestamp(cookie['expiry'])
                    if expiry_time < datetime.now():
                        logger.info('cookies已过期，重新获取')
                        if self.auth_manager.get_cookies():
                            return self.auth_manager.cookies_to_dict(
                                self.auth_manager.load_cookies()
                            )
                        return {}
                    
        return self.auth_manager.cookies_to_dict(cookies_list)

    def query_issue(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """
        查询问题数据
        
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
            pvbr = query_params.get('PVBR', '')
            time_info = query_params.get('time_info', '')
            model_type_code = query_params.get('modelTypeCode', '')
            
            url = ('https://qplant.nioint.com/q-plant-admin-front/q-plant-issue/'
                  'frame_center/define/query/list/issue_info_vehicle_operator')
                  
            logger.info(
                f"查询参数 - PVBR: {pvbr}, Time: {time_info}, "
                f"Model: {model_type_code}"
            )

            # 构建请求数据
            json_data = {
                'queryOpBeans': [
                    {
                        'key': 'ivo.rel_order_no',
                        'alias': 'pvbr',
                        'op': 6,
                        'value': pvbr,
                        'opName': None,
                        'filedType': 0,
                        'displayValue': '{"zh_CN":"PVBR","en_US":"PVBR"}',
                    },
                    {
                        'key': 'ii.report_time',
                        'alias': 'applyTime',
                        'op': 9,
                        'value': time_info,
                        'opName': '介于(包含)',
                        'filedType': 7,
                        'displayValue': '{"zh_CN":"录入时间","en_US":"录入时间"}',
                    },
                    {
                        'key': 'ii.model_type_code',
                        'alias': 'modelTypeCode',
                        'op': 0,
                        'value': model_type_code,
                        'opName': None,
                        'filedType': 2,
                        'displayValue': '{"zh_CN":"车型","en_US":"车型"}',
                    },
                    {
                        "key": "ii.issue_status",
                        "alias": "issueStatus",
                        "op": 0,
                        "value": "Confirmed~Repaired~Open",
                        "opName": None,
                        "filedType": 2,
                        "displayValue": '{"zh_CN":"问题状态","en_US":"问题状态"}'
                    },
                    {
                        "key": "ii.quality_station_type",
                        "alias": "qualityStationType",
                        "op": 0,
                        "value": "ST0011~ST0012~ST0015~ST0016~ST0030",
                        "opName": "等于",
                        "filedType": 2,
                        "displayValue": '{"zh_CN":"质量工位","en_US":"质量工位"}'
                    },
                ],
                'templateId': '',
                'templateSaveId': '',
                'code': '',
                'sortKey': '',
                'sortOrder': '',
                'sortEntity': '',
                'fuzzyQueryValue': '',
                'fuzzyViewColumns': [],
                'isJsonData': True,
                'columnFilter': [],
                'start': 0,
                'length': 5000,
            }

            cookies = self._check_cookies()
            if not cookies:
                return {
                    'data': None,
                    'status': "获取cookies失败",
                    'issue_length': 0
                }
            
            # 发送请求
            response = requests.post(
                url,
                cookies=cookies,
                json=json_data,
                timeout=30
            )
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应时间: {response.elapsed.total_seconds()}s")
            
            if response.status_code != 200:
                return {
                    'data': None,
                    'status': "请求失败",
                    'issue_length': 0
                }
                
            data = response.json()
            issue_length = data['object']['totalRows']
            
            if issue_length > 0:
                return {
                    'data': data,
                    'status': "更新成功",
                    'issue_length': issue_length
                }
            else:
                return {
                    'data': data,
                    'status': "未获取到数据",
                    'issue_length': 0
                }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求错误: {str(e)}")
            return {
                'data': None,
                'status': f"网络错误: {str(e)}",
                'issue_length': 0
            }
        except Exception as e:
            logger.error(f"查询过程发生错误: {str(e)}")
            return {
                'data': None,
                'status': f"查询错误: {str(e)}",
                'issue_length': 0
            }

    def get_issue_details(self, issues_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        获取问题详情并处理图片
        
        Args:
            issues_data: 问题数据列表
            
        Returns:
            处理后的问题数据列表
        """
        cookies = self._check_cookies()
        if not cookies:
            logger.error("获取cookies失败")
            return []
            
        try:
            for item in issues_data:
                issue_id = item.get('问题ID')
                if not issue_id:
                    continue
                    
                logger.info(f"处理问题ID: {issue_id}")
                
                # 获取问题详情
                detail_url = ('https://qplant.nioint.com/q-plant-admin-front/'
                            'q-plant-issue/issueInfo/queryIssueDetail')
                
                response = requests.post(
                    detail_url,
                    json={'id': issue_id},
                    cookies=cookies
                )
                response.raise_for_status()
                
                detail_data = response.json()
                
                # 处理图片
                file_tokens = self.image_handler.process_images(detail_data, cookies)
                item['问题图片'] = [{"file_token": token} for token in file_tokens]
                
            return issues_data
            
        except Exception as e:
            logger.error(f"获取问题详情时发生错误: {e}")
            return [] 