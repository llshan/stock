"""
数据下载器模块
包含所有数据源的下载器实现
"""

from .base import BaseDownloader
from .stooq import StooqDataDownloader

__all__ = ['BaseDownloader', 'StooqDataDownloader']
