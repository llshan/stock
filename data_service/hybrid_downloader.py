#!/usr/bin/env python3
"""
混合股票数据下载器
结合Stooq（批量历史数据）和yfinance（增量更新）的优势
使用新的DataService架构进行数据管理
"""

import os
import sys
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Stock.data_service.stooq_downloader import StooqDataDownloader
from Stock.data_service.yfinance_downloader import StockDataDownloader
from Stock.data_service.database import StockDatabase
from Stock.data_service.services import DataService


class DownloadStrategy(ABC):
    """
    下载策略抽象基类
    定义数据源的统一接口
    """
    
    def __init__(self, data_service: DataService, name: str, priority: int = 100):
        """
        初始化下载策略
        
        Args:
            data_service: 数据服务实例
            name: 策略名称
            priority: 策略优先级，数字越小优先级越高
        """
        self.data_service = data_service
        self.name = name
        self.priority = priority
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def should_handle(self, symbol: str, context: Dict) -> bool:
        """
        判断该策略是否应该处理指定股票
        
        Args:
            symbol: 股票代码
            context: 上下文信息（如是否为新股票、历史数据情况等）
            
        Returns:
            是否应该由此策略处理
        """
        pass
    
    @abstractmethod
    def download(self, symbol: str, start_date: str = None, **kwargs) -> Dict:
        """
        执行下载
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            **kwargs: 其他参数
            
        Returns:
            下载结果
        """
        pass
    
    def get_description(self) -> str:
        """获取策略描述"""
        return f"{self.name} (优先级: {self.priority})"


class StooqDownloadStrategy(DownloadStrategy):
    """
    Stooq下载策略
    适用于新股票的完整历史数据下载
    """
    
    def __init__(self, data_service: DataService):
        super().__init__(data_service, "Stooq批量历史数据", priority=20)
    
    def should_handle(self, symbol: str, context: Dict) -> bool:
        """
        Stooq策略处理条件：
        1. 新股票（数据库中没有历史数据）
        2. 或者明确指定使用Stooq
        """
        is_new_stock = context.get('is_new_stock', False)
        force_stooq = context.get('force_stooq', False)
        
        if force_stooq:
            self.logger.info(f"🎯 {symbol} 强制使用Stooq策略")
            return True
            
        if is_new_stock:
            self.logger.info(f"🆕 {symbol} 是新股票，使用Stooq进行批量历史数据下载")
            return True
            
        return False
    
    def download(self, symbol: str, start_date: str = None, **kwargs) -> Dict:
        """使用Stooq下载完整历史数据"""
        try:
            actual_start_date = start_date or "2000-01-01"
            
            result = self.data_service.download_and_store_stock_data(
                symbol=symbol,
                start_date=actual_start_date,
                incremental=False,
                downloader_type="stooq"
            )
            
            if result.get('success'):
                self.logger.info(f"✅ Stooq策略成功下载 {symbol}: {result.get('data_points', 0)} 个数据点")
            else:
                self.logger.warning(f"⚠️ Stooq策略下载 {symbol} 失败: {result.get('error', '未知错误')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Stooq策略执行失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            return {'success': False, 'error': error_msg, 'strategy': self.name}


class YFinanceDownloadStrategy(DownloadStrategy):
    """
    yfinance下载策略
    适用于已有股票的增量更新
    """
    
    def __init__(self, data_service: DataService):
        super().__init__(data_service, "yfinance增量更新", priority=10)
    
    def should_handle(self, symbol: str, context: Dict) -> bool:
        """
        yfinance策略处理条件：
        1. 已有股票（数据库中存在历史数据）
        2. 或者明确指定使用yfinance
        """
        is_new_stock = context.get('is_new_stock', False)
        force_yfinance = context.get('force_yfinance', False)
        
        if force_yfinance:
            self.logger.info(f"🎯 {symbol} 强制使用yfinance策略")
            return True
            
        if not is_new_stock:
            self.logger.info(f"🔄 {symbol} 已存在数据，使用yfinance进行增量更新")
            return True
            
        return False
    
    def download(self, symbol: str, start_date: str = None, **kwargs) -> Dict:
        """使用yfinance进行增量下载"""
        try:
            result = self.data_service.download_and_store_stock_data(
                symbol=symbol,
                start_date=start_date,
                incremental=True,
                downloader_type="yfinance"
            )
            
            if result.get('success'):
                if result.get('no_new_data'):
                    self.logger.info(f"📊 yfinance策略确认 {symbol} 数据已最新")
                else:
                    self.logger.info(f"✅ yfinance策略成功更新 {symbol}: {result.get('data_points', 0)} 个数据点")
            else:
                self.logger.warning(f"⚠️ yfinance策略更新 {symbol} 失败: {result.get('error', '未知错误')}")
            
            return result
            
        except Exception as e:
            error_msg = f"yfinance策略执行失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            return {'success': False, 'error': error_msg, 'strategy': self.name}


class FallbackDownloadStrategy(DownloadStrategy):
    """
    备用下载策略
    当所有其他策略都不适用时的兜底方案
    """
    
    def __init__(self, data_service: DataService):
        super().__init__(data_service, "备用兜底策略", priority=999)
    
    def should_handle(self, symbol: str, context: Dict) -> bool:
        """备用策略总是返回True，作为最后的兜底方案"""
        self.logger.info(f"⚡ {symbol} 使用备用策略作为兜底方案")
        return True
    
    def download(self, symbol: str, start_date: str = None, **kwargs) -> Dict:
        """尝试使用yfinance下载，如果失败则尝试Stooq"""
        try:
            # 首先尝试yfinance
            self.logger.info(f"🔄 备用策略首先尝试yfinance下载 {symbol}")
            result = self.data_service.download_and_store_stock_data(
                symbol=symbol,
                start_date=start_date,
                incremental=True,
                downloader_type="yfinance"
            )
            
            if result.get('success'):
                self.logger.info(f"✅ 备用策略通过yfinance成功下载 {symbol}")
                return result
            
            # yfinance失败，尝试Stooq
            self.logger.info(f"🔄 备用策略yfinance失败，尝试Stooq下载 {symbol}")
            result = self.data_service.download_and_store_stock_data(
                symbol=symbol,
                start_date=start_date or "2000-01-01",
                incremental=False,
                downloader_type="stooq"
            )
            
            if result.get('success'):
                self.logger.info(f"✅ 备用策略通过Stooq成功下载 {symbol}")
            else:
                self.logger.error(f"❌ 备用策略所有方式都失败 {symbol}")
            
            return result
            
        except Exception as e:
            error_msg = f"备用策略执行失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            return {'success': False, 'error': error_msg, 'strategy': self.name}


class HybridStockDownloader:
    def __init__(self, database: StockDatabase, max_retries: int = 3, base_delay: int = 30):
        """
        初始化混合股票下载器（使用策略模式）
        
        Args:
            database: 数据库实例
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # 创建下载器实例
        stooq_downloader = StooqDataDownloader(max_retries=max_retries)
        yfinance_downloader = StockDataDownloader(
            max_retries=max_retries, 
            base_delay=base_delay
        )
        
        # 创建数据服务
        self.data_service = DataService(
            database=database,
            stock_downloader=yfinance_downloader,
            stooq_downloader=stooq_downloader
        )
        
        # 初始化策略列表
        self.strategies: List[DownloadStrategy] = []
        
        # 注册默认策略
        self._register_default_strategies()
        
        self.logger.info(f"🚀 混合下载器初始化完成，注册了 {len(self.strategies)} 个策略")
        self._log_strategies()
    
    def _register_default_strategies(self):
        """注册默认的下载策略"""
        # 按优先级注册策略
        self.register_strategy(YFinanceDownloadStrategy(self.data_service))
        self.register_strategy(StooqDownloadStrategy(self.data_service))
        self.register_strategy(FallbackDownloadStrategy(self.data_service))
    
    def register_strategy(self, strategy: DownloadStrategy):
        """
        注册新的下载策略
        
        Args:
            strategy: 下载策略实例
        """
        self.strategies.append(strategy)
        # 按优先级排序，优先级数字越小越优先
        self.strategies.sort(key=lambda s: s.priority)
        self.logger.info(f"📝 注册策略: {strategy.get_description()}")
    
    def unregister_strategy(self, strategy_name: str) -> bool:
        """
        注销指定名称的策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            是否成功注销
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.name == strategy_name:
                removed = self.strategies.pop(i)
                self.logger.info(f"🗑️ 注销策略: {removed.get_description()}")
                return True
        
        self.logger.warning(f"⚠️ 未找到策略: {strategy_name}")
        return False
    
    def get_strategies(self) -> List[DownloadStrategy]:
        """获取当前注册的所有策略"""
        return self.strategies.copy()
    
    def _log_strategies(self):
        """记录当前策略配置"""
        self.logger.info("📋 当前策略配置:")
        for i, strategy in enumerate(self.strategies, 1):
            self.logger.info(f"   {i}. {strategy.get_description()}")
    
    def _build_context(self, symbol: str) -> Dict:
        """
        构建策略选择的上下文信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            上下文字典
        """
        existing_symbols = self.data_service.get_existing_symbols()
        is_new_stock = symbol not in existing_symbols
        
        last_update = None
        if not is_new_stock:
            last_update = self.data_service.get_last_update_date(symbol)
        
        return {
            'is_new_stock': is_new_stock,
            'existing_symbols': existing_symbols,
            'last_update_date': last_update,
            'symbol': symbol
        }
        
    def download_stock_data(self, symbol: str, start_date: str = "2000-01-01", **kwargs) -> Dict:
        """
        使用策略模式进行智能股票数据下载
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            **kwargs: 额外参数（如 force_stooq, force_yfinance 等）
            
        Returns:
            下载结果字典
        """
        try:
            # 构建上下文信息
            context = self._build_context(symbol)
            context.update(kwargs)  # 合并额外参数
            
            self.logger.info(f"🎯 开始为 {symbol} 选择下载策略")
            
            # 按优先级遍历策略
            for strategy in self.strategies:
                if strategy.should_handle(symbol, context):
                    self.logger.info(f"📋 选择策略: {strategy.name} 处理 {symbol}")
                    
                    result = strategy.download(symbol, start_date, **kwargs)
                    
                    # 在结果中记录使用的策略
                    if isinstance(result, dict):
                        result['used_strategy'] = strategy.name
                        result['strategy_priority'] = strategy.priority
                    
                    return result
            
            # 如果没有策略处理，这通常不应该发生（因为有备用策略）
            error_msg = f"没有找到适合处理 {symbol} 的策略"
            self.logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"策略选择过程失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def download_stock_data_with_strategy(self, symbol: str, strategy_name: str, 
                                        start_date: str = "2000-01-01", **kwargs) -> Dict:
        """
        使用指定策略下载股票数据
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称
            start_date: 开始日期
            **kwargs: 额外参数
            
        Returns:
            下载结果字典
        """
        try:
            # 查找指定策略
            target_strategy = None
            for strategy in self.strategies:
                if strategy.name == strategy_name:
                    target_strategy = strategy
                    break
            
            if not target_strategy:
                available = [s.name for s in self.strategies]
                error_msg = f"未找到策略 '{strategy_name}'，可用策略: {available}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            self.logger.info(f"🎯 强制使用策略 '{strategy_name}' 处理 {symbol}")
            
            result = target_strategy.download(symbol, start_date, **kwargs)
            
            # 在结果中记录使用的策略
            if isinstance(result, dict):
                result['used_strategy'] = target_strategy.name
                result['strategy_priority'] = target_strategy.priority
                result['forced_strategy'] = True
            
            return result
            
        except Exception as e:
            error_msg = f"强制策略执行失败: {str(e)}"
            self.logger.error(f"❌ {symbol} {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def batch_download(self, symbols: List[str], start_date: str = "2000-01-01", **kwargs) -> Dict[str, Dict]:
        """
        使用策略模式批量下载股票数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            **kwargs: 额外参数
            
        Returns:
            批量下载结果
        """
        results = {}
        total = len(symbols)
        
        self.logger.info(f"🎯 开始策略模式批量下载 {total} 个股票")
        
        # 统计策略使用情况
        strategy_usage = {}
        
        for i, symbol in enumerate(symbols):
            self.logger.info(f"进度: [{i+1}/{total}] 处理 {symbol}")
            
            try:
                result = self.download_stock_data(symbol, start_date, **kwargs)
                
                # 统计策略使用
                used_strategy = result.get('used_strategy', 'Unknown')
                strategy_usage[used_strategy] = strategy_usage.get(used_strategy, 0) + 1
                
                results[symbol] = result
                
                # 添加延迟避免API限制
                if i < total - 1:
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
        
        self.logger.info(f"✅ 策略模式批量下载完成，成功: {successful}/{total}")
        
        # 记录策略使用统计
        self.logger.info("📊 策略使用统计:")
        for strategy_name, count in strategy_usage.items():
            self.logger.info(f"   {strategy_name}: {count} 次")
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'strategy_usage': strategy_usage,
            'results': results
        }
    
    def configure_strategies(self, config: Dict):
        """
        通过配置重新设置策略
        
        Args:
            config: 策略配置字典
                格式: {
                    "strategies": [
                        {"name": "yfinance", "enabled": True, "priority": 10},
                        {"name": "stooq", "enabled": True, "priority": 20},
                        {"name": "fallback", "enabled": True, "priority": 999}
                    ]
                }
        """
        self.logger.info("🔧 重新配置策略...")
        
        # 清空现有策略
        self.strategies.clear()
        
        strategies_config = config.get('strategies', [])
        
        for strategy_config in strategies_config:
            name = strategy_config.get('name', '').lower()
            enabled = strategy_config.get('enabled', True)
            priority = strategy_config.get('priority', 100)
            
            if not enabled:
                self.logger.info(f"⏭️ 跳过已禁用的策略: {name}")
                continue
            
            # 根据名称创建策略
            strategy = self._create_strategy_by_name(name, priority)
            if strategy:
                self.register_strategy(strategy)
            else:
                self.logger.warning(f"⚠️ 未知策略名称: {name}")
        
        # 如果没有配置任何策略，使用默认配置
        if not self.strategies:
            self.logger.warning("⚠️ 没有启用任何策略，使用默认配置")
            self._register_default_strategies()
        
        self.logger.info(f"✅ 策略配置完成，共 {len(self.strategies)} 个策略")
        self._log_strategies()
    
    def _create_strategy_by_name(self, name: str, priority: int = None) -> Optional[DownloadStrategy]:
        """
        根据名称创建策略实例
        
        Args:
            name: 策略名称
            priority: 优先级（可选，会覆盖默认优先级）
            
        Returns:
            策略实例或None
        """
        strategy = None
        
        if name in ['yfinance', 'yf']:
            strategy = YFinanceDownloadStrategy(self.data_service)
        elif name in ['stooq', 'st']:
            strategy = StooqDownloadStrategy(self.data_service)
        elif name in ['fallback', 'backup']:
            strategy = FallbackDownloadStrategy(self.data_service)
        
        # 如果指定了优先级，覆盖默认优先级
        if strategy and priority is not None:
            strategy.priority = priority
        
        return strategy
    
    def get_strategy_config(self) -> Dict:
        """
        获取当前策略配置
        
        Returns:
            当前策略配置字典
        """
        return {
            'strategies': [
                {
                    'name': strategy.name,
                    'priority': strategy.priority,
                    'enabled': True,
                    'description': strategy.get_description()
                }
                for strategy in self.strategies
            ]
        }
    
    def add_custom_strategy(self, strategy_class, name: str, priority: int = 50, **kwargs):
        """
        添加自定义策略类
        
        Args:
            strategy_class: 策略类（需继承DownloadStrategy）
            name: 策略名称
            priority: 优先级
            **kwargs: 传递给策略构造函数的额外参数
        """
        try:
            # 验证策略类
            if not issubclass(strategy_class, DownloadStrategy):
                raise ValueError(f"策略类必须继承自DownloadStrategy: {strategy_class}")
            
            # 创建策略实例
            strategy = strategy_class(self.data_service, name, priority, **kwargs)
            
            # 注册策略
            self.register_strategy(strategy)
            
            self.logger.info(f"✅ 成功添加自定义策略: {strategy.get_description()}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加自定义策略失败: {str(e)}")
            raise
    
    def close(self):
        """关闭混合下载器"""
        if self.data_service:
            self.data_service.close()


def create_watchlist() -> List[str]:
    """创建需要关注的股票清单"""
    return [
        "AAPL",   # 苹果
        "GOOG",   # 谷歌
        "LULU"    # Lululemon
    ]


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔄 混合股票数据下载器（策略模式）")
    print("=" * 60)
    print("💡 使用策略模式智能选择下载源，支持配置和扩展")
    print("=" * 60)
    
    try:
        # 创建数据库和混合下载器
        database = StockDatabase("hybrid_stocks.db")
        hybrid_downloader = HybridStockDownloader(database)
        
        # 显示当前策略配置
        print(f"\n⚙️  当前策略配置:")
        for i, strategy in enumerate(hybrid_downloader.get_strategies(), 1):
            print(f"   {i}. {strategy.get_description()}")
        
        # 获取关注股票列表
        watchlist = create_watchlist()
        
        print(f"\n📊 将下载 {len(watchlist)} 个股票的数据:")
        for i, symbol in enumerate(watchlist, 1):
            print(f"  {i:2d}. {symbol}")
        
        # 演示策略配置功能
        print(f"\n🔧 演示策略配置功能...")
        config_example = {
            "strategies": [
                {"name": "yfinance", "enabled": True, "priority": 5},
                {"name": "stooq", "enabled": True, "priority": 15},
                {"name": "fallback", "enabled": True, "priority": 999}
            ]
        }
        
        print("   配置示例:")
        import json
        print(f"   {json.dumps(config_example, indent=2, ensure_ascii=False)}")
        
        # 可选：重新配置策略（取消注释以测试）
        # hybrid_downloader.configure_strategies(config_example)
        # print(f"\n✅ 策略重新配置完成")
        
        # 执行批量混合下载
        results = hybrid_downloader.batch_download(watchlist, start_date="2000-01-01")
        
        # 显示下载结果摘要
        print("\n" + "=" * 60)
        print("📊 策略模式下载结果摘要:")
        print(f"   总计: {results['total']} 个股票")
        print(f"   成功: {results['successful']} 个")
        print(f"   失败: {results['failed']} 个")
        
        # 显示策略使用统计
        if results.get('strategy_usage'):
            print(f"\n📋 策略使用统计:")
            for strategy_name, count in results['strategy_usage'].items():
                print(f"   {strategy_name}: {count} 次")
        
        # 详细结果
        if results.get('results'):
            print(f"\n📋 详细结果:")
            for symbol, result in results['results'].items():
                if result.get('success'):
                    data_points = result.get('data_points', 0)
                    if result.get('no_new_data'):
                        print(f"   {symbol}: 数据已最新 ✅")
                    else:
                        print(f"   {symbol}: {data_points} 个数据点 ✅")
                else:
                    error = result.get('error', '未知错误')[:50]
                    print(f"   {symbol}: {error}... ❌")
        
        print(f"\n💾 数据已保存到 hybrid_stocks.db")
        print(f"📈 可以使用数据库工具查看完整的股票数据")
        
    except Exception as e:
        print(f"❌ 程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理资源
        if 'hybrid_downloader' in locals():
            hybrid_downloader.close()
            print("\n🔧 混合下载器已关闭")