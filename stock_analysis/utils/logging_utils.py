#!/usr/bin/env python3
"""
Centralized logging setup for the entire codebase.

Usage:
    from utils.logging_utils import setup_logging
    setup_logging()  # preferably at app entry points
"""

import logging
from typing import Optional


DEFAULT_LEVEL = logging.INFO
DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def setup_logging(level: Optional[str] = None, fmt: Optional[str] = None):
    """Initialize root logging configuration once.

    - Attempts to read level/format from analysis_service.config if available.
    - Safe to call multiple times; only configures when no handlers exist.
    """
    # If already configured with handlers, only adjust level if provided
    root = logging.getLogger()
    if root.handlers:
        if level:
            root.setLevel(_to_level(level))
        return

    # Try to source from analysis_service.config
    log_level = DEFAULT_LEVEL
    log_format = DEFAULT_FORMAT
    if level:
        log_level = _to_level(level)
    if fmt:
        log_format = fmt

    if not level or not fmt:
        try:
            from analysis_service.config import get_config  # type: ignore
            cfg = get_config().app
            log_level = _to_level(getattr(cfg, "log_level", log_level))
            log_format = getattr(cfg, "log_format", log_format)
        except Exception:
            pass

    logging.basicConfig(level=log_level, format=log_format)


def _to_level(level_val):
    if isinstance(level_val, int):
        return level_val
    if isinstance(level_val, str):
        try:
            return getattr(logging, level_val.upper())
        except Exception:
            return DEFAULT_LEVEL
    return DEFAULT_LEVEL

