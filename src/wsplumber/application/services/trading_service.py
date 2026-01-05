# src/wsplumber/application/services/trading_service.py
"""
Servicio de Trading.

Coordina las operaciones entre el Broker y el Repositorio de persistencia.
Asegura que cada acción en el mercado se refleje en la base de datos.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from wsplumber.domain.interfaces.ports import IBroker, IRepository
from wsplumber.domain.types import (
    BrokerTicket,
    CurrencyPair,
    OperationId,
    OperationStatus,
    OrderRequest,
    OrderResult,
    Result,
)
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)


class TradingService:
    """
    Servicio que orquestra la ejecución de trades y su persistencia.
    """

    def __init__(self, broker: IBroker, repository: IRepository):
        self.broker = broker
        self.repository = repository

    async def open_operation(self, request: OrderRequest, operation: Operation) -> Result[OrderResult]:
        """
        Abre una operación en el broker y la actualiza en el repositorio.
        """
        try:
            # 1. Enviar al broker
            logger.info("Placing order", operation_id=operation.id, pair=operation.pair)
            broker_result = await self.broker.place_order(request)

            if not broker_result.success:
                logger.error("Broker rejected order", operation_id=operation.id, error=broker_result.error)
                return broker_result

            # 2. Actualizar entidad con datos del broker
            order_res = broker_result.value
            if order_res.fill_price:
                # Orden ejecutada inmediatamente (Market order o fill inmediato)
                operation.activate(
                    broker_ticket=order_res.broker_ticket,
                    fill_price=order_res.fill_price,
                    timestamp=order_res.timestamp or datetime.now()
                )
            else:
                # Orden pendiente (Stop/Limit)
                operation.mark_as_placed(order_res.broker_ticket)

            # 3. Persistir en repositorio
            save_result = await self.repository.save_operation(operation)
            if not save_result.success:
                logger.critical("Operation executed but failed to save in DB!", operation_id=operation.id)
                # TODO: Implementar outbox o compensación si es crítico
            
            return Result.ok(order_res)

        except Exception as e:
            logger.error("Failed to open operation", exception=e, operation_id=operation.id)
            return Result.fail(str(e), "TRADING_SERVICE_ERROR")

    async def close_operation(self, operation: Operation, reason: str = "manual") -> Result[OrderResult]:
        """
        Cierra una operación abierta.
        """
        if not operation.broker_ticket:
            return Result.fail("Operation has no broker ticket", "INVALID_STATE")

        try:
            # 1. Enviar cierre al broker
            logger.info("Closing position", ticket=operation.broker_ticket, operation_id=operation.id)
            broker_result = await self.broker.close_position(operation.broker_ticket)

            if not broker_result.success:
                return broker_result

            # 2. Actualizar entidad
            order_res = broker_result.value
            operation.close(
                price=order_res.fill_price,
                timestamp=order_res.timestamp or datetime.now()
            )

            # 3. Guardar en repositorio
            await self.repository.save_operation(operation)
            
            # 4. Si el ciclo se ve afectado, guardar ciclo (se asume que el orquestador maneja el impacto en el ciclo)
            
            return Result.ok(order_res)

        except Exception as e:
            logger.error("Failed to close operation", exception=e, operation_id=operation.id)
            return Result.fail(str(e), "TRADING_SERVICE_ERROR")

    async def sync_all_active_positions(self, pair: Optional[CurrencyPair] = None) -> Result[int]:
        """
        Sincroniza las posiciones abiertas entre el broker y la base de datos.
        """
        # 1. Obtener estado actual del broker
        broker_positions_res = await self.broker.get_open_positions()
        if not broker_positions_res.success:
            return Result.fail("Could not get positions from broker", "SYNC_ERROR")
        
        broker_positions = {str(p["ticket"]): p for p in broker_positions_res.value}

        # 2. Obtener operaciones del repo (Activas y Pendientes)
        repo_active_res = await self.repository.get_active_operations(pair)
        repo_pending_res = await self.repository.get_pending_operations(pair)
        
        if not repo_active_res.success or not repo_pending_res.success:
            return Result.fail("Could not get operations from repo", "SYNC_ERROR")
        
        sync_count = 0

        # 3. Sincronizar Pendientes -> Activas (Detección de activación)
        for op in repo_pending_res.value:
            if op.broker_ticket and str(op.broker_ticket) in broker_positions:
                logger.info("Pending operation activated in broker. Syncing.", operation_id=op.id)
                broker_pos = broker_positions[str(op.broker_ticket)]
                op.activate(
                    broker_ticket=op.broker_ticket,
                    fill_price=broker_pos.get("entry_price") or broker_pos.get("fill_price"),
                    timestamp=broker_pos.get("open_time") or datetime.now()
                )
                await self.repository.save_operation(op)
                sync_count += 1

        # 4. Sincronizar Activas -> Cerradas (Detección de cierre)
        for op in repo_active_res.value:
            if op.broker_ticket and str(op.broker_ticket) not in broker_positions:
                # La operación ya no está activa en el broker
                logger.warning("Active operation no longer in broker. Syncing as closed.", operation_id=op.id)
                # Intentamos buscar el precio de cierre en el historial del broker
                history_res = await self.broker.get_order_history()
                close_price = op.tp_price # Fallback si no lo encontramos
                close_time = datetime.now()
                
                if history_res.success:
                    for h_pos in history_res.value:
                        if str(h_pos.get("ticket")) == str(op.broker_ticket):
                            close_price = h_pos.get("actual_close_price") or h_pos.get("close_price") or op.tp_price
                            close_time = h_pos.get("closed_at") or h_pos.get("close_time") or datetime.now()
                            break
                            
                op.close(price=close_price, timestamp=close_time)
                await self.repository.save_operation(op)
                sync_count += 1
        
        return Result.ok(sync_count)
