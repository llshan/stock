#!/usr/bin/env python3
"""
金融计算的Decimal工具函数
处理float与Decimal之间的转换，保证精度
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


def to_decimal(value: Union[float, int, str, Decimal], precision: int = 4) -> Decimal:
    """
    将各种数值类型安全转换为Decimal
    
    Args:
        value: 要转换的值
        precision: 小数位精度，默认4位（适合股价）
        
    Returns:
        Decimal: 转换后的Decimal值
    """
    if isinstance(value, Decimal):
        return value
    
    if isinstance(value, (int, str)):
        return Decimal(str(value))
    
    if isinstance(value, float):
        # 避免float精度问题，先转为字符串再转Decimal
        return Decimal(f"{value:.{precision + 2}f}").quantize(
            Decimal('0.' + '0' * precision), 
            rounding=ROUND_HALF_UP
        )
    
    raise ValueError(f"无法将类型 {type(value)} 转换为Decimal")


def to_financial_decimal(value: Union[float, int, str, Decimal]) -> Decimal:
    """
    转换为金融精度的Decimal（2位小数，适合金额）
    
    Args:
        value: 要转换的值
        
    Returns:
        Decimal: 金融精度的Decimal值
    """
    return to_decimal(value, precision=2)


def to_quantity_decimal(value: Union[float, int, str, Decimal]) -> Decimal:
    """
    转换为数量精度的Decimal（4位小数，适合股数）
    
    Args:
        value: 要转换的值
        
    Returns:
        Decimal: 数量精度的Decimal值
    """
    return to_decimal(value, precision=4)


def to_price_decimal(value: Union[float, int, str, Decimal]) -> Decimal:
    """
    转换为价格精度的Decimal（4位小数，适合股价）
    
    Args:
        value: 要转换的值
        
    Returns:
        Decimal: 价格精度的Decimal值
    """
    return to_decimal(value, precision=4)


def decimal_to_float(value: Decimal) -> float:
    """
    将Decimal转换为float（仅在必要时使用，如数据库存储）
    
    Args:
        value: Decimal值
        
    Returns:
        float: 转换后的float值
    """
    return float(value)


def format_decimal(value: Decimal, precision: int = 2) -> str:
    """
    格式化Decimal为字符串显示
    
    Args:
        value: Decimal值
        precision: 显示精度
        
    Returns:
        str: 格式化后的字符串
    """
    format_str = f"{{:.{precision}f}}"
    return format_str.format(value)


def format_financial_amount(value: Decimal) -> str:
    """
    格式化金额显示（2位小数）
    
    Args:
        value: Decimal金额
        
    Returns:
        str: 格式化后的金额字符串
    """
    return format_decimal(value, precision=2)


def format_quantity(value: Decimal) -> str:
    """
    格式化数量显示（4位小数）
    
    Args:
        value: Decimal数量
        
    Returns:
        str: 格式化后的数量字符串
    """
    return format_decimal(value, precision=4)


def format_price(value: Decimal) -> str:
    """
    格式化价格显示（4位小数）
    
    Args:
        value: Decimal价格
        
    Returns:
        str: 格式化后的价格字符串
    """
    return format_decimal(value, precision=4)


# 常用的精度常量
FINANCIAL_PRECISION = Decimal('0.01')      # 金额精度：2位小数
QUANTITY_PRECISION = Decimal('0.0001')     # 数量精度：4位小数  
PRICE_PRECISION = Decimal('0.0001')        # 价格精度：4位小数
PERCENTAGE_PRECISION = Decimal('0.0001')   # 百分比精度：4位小数