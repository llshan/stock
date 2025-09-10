#!/usr/bin/env python3
"""
7 日跌幅预警算子（统一实现）

职责：
- 采用与 drop_alert 相同的核心逻辑，仅固定 days=7，默认阈值20%
"""

from __future__ import annotations

import logging

from .drop_alert import DropAlertOperator

logger = logging.getLogger(__name__)


class DropAlert7dOperator(DropAlertOperator):
    name = "drop_alert_7d"

    def __init__(self, threshold_percent: float = 15.0):
        # 统一到通用实现：days 固定为 7
        super().__init__(days=7, threshold_percent=threshold_percent)
