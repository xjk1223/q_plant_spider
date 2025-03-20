"""
飞书多维表格API模块，处理数据库操作
"""
import json
import os
import time
import logging
from typing import Dict, List, Any, Optional

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

from . import lark_api

logger = logging.getLogger(__name__)

class BitableClient:
    """飞书多维表格客户端"""
    
    def __init__(self, client=None):
        """
        初始化多维表格客户端
        
        Args:
            client: 飞书客户端实例，如果未提供，将创建新实例
        """
        self.client = client
        self.app_token = os.getenv("APP_TOKEN")
        self.table_id = os.getenv("TABLE_ID")
        self.batch_size = int(os.getenv("BATCH_SIZE", "990"))
        self.page_size = int(os.getenv("PAGE_SIZE", "500"))
        
    def _get_client(self):
        """获取飞书客户端"""
        if not self.client:
            self.client = lark_api.create_client().client
        return self.client
    
    def create_records(self, result_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        创建数据库记录
        
        Args:
            result_data: 要创建的记录数据列表
            
        Returns:
            Dict: 创建结果
        """
        client = self._get_client()
        total_length = len(result_data)
        logger.info(f"总共有 {total_length} 条记录要创建")
        
        # 将数据分批处理
        batches = [result_data[i:i + self.batch_size] for i in range(0, total_length, self.batch_size)]
        records = []
        
        for i, batch in enumerate(batches):
            logger.info(f"处理第 {i+1}/{len(batches)} 批数据，共 {len(batch)} 条记录")
            batch_records = [AppTableRecord.builder().fields(data).build() for data in batch]
            
            request = BatchCreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .user_id_type("user_id") \
                .request_body(BatchCreateAppTableRecordRequestBody.builder()
                    .records(batch_records)
                    .build()) \
                .build()
            
            resp = client.bitable.v1.app_table_record.batch_create(request)
            if not resp.success():
                logger.error(f"批量创建记录失败: {resp.msg}")
                continue
                
            resp_json = json.loads(lark.JSON.marshal(resp))
            records.extend(batch_records)
            logger.info(f"批量创建记录成功: {len(batch)} 条")

        return {'msg': 'success', 'length': len(records)}
    
    def get_existing_ids(self) -> List[str]:
        """
        获取已存在的问题ID列表
        
        Returns:
            List[str]: 已存在的问题ID列表
        """
        client = self._get_client()
        page_token = ""
        ids_list = []
        page_count = 0
        
        logger.info("开始获取已存在的问题ID...")
        while True:
            page_count += 1
            logger.info(f"获取第 {page_count} 页数据...")
            
            request = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .user_id_type("user_id") \
                .page_token(page_token) \
                .page_size(self.page_size) \
                .request_body(SearchAppTableRecordRequestBody.builder()
                    .field_names(["问题ID"])
                    .build()) \
                .build()
        
            resp = client.bitable.v1.app_table_record.search(request)
            if not resp.success():
                logger.error(f"搜索记录失败: {resp.msg}")
                break
                
            json_data = lark.JSON.marshal(resp.data)
            page_token = resp.data.page_token
            
            items = json.loads(json_data).get('items', [])
            problem_ids = []
            for item in items:
                problem_id = item.get('fields', {}).get('问题ID')
                if problem_id:  # 只添加非空的问题ID
                    problem_ids.append(problem_id)
            
            ids_list.extend(problem_ids)
            logger.info(f"获取到 {len(problem_ids)} 个有效问题ID")
            
            if not resp.data.has_more:
                break
                
        logger.info(f"总共获取到 {len(ids_list)} 个问题ID")
        return ids_list

# 全局单例
_bitable_client = None

def get_bitable_client() -> BitableClient:
    """获取多维表格客户端单例"""
    global _bitable_client
    if _bitable_client is None:
        _bitable_client = BitableClient()
    return _bitable_client

# 便捷函数
def create_records(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """创建记录便捷函数"""
    return get_bitable_client().create_records(data)

def get_existing_ids() -> List[str]:
    """获取已存在ID便捷函数"""
    return get_bitable_client().get_existing_ids()

# 从环境变量获取配置
APP_TOKEN = os.getenv("APP_TOKEN")
TABLE_ID = os.getenv("TABLE_ID")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "990"))



def get_existing_ids() -> List[str]:
    """
    获取已存在的问题ID列表
    
    Returns:
        List[str]: 问题ID列表
    """
    client = lark_api.create_client()
    page_token = ""
    ids_list = []
    
    logger.info("开始获取已存在的问题ID...")
    page_count = 0
    
    while True: 
        page_count += 1
        logger.info(f"获取第 {page_count} 页数据...")
        
        # 查询多维表格中的记录
        request = SearchAppTableRecordRequest.builder() \
            .app_token(APP_TOKEN) \
            .table_id(TABLE_ID) \
            .user_id_type("user_id") \
            .page_token(page_token) \
            .page_size(500) \
            .request_body(SearchAppTableRecordRequestBody.builder()
                .field_names(["问题ID"])
                .build()) \
            .build()
    
        try:
            resp = client.bitable.v1.app_table_record.search(request)
            if not resp.success():
                logger.error(f"获取问题ID失败: {resp.msg}")
                return []
                
            # 解析响应数据
            json_data = lark.JSON.marshal(resp.data)
            page_token = resp.data.page_token
            
            items = json.loads(json_data).get('items', [])
            problem_ids = []
            for item in items:
                problem_id = item.get('fields', {}).get('问题ID')
                if problem_id:  # 只添加非空的问题ID
                    problem_ids.append(problem_id)
            
            ids_list.extend(problem_ids)
            logger.info(f"获取到 {len(problem_ids)} 个有效问题ID")
            
            if not resp.data.has_more:
                break
        except Exception as e:
            logger.error(f"查询记录时出错: {e}")
            return []
            
    logger.info(f"总共获取到 {len(ids_list)} 个问题ID")
    return ids_list

def process_item_for_upload(item):
    """
    处理项目用于上传
    
    Args:
        item: 待处理的项目
        
    Returns:
        dict: 处理后的项目
    """
    # 确保字段存在且格式正确
    if not item.get('问题ID'):
        logger.warning("跳过没有问题ID的记录")
        return None
    
    # 检查所有必要字段，确保与飞书表格匹配
    result = {}
    
    # 复制所有已有字段，确保使用飞书多维表格中的字段名
    for k, v in item.items():
        # 跳过空值，防止字段错误
        if v is None or v == "":
            continue
        
        # 确保字段名在飞书表格中存在
        if k not in ['问题ID', 'PVI', 'VIN', 'PVBR', '车型', '车款', '行驶方向', 
                    '问题描述', '等级', '录入工厂', '责任部门-初判', '录入车间', 
                    '录入产线', '录入工位', '录入岗位', '发现人', '记录时间', 
                    '返工工位', '返工人', '备注', '工作时段名称', '班次', '问题图片']:
            logger.debug(f"跳过字段 {k}，可能不在飞书表格中")
            continue
            
        result[k] = v
        
    return result

def create_records(records_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    创建多维表格记录
    
    Args:
        records_data: 记录数据列表
        
    Returns:
        Dict: 创建结果
    """
    if not records_data:
        logger.warning("没有数据需要创建")
        return {'status': '无数据', 'length': 0}
        
    # 处理数据，确保字段匹配
    processed_records = []
    for item in records_data:
        processed_item = process_item_for_upload(item)
        if processed_item:
            processed_records.append(processed_item)
    
    total_length = len(processed_records)
    logger.info(f"总共有 {total_length} 条记录要创建")
    
    if not processed_records:
        return {'status': '处理后无有效数据', 'length': 0}
    
    # 分批处理
    client = lark_api.create_client()
    batches = [processed_records[i:i + BATCH_SIZE] for i in range(0, total_length, BATCH_SIZE)]
    batch_count = 0
    total_created = 0
    
    for batch in batches:
        batch_count += 1
        logger.info(f"处理第 {batch_count}/{len(batches)} 批数据，共 {len(batch)} 条记录")
        
        try:
            # 将记录转换为API所需格式
            batch_records = []
            for data_item in batch:
                # 移除问题ID，因为会作为主键列
                record = AppTableRecord.builder().fields(data_item).build()
                batch_records.append(record)
            
            # 创建请求
            request = BatchCreateAppTableRecordRequest.builder() \
                .app_token(APP_TOKEN) \
                .table_id(TABLE_ID) \
                .user_id_type("user_id") \
                .request_body(BatchCreateAppTableRecordRequestBody.builder()
                    .records(batch_records)
                    .build()) \
                .build()
            
            # 发送请求
            resp = client.bitable.v1.app_table_record.batch_create(request)
            
            # 检查响应
            if resp.success():
                total_created += len(batch)
                logger.info(f"批量创建成功，本批次创建 {len(batch)} 条记录")
            else:
                logger.error(f"批量创建记录失败: {resp.msg}")
        except Exception as e:
            logger.error(f"批量创建记录失败: {e}")
    
    logger.info(f"总共创建 {total_created} 条记录")
    return {'status': '创建成功', 'length': total_created} 