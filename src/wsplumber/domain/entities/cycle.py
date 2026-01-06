# src/wsplumber/domain/entities/cycle.py
"""
Entidad Cycle - Representa un ciclo de trading completo.

Un ciclo contiene:
- Operaciones principales (main): BUY y SELL
- Operaciones de cobertura (hedge): Cuando ambas main se activan
- Operaciones de recovery: Para recuperar pérdidas neutralizadas.

Entidad Cycle - VERSIÓN CORREGIDA (solo CycleAccounting.get_recovery_cost)

Fix aplicado:
- FIX-CY-01: get_recovery_cost basado en posición en cola, no en pips_recovered

El ciclo implementa la contabilidad FIFO para cerrar recoveries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from wsplumber.domain.types import (
    CurrencyPair,
    CycleId,
    CycleStatus,
    CycleType,
    Money,
    OperationId,
    OperationStatus,
    OperationType,
    Pips,
    RecoveryId,
)
from wsplumber.domain.entities.operation import Operation

@dataclass
class CycleAccounting:
    """
    Contabilidad del ciclo - rastrea pips y costos.

    Esta clase implementa la lógica FIFO para recoveries:
    - El primer recovery cuesta 20 pips (incluye las main)
    - Los siguientes cuestan 40 pips cada uno
    
    FIX-CY-01: El costo ahora se basa en la posición en la cola,
    no en los pips ya recuperados.
    """

    pips_locked: Pips = Pips(0.0)
    pips_recovered: Pips = Pips(0.0)
    total_main_tps: int = 0
    total_recovery_tps: int = 0
    total_commissions: Money = Money(Decimal("0"))
    total_swaps: Money = Money(Decimal("0"))
    recovery_queue: List[RecoveryId] = field(default_factory=list)
    
    # FIX-CY-01: Contador de recoveries procesados (para determinar costo)
    recoveries_closed_count: int = 0

    def add_locked_pips(self, pips: Pips) -> None:
        """Añade pips bloqueados (cuando se neutraliza)."""
        self.pips_locked = Pips(float(self.pips_locked) + float(pips))

    def add_recovered_pips(self, pips: Pips) -> None:
        """Añade pips recuperados (cuando recovery hace TP)."""
        self.pips_recovered = Pips(float(self.pips_recovered) + float(pips))

    def get_recovery_cost(self) -> Pips:
        """
        Calcula el costo del próximo recovery en la cola.
        
        FIX-CY-01: Basado en cuántos recoveries ya se han cerrado,
        no en pips_recovered.
        
        Según la teoría:
        - El primer recovery cuesta 20 pips (cubre deuda inicial de mains)
        - Los siguientes cuestan 40 pips cada uno
        
        Returns:
            Pips: Costo del próximo recovery a cerrar
        """
        if self.recoveries_closed_count == 0:
            return Pips(20.0)  # Primer recovery
        return Pips(40.0)  # Siguientes

    def mark_recovery_closed(self) -> None:
        """
        FIX-CY-01: Incrementa el contador de recoveries cerrados.
        Llamar después de cerrar un recovery.
        """
        self.recoveries_closed_count += 1

    def get_recoveries_needed(self) -> int:
        """
        Calcula cuántos recoveries se necesitan para cubrir lo bloqueado.
        """
        remaining = float(self.pips_locked) - float(self.pips_recovered)
        if remaining <= 0:
            return 0

        # Primer recovery cubre 80 pips pero cuesta 20 → neto +60
        if remaining <= 60:
            return 1

        # Recoveries adicionales (40 pips neto cada uno)
        remaining -= 60
        additional = int(remaining / 40) + (1 if remaining % 40 > 0 else 0)

        return 1 + additional

    @property
    def net_pips(self) -> Pips:
        """Pips netos (recuperados - bloqueados)."""
        return Pips(float(self.pips_recovered) - float(self.pips_locked))

    @property
    def is_fully_recovered(self) -> bool:
        """True si se han recuperado todos los pips bloqueados."""
        return float(self.pips_recovered) >= float(self.pips_locked)


# ====================================================================
# INSTRUCCIONES DE APLICACIÓN:
# 
# 1. Abrir src/wsplumber/domain/entities/cycle.py
# 2. En la clase CycleAccounting:
#    - Añadir campo: recoveries_closed_count: int = 0
#    - Reemplazar método get_recovery_cost() con la versión de arriba
#    - Añadir método mark_recovery_closed()
# 
# 3. En cycle_orchestrator.py, cuando se cierra un recovery en FIFO:
#    - Después de: closed_rec_id = parent_cycle.close_oldest_recovery()
#    - Añadir: parent_cycle.accounting.mark_recovery_closed()
# ====================================================================

@dataclass
class Cycle:
    """
    Representa un ciclo completo de trading.

    Un ciclo típico sigue este flujo:
    1. Se abren operaciones main (BUY y SELL pendientes)
    2. Una de las main se activa (precio la alcanza)
    3. Si la otra main también se activa → se activa hedge
    4. La pérdida queda neutralizada
    5. Se abren operaciones de recovery para recuperar

    Attributes:
        id: Identificador único (ej: "EURUSD_001")
        pair: Par de divisas
        cycle_type: main o recovery
        status: Estado actual del ciclo
    """

    # Identificación
    id: CycleId
    pair: CurrencyPair
    cycle_type: CycleType = CycleType.MAIN
    status: CycleStatus = CycleStatus.ACTIVE

    # Relaciones
    parent_cycle_id: Optional[CycleId] = None
    """ID del ciclo padre (para recovery cycles)."""

    recovery_level: int = 0
    """Nivel de recovery (0 = main, 1 = primer recovery, etc.)."""

    # Operaciones
    operations: List[Operation] = field(default_factory=list)
    """Todas las operaciones del ciclo."""

    # Contabilidad
    accounting: CycleAccounting = field(default_factory=CycleAccounting)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ============================================
    # PROPIEDADES: OPERACIONES POR TIPO
    # ============================================

    @property
    def main_operations(self) -> List[Operation]:
        """Operaciones principales (BUY y SELL iniciales)."""
        return [op for op in self.operations if op.is_main]

    @property
    def hedge_operations(self) -> List[Operation]:
        """Operaciones de cobertura."""
        return [op for op in self.operations if op.is_hedge]

    @property
    def recovery_operations(self) -> List[Operation]:
        """Operaciones de recovery."""
        return [op for op in self.operations if op.is_recovery]

    @property
    def active_operations(self) -> List[Operation]:
        """Operaciones actualmente activas."""
        return [op for op in self.operations if op.is_active]

    @property
    def pending_operations(self) -> List[Operation]:
        """Operaciones pendientes de activación."""
        return [op for op in self.operations if op.is_pending]

    @property
    def neutralized_operations(self) -> List[Operation]:
        """Operaciones neutralizadas."""
        return [op for op in self.operations if op.is_neutralized]

    # ============================================
    # PROPIEDADES: ESTADO
    # ============================================

    @property
    def is_active(self) -> bool:
        """True si el ciclo está activo."""
        return self.status == CycleStatus.ACTIVE

    @property
    def is_hedged(self) -> bool:
        """True si el ciclo tiene cobertura activa."""
        return self.status == CycleStatus.HEDGED

    @property
    def is_in_recovery(self) -> bool:
        """True si el ciclo está en proceso de recovery."""
        return self.status == CycleStatus.IN_RECOVERY

    @property
    def is_closed(self) -> bool:
        """True si el ciclo está cerrado."""
        return self.status == CycleStatus.CLOSED

    @property
    def needs_recovery(self) -> bool:
        """True si hay pérdidas neutralizadas sin recuperar."""
        return len(self.neutralized_operations) > 0 and not self.accounting.is_fully_recovered

    @property
    def total_operations_count(self) -> int:
        """Número total de operaciones."""
        return len(self.operations)

    # ============================================
    # PROPIEDADES: FINANCIERAS
    # ============================================

    @property
    def total_profit_pips(self) -> Pips:
        """Profit total en pips de operaciones cerradas."""
        return Pips(sum(float(op.profit_pips) for op in self.operations if op.is_closed))

    @property
    def total_profit_eur(self) -> Money:
        """Profit total en EUR."""
        return Money(sum(op.profit_eur for op in self.operations if op.is_closed))

    @property
    def total_costs(self) -> Money:
        """Costos totales (comisiones + swaps)."""
        return Money(sum(op.total_cost for op in self.operations))

    @property
    def net_profit_eur(self) -> Money:
        """Profit neto en EUR (profit - costos)."""
        return Money(self.total_profit_eur - self.total_costs)

    # ============================================
    # MÉTODOS DE NEGOCIO: OPERACIONES
    # ============================================

    def add_operation(self, operation: Operation) -> None:
        """
        Añade una operación al ciclo.

        Args:
            operation: Operación a añadir

        Raises:
            ValueError: Si la operación no pertenece a este ciclo
        """
        if operation.cycle_id != self.id:
            raise ValueError(
                f"Operation {operation.id} belongs to cycle {operation.cycle_id}, not {self.id}"
            )
        self.operations.append(operation)

    def get_operation(self, operation_id: OperationId) -> Optional[Operation]:
        """
        Obtiene una operación por ID.

        Args:
            operation_id: ID de la operación

        Returns:
            Operation si existe, None si no
        """
        for op in self.operations:
            if op.id == operation_id:
                return op
        return None

    def get_main_buy(self) -> Optional[Operation]:
        """Obtiene la operación main BUY."""
        for op in self.main_operations:
            if op.is_buy:
                return op
        return None

    def get_main_sell(self) -> Optional[Operation]:
        """Obtiene la operación main SELL."""
        for op in self.main_operations:
            if op.is_sell:
                return op
        return None

    # ============================================
    # MÉTODOS DE NEGOCIO: CICLO DE VIDA
    # ============================================

    def activate_hedge(self) -> None:
        """
        Activa el modo de cobertura.

        Se llama cuando ambas operaciones main están activas,
        indicando que el precio se movió en ambas direcciones.
        """
        if self.status != CycleStatus.ACTIVE:
            raise ValueError(f"Cannot activate hedge in status {self.status}")

        self.status = CycleStatus.HEDGED
        self.metadata["hedged_at"] = datetime.now().isoformat()
        
        # Al activar hedge, bloqueamos la deuda inicial de las mains (20 pips)
        self.accounting.add_locked_pips(Pips(20.0))

    def start_recovery(self) -> None:
        """
        Inicia el proceso de recovery.

        Se llama cuando hay operaciones neutralizadas que necesitan recuperarse.
        """
        if self.status not in (CycleStatus.ACTIVE, CycleStatus.HEDGED):
            raise ValueError(f"Cannot start recovery in status {self.status}")

        self.status = CycleStatus.IN_RECOVERY
        self.metadata["recovery_started_at"] = datetime.now().isoformat()

    def close(self, reason: str = "") -> None:
        """
        Cierra el ciclo.

        Args:
            reason: Razón del cierre
        """
        self.status = CycleStatus.CLOSED
        self.closed_at = datetime.now()
        self.metadata["close_reason"] = reason

    def pause(self, reason: str = "") -> None:
        """
        Pausa el ciclo.

        Args:
            reason: Razón de la pausa
        """
        self.metadata["previous_status"] = self.status.value
        self.status = CycleStatus.PAUSED
        self.metadata["paused_at"] = datetime.now().isoformat()
        self.metadata["pause_reason"] = reason

    def resume(self) -> None:
        """Reanuda un ciclo pausado."""
        if self.status != CycleStatus.PAUSED:
            raise ValueError(f"Cannot resume cycle in status {self.status}")

        previous = self.metadata.get("previous_status", CycleStatus.ACTIVE.value)
        self.status = CycleStatus(previous)
        self.metadata["resumed_at"] = datetime.now().isoformat()

    # ============================================
    # MÉTODOS DE NEGOCIO: RECOVERY FIFO
    # ============================================

    def add_recovery_to_queue(self, recovery_id: RecoveryId) -> None:
        """
        Añade un recovery a la cola FIFO.

        Args:
            recovery_id: ID del recovery
        """
        self.accounting.recovery_queue.append(recovery_id)

    def get_oldest_pending_recovery(self) -> Optional[RecoveryId]:
        """
        Obtiene el recovery más antiguo pendiente (FIFO).

        Returns:
            ID del recovery más antiguo, o None si no hay
        """
        for recovery_id in self.accounting.recovery_queue:
            # Buscar la operación correspondiente
            for op in self.recovery_operations:
                if op.recovery_id == recovery_id and op.is_active:
                    return recovery_id
        return None

    def close_oldest_recovery(self) -> Optional[RecoveryId]:
        """
        Marca el recovery más antiguo como recuperado.

        Returns:
            ID del recovery cerrado, o None si no había ninguno
        """
        if not self.accounting.recovery_queue:
            return None

        recovery_id = self.accounting.recovery_queue.pop(0)
        return recovery_id

    def calculate_recovery_needed(self) -> Tuple[int, Pips]:
        """
        Calcula cuántos recoveries se necesitan y cuántos pips faltan.

        Returns:
            Tuple de (número de recoveries, pips pendientes)
        """
        recoveries = self.accounting.get_recoveries_needed()
        remaining_pips = Pips(
            float(self.accounting.pips_locked) - float(self.accounting.pips_recovered)
        )
        return (recoveries, remaining_pips)

    # ============================================
    # MÉTODOS DE NEGOCIO: CONTABILIDAD
    # ============================================

    def record_neutralization(self, pips: Pips) -> None:
        """
        Registra pips neutralizados.

        Args:
            pips: Pips que se neutralizaron
        """
        self.accounting.add_locked_pips(pips)

    def record_recovery_tp(self, pips: Pips) -> None:
        """
        Registra un TP de recovery.

        Args:
            pips: Pips recuperados
        """
        self.accounting.add_recovered_pips(pips)
        self.accounting.total_recovery_tps += 1

        # Verificar si se completó la recuperación
        if self.accounting.is_fully_recovered and not self.needs_recovery:
            self.metadata["fully_recovered_at"] = datetime.now().isoformat()

    def record_main_tp(self, pips: Pips) -> None:
        """
        Registra un TP de operación main.

        Args:
            pips: Pips ganados
        """
        self.accounting.total_main_tps += 1

    # ============================================
    # SERIALIZACIÓN
    # ============================================

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para persistencia."""
        return {
            "id": self.id,
            "pair": self.pair,
            "cycle_type": self.cycle_type.value,
            "status": self.status.value,
            "parent_cycle_id": self.parent_cycle_id,
            "recovery_level": self.recovery_level,
            "operations": [op.to_dict() for op in self.operations],
            "accounting": {
                "pips_locked": self.accounting.pips_locked,
                "pips_recovered": self.accounting.pips_recovered,
                "total_main_tps": self.accounting.total_main_tps,
                "total_recovery_tps": self.accounting.total_recovery_tps,
                "total_commissions": str(self.accounting.total_commissions),
                "total_swaps": str(self.accounting.total_swaps),
                "recovery_queue": self.accounting.recovery_queue,
            },
            "created_at": self.created_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Cycle:
        """Crea Cycle desde diccionario."""
        accounting_data = data.get("accounting", {})
        accounting = CycleAccounting(
            pips_locked=Pips(accounting_data.get("pips_locked", 0.0)),
            pips_recovered=Pips(accounting_data.get("pips_recovered", 0.0)),
            total_main_tps=accounting_data.get("total_main_tps", 0),
            total_recovery_tps=accounting_data.get("total_recovery_tps", 0),
            total_commissions=Money(Decimal(accounting_data.get("total_commissions", "0"))),
            total_swaps=Money(Decimal(accounting_data.get("total_swaps", "0"))),
            recovery_queue=accounting_data.get("recovery_queue", []),
        )

        cycle = cls(
            id=CycleId(data["id"]),
            pair=CurrencyPair(data["pair"]),
            cycle_type=CycleType(data["cycle_type"]),
            status=CycleStatus(data["status"]),
            parent_cycle_id=CycleId(data["parent_cycle_id"]) if data.get("parent_cycle_id") else None,
            recovery_level=data.get("recovery_level", 0),
            accounting=accounting,
            created_at=datetime.fromisoformat(data["created_at"]),
            activated_at=datetime.fromisoformat(data["activated_at"])
            if data.get("activated_at")
            else None,
            closed_at=datetime.fromisoformat(data["closed_at"]) if data.get("closed_at") else None,
            metadata=data.get("metadata", {}),
        )

        # Reconstruir operaciones
        for op_data in data.get("operations", []):
            cycle.operations.append(Operation.from_dict(op_data))

        return cycle

    # ============================================
    # REPRESENTACIÓN
    # ============================================

    def __repr__(self) -> str:
        return (
            f"Cycle(id={self.id!r}, pair={self.pair!r}, "
            f"status={self.status.value}, ops={len(self.operations)})"
        )

    def __str__(self) -> str:
        return (
            f"{self.id} [{self.status.value}] - "
            f"{len(self.active_operations)} active, "
            f"{len(self.neutralized_operations)} neutralized"
        )
