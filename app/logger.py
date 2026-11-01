"""Centralised logging configuration for NewsEdge."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import get_settings


def setup_logging() -> logging.Logger:
    """Configure and return the root *newsedge* logger.

    * Console handler  → always attached (rich-formatted if available).
    * File handler     → ``logs/newsedge.log`` (rotating daily is left to
      the deployment layer; here we just append).
    """
    settings = get_settings()
    log_dir: Path = settings.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("newsedge")
    if logger.handlers:
        # Already configured (e.g. tests importing twice)
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Ensure stdout and stderr use UTF-8 on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File
    file_handler = logging.FileHandler(log_dir / "newsedge.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
