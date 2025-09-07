#!/usr/bin/env python3
"""
数据服务类
协调下载器和数据库之间的操作，负责数据流程管理
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Type
from Stock.data_service.database import StockDatabase
from Stock.data_service.yfinance_downloader import YFinanceDataDownloader
from Stock.data_service.stooq_downloader import StooqDataDownloader
from Stock.data_service.models import (
    StockData, FinancialData, ComprehensiveData, DataQuality,
    PriceData, SummaryStats, BasicInfo
)


class DataService:
    """
    数据服务类
    负责协调下载器和数据库操作，提供统一的数据管理接口
    """
    
    def __init__(self, database: StockDatabase, 
                 stock_downloader: Optional[YFinanceDataDownloader] = None,
                 stooq_downloader: Optional[StooqDataDownloader] = None):
        """
        初始化数据服务
        
        Args:
            database: 数据库实例
            stock_downloader: 股票数据下载器
            stooq_downloader: Stooq数据下载器
        """
        self.database = database
        self.stock_downloader = stock_downloader or YFinanceDataDownloader()
        self.stooq_downloader = stooq_downloader or StooqDataDownloader()
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
            # 查询数据库中该股票的最新日期
            query = "SELECT MAX(date) FROM stock_prices WHERE symbol = ?"
            result = self.database.cursor.execute(query, (symbol,)).fetchone()
            
            if result and result[0]:
                last_date = datetime.strptime(result[0], '%Y-%m-%d')
                # 从最后一天的下一天开始下载，避免重复
                next_date = last_date + timedelta(days=1)
                return next_date.strftime('%Y-%m-%d')
            
            return None
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 最后更新日期失败: {str(e)}")
            return None
    
    def download_stock_data(self, symbol: str, start_date: str = None, 
                          incremental: bool = True, use_retry: bool = True,
                          downloader_type: str = "yfinance") -> Union[StockData, Dict[str, str]]:
        """
        下载股票数据（支持增量下载）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            incremental: 是否启用增量下载
            use_retry: 是否使用重试机制
            downloader_type: 下载器类型 ("yfinance" 或 "stooq")
            
        Returns:
            股票数据或错误信息
        """
        try:
            # 确定实际的开始日期
            actual_start_date = start_date
            if incremental and start_date is None:
                last_update = self.get_last_update_date(symbol)
                if last_update:
                    actual_start_date = last_update
                    self.logger.info(f"🔄 {symbol} 启用增量下载，从 {actual_start_date} 开始")
                else:
                    actual_start_date = "2020-01-01"  # 默认开始日期
            elif start_date is None:
                actual_start_date = "2020-01-01"  # 默认开始日期
            
            # 选择下载器并下载数据
            if downloader_type == "stooq":
                data = self.stooq_downloader.download_stock_data(
                    symbol, actual_start_date, None
                )
            else:
                data = self.stock_downloader.download_stock_data(
                    symbol, actual_start_date, incremental=incremental, use_retry=use_retry
                )
            
            return data
            
        except Exception as e:
            error_msg = f"通过数据服务下载 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
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
            return self.stock_downloader.download_financial_data(symbol, use_retry)
        except Exception as e:
            error_msg = f"通过数据服务下载 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def download_and_store_stock_data(self, symbol: str, start_date: str = None,
                                    incremental: bool = True, use_retry: bool = True,
                                    downloader_type: str = "yfinance") -> Dict[str, any]:
        """
        下载并存储股票数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            incremental: 是否启用增量下载
            use_retry: 是否使用重试机制
            downloader_type: 下载器类型
            
        Returns:
            操作结果
        """
        try:
            self.logger.info(f"📈 开始下载并存储 {symbol} 股票数据")
            
            # 下载数据
            stock_data = self.download_stock_data(
                symbol, start_date, incremental, use_retry, downloader_type
            )
            
            # 检查下载结果
            if isinstance(stock_data, dict) and 'error' in stock_data:
                return {
                    'success': False,
                    'error': stock_data['error'],
                    'symbol': symbol
                }
            
            # 存储数据到数据库
            if isinstance(stock_data, StockData):
                if stock_data.data_points > 0:
                    self.database.store_stock_prices(
                        symbol, stock_data.price_data, incremental=incremental
                    )
                    
                    # 记录成功日志
                    self.database.store_download_log(
                        symbol, 'stock_prices', 'success', stock_data.data_points
                    )
                    
                    self.logger.info(f"✅ {symbol} 股票数据存储完成: {stock_data.data_points} 个数据点")
                    return {
                        'success': True,
                        'symbol': symbol,
                        'data_points': stock_data.data_points,
                        'incremental': incremental
                    }
                elif stock_data.no_new_data:
                    self.logger.info(f"📊 {symbol} 数据已是最新，无需更新")
                    return {
                        'success': True,
                        'symbol': symbol,
                        'data_points': 0,
                        'no_new_data': True
                    }
            
            return {
                'success': False,
                'error': f'未知数据格式: {type(stock_data)}',
                'symbol': symbol
            }
            
        except Exception as e:
            error_msg = f"下载并存储 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            
            # 记录失败日志
            self.database.store_download_log(
                symbol, 'stock_prices', 'failed', 0, error_msg
            )
            
            return {
                'success': False,
                'error': error_msg,
                'symbol': symbol
            }
    
    def download_and_store_comprehensive_data(self, symbol: str, start_date: str = None,
                                            incremental: bool = True, use_retry: bool = True,
                                            downloader_type: str = "yfinance") -> Dict[str, any]:
        """
        下载并存储综合数据（价格+财务）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            incremental: 是否启用增量下载
            use_retry: 是否使用重试机制
            downloader_type: 下载器类型
            
        Returns:
            操作结果
        """
        try:
            retry_text = "（启用重试）" if use_retry else ""
            self.logger.info(f"🚀 开始下载并存储 {symbol} 的综合数据{'（增量模式）' if incremental else '（全量模式）'}{retry_text}")
            
            # 下载股票数据
            stock_data = self.download_stock_data(
                symbol, start_date, incremental, use_retry, downloader_type
            )
            
            # 下载财务数据
            financial_data = self.download_financial_data(symbol, use_retry)
            
            # 评估数据质量
            data_quality = self._assess_data_quality(stock_data, financial_data)
            
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
            
            # 存储到数据库
            self.database.store_comprehensive_data(symbol, comprehensive_data)
            
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
    
    def batch_download_and_store(self, symbols: List[str], start_date: str = None,
                               incremental: bool = True, use_retry: bool = True,
                               downloader_type: str = "yfinance", 
                               include_financial: bool = True) -> Dict[str, Dict]:
        """
        批量下载并存储数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            incremental: 是否启用增量下载
            use_retry: 是否使用重试机制
            downloader_type: 下载器类型
            include_financial: 是否包含财务数据
            
        Returns:
            批量操作结果
        """
        results = {}
        total = len(symbols)
        
        mode_text = "增量下载" if incremental else "全量下载"
        retry_text = "（启用重试）" if use_retry else ""
        data_type = "综合数据" if include_financial else "股票数据"
        
        self.logger.info(f"🎯 开始批量{mode_text} {total} 个股票的{data_type}{retry_text}")
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                if include_financial:
                    result = self.download_and_store_comprehensive_data(
                        symbol, start_date, incremental, use_retry, downloader_type
                    )
                else:
                    result = self.download_and_store_stock_data(
                        symbol, start_date, incremental, use_retry, downloader_type
                    )
                
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
    
    def _assess_data_quality(self, stock_data: Union[StockData, Dict], 
                           financial_data: Union[FinancialData, Dict]) -> DataQuality:
        """
        评估数据质量
        
        Args:
            stock_data: 股票数据
            financial_data: 财务数据
            
        Returns:
            数据质量评估结果
        """
        # 检查数据可用性
        stock_available = False
        financial_available = False
        issues = []
        
        if isinstance(stock_data, StockData):
            stock_available = True
        elif isinstance(stock_data, dict):
            stock_available = 'error' not in stock_data
        
        if isinstance(financial_data, FinancialData):
            financial_available = True
        elif isinstance(financial_data, dict):
            financial_available = 'error' not in financial_data
        
        # 评估股票数据质量
        stock_data_completeness = None
        if stock_available:
            if isinstance(stock_data, StockData):
                data_points = stock_data.data_points
            else:
                data_points = stock_data.get('data_points', 0)
            start_date = "2020-01-01"  # 默认开始日期
            expected_points = (datetime.now() - datetime.strptime(start_date, '%Y-%m-%d')).days
            stock_data_completeness = min(1.0, data_points / (expected_points * 0.7))  # 考虑周末
        else:
            issues.append('股票价格数据不可用')
        
        # 评估财务数据质量
        financial_statements_count = 0
        if financial_available:
            if isinstance(financial_data, FinancialData):
                statements = financial_data.financial_statements
            else:
                statements = financial_data.get('financial_statements', {})
            financial_statements_count = len(statements)
            if len(statements) < 3:
                issues.append('财务报表数据不完整')
        else:
            issues.append('财务数据不可用')
        
        # 总体完整性评分
        completeness_score = 0
        if stock_available:
            completeness_score += 0.6
        if financial_available:
            completeness_score += 0.4
        
        quality_grade = self._get_quality_grade(completeness_score)
        
        return DataQuality(
            stock_data_available=stock_available,
            financial_data_available=financial_available,
            data_completeness=completeness_score,
            quality_grade=quality_grade,
            issues=issues,
            stock_data_completeness=stock_data_completeness,
            financial_statements_count=financial_statements_count
        )
    
    def _get_quality_grade(self, score: float) -> str:
        """根据完整性评分获取质量等级"""
        if score >= 0.9:
            return 'A - 优秀'
        elif score >= 0.7:
            return 'B - 良好'
        elif score >= 0.5:
            return 'C - 一般'
        elif score >= 0.3:
            return 'D - 较差'
        else:
            return 'F - 很差'
    
    def get_existing_symbols(self) -> List[str]:
        """获取数据库中已存在的股票代码列表"""
        return self.database.get_existing_symbols()
    
    def close(self):
        """关闭数据服务（关闭数据库连接）"""
        if self.database:
            self.database.close()
