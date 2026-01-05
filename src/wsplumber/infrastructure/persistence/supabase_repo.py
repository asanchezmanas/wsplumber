# src/wsplumber/infrastructure/persistence/supabase_repo.py
"""
Repositorio Supabase.

Implementa IRepository usando Supabase como backend.
Incluye manejo de errores, reintentos y logging seguro.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from wsplumber.domain.interfaces.ports import IRepository
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.types import (
    BrokerTicket,
    CurrencyPair,
    CycleId,
    OperationId,
    Result,
)
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)


class SupabaseRepository(IRepository):
    """
    Repositorio usando Supabase (PostgreSQL).

    Features:
    - CRUD completo para cycles y operations
    - Checkpoints para recovery de estado
    - Outbox pattern para consistencia
    - Métricas y alertas
    """

    def __init__(self, url: str, key: str):
        """
        Inicializa el repositorio.

        Args:
            url: URL de Supabase
            key: API key de Supabase
        """
        self.client: Client = create_client(url, key)
        self._connected = False

    async def _ensure_connected(self) -> None:
        """Verifica conexión antes de operaciones."""
        if not self._connected:
            # Supabase client no requiere conexión explícita,
            # pero hacemos un health check
            result = await self.health_check()
            if result.success:
                self._connected = True

    # ============================================
    # CYCLES
    # ============================================

    async def save_cycle(self, cycle: Cycle) -> Result[CycleId]:
        """Guarda o actualiza un ciclo."""
        try:
            data = {
                "external_id": cycle.id,
                "pair": cycle.pair,
                "cycle_type": cycle.cycle_type.value,
                "status": cycle.status.value,
                "parent_cycle_id": cycle.parent_cycle_id,
                "recovery_level": cycle.recovery_level,
                "pips_locked": float(cycle.accounting.pips_locked),
                "pips_recovered": float(cycle.accounting.pips_recovered),
                "metadata": cycle.metadata,
            }

            result = (
                self.client.table("cycles")
                .upsert(data, on_conflict="external_id")
                .execute()
            )

            if result.data:
                logger.info(
                    "Cycle saved",
                    cycle_id=cycle.id,
                    status=cycle.status.value,
                )
                return Result.ok(CycleId(cycle.id))

            return Result.fail("No data returned from upsert", "DB_ERROR")

        except Exception as e:
            logger.error("Failed to save cycle", exception=e, cycle_id=cycle.id)
            return Result.fail(str(e), "DB_ERROR")

    async def get_cycle(self, cycle_id: CycleId) -> Result[Optional[Cycle]]:
        """Obtiene un ciclo por ID."""
        try:
            result = (
                self.client.table("cycles")
                .select("*")
                .eq("external_id", cycle_id)
                .execute()
            )

            if not result.data:
                return Result.ok(None)

            row = result.data[0]

            # Obtener operaciones del ciclo
            ops_result = (
                self.client.table("operations")
                .select("*")
                .eq("cycle_id", row["id"])
                .execute()
            )

            # Construir ciclo
            cycle = self._row_to_cycle(row)

            # Añadir operaciones
            for op_row in ops_result.data or []:
                operation = self._row_to_operation(op_row)
                cycle.operations.append(operation)

            return Result.ok(cycle)

        except Exception as e:
            logger.error("Failed to get cycle", exception=e, cycle_id=cycle_id)
            return Result.fail(str(e), "DB_ERROR")

    async def get_active_cycles(
        self, pair: Optional[CurrencyPair] = None
    ) -> Result[List[Cycle]]:
        """Obtiene ciclos activos."""
        try:
            query = (
                self.client.table("cycles")
                .select("*")
                .in_("status", ["active", "hedged", "in_recovery"])
            )

            if pair:
                query = query.eq("pair", pair)

            result = query.order("created_at", desc=True).execute()

            cycles = []
            for row in result.data or []:
                cycle = self._row_to_cycle(row)

                # Obtener operaciones
                ops_result = (
                    self.client.table("operations")
                    .select("*")
                    .eq("cycle_id", row["id"])
                    .execute()
                )

                for op_row in ops_result.data or []:
                    cycle.operations.append(self._row_to_operation(op_row))

                cycles.append(cycle)

            return Result.ok(cycles)

        except Exception as e:
            logger.error("Failed to get active cycles", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def get_cycles_by_status(
        self,
        statuses: List[str],
        pair: Optional[CurrencyPair] = None,
    ) -> Result[List[Cycle]]:
        """Obtiene ciclos por estado."""
        try:
            query = self.client.table("cycles").select("*").in_("status", statuses)

            if pair:
                query = query.eq("pair", pair)

            result = query.order("created_at", desc=True).execute()

            cycles = [self._row_to_cycle(row) for row in result.data or []]
            return Result.ok(cycles)

        except Exception as e:
            logger.error("Failed to get cycles by status", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    # ============================================
    # OPERATIONS
    # ============================================

    async def save_operation(self, operation: Operation) -> Result[OperationId]:
        """Guarda o actualiza una operación."""
        try:
            # Obtener UUID del ciclo
            cycle_uuid = await self._get_cycle_uuid(operation.cycle_id)

            data = {
                "external_id": operation.id,
                "cycle_id": cycle_uuid,
                "pair": operation.pair,
                "op_type": operation.op_type.value,
                "status": operation.status.value,
                "entry_price": float(operation.entry_price),
                "tp_price": float(operation.tp_price),
                "actual_entry_price": float(operation.actual_entry_price)
                if operation.actual_entry_price
                else None,
                "actual_close_price": float(operation.actual_close_price)
                if operation.actual_close_price
                else None,
                "lot_size": float(operation.lot_size),
                "pips_target": float(operation.pips_target),
                "profit_pips": float(operation.profit_pips),
                "profit_eur": float(operation.profit_eur),
                "commission_open": float(operation.commission_open),
                "commission_close": float(operation.commission_close),
                "swap_total": float(operation.swap_total),
                "slippage_pips": float(operation.slippage_pips),
                "broker_ticket": operation.broker_ticket,
                "linked_operation_id": operation.linked_operation_id,
                "recovery_id": operation.recovery_id,
                "activated_at": operation.activated_at.isoformat()
                if operation.activated_at
                else None,
                "closed_at": operation.closed_at.isoformat()
                if operation.closed_at
                else None,
                "metadata": operation.metadata,
            }

            result = (
                self.client.table("operations")
                .upsert(data, on_conflict="external_id")
                .execute()
            )

            if result.data:
                logger.info(
                    "Operation saved",
                    operation_id=operation.id,
                    status=operation.status.value,
                )
                return Result.ok(OperationId(operation.id))

            return Result.fail("No data returned from upsert", "DB_ERROR")

        except Exception as e:
            logger.error(
                "Failed to save operation", exception=e, operation_id=operation.id
            )
            return Result.fail(str(e), "DB_ERROR")

    async def get_operation(
        self, operation_id: OperationId
    ) -> Result[Optional[Operation]]:
        """Obtiene una operación por ID."""
        try:
            result = (
                self.client.table("operations")
                .select("*")
                .eq("external_id", operation_id)
                .execute()
            )

            if not result.data:
                return Result.ok(None)

            operation = self._row_to_operation(result.data[0])
            return Result.ok(operation)

        except Exception as e:
            logger.error(
                "Failed to get operation", exception=e, operation_id=operation_id
            )
            return Result.fail(str(e), "DB_ERROR")

    async def get_active_operations(
        self, pair: Optional[CurrencyPair] = None
    ) -> Result[List[Operation]]:
        """Obtiene operaciones activas."""
        try:
            query = (
                self.client.table("operations").select("*").eq("status", "active")
            )

            if pair:
                query = query.eq("pair", pair)

            result = query.execute()

            operations = [
                self._row_to_operation(row) for row in result.data or []
            ]
            return Result.ok(operations)

        except Exception as e:
            logger.error("Failed to get active operations", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def get_pending_operations(
        self, pair: Optional[CurrencyPair] = None
    ) -> Result[List[Operation]]:
        """Obtiene operaciones pendientes."""
        try:
            query = (
                self.client.table("operations").select("*").eq("status", "pending")
            )

            if pair:
                query = query.eq("pair", pair)

            result = query.execute()

            operations = [
                self._row_to_operation(row) for row in result.data or []
            ]
            return Result.ok(operations)

        except Exception as e:
            logger.error("Failed to get pending operations", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def get_operation_by_ticket(
        self, ticket: BrokerTicket
    ) -> Result[Optional[Operation]]:
        """Obtiene operación por ticket del broker."""
        try:
            result = (
                self.client.table("operations")
                .select("*")
                .eq("broker_ticket", ticket)
                .execute()
            )

            if not result.data:
                return Result.ok(None)

            operation = self._row_to_operation(result.data[0])
            return Result.ok(operation)

        except Exception as e:
            logger.error(
                "Failed to get operation by ticket", exception=e, ticket=ticket
            )
            return Result.fail(str(e), "DB_ERROR")

    # ============================================
    # CHECKPOINTS
    # ============================================

    async def save_checkpoint(self, state: Dict[str, Any]) -> Result[str]:
        """Guarda checkpoint del estado."""
        try:
            data = {
                "state": state,
                "version": "2.0",
                "trigger_reason": state.get("trigger_reason", "periodic"),
                "cycles_count": len(state.get("cycles", [])),
                "operations_count": len(state.get("operations", [])),
            }

            result = self.client.table("checkpoints").insert(data).execute()

            if result.data:
                checkpoint_id = result.data[0]["id"]
                logger.checkpoint_created(checkpoint_id)
                return Result.ok(checkpoint_id)

            return Result.fail("No data returned", "DB_ERROR")

        except Exception as e:
            logger.error("Failed to save checkpoint", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def get_latest_checkpoint(self) -> Result[Optional[Dict[str, Any]]]:
        """Obtiene el checkpoint más reciente."""
        try:
            result = (
                self.client.table("checkpoints")
                .select("*")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                return Result.ok(None)

            return Result.ok(result.data[0]["state"])

        except Exception as e:
            logger.error("Failed to get latest checkpoint", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    # ============================================
    # OUTBOX
    # ============================================

    async def add_to_outbox(
        self,
        operation_type: str,
        payload: Dict[str, Any],
        idempotency_key: str,
    ) -> Result[str]:
        """Añade operación al outbox."""
        try:
            data = {
                "operation_type": operation_type,
                "payload": payload,
                "idempotency_key": idempotency_key,
                "status": "pending",
                "attempts": 0,
                "max_attempts": 5,
            }

            result = self.client.table("outbox").insert(data).execute()

            if result.data:
                return Result.ok(result.data[0]["id"])

            return Result.fail("No data returned", "DB_ERROR")

        except Exception as e:
            # Puede fallar por duplicate key (idempotency)
            if "duplicate" in str(e).lower():
                logger.warning(
                    "Duplicate outbox entry",
                    idempotency_key=idempotency_key,
                )
                return Result.ok(idempotency_key)

            logger.error("Failed to add to outbox", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def get_pending_outbox_entries(
        self, limit: int = 10
    ) -> Result[List[Dict[str, Any]]]:
        """Obtiene entradas pendientes del outbox."""
        try:
            result = (
                self.client.table("outbox")
                .select("*")
                .eq("status", "pending")
                .order("created_at")
                .limit(limit)
                .execute()
            )

            return Result.ok(result.data or [])

        except Exception as e:
            logger.error("Failed to get outbox entries", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def update_outbox_status(
        self,
        entry_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Result[bool]:
        """Actualiza estado de entrada en outbox."""
        try:
            data = {"status": status}

            if error_message:
                data["error_message"] = error_message

            if status == "completed":
                data["processed_at"] = datetime.now().isoformat()

            self.client.table("outbox").update(data).eq("id", entry_id).execute()

            return Result.ok(True)

        except Exception as e:
            logger.error(
                "Failed to update outbox status", exception=e, entry_id=entry_id
            )
            return Result.fail(str(e), "DB_ERROR")

    # ============================================
    # METRICS
    # ============================================

    async def save_daily_metrics(self, metrics: Dict[str, Any]) -> Result[bool]:
        """Guarda métricas diarias."""
        try:
            self.client.table("metrics_daily").upsert(
                metrics, on_conflict="date,pair"
            ).execute()

            return Result.ok(True)

        except Exception as e:
            logger.error("Failed to save daily metrics", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    async def get_daily_metrics(
        self, days: int = 30
    ) -> Result[List[Dict[str, Any]]]:
        """Obtiene métricas de los últimos N días."""
        try:
            result = (
                self.client.table("metrics_daily")
                .select("*")
                .order("date", desc=True)
                .limit(days)
                .execute()
            )

            return Result.ok(result.data or [])

        except Exception as e:
            logger.error("Failed to get daily metrics", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    # ============================================
    # ALERTS
    # ============================================

    async def create_alert(
        self,
        severity: str,
        alert_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[str]:
        """Crea una alerta."""
        try:
            data = {
                "severity": severity,
                "alert_type": alert_type,
                "message": message,
                "metadata": metadata or {},
            }

            result = self.client.table("alerts").insert(data).execute()

            if result.data:
                return Result.ok(result.data[0]["id"])

            return Result.fail("No data returned", "DB_ERROR")

        except Exception as e:
            logger.error("Failed to create alert", exception=e)
            return Result.fail(str(e), "DB_ERROR")

    # ============================================
    # HEALTH
    # ============================================

    async def health_check(self) -> Result[str]:
        """Verifica salud de la conexión."""
        try:
            # Query simple para verificar conexión
            result = (
                self.client.table("cycles")
                .select("id")
                .limit(1)
                .execute()
            )

            return Result.ok("OK")

        except Exception as e:
            logger.error("Health check failed", exception=e)
            return Result.fail(str(e), "CONNECTION_ERROR")

    async def close(self) -> None:
        """Cierra conexión con la base de datos."""
        # Supabase client no requiere cierre explícito
        self._connected = False
        logger.info("Repository connection closed")

    # ============================================
    # HELPERS PRIVADOS
    # ============================================

    async def _get_cycle_uuid(self, external_id: CycleId) -> Optional[str]:
        """Obtiene UUID interno de un ciclo por su external_id."""
        result = (
            self.client.table("cycles")
            .select("id")
            .eq("external_id", external_id)
            .execute()
        )

        if result.data:
            return result.data[0]["id"]
        return None

    def _row_to_cycle(self, row: Dict[str, Any]) -> Cycle:
        """Convierte fila de DB a Cycle."""
        from wsplumber.domain.types import CycleStatus, CycleType
        from wsplumber.domain.entities.cycle import CycleAccounting

        accounting = CycleAccounting(
            pips_locked=row.get("pips_locked", 0.0),
            pips_recovered=row.get("pips_recovered", 0.0),
        )

        return Cycle(
            id=CycleId(row["external_id"]),
            pair=CurrencyPair(row["pair"]),
            cycle_type=CycleType(row["cycle_type"]),
            status=CycleStatus(row["status"]),
            parent_cycle_id=CycleId(row["parent_cycle_id"])
            if row.get("parent_cycle_id")
            else None,
            recovery_level=row.get("recovery_level", 0),
            accounting=accounting,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            if isinstance(row["created_at"], str)
            else row["created_at"],
            metadata=row.get("metadata", {}),
        )

    def _row_to_operation(self, row: Dict[str, Any]) -> Operation:
        """Convierte fila de DB a Operation."""
        from wsplumber.domain.types import OperationStatus, OperationType

        return Operation(
            id=OperationId(row["external_id"]),
            cycle_id=CycleId(row.get("cycle_external_id", "")),
            pair=CurrencyPair(row["pair"]),
            op_type=OperationType(row["op_type"]),
            status=OperationStatus(row["status"]),
            entry_price=Decimal(str(row["entry_price"])),
            tp_price=Decimal(str(row["tp_price"])),
            actual_entry_price=Decimal(str(row["actual_entry_price"]))
            if row.get("actual_entry_price")
            else None,
            actual_close_price=Decimal(str(row["actual_close_price"]))
            if row.get("actual_close_price")
            else None,
            lot_size=row["lot_size"],
            pips_target=row["pips_target"],
            profit_pips=row.get("profit_pips", 0.0),
            profit_eur=Decimal(str(row.get("profit_eur", 0))),
            commission_open=Decimal(str(row.get("commission_open", 7))),
            commission_close=Decimal(str(row.get("commission_close", 7))),
            swap_total=Decimal(str(row.get("swap_total", 0))),
            slippage_pips=row.get("slippage_pips", 0.0),
            broker_ticket=row.get("broker_ticket"),
            linked_operation_id=row.get("linked_operation_id"),
            recovery_id=row.get("recovery_id"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            if isinstance(row["created_at"], str)
            else row["created_at"],
            activated_at=datetime.fromisoformat(
                row["activated_at"].replace("Z", "+00:00")
            )
            if row.get("activated_at")
            else None,
            closed_at=datetime.fromisoformat(row["closed_at"].replace("Z", "+00:00"))
            if row.get("closed_at")
            else None,
            metadata=row.get("metadata", {}),
        )
