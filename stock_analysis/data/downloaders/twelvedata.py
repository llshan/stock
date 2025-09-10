#!/usr/bin/env python3
"""
Twelve Data 下载器

功能：
- 通过 Twelve Data API 下载日级别价格数据（time_series 1day）

使用：
- 需要提供 API Key（环境变量 TWELVE_DATA_API_KEY 或构造参数 api_key）
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union, List

import requests

from .base import BaseDownloader
from ..models import PriceData, StockData, SummaryStats
from ..models import FinancialData, FinancialStatement, BasicInfo


class TwelveDataDownloader(BaseDownloader):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.twelvedata.com",
        max_retries: int = 3,
        base_delay: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(max_retries=max_retries, base_delay=base_delay)
        # 兼容多种环境变量命名，并去除首尾空白
        key = (
            api_key
            or os.getenv("TWELVE_DATA_API_KEY")
            or os.getenv("TWELVEDATA_API_KEY")
            or os.getenv("TD_API_KEY")
        )
        self.api_key = key.strip() if isinstance(key, str) and key.strip() else None
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.logger = logging.getLogger(__name__)

    # 公共方法
    def download_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_retry: bool = True,
    ) -> Union[StockData, Dict[str, str]]:
        def _run() -> Union[StockData, Dict[str, str]]:
            return self._download_stock_data_internal(symbol, start_date, end_date)

        if use_retry:
            return self._retry_with_backoff(_run, symbol)
        return _run()

    def download_financial_data(
        self, symbol: str, use_retry: bool = True
    ) -> Union[FinancialData, Dict[str, str]]:
        """下载财务数据（损益表、资产负债表、现金流 + 基本信息）"""
        def _run() -> Union[FinancialData, Dict[str, str]]:
            return self._download_financial_data_internal(symbol)

        if use_retry:
            return self._retry_with_backoff(_run, symbol)
        return _run()

    # 内部实现
    def _download_stock_data_internal(
        self, symbol: str, start_date: Optional[str], end_date: Optional[str]
    ) -> Union[StockData, Dict[str, str]]:
        if not self.api_key:
            return {
                "error": (
                    "缺少 Twelve Data API Key（请设置环境变量 TWELVE_DATA_API_KEY / TWELVEDATA_API_KEY / TD_API_KEY，"
                    "或通过 --api-key 明确传入）"
                )
            }

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            start = start_date or "2000-01-01"
            end = end_date or today

            params = {
                "symbol": symbol,
                "interval": "1day",
                "start_date": start,
                "end_date": end,
                "order": "ASC",
                "outputsize": 5000,
                "format": "JSON",
                "apikey": self.api_key,
            }
            url = f"{self.base_url}/time_series"

            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                return {"error": f"Twelve Data 请求失败: HTTP {resp.status_code}"}

            data = resp.json()
            # 错误格式兼容：可能有 code/status/message
            if isinstance(data, dict) and data.get("status") == "error":
                msg = data.get("message") or "Twelve Data 返回错误"
                return {"error": f"{symbol}: {msg}"}

            values = data.get("values") if isinstance(data, dict) else None
            if not values:
                return {"error": f"{symbol}: 未获取到价格数据"}

            # 组装 PriceData（确保按时间升序）
            # Twelve Data 通常已按 ASC 返回；为稳妥，按 datetime 排序
            def _parse_float(v: Any) -> float:
                try:
                    return float(v)
                except Exception:
                    return 0.0

            def _parse_int(v: Any) -> int:
                try:
                    return int(float(v))
                except Exception:
                    return 0

            values_sorted = sorted(values, key=lambda x: x.get("datetime", ""))
            dates: List[str] = [str(it.get("datetime", ""))[:10] for it in values_sorted]
            open_: List[float] = [_parse_float(it.get("open")) for it in values_sorted]
            high_: List[float] = [_parse_float(it.get("high")) for it in values_sorted]
            low_: List[float] = [_parse_float(it.get("low")) for it in values_sorted]
            close_: List[float] = [_parse_float(it.get("close")) for it in values_sorted]
            volume_: List[int] = [_parse_int(it.get("volume")) for it in values_sorted]

            price = PriceData(
                dates=dates,
                open=open_,
                high=high_,
                low=low_,
                close=close_,
                volume=volume_,
                adj_close=close_.copy(),
            )
            stats = SummaryStats(
                min_price=min(close_) if close_ else 0.0,
                max_price=max(close_) if close_ else 0.0,
                mean_price=(sum(close_) / len(close_)) if close_ else 0.0,
                std_price=0.0,
                total_volume=sum(volume_) if volume_ else 0,
            )
            sd = StockData(
                symbol=symbol,
                start_date=dates[0] if dates else start,
                end_date=dates[-1] if dates else end,
                data_points=len(dates),
                price_data=price,
                summary_stats=stats,
                downloaded_at=datetime.now().isoformat(),
                data_source="twelvedata",
                incremental_update=True,
                no_new_data=(len(dates) == 0),
            )
            return sd
        except Exception as e:
            err = f"Twelve Data 下载失败 {symbol}: {e}"
            self.logger.error(err)
            return {"error": err}

    # ---------- 财务内部实现 ----------
    def _fetch_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        p = dict(params)
        p.setdefault("apikey", self.api_key)
        resp = self.session.get(url, params=p, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("status") == "error":
            msg = data.get("message") or "remote error"
            raise RuntimeError(msg)
        return data

    def _download_financial_data_internal(self, symbol: str) -> Union[FinancialData, Dict[str, str]]:
        if not self.api_key:
            return {
                "error": (
                    "缺少 Twelve Data API Key（请设置环境变量 TWELVE_DATA_API_KEY / TWELVEDATA_API_KEY / TD_API_KEY，"
                    "或通过 --api-key 明确传入）"
                )
            }
        try:
            # 基本信息（profile）
            try:
                prof = self._fetch_json("profile", {"symbol": symbol})
                # 可能返回 {data: {...}} 或列表
                prof_data = (
                    (prof.get("data") if isinstance(prof, dict) else prof) or {}
                )
                if isinstance(prof_data, list) and prof_data:
                    prof_data = prof_data[0]
            except Exception:
                prof_data = {}

            basic_info = BasicInfo(
                company_name=str(prof_data.get("name", "")) if prof_data else "",
                sector=str(prof_data.get("sector", "")) if prof_data else "",
                industry=str(prof_data.get("industry", "")) if prof_data else "",
                market_cap=int(float(prof_data.get("market_cap", 0) or 0)) if prof_data else 0,
                employees=int(float(prof_data.get("employees", 0) or 0)) if prof_data else 0,
                description=str(prof_data.get("description", "")) if prof_data else "",
            )

            # 报表：income_statement / balance_sheet / cash_flow
            stmts: Dict[str, FinancialStatement] = {}
            for endpoint, key in (
                ("income_statement", "income_statement"),
                ("balance_sheet", "balance_sheet"),
                ("cash_flow", "cash_flow"),
            ):
                try:
                    raw = self._fetch_json(endpoint, {"symbol": symbol})
                    # 常见格式：{"symbol":..., "financials":[{...}]} 或 {"data":[{...}]}
                    rows = (
                        raw.get("financials")
                        if isinstance(raw, dict)
                        else None
                    ) or (raw.get("data") if isinstance(raw, dict) else None)
                    if not rows and isinstance(raw, list):
                        rows = raw
                    if not rows:
                        continue
                    stmt = self._rows_to_statement(key, rows)
                    if stmt and stmt.periods:
                        stmts[key] = stmt
                except Exception as ex:
                    self.logger.warning(f"获取 {endpoint} 失败: {ex}")

            fin = FinancialData(
                symbol=symbol,
                basic_info=BasicInfo(
                    company_name=basic_info.company_name,
                    sector=basic_info.sector,
                    industry=basic_info.industry,
                    market_cap=basic_info.market_cap,
                    employees=basic_info.employees,
                    description=basic_info.description,
                ),
                financial_statements=stmts,
                downloaded_at=datetime.now().isoformat(),
            )
            return fin
        except Exception as e:
            err = f"Twelve Data 财务下载失败 {symbol}: {e}"
            self.logger.error(err)
            return {"error": err}

    def _rows_to_statement(self, stmt_type: str, rows: List[Dict[str, Any]]) -> FinancialStatement:
        # 识别期间字段
        periods: List[str] = []
        items: Dict[str, List[Optional[float]]] = {}
        # 取前 N 期，按时间降序（最新在前）
        def _to_date(r: Dict[str, Any]) -> str:
            for k in ("fiscal_date", "date", "period", "reportDate"):
                if k in r and r[k]:
                    s = str(r[k])
                    return s[:10]
            return ""

        sorted_rows = sorted(rows, key=_to_date, reverse=True)
        periods = [_to_date(r) or f"idx{i}" for i, r in enumerate(sorted_rows)]
        # 收集所有数值型键，排除元字段
        exclude = {
            "symbol",
            "currency",
            "reportedCurrency",
            "fiscal_year",
            "fiscal_quarter",
            "fiscal_date",
            "date",
            "period",
            "reportDate",
            "type",
            "ebitdaAdjusted",
        }
        keys: List[str] = []
        for r in sorted_rows:
            for k, v in r.items():
                if k in exclude:
                    continue
                if k not in keys and isinstance(v, (int, float, str)):
                    keys.append(k)

        def _to_float(x: Any) -> Optional[float]:
            try:
                if x is None or x == "":
                    return None
                return float(x)
            except Exception:
                return None

        for k in keys:
            values: List[Optional[float]] = []
            for r in sorted_rows:
                values.append(_to_float(r.get(k)))
            items[k] = values

        return FinancialStatement(statement_type=stmt_type, periods=periods, items=items)
