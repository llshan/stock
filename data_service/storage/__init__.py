#!/usr/bin/env python3
"""
存储层模块
提供统一的数据存储接口和多种存储实现
"""

from .base import BaseStorage, StorageError
from .sqlite_storage import SQLiteStorage

# 存储工厂函数
def create_storage(storage_type: str = "sqlite", **kwargs) -> BaseStorage:
    """
    创建存储实例的工厂函数
    
    Args:
        storage_type: 存储类型 ('sqlite', 'postgresql', 等)
        **kwargs: 存储特定的配置参数
        
    Returns:
        存储实例
        
    Raises:
        StorageError: 不支持的存储类型
    """
    storage_map = {
        'sqlite': SQLiteStorage,
        # 可以添加更多存储类型
        # 'postgresql': PostgreSQLStorage,
        # 'redis': RedisStorage,
    }
    
    if storage_type not in storage_map:
        raise StorageError(f"不支持的存储类型: {storage_type}")
    
    storage_class = storage_map[storage_type]
    return storage_class(**kwargs)

# 向后兼容性别名
StockDatabase = SQLiteStorage  # 保持原有接口

__all__ = [
    'BaseStorage',
    'StorageError', 
    'SQLiteStorage',
    'create_storage',
    'StockDatabase'  # 向后兼容
]