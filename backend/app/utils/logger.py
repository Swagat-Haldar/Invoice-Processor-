from __future__ import annotations

import logging
import os
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_error_trace(exc: BaseException) -> str:
    # Avoid importing traceback everywhere; keep the helper centralized.
    import traceback

    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

