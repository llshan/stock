#!/usr/bin/env python3
"""
数据服务层（DataService）

职责：
- 协调下载器与存储层，提供统一的数据获取/存储入口
- 封装增量下载、批量下载与数据质量评估流程

说明：
- 模块侧重于数据流转（下载→规范化→存储）
- 依赖 storage 与 downloaders 子模块
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from .storage import create_storage, SQLiteStorage
from .downloaders.yfinance import YFinanceDataDownloader
from .downloaders.hybrid import HybridDataDownloader
from .models import (
    StockData, FinancialData, ComprehensiveData, DataQuality,
    PriceData, SummaryStats, BasicInfo
)
from .quality import assess_data_quality


class DataService:
    """
    数据服务类
    负责协调下载器和数据库操作，提供统一的数据管理接口
    """
    
    def __init__(self, storage=None):
        """
        初始化数据服务
        
        Args:
            storage: 存储实例，默认使用SQLite
            注：价格数据一律走 Hybrid 下载器；财务数据走 yfinance
        """
        self.storage = storage or create_storage('sqlite')
        self.hybrid = HybridDataDownloader(self.storage)
        # 财务数据下载仍使用 yfinance 下载器
        self.yfinance_downloader = YFinanceDataDownloader()
    
        self.logger = logging.getLogger(__name__)

    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """
        获取股票的最后更新日期
        
        Args:
            symbol: 股票代码
            
        Returns:
            最后更新日期，如果没有记录则返回None
        """
        try:
            last_date = self.storage.get_last_update_date(symbol)
            if last_date:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                next_date = last_dt + timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            return None
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 最后更新日期失败: {str(e)}")
            return None
    
    def download_stock_data(self, symbol: str, start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        下载股票价格数据（统一走 Hybrid 下载器）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（None 则由 Hybrid 内部自动计算增量）
            
        Returns:
            结果字典（由 Hybrid 返回，并已入库）
        """
        try:
            # 确保股票记录存在（必须先于价格数据）
            self._ensure_stock_record(symbol)
            return self.hybrid.download_stock_data(symbol, start_date or "2000-01-01")
        except Exception as e:
            error_msg = f"通过数据服务(混合)下载 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'symbol': symbol}
    
    def download_financial_data(self, symbol: str, use_retry: bool = True) -> Union[FinancialData, Dict[str, str]]:
        """
        下载财务数据
        
        Args:
            symbol: 股票代码
            use_retry: 是否使用重试机制
            
        Returns:
            财务数据或错误信息
        """
        try:
            return self.yfinance_downloader.download_financial_data(symbol, use_retry)
        except Exception as e:
            error_msg = f"通过数据服务下载 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def download_and_store_stock_data(self, symbol: str, start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        下载并存储股票数据（统一走 Hybrid，内部已入库）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            
        Returns:
            操作结果
        """
        try:
            self.logger.info(f"📈 开始下载并存储 {symbol} 股票数据（Hybrid）")
            # 确保股票记录存在（必须先于价格数据）
            self._ensure_stock_record(symbol)
            return self.hybrid.download_stock_data(symbol, start_date or "2000-01-01")
        except Exception as e:
            error_msg = f"下载并存储 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'symbol': symbol}
    
    def download_and_store_comprehensive_data(self, symbol: str, start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        下载并存储综合数据（价格+财务）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            
        Returns:
            操作结果
        """
        try:
            # 价格数据：统一走 Hybrid（内部已入库）
            # 为确保价格入库顺序正确，先确保股票记录存在
            self._ensure_stock_record(symbol)
            stock_data = self.download_stock_data(symbol, start_date)
            # 财务数据：走 yfinance
            financial_data = self.download_financial_data(symbol, use_retry=True)
            
            # 评估数据质量
            # 使用集中化的质量评估逻辑
            data_quality = assess_data_quality(
                stock_data,
                financial_data,
                start_date or "2000-01-01"
            )
            
            # 创建综合数据对象
            stock_data_obj = stock_data if isinstance(stock_data, StockData) else None
            financial_data_obj = financial_data if isinstance(financial_data, FinancialData) else None
            
            comprehensive_data = ComprehensiveData(
                symbol=symbol,
                download_timestamp=datetime.now().isoformat(),
                stock_data=stock_data_obj,
                financial_data=financial_data_obj,
                data_quality=data_quality
            )
            
            # 存储到存储层
            # stock_data 已在 Hybrid 中入库，这里只入库财务与质量
            if comprehensive_data.financial_data:
                self.storage.store_financial_data(symbol, comprehensive_data.financial_data)
            self.storage.store_data_quality(symbol, comprehensive_data.data_quality)
            
            # 计算成功状态
            success_count = 0
            if stock_data_obj:
                success_count += 1
            if financial_data_obj:
                success_count += 1
                
            self.logger.info(f"✅ {symbol} 综合数据处理完成")
            
            return {
                'success': True,
                'symbol': symbol,
                'stock_data_success': stock_data_obj is not None,
                'financial_data_success': financial_data_obj is not None,
                'data_quality_grade': data_quality.quality_grade,
                'comprehensive_data': comprehensive_data
            }
            
        except Exception as e:
            error_msg = f"下载并存储 {symbol} 综合数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'symbol': symbol
            }
    
    def batch_download_and_store(self, symbols: List[str], start_date: Optional[str] = None,
                               include_financial: bool = True) -> Dict[str, Dict]:
        """
        批量下载并存储数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            include_financial: 是否包含财务数据
            
        Returns:
            批量操作结果
        """
        results = {}
        total = len(symbols)
        
        data_type = "综合数据" if include_financial else "股票数据"
        self.logger.info(f"🎯 开始批量处理 {total} 个股票的{data_type}")
        
        # 批量路径：逐只处理（下载器不再提供批量接口）

        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                if include_financial:
                    result = self.download_and_store_comprehensive_data(symbol, start_date)
                else:
                    result = self.download_and_store_stock_data(symbol, start_date)
                
                results[symbol] = result
                
                # 添加延迟避免API限制
                if i < total - 1:  # 最后一个不需要延迟
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"处理 {symbol} 时出错: {str(e)}")
                results[symbol] = {
                    'success': False,
                    'error': str(e),
                    'symbol': symbol
                }
        
        # 统计结果
        successful = len([r for r in results.values() if r.get('success', False)])
        failed = total - successful
        
        self.logger.info(f"✅ 批量处理完成，成功: {successful}/{total}")
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    # 质量评估逻辑已集中到 quality.assess_data_quality，无需本地额外包装
    
    def get_existing_symbols(self) -> List[str]:
        """获取数据库中已存在的股票代码列表"""
        return self.storage.get_existing_symbols()
    
    def close(self):
        """关闭数据服务（关闭数据库连接）"""
        if self.storage:
            self.storage.close()

    # 内部工具
    def _ensure_stock_record(self, symbol: str):
        """确保股票记录存在，直接创建空记录以满足外键约束。
        
        仅为价格数据存储创建必要的stocks表记录，不强制下载财务数据。
        """
        try:
            existing = set(self.get_existing_symbols())
            if symbol in existing:
                return
        except Exception:
            # 如果无法读取现有列表，继续创建记录
            pass

        # 直接创建空的股票记录，避免不必要的财务数据下载
        try:
            self.storage._ensure_stock_exists(symbol)
            self.logger.info(f"🪪 已创建空股票记录: {symbol}")
        except Exception as e:
            self.logger.error(f"❌ 创建股票记录失败 {symbol}: {e}")
