#!/usr/bin/env python3
"""
财务相关数据模型
财务报表、基本信息等财务数据的模型定义
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base_models import BaseDataModel, BasicInfo


@dataclass
class FinancialStatement:
    """财务报表数据模型"""
    statement_type: str  # 报表类型：income_statement, balance_sheet, cash_flow
    periods: List[str]   # 报告期列表
    items: Dict[str, List[Optional[float]]]  # 财务项目及其值
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialStatement':
        """从字典创建实例"""
        return cls(**data)
    
    def get_item_value(self, item_name: str, period: str = None) -> Optional[float]:
        """
        获取指定项目的值
        
        Args:
            item_name: 财务项目名称
            period: 报告期，None表示最新期
            
        Returns:
            财务项目值
        """
        if item_name not in self.items:
            return None
        
        values = self.items[item_name]
        if not values:
            return None
        
        if period is None:
            # 返回最新期的值
            return values[0] if values else None
        
        # 查找指定期间的值
        try:
            period_index = self.periods.index(period)
            if period_index < len(values):
                return values[period_index]
        except ValueError:
            pass
        
        return None
    
    def get_latest_items(self) -> Dict[str, Optional[float]]:
        """获取最新期的所有项目值"""
        result = {}
        for item_name, values in self.items.items():
            result[item_name] = values[0] if values else None
        return result
    
    def validate(self) -> List[str]:
        """验证财务报表数据完整性"""
        issues = []
        
        if not self.statement_type:
            issues.append("报表类型为空")
        
        if not self.periods:
            issues.append("没有报告期数据")
        
        if not self.items:
            issues.append("没有财务项目数据")
        
        # 检查数据一致性
        period_count = len(self.periods)
        for item_name, values in self.items.items():
            if len(values) != period_count:
                issues.append(f"项目 {item_name} 的数据长度与报告期不匹配")
        
        return issues


@dataclass
class FinancialData:
    """完整财务数据模型"""
    symbol: str
    basic_info: BasicInfo
    financial_statements: Dict[str, FinancialStatement]  # 报表类型 -> 财务报表
    downloaded_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'symbol': self.symbol,
            'basic_info': self.basic_info.to_dict(),
            'financial_statements': {},
            'downloaded_at': self.downloaded_at
        }
        
        for key, statement in self.financial_statements.items():
            result['financial_statements'][key] = statement.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialData':
        """从字典创建实例"""
        basic_info = BasicInfo.from_dict(data.get('basic_info', {}))
        statements = {}
        
        for key, stmt_data in data.get('financial_statements', {}).items():
            if 'error' not in stmt_data:
                statements[key] = FinancialStatement.from_dict(stmt_data)
        
        return cls(
            symbol=data['symbol'],
            basic_info=basic_info,
            financial_statements=statements,
            downloaded_at=data['downloaded_at']
        )
    
    def get_statement(self, statement_type: str) -> Optional[FinancialStatement]:
        """获取指定类型的财务报表"""
        return self.financial_statements.get(statement_type)
    
    def get_income_statement(self) -> Optional[FinancialStatement]:
        """获取损益表"""
        return self.get_statement('income_statement')
    
    def get_balance_sheet(self) -> Optional[FinancialStatement]:
        """获取资产负债表"""
        return self.get_statement('balance_sheet')
    
    def get_cash_flow(self) -> Optional[FinancialStatement]:
        """获取现金流量表"""
        return self.get_statement('cash_flow')
    
    def calculate_financial_ratios(self) -> Dict[str, Optional[float]]:
        """
        计算常用财务比率
        
        Returns:
            财务比率字典
        """
        ratios = {}
        
        income_stmt = self.get_income_statement()
        balance_sheet = self.get_balance_sheet()
        
        if income_stmt and balance_sheet:
            # 获取关键财务数据
            revenue = income_stmt.get_item_value('Total Revenue')
            net_income = income_stmt.get_item_value('Net Income')
            total_assets = balance_sheet.get_item_value('Total Assets')
            total_equity = balance_sheet.get_item_value('Total Stockholder Equity')
            total_debt = balance_sheet.get_item_value('Total Debt')
            current_assets = balance_sheet.get_item_value('Current Assets')
            current_liabilities = balance_sheet.get_item_value('Current Liabilities')
            
            # 计算比率
            if revenue and revenue != 0:
                ratios['net_profit_margin'] = (net_income / revenue * 100) if net_income else None
            
            if total_assets and total_assets != 0:
                ratios['roa'] = (net_income / total_assets * 100) if net_income else None
                ratios['debt_to_assets'] = (total_debt / total_assets * 100) if total_debt else None
            
            if total_equity and total_equity != 0:
                ratios['roe'] = (net_income / total_equity * 100) if net_income else None
                ratios['debt_to_equity'] = (total_debt / total_equity) if total_debt else None
            
            if current_liabilities and current_liabilities != 0:
                ratios['current_ratio'] = (current_assets / current_liabilities) if current_assets else None
        
        return ratios
    
    def validate(self) -> List[str]:
        """验证财务数据完整性"""
        issues = []
        
        if not self.symbol:
            issues.append("股票代码为空")
        
        if not self.financial_statements:
            issues.append("没有财务报表数据")
        
        # 验证各个报表
        for stmt_type, statement in self.financial_statements.items():
            stmt_issues = statement.validate()
            for issue in stmt_issues:
                issues.append(f"{stmt_type}: {issue}")
        
        return issues


# 工具函数
def create_empty_basic_info() -> BasicInfo:
    """创建空的基本信息"""
    return BasicInfo(
        company_name="", sector="", industry="",
        market_cap=0, employees=0, description=""
    )


def create_empty_financial_statement(statement_type: str) -> FinancialStatement:
    """创建空的财务报表"""
    return FinancialStatement(
        statement_type=statement_type,
        periods=[],
        items={}
    )


def create_empty_financial_data(symbol: str, error_msg: str = None) -> Dict[str, Any]:
    """创建包含错误信息的空财务数据"""
    return {
        'symbol': symbol,
        'basic_info': create_empty_basic_info().to_dict(),
        'financial_statements': {},
        'downloaded_at': datetime.now().isoformat(),
        'error': error_msg or '财务数据不可用'
    }


def merge_financial_statements(old_stmt: FinancialStatement, new_stmt: FinancialStatement) -> FinancialStatement:
    """
    合并财务报表（用于数据更新）
    
    Args:
        old_stmt: 原有报表
        new_stmt: 新报表
        
    Returns:
        合并后的报表
    """
    # 合并报告期（去重并保持顺序）
    periods = new_stmt.periods.copy()
    for period in old_stmt.periods:
        if period not in periods:
            periods.append(period)
    
    # 合并财务项目
    items = {}
    all_items = set(old_stmt.items.keys()) | set(new_stmt.items.keys())
    
    for item_name in all_items:
        old_values = old_stmt.items.get(item_name, [])
        new_values = new_stmt.items.get(item_name, [])
        
        # 创建合并后的值列表
        merged_values = []
        for period in periods:
            value = None
            
            # 优先使用新数据
            if period in new_stmt.periods:
                idx = new_stmt.periods.index(period)
                if idx < len(new_values):
                    value = new_values[idx]
            
            # 如果新数据没有，使用旧数据
            if value is None and period in old_stmt.periods:
                idx = old_stmt.periods.index(period)
                if idx < len(old_values):
                    value = old_values[idx]
            
            merged_values.append(value)
        
        items[item_name] = merged_values
    
    return FinancialStatement(
        statement_type=new_stmt.statement_type,
        periods=periods,
        items=items
    )