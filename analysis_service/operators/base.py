#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any


class Operator(ABC):
    """Operator interface for pluggable analysis steps."""

    name: str = "operator"

    @abstractmethod
    def run(self, ctx: "AnalysisContext") -> Dict[str, Any]:
        """Execute operator with the provided context and return structured results."""
        raise NotImplementedError


