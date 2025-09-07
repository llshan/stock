#!/usr/bin/env python3
"""
基础数据下载器抽象类
封装通用的重试机制和日志功能
"""

from abc import ABC, abstractmethod
import time
import logging
from typing import Callable, Any


class BaseDownloader(ABC):
    """基础下载器抽象类，提供通用的重试和日志功能"""
    
    def __init__(self, max_retries: int = 3, base_delay: int = 30):
        """
        初始化基础下载器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
    
    def _retry_with_backoff(self, func: Callable, symbol: str) -> Any:
        """
        带退避策略的重试机制
        
        Args:
            func: 要执行的函数
            symbol: 股票代码（用于日志）
            
        Returns:
            函数执行结果
        """
        for attempt in range(self.max_retries):
            try:
                return func()
            except Exception as e:
                if self._is_api_error_retryable(e) and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # 指数退避
                    self.logger.warning(f"⏰ {symbol} API请求失败，等待 {delay} 秒后重试 (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    # 非可重试错误或已达最大重试次数
                    raise e
        
        raise Exception(f"{symbol} 重试 {self.max_retries} 次后仍然失败")
    
    def _is_api_error_retryable(self, error: Exception) -> bool:
        """
        判断API错误是否可重试
        
        Args:
            error: 异常对象
            
        Returns:
            是否可重试
        """
        error_msg = str(error).lower()
        retryable_patterns = [
            "429",
            "too many requests",
            "rate limit",
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable"
        ]
        return any(pattern in error_msg for pattern in retryable_patterns)