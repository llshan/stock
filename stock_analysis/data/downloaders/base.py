#!/usr/bin/env python3
"""
基础数据下载器抽象类
封装通用的重试机制和日志功能
"""

import logging
import time
from abc import ABC
from typing import Any, Callable
from typing import Optional

import requests
from requests import exceptions as req_exc


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
                    delay = self.base_delay * (2**attempt)  # 指数退避
                    self.logger.warning(
                        f"⏰ {symbol} API请求失败，等待 {delay} 秒后重试 (尝试 {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    # 非可重试错误或已达最大重试次数
                    if isinstance(e, DownloaderError):
                        raise
                    raise DownloaderError(str(e))

        raise DownloaderError(f"{symbol} 重试 {self.max_retries} 次后仍然失败")

    def _is_api_error_retryable(self, error: Exception) -> bool:
        """判断是否属于“必要的可重试”错误。

        仅保留最必要的几类：
        - HTTP 429（限流）
        - HTTP 5xx 常见临时错误：502/503/504
        - 超时与连接错误（requests Timeout/ConnectionError）
        """
        # requests 超时/连接错误
        if isinstance(error, (req_exc.Timeout, req_exc.ConnectionError)):
            return True

        # 带有 HTTP 响应码的错误（如 requests.HTTPError）
        resp = getattr(error, "response", None)
        try:
            status = int(getattr(resp, "status_code", 0)) if resp is not None else 0
        except Exception:
            status = 0
        if status in (429, 502, 503, 504):
            return True

        # 字符串兜底（仅必要的几项，避免过度匹配）
        msg = str(error).lower()
        substrings = ("429", "too many requests", "rate limit", "timeout", "timed out")
        if any(s in msg for s in substrings):
            return True

        return False


class DownloaderError(Exception):
    """下载器错误，统一由下载器抛出，服务层捕获并包装为 DownloadResult"""
    pass
