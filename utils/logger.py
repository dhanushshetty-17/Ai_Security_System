"""Logging setup for the surveillance system."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_dir: str | Path = "outputs/logs") -> None:
    """Configure console and file logging once for the application."""

    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    log_file = path / "security_ai_system.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""

    return logging.getLogger(name)

