#!/usr/bin/env python3
"""
数据质量相关模型
数据质量评估、综合数据等模型定义
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .financial_models import FinancialData
from .price_models import StockData


@dataclass
class DataQuality:
    """数据质量评估模型"""

    stock_data_available: bool
    financial_data_available: bool
    data_completeness: float  # 0.0 - 1.0
    quality_grade: str  # A-F 等级
    issues: List[str] = field(default_factory=list)
    stock_data_completeness: Optional[float] = None
    financial_statements_count: Optional[int] = None
    assessment_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataQuality':
        """从字典创建实例"""
        return cls(**data)

    def is_high_quality(self, threshold: float = 0.8) -> bool:
        """判断是否为高质量数据"""
        return self.data_completeness >= threshold

    def get_quality_score(self) -> int:
        """获取质量分数（0-100）"""
        return int(self.data_completeness * 100)

    def add_issue(self, issue: str) -> None:
        """添加数据质量问题"""
        if issue not in self.issues:
            self.issues.append(issue)

    def has_critical_issues(self) -> bool:
        """检查是否有严重问题"""
        critical_keywords = ['失败', '错误', '不可用', '无法获取']
        return any(keyword in issue for issue in self.issues for keyword in critical_keywords)


@dataclass
class ComprehensiveData:
    """综合股票数据模型（价格 + 财务）"""

    symbol: str
    download_timestamp: str
    stock_data: Optional[StockData]
    financial_data: Optional[FinancialData]
    data_quality: DataQuality
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'symbol': self.symbol,
            'download_timestamp': self.download_timestamp,
            'data_quality': self.data_quality.to_dict(),
            'metadata': self.metadata,
        }

        if self.stock_data:
            result['stock_data'] = self.stock_data.to_dict()
        else:
            result['stock_data'] = {'error': 'Stock data not available'}

        if self.financial_data:
            result['financial_data'] = self.financial_data.to_dict()
        else:
            result['financial_data'] = {'error': 'Financial data not available'}

        if self.error:
            result['error'] = self.error

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComprehensiveData':
        """从字典创建实例"""
        stock_data = None
        financial_data = None

        if 'stock_data' in data and 'error' not in data['stock_data']:
            stock_data = StockData.from_dict(data['stock_data'])

        if 'financial_data' in data and 'error' not in data['financial_data']:
            financial_data = FinancialData.from_dict(data['financial_data'])

        return cls(
            symbol=data['symbol'],
            download_timestamp=data['download_timestamp'],
            stock_data=stock_data,
            financial_data=financial_data,
            data_quality=DataQuality.from_dict(data['data_quality']),
            error=data.get('error'),
            metadata=data.get('metadata', {}),
        )

    def has_stock_data(self) -> bool:
        """检查是否有股票数据"""
        return self.stock_data is not None

    def has_financial_data(self) -> bool:
        """检查是否有财务数据"""
        return self.financial_data is not None

    def is_complete(self) -> bool:
        """检查数据是否完整（同时有价格和财务数据）"""
        return self.has_stock_data() and self.has_financial_data()

    def get_latest_price(self) -> Optional[float]:
        """获取最新价格"""
        if self.stock_data:
            return self.stock_data.get_latest_price()
        return None

    def get_financial_ratios(self) -> Dict[str, Optional[float]]:
        """获取财务比率"""
        if self.financial_data:
            return self.financial_data.calculate_financial_ratios()
        return {}

    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value

    def validate(self) -> List[str]:
        """验证综合数据完整性"""
        issues = []

        if not self.symbol:
            issues.append("股票代码为空")

        # 验证股票数据
        if self.stock_data:
            stock_issues = self.stock_data.validate()
            for issue in stock_issues:
                issues.append(f"股票数据: {issue}")

        # 验证财务数据
        if self.financial_data:
            financial_issues = self.financial_data.validate()
            for issue in financial_issues:
                issues.append(f"财务数据: {issue}")

        # 验证数据质量
        if self.data_quality.has_critical_issues():
            issues.append("数据质量存在严重问题")

        return issues


@dataclass
class DownloadResult:
    """下载结果模型"""

    success: bool
    symbol: str
    data_type: str  # 'stock', 'financial', 'comprehensive'
    data_points: int = 0
    error_message: Optional[str] = None
    download_duration: Optional[float] = None  # 秒
    data_source: Optional[str] = None
    used_strategy: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadResult':
        """从字典创建实例"""
        return cls(**data)

    def is_successful(self) -> bool:
        """检查是否成功"""
        return self.success

    def has_data(self) -> bool:
        """检查是否有数据"""
        return self.success and self.data_points > 0


@dataclass
class BatchDownloadResult:
    """批量下载结果模型"""

    total: int
    successful: int
    failed: int
    results: Dict[str, DownloadResult]
    start_time: str
    end_time: str
    total_duration: float  # 秒
    strategy_usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        # 转换results中的DownloadResult对象
        result['results'] = {k: v.to_dict() for k, v in self.results.items()}
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchDownloadResult':
        """从字典创建实例"""
        results = {}
        for k, v in data.get('results', {}).items():
            results[k] = DownloadResult.from_dict(v)

        return cls(
            total=data['total'],
            successful=data['successful'],
            failed=data['failed'],
            results=results,
            start_time=data['start_time'],
            end_time=data['end_time'],
            total_duration=data['total_duration'],
            strategy_usage=data.get('strategy_usage', {}),
            metadata=data.get('metadata', {}),
        )

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total == 0:
            return 0.0
        return self.successful / self.total

    def get_failed_symbols(self) -> List[str]:
        """获取失败的股票代码列表"""
        return [symbol for symbol, result in self.results.items() if not result.is_successful()]

    def get_successful_symbols(self) -> List[str]:
        """获取成功的股票代码列表"""
        return [symbol for symbol, result in self.results.items() if result.is_successful()]

    def get_summary(self) -> str:
        """获取结果摘要"""
        return (
            f"批量下载完成: {self.successful}/{self.total} 成功，耗时 {self.total_duration:.2f}秒"
        )


# 工具函数
def create_empty_data_quality(symbol: str, issues: Optional[List[str]] = None) -> DataQuality:
    """创建空的数据质量评估"""
    return DataQuality(
        stock_data_available=False,
        financial_data_available=False,
        data_completeness=0.0,
        quality_grade='F - 无数据',
        issues=issues or ['数据不可用'],
        stock_data_completeness=None,
        financial_statements_count=0,
    )


def assess_overall_quality(
    stock_available: bool,
    financial_available: bool,
    stock_completeness: float = 0.0,
    financial_completeness: float = 0.0,
) -> str:
    """
    评估整体数据质量等级

    Args:
        stock_available: 股票数据是否可用
        financial_available: 财务数据是否可用
        stock_completeness: 股票数据完整性
        financial_completeness: 财务数据完整性

    Returns:
        质量等级字符串
    """
    # 计算总体完整性
    total_score: float = 0.0
    if stock_available:
        total_score += 0.6 * stock_completeness
    if financial_available:
        total_score += 0.4 * financial_completeness

    # 分级评定
    if total_score >= 0.9:
        return 'A - 优秀'
    elif total_score >= 0.7:
        return 'B - 良好'
    elif total_score >= 0.5:
        return 'C - 一般'
    elif total_score >= 0.3:
        return 'D - 较差'
    else:
        return 'F - 很差'


def create_download_result(
    success: bool,
    symbol: str,
    data_type: str,
    data_points: int = 0,
    error_message: Optional[str] = None,
    **kwargs: Any,
) -> DownloadResult:
    """创建下载结果的便捷函数"""
    return DownloadResult(
        success=success,
        symbol=symbol,
        data_type=data_type,
        data_points=data_points,
        error_message=error_message,
        **kwargs,
    )
