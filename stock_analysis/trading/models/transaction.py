#!/usr/bin/env python3
"""
交易记录数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal
from ..utils.decimal_utils import to_quantity_decimal, to_price_decimal, to_financial_decimal


@dataclass
class Transaction:
    """股票交易记录模型"""
    symbol: str                        # 股票代码
    transaction_type: str              # 交易类型: 'BUY', 'SELL'
    quantity: Decimal                  # 交易数量
    price: Decimal                     # 交易价格
    transaction_date: str              # 交易日期（YYYY-MM-DD格式）
    platform: Optional[str] = None     # 交易平台: 'ml', 'schwab', etc.
    external_id: Optional[str] = None  # 外部业务ID，用于去重
    notes: Optional[str] = None        # 备注
    id: Optional[int] = None           # 数据库ID
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)

    def __post_init__(self):
        """数据验证和类型转换"""
        # 确保数值字段为Decimal类型
        if not isinstance(self.quantity, Decimal):
            self.quantity = to_quantity_decimal(self.quantity)
        if not isinstance(self.price, Decimal):
            self.price = to_price_decimal(self.price)
        
        # 业务验证
        if self.transaction_type not in ['BUY', 'SELL']:
            raise ValueError(f"无效的交易类型: {self.transaction_type}")
        
        if self.quantity <= 0:
            raise ValueError(f"交易数量必须大于0: {self.quantity}")
            
        if self.price <= 0:
            raise ValueError(f"交易价格必须大于0: {self.price}")

    @property
    def total_amount(self) -> Decimal:
        """交易总金额"""
        return self.quantity * self.price

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'price': self.price,
            'transaction_date': self.transaction_date,
            'platform': self.platform,
            'external_id': self.external_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """从字典创建实例"""
        # 处理datetime字段
        created_at = None
        updated_at = None
        
        if data.get('created_at'):
            if isinstance(data['created_at'], str):
                created_at = datetime.fromisoformat(data['created_at'])
            else:
                created_at = data['created_at']
                
        if data.get('updated_at'):
            if isinstance(data['updated_at'], str):
                updated_at = datetime.fromisoformat(data['updated_at'])
            else:
                updated_at = data['updated_at']
        
        return cls(
            id=data.get('id'),
            symbol=data['symbol'],
            transaction_type=data['transaction_type'],
            quantity=data['quantity'],
            price=data['price'],
            transaction_date=data['transaction_date'],
            platform=data.get('platform'),
            external_id=data.get('external_id'),
            notes=data.get('notes'),
            created_at=created_at,
            updated_at=updated_at,
        )