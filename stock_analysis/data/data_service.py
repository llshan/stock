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
from .downloaders.base import DownloaderError
from .models import (
    FinancialData,
    StockData,
)
from .models.quality_models import DownloadResult, BatchDownloadResult
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
    ) -> DownloadResult:
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
            self._ensure_stock_record(symbol)

            # 获取已有最新日期
            try:
                raw_last = self.storage.get_last_update_date(symbol)
            except Exception:
                raw_last = None

            # 已最新则跳过
            if raw_last:
                today = datetime.now().strftime('%Y-%m-%d')
                if raw_last >= today:
                    return DownloadResult(
                        success=True,
                        symbol=symbol,
                        data_type='stock',
                        data_points=0,
                        used_strategy='skip_already_current',
                        metadata={'no_new_data': True},
                    )

            actual_start = (
                (datetime.strptime(raw_last, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                if raw_last
                else (start_date or '2000-01-01')
            )

            # 策略选择
            if raw_last is None:
                used = 'Stooq批量历史数据'
                stock = self.stooq_downloader.download_stock_data(symbol, actual_start)
            else:
                days_since_last = (datetime.now() - datetime.strptime(raw_last, '%Y-%m-%d')).days
                threshold_days = getattr(self.config.downloader, 'stock_incremental_threshold_days', 100)
                if days_since_last <= threshold_days:
                    used = 'Finnhub增量更新'
                    stock = self.finnhub_downloader.download_stock_data(symbol, actual_start)
                else:
                    used = f'Stooq批量重下载(超过{threshold_days}天阈值)'
                    self.logger.info(
                        f"{symbol} 最后更新距今 {days_since_last} 天，超过 {threshold_days} 天阈值，使用批量下载"
                    )
                    stock = self.stooq_downloader.download_stock_data(symbol, actual_start)

            # 入库
            self.storage.store_stock_data(symbol, stock)
            return DownloadResult(
                success=True,
                symbol=symbol,
                data_type='stock',
                data_points=stock.data_points,
                used_strategy=used,
                data_source=stock.data_source,
                metadata={'incremental': stock.incremental_update, 'no_new_data': stock.no_new_data},
            )
        except DownloaderError as e:
            return DownloadResult(
                success=False,
                symbol=symbol,
                data_type='stock',
                data_points=0,
                error_message=str(e),
                used_strategy=locals().get('used'),
            )
        except Exception as e:
            error_msg = f"下载并存储 {symbol} 数据失败: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(success=False, symbol=symbol, data_type='stock', error_message=error_msg)

    def download_and_store_financial_data(self, symbol: str) -> DownloadResult:
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
                return DownloadResult(
                    success=True,
                    symbol=symbol,
                    data_type='financial',
                    data_points=0,
                    used_strategy='skip_recent_financial',
                    metadata={'no_new_data': True},
                )

            downloader = self.finnhub_downloader
            downloader_name = 'finnhub'
            
            fin = downloader.download_financial_data(symbol, use_retry=True)
            stmt_count = len(fin.financial_statements)
            if stmt_count == 0:
                return DownloadResult(
                    success=False,
                    symbol=symbol,
                    data_type='financial',
                    data_points=0,
                    error_message='未获取到财务报表（返回为空）',
                    used_strategy=f'{downloader_name}_financial_empty',
                )
            self.storage.store_financial_data(symbol, fin)
            return DownloadResult(
                success=True,
                symbol=symbol,
                data_type='financial',
                data_points=stmt_count,
                used_strategy=f'{downloader_name}_financial',
            )

        except DownloaderError as e:
            return DownloadResult(
                success=False,
                symbol=symbol,
                data_type='financial',
                data_points=0,
                error_message=str(e),
                used_strategy=f'{downloader_name}_financial_error',
            )
        except Exception as e:
            error_msg = f"下载并存储 {symbol} 财务数据失败: {str(e)}"
            self.logger.error(error_msg)
            return DownloadResult(success=False, symbol=symbol, data_type='financial', error_message=error_msg)

    def batch_download_and_store(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        include_financial: bool = True,
    ) -> BatchDownloadResult:
        """
        批量下载并存储数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            include_financial: 是否包含财务数据

        Returns:
            批量操作结果
        """
        results: Dict[str, DownloadResult] = {}
        total = len(symbols)
        import time as _time
        start_ts = _time.time()
        start_time = datetime.now().isoformat()

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
                    # 聚合：以两者成功为总成功
                    success = stock_result.success and financial_result.success
                    # 记录主要策略
                    used_strategy = stock_result.used_strategy or financial_result.used_strategy
                    results[symbol] = DownloadResult(
                        success=success,
                        symbol=symbol,
                        data_type='comprehensive',
                        data_points=stock_result.data_points + financial_result.data_points,
                        used_strategy=used_strategy,
                        metadata={
                            'stock': stock_result.to_dict(),
                            'financial': financial_result.to_dict(),
                        },
                    )
                else:
                    results[symbol] = stock_result

                # 添加延迟避免API限制
                if i < total - 1:  # 最后一个不需要延迟
                    import time

                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"处理 {symbol} 时出错: {str(e)}")
                results[symbol] = DownloadResult(
                    success=False, symbol=symbol, data_type='comprehensive', error_message=str(e)
                )

        # 统计结果
        successful = len([r for r in results.values() if r.success])
        failed = total - successful

        self.logger.info(f"✅ 批量处理完成，成功: {successful}/{total}")
        end_time = datetime.now().isoformat()
        total_duration = _time.time() - start_ts

        # 统计策略使用
        strategy_usage: Dict[str, int] = {}
        for r in results.values():
            if r.used_strategy:
                strategy_usage[r.used_strategy] = strategy_usage.get(r.used_strategy, 0) + 1

        return BatchDownloadResult(
            total=total,
            successful=successful,
            failed=failed,
            results=results,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            strategy_usage=strategy_usage,
        )

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
