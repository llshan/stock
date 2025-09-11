#!/usr/bin/env python3
"""
Finnhub 下载器

支持：
- 日线价格数据：/stock/candle（resolution=D）
- 财务数据与公司概况：/stock/profile2, /stock/financials-reported（回退 /stock/financials）

需要 API Key：
- 环境变量 FINNHUB_API_KEY 或 FINNHUB_TOKEN，或构造函数传入 api_key
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import requests

from .base import BaseDownloader
from ..models import (
    PriceData,
    StockData,
    SummaryStats,
    FinancialData,
    FinancialStatement,
    BasicInfo,
)


class FinnhubDownloader(BaseDownloader):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://finnhub.io/api/v1",
        max_retries: int = 3,
        base_delay: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(max_retries=max_retries, base_delay=base_delay)
        key = api_key or os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_TOKEN")
        self.api_key = key.strip() if isinstance(key, str) and key.strip() else None
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.logger = logging.getLogger(__name__)

    # ---------- 公共接口 ----------
    def download_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_retry: bool = True,
    ) -> Union[StockData, Dict[str, str]]:
        def _run() -> Union[StockData, Dict[str, str]]:
            return self._download_stock_data_internal(symbol, start_date, end_date)

        return self._retry_with_backoff(_run, symbol) if use_retry else _run()

    def download_financial_data(
        self, symbol: str, use_retry: bool = True
    ) -> Union[FinancialData, Dict[str, str]]:
        def _run() -> Union[FinancialData, Dict[str, str]]:
            return self._download_financial_data_internal(symbol)

        return self._retry_with_backoff(_run, symbol) if use_retry else _run()

    # ---------- 价格内部实现 ----------
    def _download_stock_data_internal(
        self, symbol: str, start_date: Optional[str], end_date: Optional[str]
    ) -> Union[StockData, Dict[str, str]]:
        if not self.api_key:
            return {
                "error": (
                    "缺少 Finnhub API Key（请设置 FINNHUB_API_KEY / FINNHUB_TOKEN，或通过构造参数 api_key 传入）"
                )
            }
        try:
            # 时间范围
            start_str = start_date or "2000-01-01"
            end_str = end_date or datetime.now().strftime("%Y-%m-%d")
            start_ts = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_str, "%Y-%m-%d").timestamp())

            url = f"{self.base_url}/stock/candle"
            params = {
                "symbol": symbol,
                "resolution": "D",
                "from": start_ts,
                "to": end_ts,
                "token": self.api_key,
            }
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, dict) or data.get("s") != "ok":
                msg = data.get("s") if isinstance(data, dict) else str(data)[:120]
                return {"error": f"Finnhub candle 返回异常: {msg}"}

            t: List[int] = data.get("t", [])
            o = data.get("o", [])
            h = data.get("h", [])
            l = data.get("l", [])
            c = data.get("c", [])
            v = data.get("v", [])
            if not t:
                return {"error": f"{symbol}: 无价格数据"}

            dates = [datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") for ts in t]
            price = PriceData(
                dates=dates,
                open=list(map(float, o)),
                high=list(map(float, h)),
                low=list(map(float, l)),
                close=list(map(float, c)),
                volume=list(map(int, v)),
                adj_close=list(map(float, c)),
            )
            stats = SummaryStats(
                min_price=min(price.close) if price.close else 0.0,
                max_price=max(price.close) if price.close else 0.0,
                mean_price=(sum(price.close) / len(price.close)) if price.close else 0.0,
                std_price=0.0,
                total_volume=sum(price.volume) if price.volume else 0,
            )
            sd = StockData(
                symbol=symbol,
                start_date=dates[0],
                end_date=dates[-1],
                data_points=len(dates),
                price_data=price,
                summary_stats=stats,
                downloaded_at=datetime.now().isoformat(),
                data_source="finnhub",
                incremental_update=True,
                no_new_data=(len(dates) == 0),
            )
            return sd
        except Exception as e:
            err = f"Finnhub 价格下载失败 {symbol}: {e}"
            self.logger.error(err)
            return {"error": err}

    # ---------- 财务内部实现 ----------
    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        p = dict(params)
        p.setdefault("token", self.api_key)
        resp = self.session.get(url, params=p, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _download_financial_data_internal(self, symbol: str) -> Union[FinancialData, Dict[str, str]]:
        if not self.api_key:
            return {
                "error": (
                    "缺少 Finnhub API Key（请设置 FINNHUB_API_KEY / FINNHUB_TOKEN，或通过构造参数 api_key 传入）"
                )
            }
        try:
            # 公司概况
            try:
                prof = self._get_json("stock/profile2", {"symbol": symbol})
            except Exception:
                prof = {}
            basic_info = BasicInfo(
                company_name=str(prof.get("name", "")) if isinstance(prof, dict) else "",
                sector=str(prof.get("finnhubIndustry", "")) if isinstance(prof, dict) else "",
                industry=str(prof.get("finnhubIndustry", "")) if isinstance(prof, dict) else "",
                market_cap=int(float(prof.get("marketCapitalization", 0) or 0)) if isinstance(prof, dict) else 0,
                employees=int(float(prof.get("employeeTotal", 0) or 0)) if isinstance(prof, dict) else 0,
                description=str(prof.get("weburl", "")) if isinstance(prof, dict) else "",
            )

            stmts: Dict[str, FinancialStatement] = {}
            # 优先 financials-reported
            try:
                reported = self._get_json("stock/financials-reported", {"symbol": symbol})
                rows = reported.get("data") if isinstance(reported, dict) else None
                if rows:
                    self._parse_reported_rows(rows, stmts)
            except Exception as e:
                self.logger.warning(f"financials-reported 失败: {e}")

            # 回退 legacy financials 接口
            if not stmts:
                for endpoint, key, stmt_param in (
                    ("stock/financials", "income_statement", "ic"),
                    ("stock/financials", "balance_sheet", "bs"),
                    ("stock/financials", "cash_flow", "cf"),
                ):
                    try:
                        raw = self._get_json(endpoint, {"symbol": symbol, "statement": stmt_param, "freq": "annual"})
                        rows = raw.get("financials") if isinstance(raw, dict) else None
                        if rows:
                            stmt = self._rows_to_statement_legacy(key, rows)
                            if stmt and stmt.periods:
                                stmts[key] = stmt
                    except Exception as ex:
                        self.logger.warning(f"获取 {endpoint}({stmt_param}) 失败: {ex}")

            fin = FinancialData(
                symbol=symbol,
                basic_info=basic_info,
                financial_statements=stmts,
                downloaded_at=datetime.now().isoformat(),
            )
            return fin
        except Exception as e:
            err = f"Finnhub 财务下载失败 {symbol}: {e}"
            self.logger.error(err)
            return {"error": err}

    def _parse_reported_rows(self, rows: List[Dict[str, Any]], out: Dict[str, FinancialStatement]) -> None:
        # rows: [{year, period, endDate, report: { ic: [...], bs: [...], cf: [...] }}]
        def _end_date(r: Dict[str, Any]) -> str:
            for k in ("endDate", "reportDate", "period"):
                if k in r and r[k]:
                    s = str(r[k])
                    return s[:10]
            if "year" in r and r.get("year"):
                return f"{r['year']}-12-31"
            return ""

        sorted_rows = sorted(rows, key=_end_date, reverse=True)
        periods = [_end_date(r) or f"idx{i}" for i, r in enumerate(sorted_rows)]

        items_map: Dict[str, Dict[str, List[Optional[float]]]] = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        }

        # 收集键
        for r in sorted_rows:
            rep = r.get("report") or {}
            for sec, key in (("ic", "income_statement"), ("bs", "balance_sheet"), ("cf", "cash_flow")):
                arr = rep.get(sec)
                if not isinstance(arr, list):
                    continue
                for entry in arr:
                    name = entry.get("label") or entry.get("concept") or entry.get("field") or entry.get("name")
                    if not name:
                        continue
                    if name not in items_map[key]:
                        items_map[key][name] = [None] * len(sorted_rows)

        # 填充值
        for idx, r in enumerate(sorted_rows):
            rep = r.get("report") or {}
            for sec, key in (("ic", "income_statement"), ("bs", "balance_sheet"), ("cf", "cash_flow")):
                arr = rep.get(sec)
                if not isinstance(arr, list):
                    continue
                for entry in arr:
                    name = entry.get("label") or entry.get("concept") or entry.get("field") or entry.get("name")
                    if not name:
                        continue
                    try:
                        val = float(entry.get("value")) if entry.get("value") not in (None, "") else None
                    except Exception:
                        val = None
                    items_map[key][name][idx] = val

        for key, items in items_map.items():
            out[key] = FinancialStatement(statement_type=key, periods=periods, items=items)

    def _rows_to_statement_legacy(self, stmt_type: str, rows: List[Dict[str, Any]]) -> FinancialStatement:
        # rows: [{"year":..., "quarter":..., "data": [{"concept":..., "value":...}, ...]}]
        def _to_period(r: Dict[str, Any]) -> str:
            y = str(r.get("year", ""))
            q = str(r.get("quarter", ""))
            if y and q:
                try:
                    qn = int(q)
                    # 简化：直接用季度末的近似日期
                    month = 3 * qn
                    return f"{y}-{month:02d}-28"
                except Exception:
                    pass
            return y or ""

        sorted_rows = sorted(rows, key=_to_period, reverse=True)
        periods = [_to_period(r) or f"idx{i}" for i, r in enumerate(sorted_rows)]

        # 收集所有概念键
        keys: List[str] = []
        for r in sorted_rows:
            data_arr = r.get("data")
            if isinstance(data_arr, list):
                for e in data_arr:
                    name = e.get("label") or e.get("concept") or e.get("field") or e.get("name")
                    if name and name not in keys:
                        keys.append(name)
        # 填充值
        items: Dict[str, List[Optional[float]]] = {}
        for k in keys:
            vals: List[Optional[float]] = []
            for r in sorted_rows:
                data_arr = r.get("data")
                value: Optional[float] = None
                if isinstance(data_arr, list):
                    for e in data_arr:
                        name = e.get("label") or e.get("concept") or e.get("field") or e.get("name")
                        if name == k:
                            try:
                                value = float(e.get("value")) if e.get("value") not in (None, "") else None
                            except Exception:
                                value = None
                            break
                vals.append(value)
            items[k] = vals

        return FinancialStatement(statement_type=stmt_type, periods=periods, items=items)

