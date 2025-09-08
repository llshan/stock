#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import pandas as pd


@dataclass
class AnalysisContext:
    symbol: str
    data: pd.DataFrame
    config: Any
    extras: Dict[str, Any] = field(default_factory=dict)

