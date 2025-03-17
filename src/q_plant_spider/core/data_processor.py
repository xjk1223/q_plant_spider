"""
数据处理模块，负责处理和转换数据
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 字段映射
KEY_MAPPING = {
    'id': '问题ID',
    'pvi': 'PVI',
    'vin': 'VIN',
    'pvbr': 'PVBR',
    'modelTypeCode': '车型',
    'modeYear': '车款',
    'driveDirection': '行驶方向',
    'issueDesc': '问题描述',
    'issueLevel': '等级',
    'factoryCode': '录入工厂',
    'responsibilityDeptName': '责任部门-初判',
    'workshopName': '录入车间',
    'prodlineName': '录入产线', 
    'stationNo': '录入工位',
    'findPostName': '录入岗位',
    'createUser': '发现人',
    'reportTime': '记录时间',
    'repairStationName': '返工工位',
    'repairUser': '返工人',
    'issueRemark': '备注',
    'shift': '工作时段名称',
    'classes': '班次',
    'otherDesc': '问题补充'
}

class DataProcessor:
    """数据处理器，处理数据字段转换和规范化"""
    
    @staticmethod
    def process_item_fields(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理数据项的字段
        
        Args:
            item: 原始数据项
            
        Returns:
            Dict: 处理后的数据项
        """
        # 创建副本避免修改原始数据
        processed_item = item.copy()
        
        # 合并问题描述和问题补充
        issue_desc = processed_item.get('问题描述', '')
        other_desc = processed_item.get('问题补充', '')
        if other_desc:
            processed_item['问题描述'] = f"{issue_desc}({other_desc})" if issue_desc else other_desc
        
        # 删除单独的问题补充字段
        if '问题补充' in processed_item:
            del processed_item['问题补充']
            
        # 处理发现人字段
        if processed_item.get('发现人'):
            processed_item['发现人'] = [{'id': processed_item['发现人']}]
        else:
            processed_item['发现人'] = None
            
        # 处理返工人字段
        if processed_item.get('返工人'):
            processed_item['返工人'] = [{'id': processed_item['返工人']}]
        else:
            processed_item['返工人'] = None
            
        return processed_item
    
    @staticmethod
    def standardize_field_names(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化字段名称
        
        Args:
            raw_data: 原始数据
            
        Returns:
            Dict: 标准化后的数据
        """
        result = {}
        for k, v in raw_data.items():
            # 使用映射表转换字段名
            field_name = KEY_MAPPING.get(k, k)
            result[field_name] = v
        return result
    
    @staticmethod
    def filter_new_data(data_list, existing_ids):
        """
        过滤出新数据
        
        Args:
            data_list: 原始数据列表
            existing_ids: 已存在的ID列表
            
        Returns:
            List[Dict]: 新数据列表
        """
        # 确保我们收到了正确的数据格式
        if not data_list or not isinstance(data_list, list):
            logger.warning(f"数据列表为空或格式错误: {type(data_list)}")
            return []
        
        new_data = []
        
        # 转换existing_ids为集合以提高查找效率
        existing_ids_set = set(existing_ids)
        
        # 记录所有ID和新ID的列表，用于调试
        all_ids = []
        new_ids = []
        
        for item in data_list:
            item_id = item.get('问题ID')
            if item_id:
                all_ids.append(item_id)
                if item_id not in existing_ids_set:
                    new_data.append(item)
                    new_ids.append(item_id)
        
        # 详细日志记录用于排查问题
        logger.info(f"数据处理详情:")
        logger.info(f"- 原始数据总数: {len(data_list)}条")
        logger.info(f"- 已存在ID总数: {len(existing_ids)}个")
        logger.info(f"- 筛选出的新数据: {len(new_data)}条")
        if new_ids:
            logger.info(f"- 新数据ID: {new_ids}")
        
        return new_data
    
    @staticmethod
    def process_data_batch(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理数据
        
        Args:
            data_list: 原始数据列表
            
        Returns:
            List[Dict]: 处理后的数据列表
        """
        processed_data = []
        for item in data_list:
            # 标准化字段名
            std_item = DataProcessor.standardize_field_names(item)
            # 处理字段
            processed_item = DataProcessor.process_item_fields(std_item)
            processed_data.append(processed_item)
            
        return processed_data

# 便捷函数
def process_item_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个数据项字段便捷函数"""
    return DataProcessor.process_item_fields(item)

def standardize_field_names(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """标准化字段名称便捷函数"""
    return DataProcessor.standardize_field_names(raw_data)

def filter_new_data(data_list, existing_ids):
    """过滤新数据便捷函数"""
    return DataProcessor.filter_new_data(data_list, existing_ids)

def process_data_batch(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理数据便捷函数"""
    return DataProcessor.process_data_batch(data_list) 