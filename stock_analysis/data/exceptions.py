#!/usr/bin/env python3
"""
数据服务异常类
统一的异常处理体系
"""

from typing import Any, Callable, Dict, List, Optional, Union


class DataServiceError(Exception):
    """
    数据服务基础异常类
    所有数据服务相关异常的基类
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化异常

        Args:
            message: 异常消息
            error_code: 错误代码
            context: 错误上下文信息
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}

    def __str__(self) -> str:
        """返回异常的字符串表示"""
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"

        return base_msg

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context,
        }


class ConfigurationError(DataServiceError):
    """配置错误"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, "CONFIG_ERROR", {'config_key': config_key})


class DownloadError(DataServiceError):
    """数据下载错误"""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        retries: Optional[int] = None,
    ):
        context: Dict[str, Any] = {}
        if symbol:
            context['symbol'] = symbol
        if source:
            context['source'] = source
        if retries is not None:
            context['retries'] = retries

        super().__init__(message, "DOWNLOAD_ERROR", context)


class NetworkError(DownloadError):
    """网络连接错误"""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        context: Dict[str, Any] = {}
        if symbol:
            context['symbol'] = symbol
        if url:
            context['url'] = url
        if status_code:
            context['status_code'] = status_code

        super().__init__(message, symbol, "network")
        self.error_code = "NETWORK_ERROR"
        self.context.update(context)


class RateLimitError(DownloadError):
    """API速率限制错误"""

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        context: Dict[str, Any] = {}
        if retry_after:
            context['retry_after'] = retry_after

        super().__init__(message, symbol, source)
        self.error_code = "RATE_LIMIT_ERROR"
        self.context.update(context)


class DataValidationError(DataServiceError):
    """数据验证错误"""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        field: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
    ):
        context: Dict[str, Any] = {}
        if symbol:
            context['symbol'] = symbol
        if field:
            context['field'] = field
        if expected is not None:
            context['expected'] = expected
        if actual is not None:
            context['actual'] = actual

        super().__init__(message, "VALIDATION_ERROR", context)


class StorageError(DataServiceError):
    """数据存储错误"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        symbol: Optional[str] = None,
    ):
        context: Dict[str, Any] = {}
        if operation:
            context['operation'] = operation
        if table:
            context['table'] = table
        if symbol:
            context['symbol'] = symbol

        super().__init__(message, "STORAGE_ERROR", context)


class DatabaseConnectionError(StorageError):
    """数据库连接错误"""

    def __init__(
        self,
        message: str,
        db_path: Optional[str] = None,
        db_type: Optional[str] = None,
    ):
        context: Dict[str, Any] = {}
        if db_path:
            context['db_path'] = db_path
        if db_type:
            context['db_type'] = db_type

        super().__init__(message, "database_connection")
        self.error_code = "DB_CONNECTION_ERROR"
        self.context.update(context)


class DatabaseOperationError(StorageError):
    """数据库操作错误"""

    def __init__(
        self,
        message: str,
        operation: str,
        table: Optional[str] = None,
        query: Optional[str] = None,
        symbol: Optional[str] = None,
    ):
        context: Dict[str, Any] = {'operation': operation}
        if table:
            context['table'] = table
        if query:
            context['query'] = query
        if symbol:
            context['symbol'] = symbol

        super().__init__(message, operation, table, symbol)
        self.error_code = "DB_OPERATION_ERROR"


class DataQualityError(DataServiceError):
    """数据质量错误"""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        quality_issues: Optional[List[Any]] = None,
        quality_grade: Optional[str] = None,
    ):
        context: Dict[str, Any] = {}
        if symbol:
            context['symbol'] = symbol
        if quality_issues:
            context['quality_issues'] = quality_issues
        if quality_grade:
            context['quality_grade'] = quality_grade

        super().__init__(message, "QUALITY_ERROR", context)


class SymbolNotFoundError(DownloadError):
    """股票代码未找到错误"""

    def __init__(self, symbol: str, source: Optional[str] = None):
        message = f"Stock symbol '{symbol}' not found"
        if source:
            message += f" on {source}"

        super().__init__(message, symbol, source)
        self.error_code = "SYMBOL_NOT_FOUND"


class InsufficientDataError(DataServiceError):
    """数据不足错误"""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        required_points: Optional[int] = None,
        actual_points: Optional[int] = None,
    ):
        context: Dict[str, Any] = {}
        if symbol:
            context['symbol'] = symbol
        if required_points is not None:
            context['required_points'] = required_points
        if actual_points is not None:
            context['actual_points'] = actual_points

        super().__init__(message, "INSUFFICIENT_DATA", context)


class TimeoutError(DataServiceError):
    """操作超时错误"""

    def __init__(
        self,
        message: str = "Operation timed out",
        operation: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        context: Dict[str, Any] = {}
        if operation:
            context['operation'] = operation
        if timeout_seconds:
            context['timeout_seconds'] = timeout_seconds

        super().__init__(message, "TIMEOUT_ERROR", context)


# 异常工厂函数，方便创建常见异常
def create_download_error(
    symbol: str, source: str, error_msg: str, retries: int = 0
) -> DownloadError:
    """创建下载错误"""
    return DownloadError(
        f"Failed to download {symbol} from {source}: {error_msg}",
        symbol=symbol,
        source=source,
        retries=retries,
    )


def create_network_error(symbol: str, url: str, status_code: Optional[int] = None) -> NetworkError:
    """创建网络错误"""
    message = f"Network error when downloading {symbol}"
    if status_code:
        message += f" (HTTP {status_code})"
    return NetworkError(message, symbol=symbol, url=url, status_code=status_code)


def create_storage_error(
    operation: str, table: str, symbol: Optional[str] = None, error_msg: Optional[str] = None
) -> StorageError:
    """创建存储错误"""
    message = f"Storage error during {operation} on {table}"
    if symbol:
        message += f" for symbol {symbol}"
    if error_msg:
        message += f": {error_msg}"

    return StorageError(message, operation=operation, table=table, symbol=symbol)


def create_validation_error(
    field: str, expected: Any, actual: Any, symbol: Optional[str] = None
) -> DataValidationError:
    """创建验证错误"""
    message = f"Validation failed for field '{field}': expected {expected}, got {actual}"
    if symbol:
        message = f"[{symbol}] {message}"

    return DataValidationError(
        message, symbol=symbol, field=field, expected=expected, actual=actual
    )


# 异常处理装饰器
def handle_exceptions(
    default_return: Any = None, log_errors: bool = True
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    异常处理装饰器

    Args:
        default_return: 异常时的默认返回值
        log_errors: 是否记录错误日志
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except DataServiceError as e:
                if log_errors:
                    import logging

                    logger = logging.getLogger(func.__module__)
                    logger.error(f"DataService error in {func.__name__}: {e}")
                return default_return
            except Exception as e:
                if log_errors:
                    import logging

                    logger = logging.getLogger(func.__module__)
                    logger.error(
                        f"Unexpected error in {func.__name__}: {e}",
                        exc_info=True,
                    )
                # 将普通异常包装为DataServiceError
                raise DataServiceError(f"Unexpected error: {str(e)}") from e

        return wrapper

    return decorator
