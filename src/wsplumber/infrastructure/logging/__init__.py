# src/wsplumber/infrastructure/logging/__init__.py
"""Sistema de Logging seguro y estructurado."""

from wsplumber.infrastructure.logging.safe_logger import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging"]
