#!/usr/bin/env python3
"""
股票数据下载器
下载从2000年开始的股票价格数据和财务报表
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import time
import logging
from .base import BaseDownloader
from ..models import (
    StockData, FinancialData, ComprehensiveData, PriceData, SummaryStats, 
    BasicInfo, FinancialStatement, DataQuality,
    create_empty_stock_data, create_empty_financial_data
)
from ..quality import assess_data_quality

class YFinanceDataDownloader(BaseDownloader):
    def __init__(self, max_retries=3, base_delay=30):
        """初始化股票数据下载器"""
        super().__init__(max_retries=max_retries, base_delay=base_delay)
        self.start_date = "2000-01-01"
    
        

    def download_stock_data(self, symbol: str, start_date: str = None, incremental: bool = True, use_retry: bool = True) -> Union[StockData, Dict[str, str]]:
        """
        下载股票的历史价格数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期，默认2000-01-01
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制
            
        Returns:
            包含价格数据的字典
        """
        def _download_data():
            return self._download_stock_data_internal(symbol, start_date, incremental)
        
        if use_retry:
            return self._retry_with_backoff(_download_data, symbol)
        else:
            return _download_data()
    
    def _download_stock_data_internal(self, symbol: str, start_date: str = None, incremental: bool = True) -> Union[StockData, Dict[str, str]]:
        """内部股票数据下载实现"""
        try:
            # 设置默认开始日期
            if start_date is None:
                start_date = self.start_date
                
            self.logger.info(f"📈 下载 {symbol} 股票数据 (从 {start_date})")
            
            # 检查日期范围是否有效
            today = datetime.now().strftime('%Y-%m-%d')
            if start_date >= today:
                self.logger.info(f"📊 {symbol} 数据已是最新，无需更新")
                return StockData(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=today,
                    data_points=0,
                    price_data=PriceData(
                        dates=[], open=[], high=[], low=[], 
                        close=[], volume=[], adj_close=[]
                    ),
                    summary_stats=SummaryStats(
                        min_price=0.0, max_price=0.0, avg_price=0.0,
                        total_volume=0, avg_volume=0
                    ),
                    downloaded_at=datetime.now().isoformat(),
                    incremental_update=True,
                    no_new_data=True
                )
            
            # 下载股票数据
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(start=start_date, end=today)
            
            if hist_data.empty:
                return {'error': f'无法获取 {symbol} 的历史数据（时间范围: {start_date} 到 {today}）'}
            
            # 转换为dataclass格式
            price_data = PriceData(
                dates=[d.strftime('%Y-%m-%d') for d in hist_data.index],
                open=hist_data['Open'].tolist(),
                high=hist_data['High'].tolist(),
                low=hist_data['Low'].tolist(),
                close=hist_data['Close'].tolist(),
                volume=hist_data['Volume'].tolist(),
                adj_close=hist_data['Adj Close'].tolist()
            )
            
            summary_stats = SummaryStats(
                min_price=float(hist_data['Close'].min()),
                max_price=float(hist_data['Close'].max()),
                avg_price=float(hist_data['Close'].mean()),
                total_volume=int(hist_data['Volume'].sum()),
                avg_volume=int(hist_data['Volume'].mean())
            )
            
            stock_data = StockData(
                symbol=symbol,
                start_date=start_date,
                end_date=today,
                data_points=len(hist_data),
                price_data=price_data,
                summary_stats=summary_stats,
                downloaded_at=datetime.now().isoformat(),
                incremental_update=incremental
            )
            
            self.logger.info(f"✅ {symbol} 数据下载完成: {len(hist_data)} 个数据点")
            return stock_data
            
        except Exception as e:
            error_msg = f"下载 {symbol} 股票数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def download_financial_data(self, symbol: str, use_retry: bool = True) -> Union[FinancialData, Dict[str, str]]:
        """
        下载股票的财务报表数据
        
        Args:
            symbol: 股票代码
            use_retry: 是否使用重试机制
            
        Returns:
            包含财务数据的字典
        """
        def _download_data():
            return self._download_financial_data_internal(symbol)
        
        if use_retry:
            return self._retry_with_backoff(_download_data, symbol)
        else:
            return _download_data()
    
    def _download_financial_data_internal(self, symbol: str) -> Union[FinancialData, Dict[str, str]]:
        """内部财务数据下载实现"""
        try:
            self.logger.info(f"💼 下载 {symbol} 财务报表数据")
            
            ticker = yf.Ticker(symbol)
            
            # 获取财务报表
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
            
            # 获取基本信息
            info = ticker.info
            
            basic_info = BasicInfo(
                company_name=info.get('longName', ''),
                sector=info.get('sector', ''),
                industry=info.get('industry', ''),
                market_cap=info.get('marketCap', 0),
                employees=info.get('fullTimeEmployees', 0),
                description=info.get('longBusinessSummary', '')
            )
            
            financial_statements = {}
            
            # 处理损益表
            if not financials.empty:
                income_stmt = self._process_financial_statement(financials, '损益表')
                if 'error' not in income_stmt:
                    financial_statements['income_statement'] = FinancialStatement.from_dict(income_stmt)
            
            # 处理资产负债表
            if not balance_sheet.empty:
                balance_stmt = self._process_financial_statement(balance_sheet, '资产负债表')
                if 'error' not in balance_stmt:
                    financial_statements['balance_sheet'] = FinancialStatement.from_dict(balance_stmt)
            
            # 处理现金流量表
            if not cash_flow.empty:
                cash_flow_stmt = self._process_financial_statement(cash_flow, '现金流量表')
                if 'error' not in cash_flow_stmt:
                    financial_statements['cash_flow'] = FinancialStatement.from_dict(cash_flow_stmt)
            
            financial_data = FinancialData(
                symbol=symbol,
                basic_info=basic_info,
                financial_statements=financial_statements,
                downloaded_at=datetime.now().isoformat()
            )
            
            self.logger.info(f"✅ {symbol} 财务数据下载完成")
            return financial_data
            
        except Exception as e:
            error_msg = f"下载 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'error': error_msg}
    
    def _process_financial_statement(self, df: pd.DataFrame, statement_type: str) -> Dict:
        """处理财务报表数据"""
        try:
            # 获取最近4年的数据
            processed_data = {
                'statement_type': statement_type,
                'periods': [col.strftime('%Y-%m-%d') for col in df.columns],
                'items': {}
            }
            
            for index in df.index:
                # 清理指标名称
                item_name = str(index).strip()
                if item_name and item_name != 'nan':
                    values = []
                    for col in df.columns:
                        value = df.loc[index, col]
                        if pd.isna(value):
                            values.append(None)
                        else:
                            values.append(float(value))
                    processed_data['items'][item_name] = values
            
            return processed_data
            
        except Exception as e:
            self.logger.warning(f"处理财务报表 {statement_type} 时出错: {str(e)}")
            return {'error': f'处理 {statement_type} 失败: {str(e)}'}
    
    def download_comprehensive_data(self, symbol: str, start_date: str = None, incremental: bool = True, use_retry: bool = True) -> ComprehensiveData:
        """
        下载股票的综合数据（价格+财务）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制
            
        Returns:
            综合数据字典
        """
        retry_text = "（启用重试）" if use_retry else ""
        self.logger.info(f"🚀 开始下载 {symbol} 的综合数据{'（增量模式）' if incremental else '（全量模式）'}{retry_text}")
        
        # 下载股票价格数据
        stock_data = self.download_stock_data(symbol, start_date, incremental, use_retry)
        
        # 添加延迟避免API限制
        time.sleep(1)
        
        # 下载财务数据
        financial_data = self.download_financial_data(symbol, use_retry)
        
        # 评估数据质量（统一工具函数）
        data_quality = assess_data_quality(stock_data, financial_data, self.start_date)
        
        # 创建综合数据对象
        stock_data_obj = None
        financial_data_obj = None
        
        if isinstance(stock_data, StockData):
            stock_data_obj = stock_data
        elif isinstance(stock_data, dict) and 'error' not in stock_data:
            stock_data_obj = StockData.from_dict(stock_data)
        
        if isinstance(financial_data, FinancialData):
            financial_data_obj = financial_data
        elif isinstance(financial_data, dict) and 'error' not in financial_data:
            financial_data_obj = FinancialData.from_dict(financial_data)
        
        comprehensive_data = ComprehensiveData(
            symbol=symbol,
            download_timestamp=datetime.now().isoformat(),
            stock_data=stock_data_obj,
            financial_data=financial_data_obj,
            data_quality=data_quality
        )
        
        return comprehensive_data
    
    def batch_download(self, symbols: List[str], start_date: str = None, incremental: bool = True, use_retry: bool = True) -> Dict[str, ComprehensiveData]:
        """
        批量下载多个股票的数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            incremental: 是否进行增量下载
            use_retry: 是否使用重试机制
            
        Returns:
            所有股票数据的字典
        """
        results = {}
        total = len(symbols)
        
        mode_text = "增量下载" if incremental else "全量下载"
        retry_text = "（启用重试）" if use_retry else ""
        self.logger.info(f"🎯 开始批量{mode_text} {total} 个股票的数据{retry_text}")
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                results[symbol] = self.download_comprehensive_data(symbol, start_date, incremental, use_retry)
                
                # 添加延迟避免API限制
                if i < total - 1:  # 最后一个不需要延迟
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"下载 {symbol} 时出错: {str(e)}")
                results[symbol] = {'error': str(e)}
        
        self.logger.info(f"✅ 批量下载完成，成功: {len([r for r in results.values() if 'error' not in r])}/{total}")
        return results
    
    # 质量评估与评级逻辑统一在 quality.py 中

def create_watchlist() -> List[str]:
    """创建需要关注的股票清单"""
    return [
        "AAPL",   # 苹果
        "GOOG",   # 谷歌
        "LULU"    # Lululemon
    ]

if __name__ == "__main__":
    # 配置日志
    from logging_utils import setup_logging
    setup_logging()
    
    logging.getLogger(__name__).info("🚀 股票数据下载器（使用DataService）")
    logging.getLogger(__name__).info("=" * 50)
    logging.getLogger(__name__).info("⚠️  注意: 这个示例展示下载器功能，但不包含数据库存储")
    logging.getLogger(__name__).info("💡 要使用完整功能（包括数据库），请使用 DataService 类")
    
    # 创建下载器
    downloader = YFinanceDataDownloader()
    
    # 获取关注股票列表
    watchlist = create_watchlist()
    
    logging.getLogger(__name__).info(f"📊 将下载 {len(watchlist)} 个股票的数据:")
    for i, symbol in enumerate(watchlist, 1):
        logging.getLogger(__name__).info(f"  {i:2d}. {symbol}")
    
    logging.getLogger(__name__).info(f"⏰ 数据时间范围: {downloader.start_date} 至今")
    logging.getLogger(__name__).info("📈 包含: 股票价格数据 + 财务报表数据")
    
    # 执行批量下载（仅下载，不存储）
    results = downloader.batch_download(watchlist)
    
    # 显示下载结果摘要
    successful = len([r for r in results.values() if not isinstance(r, dict) or 'error' not in r])
    failed = len(results) - successful
    
    logging.getLogger(__name__).info("=" * 50)
    logging.getLogger(__name__).info("📊 下载结果摘要:")
    logging.getLogger(__name__).info(f"✅ 成功: {successful} 个股票")
    logging.getLogger(__name__).info(f"❌ 失败: {failed} 个股票")
    
    if failed > 0:
        logging.getLogger(__name__).info("❌ 失败的股票:")
        for symbol, data in results.items():
            if isinstance(data, dict) and 'error' in data:
                logging.getLogger(__name__).info(f"   • {symbol}: {data['error']}")
    
    # 数据质量报告
    logging.getLogger(__name__).info("📈 下载的数据统计:")
    for symbol, data in results.items():
        if hasattr(data, 'data_quality'):
            logging.getLogger(__name__).info(f"   {symbol}: {data.data_quality.quality_grade}")
        elif isinstance(data, ComprehensiveData):
            logging.getLogger(__name__).info(f"   {symbol}: {data.data_quality.quality_grade}")
        elif not isinstance(data, dict) or 'error' not in data:
            logging.getLogger(__name__).info(f"   {symbol}: 数据下载完成")
    
    logging.getLogger(__name__).info("💡 要使用完整的数据管理功能（包括数据库存储），请参考:")
    logging.getLogger(__name__).info("   from data_service import DataService, StockDatabase")
    logging.getLogger(__name__).info("   data_service = DataService(StockDatabase('stocks.db'))")
    logging.getLogger(__name__).info("   data_service.batch_download_and_store(symbols)")


def main():
    """主函数，用于 python -m Stock.data_service.downloaders.yfinance 调用"""
    if __name__ == "__main__":
        # 运行主程序代码
        pass
