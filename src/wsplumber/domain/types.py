# src/wsplumber/domain/types.py
"""
Tipos centralizados para type hints consistentes.

Este módulo define todos los tipos custom usados en el proyecto
para garantizar consistencia y facilitar el debug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    NewType,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

# ============================================
# TYPE ALIASES - IDs
# ============================================

OperationId = NewType("OperationId", str)
"""ID único de operación. Formato: 'EURUSD_001_BUY'"""

CycleId = NewType("CycleId", str)
"""ID único de ciclo. Formato: 'EURUSD_001'"""

RecoveryId = NewType("RecoveryId", str)
"""ID único de recovery. Formato: 'REC_EURUSD_001_001'"""

HedgeId = NewType("HedgeId", str)
"""ID único de cobertura. Formato: 'COB_EURUSD_001_BUY'"""

BrokerTicket = NewType("BrokerTicket", str)
"""Ticket/ID del broker. Formato: '12345678'"""

CheckpointId = NewType("CheckpointId", str)
"""ID de checkpoint de estado."""


# ============================================
# TYPE ALIASES - VALORES DE TRADING
# ============================================

Pips = NewType("Pips", float)
"""Valor en pips. 1 pip = 0.0001 para pares XXX/USD"""

Price = NewType("Price", Decimal)
"""Precio con precisión decimal."""

LotSize = NewType("LotSize", float)
"""Tamaño de posición en lotes. 0.01 = micro lote"""

Money = NewType("Money", Decimal)
"""Cantidad monetaria en EUR."""

Spread = NewType("Spread", float)
"""Spread en pips."""


# ============================================
# TYPE ALIASES - TRADING
# ============================================

CurrencyPair = NewType("CurrencyPair", str)
"""Par de divisas. Formato: 'EURUSD', 'GBPUSD'"""

Direction = Literal["buy", "sell"]
"""Dirección de operación."""

Timestamp = NewType("Timestamp", datetime)
"""Timestamp con timezone."""


# ============================================
# ENUMS
# ============================================


class OperationType(str, Enum):
    """Tipos de operación en el sistema."""

    MAIN_BUY = "main_buy"
    MAIN_SELL = "main_sell"
    HEDGE_BUY = "hedge_buy"
    HEDGE_SELL = "hedge_sell"
    RECOVERY_BUY = "recovery_buy"
    RECOVERY_SELL = "recovery_sell"

    @property
    def is_buy(self) -> bool:
        return "buy" in self.value

    @property
    def is_sell(self) -> bool:
        return "sell" in self.value

    @property
    def is_main(self) -> bool:
        return self.value.startswith("main_")

    @property
    def is_hedge(self) -> bool:
        return self.value.startswith("hedge_")

    @property
    def is_recovery(self) -> bool:
        return self.value.startswith("recovery_")


class OperationStatus(str, Enum):
    """Estados posibles de una operación."""

    PENDING = "pending"  # Orden pendiente (stop order)
    ACTIVE = "active"  # Posición abierta
    TP_HIT = "tp_hit"  # Take profit tocado
    NEUTRALIZED = "neutralized"  # Neutralizada por cobertura
    CLOSED = "closed"  # Cerrada completamente
    CANCELLED = "cancelled"  # Cancelada antes de activarse


class CycleType(str, Enum):
    """Tipos de ciclo."""

    MAIN = "main"
    RECOVERY = "recovery"


class CycleStatus(str, Enum):
    """Estados posibles de un ciclo."""

    PENDING = "pending"  # Creado pero sin órdenes confirmadas
    ACTIVE = "active"  # Operando normalmente
    HEDGED = "hedged"  # Con cobertura activa
    IN_RECOVERY = "in_recovery"  # En proceso de recovery
    CLOSED = "closed"  # Completado
    PAUSED = "paused"  # Pausado manualmente


class SignalType(str, Enum):
    """Tipos de señal del core de estrategia."""

    NO_ACTION = "no_action"
    OPEN_CYCLE = "open_cycle"
    ACTIVATE_HEDGE = "activate_hedge"
    OPEN_RECOVERY = "open_recovery"
    CLOSE_OPERATIONS = "close_operations"
    PAUSE = "pause"


class AlertSeverity(str, Enum):
    """Severidad de alertas."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConnectionStatus(str, Enum):
    """Estado de conexión."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class CircuitState(str, Enum):
    """Estado del circuit breaker."""

    CLOSED = "closed"  # Funcionando normal
    OPEN = "open"  # Bloqueado
    HALF_OPEN = "half_open"  # Probando recuperación


# ============================================
# GENERIC RESULT TYPES
# ============================================

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass
class Result(Generic[T]):
    """
    Result type para operaciones que pueden fallar.

    Evita usar excepciones para control de flujo.
    Inspirado en Rust's Result<T, E>.
    """

    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, value: T, **metadata: Any) -> Result[T]:
        """Crea un Result exitoso."""
        return cls(success=True, value=value, metadata=metadata)

    @classmethod
    def fail(
        cls,
        error: str,
        code: Optional[str] = None,
        **metadata: Any,
    ) -> Result[T]:
        """Crea un Result fallido."""
        return cls(
            success=False,
            error=error,
            error_code=code,
            metadata=metadata,
        )

    def unwrap(self) -> T:
        """Obtiene el valor o lanza ValueError."""
        if not self.success:
            raise ValueError(f"Unwrap failed: {self.error} (code: {self.error_code})")
        return self.value  # type: ignore

    def unwrap_or(self, default: T) -> T:
        """Obtiene el valor o retorna default."""
        return self.value if self.success and self.value is not None else default

    def map(self, func: Callable[[T], Any]) -> Result[Any]:
        """Aplica función al valor si es exitoso."""
        if self.success and self.value is not None:
            try:
                return Result.ok(func(self.value))
            except Exception as e:
                return Result.fail(str(e))
        return Result.fail(self.error or "No value", self.error_code)

    def __bool__(self) -> bool:
        """Permite usar Result en contextos booleanos."""
        return self.success


@dataclass
class AsyncResult(Generic[T]):
    """Result para operaciones async."""

    success: bool
    value: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    async def from_awaitable(cls, awaitable: Awaitable[T]) -> AsyncResult[T]:
        """Crea AsyncResult desde un awaitable."""
        try:
            value = await awaitable
            return cls(success=True, value=value)
        except Exception as e:
            return cls(success=False, error=str(e))


# ============================================
# VALUE OBJECTS
# ============================================


@dataclass(frozen=True)
class PriceLevel:
    """Nivel de precio inmutable."""

    value: Decimal
    pair: CurrencyPair

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(f"Price must be positive: {self.value}")

    def to_pips(self, other: PriceLevel) -> Pips:
        """Calcula diferencia en pips con otro nivel."""
        if self.pair != other.pair:
            raise ValueError(f"Cannot compare different pairs: {self.pair} vs {other.pair}")

        diff = abs(self.value - other.value)
        # Ajustar para pares JPY (2 decimales vs 4)
        multiplier = 100 if "JPY" in self.pair else 10000
        return Pips(float(diff * multiplier))


@dataclass(frozen=True)
class MoneyAmount:
    """Cantidad monetaria inmutable."""

    value: Decimal
    currency: str = "EUR"

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Money cannot be negative: {self.value}")

    def __add__(self, other: MoneyAmount) -> MoneyAmount:
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} vs {other.currency}")
        return MoneyAmount(self.value + other.value, self.currency)

    def __sub__(self, other: MoneyAmount) -> MoneyAmount:
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies")
        return MoneyAmount(self.value - other.value, self.currency)


# ============================================
# DATA CLASSES PARA COMUNICACIÓN
# ============================================


@dataclass
class TickData:
    """Datos de un tick de mercado."""

    pair: CurrencyPair
    bid: Price
    ask: Price
    timestamp: Timestamp
    spread_pips: Pips

    @property
    def mid(self) -> Price:
        """Precio medio."""
        return Price((self.bid + self.ask) / 2)


@dataclass
class OrderRequest:
    """Solicitud de orden al broker."""

    operation_id: OperationId
    pair: CurrencyPair
    order_type: OperationType
    entry_price: Price
    tp_price: Price
    lot_size: LotSize
    comment: str = ""


@dataclass
class OrderResult:
    """Resultado de envío de orden."""

    success: bool
    broker_ticket: Optional[BrokerTicket] = None
    error_message: Optional[str] = None
    fill_price: Optional[Price] = None
    timestamp: Optional[Timestamp] = None


@dataclass
class StrategySignal:
    """Señal emitida por el core de estrategia."""

    signal_type: SignalType
    pair: CurrencyPair
    direction: Optional[Direction] = None
    entry_price: Optional[Price] = None
    tp_price: Optional[Price] = None
    operations_to_close: Optional[List[OperationId]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Timestamp = field(default_factory=datetime.now)


# ============================================
# TYPE GUARDS
# ============================================


def is_valid_pair(value: str) -> bool:
    """Verifica si es un par de divisas válido."""
    valid_pairs = {
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "USDCHF",
        "AUDUSD",
        "NZDUSD",
        "USDCAD",
        "EURGBP",
        "EURJPY",
        "GBPJPY",
    }
    return value.upper() in valid_pairs


def is_valid_lot_size(value: float) -> bool:
    """Verifica si es un tamaño de lote válido."""
    return 0.01 <= value <= 100.0


def is_valid_pips(value: float) -> bool:
    """Verifica si es un valor de pips razonable."""
    return -10000 <= value <= 10000
