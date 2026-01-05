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
            operation.activate(
                ticket=order_res.broker_ticket,
                price=order_res.fill_price,
                timestamp=order_res.timestamp or datetime.now()
            )

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
        Útil para recuperarse de reinicios o fallos de red.
        """
        # 1. Obtener posiciones del broker
        broker_positions_res = await self.broker.get_open_positions()
        if not broker_positions_res.success:
            return Result.fail("Could not get positions from broker", "SYNC_ERROR")
        
        broker_positions = {str(p["ticket"]): p for p in broker_positions_res.value}

        # 2. Obtener operaciones activas del repo
        repo_ops_res = await self.repository.get_active_operations(pair)
        if not repo_ops_res.success:
            return Result.fail("Could not get active operations from repo", "SYNC_ERROR")
        
        repo_ops = repo_ops_res.value
        sync_count = 0

        # 3. Comparar y corregir
        for op in repo_ops:
            if op.broker_ticket not in broker_positions:
                # La operación está en el repo como activa pero NO en el broker
                # Probablemente se cerró por TP/SL manual o externo
                logger.warning("Operation in repo but not in broker. Syncing as closed.", operation_id=op.id, ticket=op.broker_ticket)
                # Habría que buscar el deal history para tener el precio real de cierre
                op.status = OperationStatus.CLOSED
                await self.repository.save_operation(op)
                sync_count += 1
        
        return Result.ok(sync_count)
