#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ..pipeline.context import AnalysisContext


class Operator(ABC):
    """Operator interface for pluggable analysis steps."""

    name: str = "operator"

    @abstractmethod
    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        """Execute operator with the provided context and return structured results."""
        raise NotImplementedError
