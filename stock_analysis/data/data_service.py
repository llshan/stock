#!/usr/bin/env python3
"""
数据服务层（DataService）

职责：
- 协调多个下载器与存储层，提供统一的数据获取/存储入口
- 封装增量下载、批量下载与数据质量评估流程

说明：
- 混合下载策略：
  * 股票价格数据：批量下载用Stooq，增量更新用Finnhub
  * 财务数据：全部使用Finnhub
- 模块侧重于数据流转（下载→规范化→存储）
- 依赖 storage 与 downloaders 子模块
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from .config import DataServiceConfig
from .downloaders.stooq import StooqDataDownloader
from .downloaders.finnhub import FinnhubDownloader
from .models import (
    FinancialData,
    StockData,
)
from .storage import create_storage
from .storage.base import BaseStorage


class DataService:
    """
    数据服务类
    负责协调下载器和数据库操作，提供统一的数据管理接口
    """

    def __init__(
        self, storage: Optional[BaseStorage] = None, config: Optional[DataServiceConfig] = None
    ):
        """
        初始化数据服务

        Args:
            storage: 存储实例，默认使用SQLite
            config: 数据服务配置，包含下载器选择
        """
        self.storage: BaseStorage = storage or create_storage('sqlite')
        self.config = config or DataServiceConfig()
        # 价格数据：批量用Stooq，增量用Finnhub
        self.stooq_downloader = StooqDataDownloader()
        self.finnhub_downloader = FinnhubDownloader()

        self.logger = logging.getLogger(__name__)

    def _get_financial_downloader(self):
        """根据配置获取财务数据下载器"""
        downloader_type = self.config.downloader.financial_downloader.lower()
        if downloader_type == 'finnhub':
            return self.finnhub_downloader
        else:
            self.logger.warning(f"未知的财务下载器类型: {downloader_type}, 使用默认的 Finnhub")
            return self.finnhub_downloader

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

    def download_and_store_stock_data(
        self, symbol: str, start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        下载并存储股票数据（批量用Stooq，增量用Finnhub）

        Args:
            symbol: 股票代码
            start_date: 开始日期

        Returns:
            操作结果
        """
        try:
            self.logger.info(f"📈 开始下载并存储 {symbol} 股票数据")
            # 统一自动策略，并入库
            self._ensure_stock_record(symbol)
            # 增量起点
            raw_last = None
            try:
                raw_last = self.storage.get_last_update_date(symbol)
            except Exception:
                raw_last = None
            
            # 检查数据是否已经是最新的
            if raw_last:
                today = datetime.now().strftime('%Y-%m-%d')
                if raw_last >= today:
                    return {
                        'success': True,
                        'symbol': symbol,
                        'no_new_data': True,
                        'used_strategy': 'skip_already_current',
                        'data_points': 0,
                    }
            
            actual_start = (
                (datetime.strptime(raw_last, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                if raw_last
                else (start_date or '2000-01-01')
            )

            # 混合策略：根据最新数据时间决定批量还是增量
            if raw_last is None:
                # 首次下载，使用Stooq批量下载历史数据
                used = 'Stooq批量历史数据'
                data = self.stooq_downloader.download_stock_data(symbol, actual_start)
            else:
                # 计算距今天数，决定是否使用增量更新
                days_since_last = (datetime.now() - datetime.strptime(raw_last, '%Y-%m-%d')).days
                threshold_days = getattr(self.config.downloader, 'stock_incremental_threshold_days', 100)
                
                if days_since_last <= threshold_days:
                    # 在阈值内，使用增量更新（优先Finnhub）
                    used = 'Finnhub增量更新'
                    data = self.finnhub_downloader.download_stock_data(symbol, actual_start)
                    
                    # 如果Finnhub失败，回退到Stooq
                    if isinstance(data, dict) and 'error' in data:
                        self.logger.warning(f"Finnhub增量更新失败，回退到Stooq: {data['error']}")
                        used = 'Stooq增量更新(Finnhub失败回退)'
                        data = self.stooq_downloader.download_stock_data(symbol, actual_start)
                else:
                    # 超过阈值，使用Stooq批量重新下载
                    used = f'Stooq批量重下载(超过{threshold_days}天阈值)'
                    self.logger.info(f"{symbol} 最后更新距今 {days_since_last} 天，超过 {threshold_days} 天阈值，使用批量下载")
                    data = self.stooq_downloader.download_stock_data(symbol, actual_start)

            if isinstance(data, dict) and 'error' in data:
                return {
                    'success': False,
                    'error': data['error'],
                    'symbol': symbol,
                    'used_strategy': used,
                }
            if isinstance(data, StockData):
                if data.data_points > 0:
                    self.storage.store_stock_data(symbol, data)
                    return {
                        'success': True,
                        'symbol': symbol,
                        'data_points': data.data_points,
                        'used_strategy': used,
                        'incremental': True,
                    }
                return {
                    'success': True,
                    'symbol': symbol,
                    'data_points': 0,
                    'no_new_data': True,
                    'used_strategy': used,
                }
            return {
                'success': False,
                'error': f'未知数据格式: {type(data)}',
                'symbol': symbol,
            }
        except Exception as e:
            error_msg = f"下载并存储 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'symbol': symbol}

    def download_and_store_financial_data(self, symbol: str) -> Dict[str, Any]:
        """
        下载并存储财务数据（带刷新阈值）。

        - 如果最近财报期间距今不超过阈值（默认 90 天），则跳过并返回 no_new_data。
        - 否则使用 Finnhub 下载财报并入库。
        """
        try:
            # 判定是否需要刷新
            try:
                last_period = self.storage.get_last_financial_period(symbol)
            except Exception:
                last_period = None

            need_refresh = True
            if last_period:
                try:
                    days = (datetime.now() - datetime.strptime(last_period, '%Y-%m-%d')).days
                    threshold = getattr(self.config.downloader, 'financial_refresh_days', 90)
                    need_refresh = days > threshold
                except Exception:
                    need_refresh = True

            if not need_refresh:
                return {
                    'success': True,
                    'symbol': symbol,
                    'no_new_data': True,
                    'used_strategy': 'skip_recent_financial',
                }

            downloader = self._get_financial_downloader()
            downloader_name = self.config.downloader.financial_downloader.lower()
            
            fin = downloader.download_financial_data(symbol, use_retry=True)
            if isinstance(fin, dict) and 'error' in fin:
                return {
                    'success': False,
                    'symbol': symbol,
                    'error': fin['error'],
                    'used_strategy': f'{downloader_name}_financial_error',
                }

            if isinstance(fin, FinancialData):
                stmt_count = len(fin.financial_statements)
                if stmt_count == 0:
                    # 不写入空财务数据，视为无有效数据
                    return {
                        'success': False,
                        'symbol': symbol,
                        'error': '未获取到财务报表（返回为空）',
                        'used_strategy': f'{downloader_name}_financial_empty',
                    }
                self.storage.store_financial_data(symbol, fin)
                return {
                    'success': True,
                    'symbol': symbol,
                    'statements': stmt_count,
                    'used_strategy': f'{downloader_name}_financial',
                }

            return {
                'success': False,
                'symbol': symbol,
                'error': f'未知数据格式: {type(fin)}',
            }

        except Exception as e:
            error_msg = f"下载并存储 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'symbol': symbol}

    def batch_download_and_store(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        include_financial: bool = True,
    ) -> Dict[str, Any]:
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

        data_type = "股票+财务数据" if include_financial else "股票数据"
        self.logger.info(f"🎯 开始批量处理 {total} 个股票的{data_type}")

        # 批量路径：逐只处理（下载器不再提供批量接口）

        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")

            try:
                # 始终先处理价格数据
                stock_result = self.download_and_store_stock_data(symbol, start_date)

                if include_financial:
                    financial_result = self.download_and_store_financial_data(symbol)
                    combined = {
                        'success': stock_result.get('success', False)
                        and financial_result.get('success', False),
                        'symbol': symbol,
                        'stock': stock_result,
                        'financial': financial_result,
                    }
                    results[symbol] = combined
                else:
                    results[symbol] = stock_result

                # 添加延迟避免API限制
                if i < total - 1:  # 最后一个不需要延迟
                    import time

                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"处理 {symbol} 时出错: {str(e)}")
                results[symbol] = {
                    'success': False,
                    'error': str(e),
                    'symbol': symbol,
                }

        # 统计结果
        successful = len([r for r in results.values() if r.get('success', False)])
        failed = total - successful

        self.logger.info(f"✅ 批量处理完成，成功: {successful}/{total}")

        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'results': results,
        }

    # 质量评估逻辑已集中到 quality.assess_data_quality，无需本地额外包装

    def get_existing_symbols(self) -> List[str]:
        """获取数据库中已存在的股票代码列表"""
        return self.storage.get_existing_symbols()

    def close(self) -> None:
        """关闭数据服务（关闭数据库连接）"""
        if self.storage:
            self.storage.close()

    # 内部工具
    def _ensure_stock_record(self, symbol: str) -> None:
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
            # Use hasattr to check if the storage implementation has this method
            if hasattr(self.storage, '_ensure_stock_exists'):
                self.storage._ensure_stock_exists(symbol)
                self.logger.info(f"🪪 已创建空股票记录: {symbol}")
            else:
                self.logger.warning(
                    f"Storage implementation does not support _ensure_stock_exists for {symbol}"
                )
        except Exception as e:
            self.logger.error(f"❌ 创建股票记录失败 {symbol}: {e}")
