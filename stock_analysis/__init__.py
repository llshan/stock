"""
Stock Analysis System - 股票分析系统

一个现代化的股票数据获取、存储和技术分析系统。

主要模块:
- data: 数据获取和存储
- analysis: 技术分析和财务分析
- cli: 命令行工具
- utils: 工具函数
"""

__version__ = "1.0.0"
__author__ = "Jiulong Shan"

from .analysis import AnalysisService
from .data import DataService

__all__ = ["DataService", "AnalysisService"]
