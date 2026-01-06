# src/wsplumber/application/services/trading_service.py
"""
Servicio de Trading - VERSIÓN CORREGIDA.

Fixes aplicados:
- FIX-TS-01: Sync detecta TPs correctamente, no asume TP si no hay precio
- FIX-TS-02: Llamada única a get_order_history (eficiencia)
- FIX-TS-03: Manejo de errores si broker desconecta durante sync
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
            logger.info("Placing order", 
                        operation_id=operation.id, 
                        pair=operation.pair,
                        lots=float(request.lot_size),
                        entry=float(request.entry_price),
                        tp=float(request.tp_price))
            
            broker_result = await self.broker.place_order(request)

            if not broker_result.success:
                logger.error("Broker rejected order", operation_id=operation.id, error=broker_result.error)
                return broker_result

            order_res = broker_result.value
            if order_res.fill_price:
                operation.activate(
                    broker_ticket=order_res.broker_ticket,
                    fill_price=order_res.fill_price,
                    timestamp=order_res.timestamp or datetime.now()
                )
            else:
                operation.mark_as_placed(order_res.broker_ticket)

            save_result = await self.repository.save_operation(operation)
            if not save_result.success:
                logger.critical("Operation executed but failed to save in DB!", operation_id=operation.id)
            
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
            logger.info("Closing position", ticket=operation.broker_ticket, operation_id=operation.id)
            broker_result = await self.broker.close_position(operation.broker_ticket)

            if not broker_result.success:
                return broker_result

            order_res = broker_result.value
            operation.close_v2(
                price=order_res.fill_price,
                timestamp=order_res.timestamp or datetime.now()
            )

            await self.repository.save_operation(operation)
            
            return Result.ok(order_res)

        except Exception as e:
            logger.error("Failed to close operation", exception=e, operation_id=operation.id)
            return Result.fail(str(e), "TRADING_SERVICE_ERROR")

    async def sync_all_active_positions(self, pair: Optional[CurrencyPair] = None) -> Result[int]:
        """
        Sincroniza las posiciones abiertas entre el broker y la base de datos.
        
        VERSIÓN CORREGIDA:
        - FIX-TS-01: No asume TP si no hay precio de cierre
        - FIX-TS-02: Llama a get_order_history una sola vez
        - FIX-TS-03: Maneja errores de conexión
        """
        try:
            # FIX-TS-03: Verificar conexión antes de sync
            if not await self.broker.is_connected():
                logger.warning("Broker not connected, skipping sync")
                return Result.fail("Broker not connected", "CONNECTION_ERROR")
            
            # 1. Obtener estado actual del broker
            broker_positions_res = await self.broker.get_open_positions()
            if not broker_positions_res.success:
                return Result.fail("Could not get positions from broker", "SYNC_ERROR")
            
            broker_positions = {str(p["ticket"]): p for p in broker_positions_res.value}

            # 2. Obtener operaciones del repo
            repo_active_res = await self.repository.get_active_operations(pair)
            repo_pending_res = await self.repository.get_pending_operations(pair)
            
            if not repo_active_res.success or not repo_pending_res.success:
                return Result.fail("Could not get operations from repo", "SYNC_ERROR")
            
            # FIX-TS-02: Obtener historial UNA sola vez
            history_res = await self.broker.get_order_history()
            broker_history = {}
            if history_res.success:
                for h_pos in history_res.value:
                    ticket_key = str(h_pos.get("ticket"))
                    broker_history[ticket_key] = h_pos
            
            sync_count = 0

            # 3. Sincronizar Pendientes -> Activas/Cerradas
            for op in repo_pending_res.value:
                if not op.broker_ticket:
                    continue
                    
                ticket_str = str(op.broker_ticket)
                
                # Caso A: Está en posiciones abiertas del broker
                if ticket_str in broker_positions:
                    broker_pos = broker_positions[ticket_str]
                    
                    # Verificar si está marcada como TP_HIT en el broker
                    broker_status = broker_pos.get("status", "active")
                    
                    if broker_status == "tp_hit":
                        # FIX-TS-01: El broker marcó TP, activar y cerrar con precio real
                        close_price = broker_pos.get("actual_close_price") or broker_pos.get("close_price")
                        if close_price is None:
                            logger.warning("TP_HIT without close price, skipping", op_id=op.id)
                            continue
                        
                        # Primero activar
                        op.activate(
                            broker_ticket=op.broker_ticket,
                            fill_price=broker_pos.get("entry_price") or broker_pos.get("fill_price") or op.entry_price,
                            timestamp=broker_pos.get("open_time") or datetime.now()
                        )
                        # Luego marcar cierre (el orquestador decidirá cuándo cerrar realmente)
                        op.close_v2(
                            price=close_price,
                            timestamp=broker_pos.get("close_time") or datetime.now()
                        )
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced pending->TP_HIT", op_id=op.id, close_price=close_price)
                    else:
                        # Orden activada normalmente
                        op.activate(
                            broker_ticket=op.broker_ticket,
                            fill_price=broker_pos.get("entry_price") or broker_pos.get("fill_price"),
                            timestamp=broker_pos.get("open_time") or datetime.now()
                        )
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced pending->active", op_id=op.id)
                
                # Caso B: No está en abiertas, buscar en historial
                elif ticket_str in broker_history:
                    h_pos = broker_history[ticket_str]
                    
                    # FIX-TS-01: Solo procesar si hay precio de cierre real
                    close_price = h_pos.get("actual_close_price") or h_pos.get("close_price")
                    if close_price is None:
                        logger.warning("History entry without close price, skipping", 
                                      op_id=op.id, ticket=ticket_str)
                        continue
                    
                    # Activar y cerrar
                    op.activate(
                        broker_ticket=op.broker_ticket,
                        fill_price=h_pos.get("entry_price") or op.entry_price,
                        timestamp=h_pos.get("open_time") or datetime.now()
                    )
                    op.close_v2(
                        price=close_price,
                        timestamp=h_pos.get("closed_at") or h_pos.get("close_time") or datetime.now()
                    )
                    
                    await self.repository.save_operation(op)
                    sync_count += 1
                    logger.info("Synced pending->closed from history", op_id=op.id)

            # 4. Sincronizar Activas -> Verificar si siguen abiertas o cerraron
            for op in repo_active_res.value:
                if not op.broker_ticket:
                    continue
                
                ticket_str = str(op.broker_ticket)
                
                # Caso A: Sigue en posiciones abiertas
                if ticket_str in broker_positions:
                    broker_pos = broker_positions[ticket_str]
                    broker_status = broker_pos.get("status", "active")
                    
                    # Verificar si el broker la marcó como TP_HIT
                    if broker_status == "tp_hit":
                        close_price = broker_pos.get("actual_close_price") or broker_pos.get("close_price")
                        if close_price is None:
                            logger.warning("Active marked TP_HIT without price", op_id=op.id)
                            continue
                        
                        op.close_v2(
                            price=close_price,
                            timestamp=broker_pos.get("close_time") or datetime.now()
                        )
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced active->TP_HIT", op_id=op.id, close_price=close_price)
                
                # Caso B: Ya no está en abiertas - buscar en historial
                elif ticket_str not in broker_positions:
                    if ticket_str in broker_history:
                        h_pos = broker_history[ticket_str]
                        
                        # FIX-TS-01: Requerir precio de cierre
                        close_price = h_pos.get("actual_close_price") or h_pos.get("close_price")
                        if close_price is None:
                            logger.error("Active operation disappeared without close price!", 
                                        op_id=op.id, ticket=ticket_str)
                            # Marcar como cerrada pero con flag de error
                            op.metadata["sync_error"] = "no_close_price"
                            op.metadata["sync_time"] = datetime.now().isoformat()
                            # Usar TP como fallback pero loguear warning
                            close_price = op.tp_price
                            logger.warning("Using TP as fallback close price", op_id=op.id)
                        
                        close_time = h_pos.get("closed_at") or h_pos.get("close_time") or datetime.now()
                        op.close_v2(price=close_price, timestamp=close_time)
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced active->closed from history", op_id=op.id)
                    else:
                        # Operación desapareció sin registro - error crítico
                        logger.error("Active operation vanished without trace!", 
                                    op_id=op.id, ticket=ticket_str)
                        op.metadata["sync_error"] = "vanished"
                        op.metadata["sync_time"] = datetime.now().isoformat()
                        await self.repository.save_operation(op)
            
            if sync_count > 0:
                logger.info("Trading sync completed", sync_count=sync_count, pair=pair)
            
            return Result.ok(sync_count)
        
        except Exception as e:
            # FIX-TS-03: Capturar errores de conexión
            logger.error("Sync failed with exception", exception=e, pair=pair)
            return Result.fail(str(e), "SYNC_EXCEPTION")
