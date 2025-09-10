#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional


@dataclass
class Error:
    code: str
    message: str
    severity: Literal['warn', 'error'] = 'error'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OperatorResult:
    data: Optional[Dict[str, Any]]
    error: Optional[Error]
    duration_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'data': self.data,
            'error': self.error.to_dict() if self.error else None,
            'duration_ms': self.duration_ms,
        }


@dataclass
class AnalysisSummary:
    trend: str
    rsi_signal: str
    drop_alert: bool
    drop_change: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    operators: Dict[str, OperatorResult]
    summary: AnalysisSummary
    errors: List[Error]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'operators': {k: v.to_dict() for k, v in self.operators.items()},
            'summary': self.summary.to_dict(),
            'errors': [e.to_dict() for e in self.errors],
            'metrics': self.metrics,
        }
