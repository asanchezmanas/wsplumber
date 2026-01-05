# src/wsplumber/infrastructure/logging/safe_logger.py
"""
Sistema de Logging Seguro.

Este módulo implementa logging que:
1. Sanitiza información sensible automáticamente
2. Usa terminología pública (no revela estrategia)
3. Soporta JSON estructurado
4. Incluye correlation IDs para tracing
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Set

# Context variables para tracing
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
operation_context: ContextVar[str] = ContextVar("operation_context", default="")


# ============================================
# TERMINOLOGÍA PÚBLICA
# ============================================

TERMINOLOGY_MAP: Dict[str, str] = {
    # Entidades (interno → público)
    "cycle": "position_group",
    "main_cycle": "primary_group",
    "recovery_cycle": "secondary_group",
    "hedge": "balance_position",
    "recovery": "correction",
    "neutralize": "offset",
    "neutralized": "offset",
    # Acciones
    "open_cycle": "init_group",
    "activate_hedge": "balance",
    "open_recovery": "correct",
    "close_cycle": "finalize_group",
    # Métricas
    "pips_locked": "units_pending",
    "recovery_ratio": "correction_frequency",
    "tp_hit": "target_reached",
    "drawdown": "temporary_variance",
    # Estados
    "in_recovery": "correcting",
    "hedged": "balanced",
}


def to_public_term(internal_term: str) -> str:
    """Convierte término interno a público."""
    return TERMINOLOGY_MAP.get(internal_term.lower(), internal_term)


def sanitize_message(message: str, use_public_terms: bool = True) -> str:
    """Sanitiza mensaje reemplazando términos internos."""
    if not use_public_terms:
        return message

    result = message
    for internal, public in TERMINOLOGY_MAP.items():
        # Reemplazar con case-insensitive
        pattern = re.compile(re.escape(internal), re.IGNORECASE)
        result = pattern.sub(public, result)

    return result


# ============================================
# CONFIGURACIÓN DE SANITIZACIÓN
# ============================================


@dataclass
class SanitizerConfig:
    """Configuración de sanitización de logs."""

    # Campos a NUNCA loguear (se reemplazan por ***)
    secret_fields: Set[str] = field(
        default_factory=lambda: {
            # Credenciales
            "password",
            "api_key",
            "secret",
            "token",
            "private_key",
            # Parámetros de estrategia (CRÍTICO)
            "entry_threshold",
            "exit_threshold",
            "recovery_formula",
            "pip_calculation",
            "strategy_params",
            "decision_factors",
            "internal_state",
            "calculation_result",
            "threshold",
            "multiplier",
        }
    )

    # Campos a ofuscar parcialmente (mostrar solo inicio/fin)
    partial_mask_fields: Set[str] = field(
        default_factory=lambda: {
            "account_id",
            "ticket",
            "broker_ticket",
            "broker_response",
            "operation_id",
            "cycle_id",
        }
    )

    # Campos numéricos a redondear (ocultar precisión exacta)
    round_fields: Dict[str, int] = field(
        default_factory=lambda: {
            "entry_price": 3,
            "tp_price": 3,
            "close_price": 3,
            "balance": 0,
            "profit": 0,
            "profit_pips": 1,
            "spread": 1,
        }
    )

    # Usar terminología pública
    use_public_terms: bool = True

    # Patrones a eliminar de mensajes de error
    error_sanitize_patterns: list = field(
        default_factory=lambda: [
            (r"/.*?/core/.*?\.py", "[core]"),
            (r"threshold=[\d.]+", "threshold=***"),
            (r"multiplier=[\d.]+", "multiplier=***"),
            (r"formula=.*?(?=\s|$)", "formula=***"),
        ]
    )


# Configuraciones por entorno
SANITIZER_CONFIGS = {
    "development": SanitizerConfig(
        secret_fields={"password", "api_key", "token", "secret"},
        partial_mask_fields=set(),
        round_fields={},
        use_public_terms=False,  # En dev, usar términos reales
    ),
    "staging": SanitizerConfig(
        use_public_terms=True,
    ),
    "production": SanitizerConfig(
        use_public_terms=True,
    ),
}


# ============================================
# SAFE LOGGER
# ============================================


class LogLevel(str, Enum):
    """Niveles de log."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SafeLogger:
    """
    Logger que sanitiza información sensible automáticamente.
    """

    def __init__(
        self,
        name: str,
        config: Optional[SanitizerConfig] = None,
        output_json: bool = True,
    ):
        self.name = name
        self.config = config or SanitizerConfig()
        self.output_json = output_json
        self._logger = logging.getLogger(name)

    def _sanitize_value(self, key: str, value: Any) -> Any:
        """Sanitiza un valor según su tipo y configuración."""
        key_lower = key.lower()

        # Campos secretos → ***REDACTED***
        if key_lower in self.config.secret_fields:
            return "***REDACTED***"

        # Campos parcialmente enmascarados
        if key_lower in self.config.partial_mask_fields:
            if isinstance(value, str) and len(value) > 4:
                return f"{value[:2]}***{value[-2:]}"
            return "***"

        # Campos numéricos a redondear
        if key_lower in self.config.round_fields:
            if isinstance(value, (int, float)):
                decimals = self.config.round_fields[key_lower]
                return round(value, decimals)

        return value

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza un diccionario recursivamente."""
        sanitized = {}

        for key, value in data.items():
            # Convertir key a terminología pública si está configurado
            public_key = to_public_term(key) if self.config.use_public_terms else key

            if isinstance(value, dict):
                sanitized[public_key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[public_key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[public_key] = self._sanitize_value(key, value)

        return sanitized

    def _sanitize_error_message(self, message: str) -> str:
        """Sanitiza mensajes de error para no revelar lógica interna."""
        result = message
        for pattern, replacement in self.config.error_sanitize_patterns:
            result = re.sub(pattern, replacement, result)
        return result

    def _build_log_entry(
        self,
        level: str,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Construye entrada de log estructurada y sanitizada."""
        # Sanitizar kwargs
        sanitized_data = self._sanitize_dict(kwargs) if kwargs else {}

        # Sanitizar mensaje
        public_message = sanitize_message(message, self.config.use_public_terms)

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "message": public_message,
        }

        # Añadir correlation ID si existe
        corr_id = correlation_id.get()
        if corr_id:
            entry["correlation_id"] = corr_id

        # Añadir contexto si existe
        ctx = operation_context.get()
        if ctx:
            entry["context"] = ctx

        # Añadir datos sanitizados
        if sanitized_data:
            entry["data"] = sanitized_data

        # Añadir excepción sanitizada
        if exception:
            entry["error"] = {
                "type": type(exception).__name__,
                "message": self._sanitize_error_message(str(exception)),
            }

        return entry

    def _log(
        self,
        level: LogLevel,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Método interno de logging."""
        entry = self._build_log_entry(level.value, message, exception, **kwargs)

        if self.output_json:
            log_str = json.dumps(entry, default=str, ensure_ascii=False)
        else:
            log_str = f"[{entry['timestamp']}] {level.value} - {entry['message']}"
            if entry.get("data"):
                log_str += f" | {entry['data']}"

        getattr(self._logger, level.value.lower())(log_str)

    # ============================================
    # MÉTODOS PÚBLICOS DE LOGGING
    # ============================================

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log nivel DEBUG."""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log nivel INFO."""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log nivel WARNING."""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(
        self, message: str, exception: Optional[Exception] = None, **kwargs: Any
    ) -> None:
        """Log nivel ERROR."""
        self._log(LogLevel.ERROR, message, exception, **kwargs)

    def critical(
        self, message: str, exception: Optional[Exception] = None, **kwargs: Any
    ) -> None:
        """Log nivel CRITICAL."""
        self._log(LogLevel.CRITICAL, message, exception, **kwargs)

    # ============================================
    # MÉTODOS ESPECÍFICOS DE TRADING (PRE-SANITIZADOS)
    # ============================================

    def order_sent(self, operation_id: str, order_type: str, **kwargs: Any) -> None:
        """Log de orden enviada."""
        self.info(
            "Order sent to broker",
            event="order_sent",
            operation_id=operation_id,
            order_type=order_type,
            **kwargs,
        )

    def order_filled(
        self, operation_id: str, broker_ticket: str, **kwargs: Any
    ) -> None:
        """Log de orden ejecutada."""
        self.info(
            "Order filled",
            event="order_filled",
            operation_id=operation_id,
            broker_ticket=broker_ticket,
            **kwargs,
        )

    def order_failed(self, operation_id: str, error: str, **kwargs: Any) -> None:
        """Log de orden fallida."""
        self.error(
            "Order failed",
            event="order_failed",
            operation_id=operation_id,
            error=error,
            **kwargs,
        )

    def position_opened(self, group_id: str, direction: str, **kwargs: Any) -> None:
        """Log de posición abierta (términos públicos)."""
        self.info(
            "Position group initialized",
            event="group_init",
            group_id=group_id,
            direction=direction,
            **kwargs,
        )

    def correction_started(self, group_id: str, **kwargs: Any) -> None:
        """Log de recovery iniciado (términos públicos)."""
        self.info(
            "Correction sequence started",
            event="correction_start",
            group_id=group_id,
            **kwargs,
        )

    def reconciliation_done(self, discrepancies: int, **kwargs: Any) -> None:
        """Log de reconciliación completada."""
        level = "warning" if discrepancies > 0 else "info"
        getattr(self, level)(
            "Reconciliation completed",
            event="reconciliation",
            discrepancies=discrepancies,
            **kwargs,
        )

    def checkpoint_created(self, checkpoint_id: str, **kwargs: Any) -> None:
        """Log de checkpoint creado."""
        self.info(
            "State checkpoint created",
            event="checkpoint",
            checkpoint_id=checkpoint_id,
            **kwargs,
        )


# ============================================
# FACTORY Y CONFIGURACIÓN
# ============================================


def get_logger(name: str, environment: str = "production") -> SafeLogger:
    """
    Factory para obtener logger seguro configurado.
    """
    config = SANITIZER_CONFIGS.get(environment, SanitizerConfig())
    return SafeLogger(name, config)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    json_output: bool = True,
    environment: str = "production",
) -> None:
    """
    Configura logging global.
    """
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level))

    handlers = [console_handler]

    # Handler para archivo (si se especifica)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(getattr(logging, level))
        handlers.append(file_handler)

    # Configurar root logger
    logging.basicConfig(
        level=getattr(logging, level),
        handlers=handlers,
        format="%(message)s",  # JSON ya formateado por SafeLogger
    )
