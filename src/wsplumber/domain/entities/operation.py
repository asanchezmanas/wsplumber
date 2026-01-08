# src/wsplumber/domain/entities/operation.py
"""
Entidad Operation - Representa una operación de trading.

Esta entidad es el corazón del sistema. Cada operación puede ser:
- Main (principal): Las operaciones iniciales del ciclo
- Hedge (cobertura): Neutraliza pérdidas cuando ambas main se activan
- Recovery (recuperación): Intenta recuperar pérdidas neutralizadas
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from wsplumber.domain.types import (
    BrokerTicket,
    CycleId,
    Direction,
    LotSize,
    Money,
    OperationId,
    OperationStatus,
    OperationType,
    Pips,
    Price,
    CurrencyPair,
    RecoveryId,
)


@dataclass
class Operation:
    """
    Representa una operación de trading individual.

    Una operación puede estar en diferentes estados durante su ciclo de vida:
    - PENDING: Orden colocada pero no ejecutada (stop order)
    - ACTIVE: Posición abierta en el mercado
    - TP_HIT: Take profit alcanzado
    - NEUTRALIZED: Neutralizada por cobertura
    - CLOSED: Cerrada completamente
    - CANCELLED: Cancelada antes de ejecutarse

    Attributes:
        id: Identificador único (ej: "EURUSD_001_BUY")
        cycle_id: ID del ciclo al que pertenece
        pair: Par de divisas
        op_type: Tipo de operación (main, hedge, recovery)
        status: Estado actual
        entry_price: Precio de entrada deseado
        tp_price: Precio de take profit
        lot_size: Tamaño en lotes
    """

    # Identificación
    id: OperationId
    cycle_id: CycleId
    pair: CurrencyPair
    op_type: OperationType
    status: OperationStatus = OperationStatus.PENDING

    # Precios
    entry_price: Price = Price(Decimal("0"))
    tp_price: Price = Price(Decimal("0"))
    actual_entry_price: Optional[Price] = None
    actual_close_price: Optional[Price] = None

    # Tamaño
    lot_size: LotSize = LotSize(0.01)
    pips_target: Pips = Pips(10.0)

    # Resultado
    profit_pips: Pips = Pips(0.0)
    profit_eur: Money = Money(Decimal("0"))

    # Costos
    commission_open: Money = Money(Decimal("7.0"))
    commission_close: Money = Money(Decimal("7.0"))
    swap_total: Money = Money(Decimal("0"))
    slippage_pips: Pips = Pips(0.0)

    # Broker
    broker_ticket: Optional[BrokerTicket] = None
    broker_response: Optional[Dict[str, Any]] = None

    # Relaciones
    linked_operation_id: Optional[OperationId] = None  # Para hedge: la main que cubre
    recovery_id: Optional[RecoveryId] = None  # Para recovery: REC_EURUSD_001_001

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Metadata (para extensibilidad)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ============================================
    # PROPIEDADES CALCULADAS
    # ============================================

    @property
    def direction(self) -> Direction:
        """Dirección de la operación (buy/sell)."""
        return "buy" if self.op_type.is_buy else "sell"

    @property
    def is_buy(self) -> bool:
        """True si es operación de compra."""
        return self.op_type.is_buy

    @property
    def is_sell(self) -> bool:
        """True si es operación de venta."""
        return self.op_type.is_sell

    @property
    def is_main(self) -> bool:
        """True si es operación principal."""
        return self.op_type.is_main

    @property
    def is_hedge(self) -> bool:
        """True si es operación de cobertura."""
        return self.op_type.is_hedge

    @property
    def is_recovery(self) -> bool:
        """True si es operación de recovery."""
        return self.op_type.is_recovery

    @property
    def is_pending(self) -> bool:
        """True si está pendiente de activación."""
        return self.status == OperationStatus.PENDING

    @property
    def is_active(self) -> bool:
        """True si está activa (posición abierta)."""
        return self.status == OperationStatus.ACTIVE

    @property
    def is_closed(self) -> bool:
        """True si está cerrada."""
        return self.status in (
            OperationStatus.CLOSED,
            OperationStatus.TP_HIT,
            OperationStatus.CANCELLED,
        )

    @property
    def is_neutralized(self) -> bool:
        """True si está neutralizada."""
        return self.status == OperationStatus.NEUTRALIZED

    @property
    def current_pips(self) -> float:
        """Pips actuales (flotantes si está activa, realizados si está cerrada)."""
        if self.is_closed:
            return float(self.profit_pips)
        return float(self.metadata.get("current_pips", 0.0))

    @property
    def total_cost(self) -> Money:

        """Costo total de la operación (comisiones + swap)."""
        return Money(self.commission_open + self.commission_close + self.swap_total)

    @property
    def net_profit_pips(self) -> Pips:
        """Profit neto en pips (descontando slippage)."""
        return Pips(float(self.profit_pips) - float(self.slippage_pips))

    @property
    def net_profit_eur(self) -> Money:
        """Profit neto en EUR (descontando costos)."""
        return Money(self.profit_eur - self.total_cost)

    @property
    def days_open(self) -> int:
        """Días que la operación ha estado abierta."""
        if self.activated_at is None:
            return 0

        end_time = self.closed_at or datetime.now()
        delta = end_time - self.activated_at
        return delta.days

    @property
    def pip_value(self) -> float:
        """Valor de 1 pip para esta operación (aproximado)."""
        # Para 0.01 lotes en pares XXX/USD, 1 pip ≈ 0.10 USD
        # Esto es una aproximación, el valor real depende del par
        base_pip_value = 10.0  # USD por lote estándar
        return base_pip_value * float(self.lot_size)

    # ============================================
    # MÉTODOS DE NEGOCIO
    # ============================================

    def mark_as_placed(self, broker_ticket: BrokerTicket) -> None:
        """Marca la operación como enviada al broker (aún pendiente)."""
        self.broker_ticket = broker_ticket
        self.status = OperationStatus.PENDING

    def activate(self, fill_price: Price, broker_ticket: BrokerTicket, timestamp: Optional[datetime] = None) -> None:
        """
        Activa la operación (orden ejecutada).

        Args:
            fill_price: Precio real de ejecución
            broker_ticket: Ticket del broker
            timestamp: Momento de activación (opcional)
        """
        if self.status != OperationStatus.PENDING:
            raise ValueError(f"Cannot activate operation in status {self.status}")

        self.status = OperationStatus.ACTIVE
        self.actual_entry_price = fill_price
        self.broker_ticket = broker_ticket
        self.activated_at = timestamp or datetime.now()

        # Calcular slippage
        expected = float(self.entry_price)
        actual = float(fill_price)
        diff = abs(actual - expected)

        # Convertir a pips (ajustar para JPY)
        multiplier = 100 if "JPY" in self.pair else 10000
        self.slippage_pips = Pips(diff * multiplier)



    def close_v2(self, price: Price, timestamp: Optional[datetime] = None) -> None:
        """
        Cierre de operación - versión alternativa más robusta.

        Detecta TP comparando precios directamente con tolerancia relativa.
        """
        # FIX: Allow closing TP_HIT operations (broker already marked them)
        if self.status not in (OperationStatus.ACTIVE, OperationStatus.NEUTRALIZED, 
                               OperationStatus.PENDING, OperationStatus.TP_HIT):
            raise ValueError(f"Cannot close operation in status {self.status}")

        self.actual_close_price = price
        self.closed_at = timestamp or datetime.now()

        if self.tp_price:
            # Usar tolerancia relativa (0.01% del precio)
            # Esto funciona igual para todos los pares
            price_float = float(price)
            tp_float = float(self.tp_price)

            # Tolerancia de 0.01% del precio (~1 pip para la mayoría de pares)
            tolerance = tp_float * 0.0001

            if abs(price_float - tp_float) <= tolerance:
                self.status = OperationStatus.TP_HIT
            else:
                # Verificar si superó el TP en la dirección correcta
                if self.is_buy and price_float >= tp_float:
                    self.status = OperationStatus.TP_HIT
                elif self.is_sell and price_float <= tp_float:
                    self.status = OperationStatus.TP_HIT
                else:
                    self.status = OperationStatus.CLOSED
        else:
            self.status = OperationStatus.CLOSED

        self._calculate_profit()

    def close_with_tp(self, close_price: Price) -> None:
        """
        Cierra la operación por take profit.

        Args:
            close_price: Precio de cierre
        """
        if self.status != OperationStatus.ACTIVE:
            raise ValueError(f"Cannot close operation in status {self.status}")

        self.status = OperationStatus.TP_HIT
        self.actual_close_price = close_price
        self.closed_at = datetime.now()
        self._calculate_profit()

    def close_manually(self, close_price: Price, reason: str = "") -> None:
        """
        Cierra la operación manualmente.

        Args:
            close_price: Precio de cierre
            reason: Razón del cierre
        """
        if self.status not in (OperationStatus.ACTIVE, OperationStatus.NEUTRALIZED):
            raise ValueError(f"Cannot close operation in status {self.status}")

        self.status = OperationStatus.CLOSED
        self.actual_close_price = close_price
        self.closed_at = datetime.now()
        self.metadata["close_reason"] = reason
        self._calculate_profit()

    def neutralize(self, hedge_operation_id: OperationId) -> None:
        """
        Neutraliza la operación (cubierta por hedge).

        Args:
            hedge_operation_id: ID de la operación de cobertura
        """
        if self.status != OperationStatus.ACTIVE:
            raise ValueError(f"Cannot neutralize operation in status {self.status}")

        self.status = OperationStatus.NEUTRALIZED
        self.linked_operation_id = hedge_operation_id
        self.metadata["neutralized_by"] = hedge_operation_id

    def cancel(self, reason: str = "") -> None:
        """
        Cancela la operación pendiente.

        Args:
            reason: Razón de la cancelación
        """
        if self.status != OperationStatus.PENDING:
            raise ValueError(f"Cannot cancel operation in status {self.status}")

        self.status = OperationStatus.CANCELLED
        self.closed_at = datetime.now()
        self.metadata["cancel_reason"] = reason

    def add_swap(self, amount: Money) -> None:
        """
        Añade swap/rollover a la operación.

        Args:
            amount: Cantidad de swap (puede ser negativa)
        """
        self.swap_total = Money(self.swap_total + amount)

    def _calculate_profit(self) -> None:
        """Calcula el profit en pips y EUR."""
        if self.actual_entry_price is None or self.actual_close_price is None:
            return

        entry = float(self.actual_entry_price)
        close = float(self.actual_close_price)

        # Calcular diferencia
        if self.is_buy:
            diff = close - entry
        else:
            diff = entry - close

        # Convertir a pips
        multiplier = 100 if "JPY" in self.pair else 10000
        self.profit_pips = Pips(diff * multiplier)

        # Convertir a EUR (aproximado)
        self.profit_eur = Money(Decimal(str(self.profit_pips * self.pip_value)))

    # ============================================
    # SERIALIZACIÓN
    # ============================================

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para persistencia."""
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "pair": self.pair,
            "op_type": self.op_type.value,
            "status": self.status.value,
            "entry_price": str(self.entry_price),
            "tp_price": str(self.tp_price),
            "actual_entry_price": str(self.actual_entry_price) if self.actual_entry_price else None,
            "actual_close_price": str(self.actual_close_price) if self.actual_close_price else None,
            "lot_size": self.lot_size,
            "pips_target": self.pips_target,
            "profit_pips": self.profit_pips,
            "profit_eur": str(self.profit_eur),
            "commission_open": str(self.commission_open),
            "commission_close": str(self.commission_close),
            "swap_total": str(self.swap_total),
            "slippage_pips": self.slippage_pips,
            "broker_ticket": self.broker_ticket,
            "linked_operation_id": self.linked_operation_id,
            "recovery_id": self.recovery_id,
            "created_at": self.created_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Operation:
        """Crea Operation desde diccionario."""
        return cls(
            id=OperationId(data["id"]),
            cycle_id=CycleId(data["cycle_id"]),
            pair=CurrencyPair(data["pair"]),
            op_type=OperationType(data["op_type"]),
            status=OperationStatus(data["status"]),
            entry_price=Price(Decimal(data["entry_price"])),
            tp_price=Price(Decimal(data["tp_price"])),
            actual_entry_price=Price(Decimal(data["actual_entry_price"]))
            if data.get("actual_entry_price")
            else None,
            actual_close_price=Price(Decimal(data["actual_close_price"]))
            if data.get("actual_close_price")
            else None,
            lot_size=LotSize(data["lot_size"]),
            pips_target=Pips(data["pips_target"]),
            profit_pips=Pips(data["profit_pips"]),
            profit_eur=Money(Decimal(data["profit_eur"])),
            commission_open=Money(Decimal(data["commission_open"])),
            commission_close=Money(Decimal(data["commission_close"])),
            swap_total=Money(Decimal(data["swap_total"])),
            slippage_pips=Pips(data["slippage_pips"]),
            broker_ticket=BrokerTicket(data["broker_ticket"]) if data.get("broker_ticket") else None,
            linked_operation_id=OperationId(data["linked_operation_id"])
            if data.get("linked_operation_id")
            else None,
            recovery_id=RecoveryId(data["recovery_id"]) if data.get("recovery_id") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            activated_at=datetime.fromisoformat(data["activated_at"])
            if data.get("activated_at")
            else None,
            closed_at=datetime.fromisoformat(data["closed_at"]) if data.get("closed_at") else None,
            metadata=data.get("metadata", {}),
        )

    # ============================================
    # REPRESENTACIÓN
    # ============================================

    def __repr__(self) -> str:
        return (
            f"Operation(id={self.id!r}, pair={self.pair!r}, "
            f"type={self.op_type.value}, status={self.status.value})"
        )

    def __str__(self) -> str:
        return f"{self.id} [{self.status.value}] {self.op_type.value} @ {self.entry_price}"
