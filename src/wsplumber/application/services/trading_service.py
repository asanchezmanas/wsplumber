# src/wsplumber/application/services/trading_service.py
"""
Servicio de Trading - VERSIÓN CORREGIDA.

Fixes aplicados:
- FIX-TS-01: Sync detecta TPs correctamente, no asume TP si no hay precio
- FIX-TS-02: Llamada única a get_order_history (eficiencia)
- FIX-TS-03: Manejo de errores si broker desconecta durante sync
- FIX-CLOSE-03: Prevenir cierre de operaciones ya cerradas (double-close protection + race condition)
  * Verificar estado antes y después del broker.close_position()
  * Capturar ValueError de close_v2() cuando estado no permite cerrar
  * Aplicado en close_operation() líneas 90-127
- FIX-CLOSE-04: Realizar P&L en sync cuando broker marca TP_HIT
  * Llamar a broker.close_position() durante sync para mover P&L al balance
  * Aplicado en sync_all_active_positions() para pending->TP_HIT y active->TP_HIT
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from wsplumber.domain.interfaces.ports import IBroker, IRepository
from wsplumber.domain.types import (
    BrokerTicket,
    CurrencyPair,
    OperationId,
    OperationStatus,
    OrderRequest,
    OrderResult,
    Result,
    Price,
)
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.infrastructure.logging.safe_logger import get_logger
from wsplumber.core.strategy._params import (
    LAYER1_MODE, TRAILING_LEVELS, TRAILING_REPOSITION, TRAILING_MIN_LOCK
)

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
            # FIX-CLOSE-05: Solo rechazar si está CLOSED, permitir TP_HIT
            # Las operaciones en TP_HIT necesitan cerrarse en el broker para realizar el P&L
            if operation.status == OperationStatus.CLOSED:
                logger.warning("Attempted to close already-closed operation",
                             operation_id=operation.id,
                             status=operation.status.value)
                return Result.fail(f"Operation already closed (status={operation.status.value})", "ALREADY_CLOSED")

            logger.info("Closing position", ticket=operation.broker_ticket, operation_id=operation.id)
            broker_result = await self.broker.close_position(operation.broker_ticket)

            if not broker_result.success:
                # FIX-CLOSE-07: Idempotencia para "Position not found"
                # Si el broker dice que no existe, es que ya se cerró (probablemente por sync o TP real)
                if "not found" in str(broker_result.error).lower():
                    logger.warning("Position not found in broker (already closed?), continuing", 
                                 op_id=operation.id, ticket=operation.broker_ticket)
                    # Forjamos un OrderResult básico para continuar el flujo local
                    order_res = OrderResult(
                        success=True, 
                        broker_ticket=operation.broker_ticket,
                        fill_price=operation.tp_price or operation.entry_price, # Fallback
                        timestamp=datetime.now()
                    )
                else:
                    return broker_result
            else:
                order_res = broker_result.value

            # FIX-CLOSE-05: Verificar si ya está CLOSED (race condition)
            # Si está en TP_HIT, es normal - el orchestrator lo marcó así antes de llamarnos
            if operation.status == OperationStatus.CLOSED:
                logger.warning("Operation was closed by another process during broker close",
                             operation_id=operation.id,
                             status=operation.status.value)
                return Result.ok(order_res)  # El broker cerró exitosamente, aceptar

            # Si estaba en TP_HIT, no llamar close_v2 de nuevo (ya está cerrado lógicamente)
            if operation.status != OperationStatus.TP_HIT:
                operation.close_v2(
                    price=order_res.fill_price,
                    timestamp=order_res.timestamp or datetime.now()
                )

            await self.repository.save_operation(operation)

            return Result.ok(order_res)

        except ValueError as e:
            # close_v2() puede lanzar ValueError si el estado no permite cerrar
            logger.error("Failed to close operation - invalid state",
                        exception=e,
                        operation_id=operation.id,
                        status=operation.status.value)
            return Result.fail(f"Invalid state for close: {str(e)}", "INVALID_STATE")
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
                        raw_close_price = broker_pos.get("actual_close_price") or broker_pos.get("close_price")
                        if raw_close_price is None:
                            logger.warning("TP_HIT without close price, skipping", op_id=op.id)
                            continue
                        
                        # FIX-CLOSE-04: Cerrar en el broker para realizar el P&L
                        close_result = await self.broker.close_position(op.broker_ticket)
                        if not close_result.success:
                            logger.error("Failed to close TP_HIT position in broker", 
                                        op_id=op.id, error=close_result.error)
                            continue
                        
                        close_price = Price(Decimal(str(raw_close_price)))
                        fill_price = Price(Decimal(str(broker_pos.get("entry_price") or broker_pos.get("fill_price") or op.entry_price)))
                        
                        # Primero activar
                        op.activate(
                            fill_price=fill_price,
                            broker_ticket=op.broker_ticket,
                            timestamp=broker_pos.get("open_time") or datetime.now()
                        )
                        # Luego marcar cierre
                        op.close_v2(
                            price=close_price,
                            timestamp=broker_pos.get("close_time") or datetime.now()
                        )
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced pending->TP_HIT (P&L realized)", op_id=op.id, close_price=float(close_price))
                    else:
                        # FIX-SYNC-NULLENTRY: Skip if no entry price available
                        raw_fill_price = broker_pos.get("entry_price") or broker_pos.get("fill_price") or op.entry_price
                        if raw_fill_price is None:
                            logger.warning("Cannot sync pending->active: no entry price", op_id=op.id)
                            continue
                        fill_price = Price(Decimal(str(raw_fill_price)))
                        # Orden activada normalmente
                        op.activate(
                            fill_price=fill_price,
                            broker_ticket=op.broker_ticket,
                            timestamp=broker_pos.get("open_time") or datetime.now()
                        )
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced pending->active", op_id=op.id)
                
                # Caso B: No está en abiertas, buscar en historial
                elif ticket_str in broker_history:
                    h_pos = broker_history[ticket_str]
                    
                    # FIX-TS-01: Solo procesar si hay precio de cierre real
                    raw_close_price = h_pos.get("actual_close_price") or h_pos.get("close_price")
                    if raw_close_price is None:
                        logger.warning("History entry without close price, skipping", 
                                      op_id=op.id, ticket=ticket_str)
                        continue
                    
                    # Garantizar tipos Decimal para operar con seguridad
                    close_price = Price(Decimal(str(raw_close_price)))
                    raw_entry_price = h_pos.get("entry_price") or op.entry_price
                    fill_price = Price(Decimal(str(raw_entry_price)))
                    
                    # Activar y cerrar
                    op.activate(
                        fill_price=fill_price,
                        broker_ticket=op.broker_ticket,
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
                        raw_close_price = broker_pos.get("actual_close_price") or broker_pos.get("close_price")
                        if raw_close_price is None:
                            logger.warning("Active marked TP_HIT without price", op_id=op.id)
                            continue
                        
                        # FIX-CLOSE-04: Cerrar en el broker para realizar el P&L
                        close_result = await self.broker.close_position(op.broker_ticket)
                        if not close_result.success:
                            logger.error("Failed to close TP_HIT position in broker", 
                                        op_id=op.id, error=close_result.error)
                            continue
                        
                        close_price = Price(Decimal(str(raw_close_price)))
                        op.close_v2(
                            price=close_price,
                            timestamp=broker_pos.get("close_time") or datetime.now()
                        )
                        await self.repository.save_operation(op)
                        sync_count += 1
                        logger.info("Synced active->TP_HIT (P&L realized)", op_id=op.id, close_price=float(close_price))
                    
                    # ══════════════════════════════════════════════════════════════
                    # IMMUNE SYSTEM LAYER 1: ADAPTIVE TRAILING STOP
                    # ══════════════════════════════════════════════════════════════
                    elif broker_status == "active" and LAYER1_MODE == "ADAPTIVE_TRAILING":
                        # Only apply to recovery operations
                        if op.is_recovery:
                            if await self._process_adaptive_trailing(op, broker_pos):
                                sync_count += 1
                
                # Caso B: Ya no está en abiertas - buscar en historial
                elif ticket_str not in broker_positions:
                    if ticket_str in broker_history:
                        h_pos = broker_history[ticket_str]
                        
                        # FIX-TS-01: Requerir precio de cierre
                        raw_close_price = h_pos.get("actual_close_price") or h_pos.get("close_price")
                        if raw_close_price is None:
                            logger.error("Active operation disappeared without close price!", 
                                        op_id=op.id, ticket=ticket_str)
                            # Marcar como cerrada pero con flag de error
                            op.metadata["sync_error"] = "no_close_price"
                            op.metadata["sync_time"] = datetime.now().isoformat()
                            # Usar TP como fallback pero loguear warning
                            close_price = op.tp_price
                            logger.warning("Using TP as fallback close price", op_id=op.id)
                        else:
                            close_price = Price(Decimal(str(raw_close_price)))
                        
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

            # 5. FIX-CLOSE-06: Limpiar posiciones zombie (tp_hit en broker pero sin cerrar)
            # Buscar operaciones TP_HIT en el repo que aún tienen posiciones abiertas en el broker
            all_ops = await self.repository.get_all_operations()
            tp_hit_ops = [op for op in all_ops if op.status == OperationStatus.TP_HIT]
            if pair:
                tp_hit_ops = [op for op in tp_hit_ops if op.pair == pair]

            for op in tp_hit_ops:
                    if not op.broker_ticket:
                        continue

                    ticket_str = str(op.broker_ticket)

                    # Si la posición sigue en el broker con status tp_hit, cerrarla
                    if ticket_str in broker_positions:
                        broker_pos = broker_positions[ticket_str]
                        broker_status = broker_pos.get("status", "active")

                        if broker_status == "tp_hit":
                            logger.warning("Found zombie TP_HIT position, closing in broker",
                                          op_id=op.id, ticket=ticket_str)

                            close_result = await self.broker.close_position(op.broker_ticket)
                            if close_result.success:
                                sync_count += 1
                                logger.info("Zombie position closed successfully", op_id=op.id)
                            else:
                                logger.error("Failed to close zombie position",
                                           op_id=op.id, error=close_result.error)

            if sync_count > 0:
                logger.info("Trading sync completed", sync_count=sync_count, pair=pair)
            
            return Result.ok(sync_count)
        
        except Exception as e:
            # FIX-TS-03: Capturar errores de conexión
            logger.error("Sync failed with exception", _exception=e, pair=pair)
            return Result.fail(str(e), "SYNC_EXCEPTION")

    async def _process_adaptive_trailing(self, op: Operation, broker_pos: Dict[str, Any]) -> bool:
        """
        IMMUNE SYSTEM LAYER 1: Adaptive Trailing Stop
        
        Tracks maximum profit and applies progressive trailing stops
        to capture partial profits instead of letting them evaporate.
        
        Returns True if position was closed (for sync_count tracking).
        
        BUGS FIXED:
        - BUG1: Correct BID/ASK for BUY/SELL
        - BUG2: Returns bool for sync_count
        - BUG3: Checks status before close_v2
        - BUG4: Sets metadata for orchestrator to reduce debt proportionally
        - BUG5: REPOSITION handled by orchestrator via metadata
        """
        try:
            # BUG3 FIX: Skip if already closed
            if op.status in (OperationStatus.CLOSED, OperationStatus.TP_HIT, OperationStatus.CANCELLED):
                return False
            
            # 1. Calculate current floating pips with correct price
            # BUG1 FIX: Use ASK for closing BUY, BID for closing SELL
            if op.is_buy:
                current_price = broker_pos.get("bid") or broker_pos.get("current_price")
            else:
                current_price = broker_pos.get("ask") or broker_pos.get("current_price")
            
            if not current_price:
                return False
            
            multiplier = 100 if "JPY" in str(op.pair) else 10000
            entry = float(op.actual_entry_price or op.entry_price)
            curr = float(current_price)
            
            if op.is_buy:
                floating_pips = (curr - entry) * multiplier
            else:
                floating_pips = (entry - curr) * multiplier
            
            # 2. Track maximum profit reached
            max_profit = op.metadata.get("max_profit_pips", 0.0)
            prev_max = max_profit
            if floating_pips > max_profit:
                op.metadata["max_profit_pips"] = floating_pips
                max_profit = floating_pips
                await self.repository.save_operation(op)
                
                # Log significant profit increases (every 10 pips)
                if int(max_profit / 10) > int(prev_max / 10):
                    logger.info("LAYER1-TRAILING: New max profit milestone",
                               op_id=op.id,
                               max_profit=round(max_profit, 1),
                               prev_max=round(prev_max, 1))
            
            # 3. Determine current trailing stop level based on max_profit
            trailing_stop = 0.0
            active_level = 0
            for i, (threshold, lock) in enumerate(TRAILING_LEVELS):
                if max_profit >= threshold:
                    trailing_stop = lock
                    active_level = i + 1
            
            # 4. If no trailing level reached, nothing to do
            if trailing_stop <= 0:
                return False
            
            # 5. Update trailing metadata if level changed
            if op.metadata.get("trailing_level", 0) != active_level:
                op.metadata["trailing_level"] = active_level
                op.metadata["trailing_stop_pips"] = trailing_stop
                op.metadata["trailing_active"] = True
                await self.repository.save_operation(op)
                logger.info("LAYER1-TRAILING: Level activated",
                           op_id=op.id,
                           level=active_level,
                           max_profit=round(max_profit, 1),
                           trailing_stop=trailing_stop)
            
            # 6. Check if price hit trailing stop
            if floating_pips <= trailing_stop and op.metadata.get("trailing_active"):
                # Ensure minimum profit threshold
                if floating_pips < TRAILING_MIN_LOCK:
                    logger.debug("LAYER1-TRAILING: Below minimum lock, waiting",
                               op_id=op.id,
                               floating_pips=round(floating_pips, 1),
                               min_lock=TRAILING_MIN_LOCK)
                    return False
                
                logger.info("LAYER1-TRAILING: Stop hit, closing with partial profit",
                           op_id=op.id,
                           max_profit=round(max_profit, 1),
                           close_at=round(floating_pips, 1),
                           captured_pct=round(floating_pips / max_profit * 100, 0) if max_profit > 0 else 0,
                           level=active_level,
                           entry_price=entry,
                           exit_price=curr,
                           distance_to_tp=round(80.0 - max_profit, 1))
                
                # Close position
                close_result = await self.broker.close_position(op.broker_ticket)
                if close_result.success:
                    close_price = Price(Decimal(str(current_price)))
                    
                    # BUG4 FIX: Set metadata for orchestrator to process partial profit
                    # The orchestrator will read this and apply proportional debt reduction
                    op.metadata["trailing_closed"] = True
                    op.metadata["trailing_profit_pips"] = floating_pips
                    op.metadata["close_reason"] = "trailing_stop"
                    
                    # BUG5 FIX: Signal orchestrator to open replacement recovery
                    if TRAILING_REPOSITION:
                        op.metadata["needs_reposition"] = True
                        op.metadata["reposition_price"] = float(current_price)
                    
                    # BUG3 FIX: Check status before close_v2
                    if op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
                        op.close_v2(price=close_price, timestamp=datetime.now())
                    
                    await self.repository.save_operation(op)
                    
                    logger.info("LAYER1-TRAILING: Position closed successfully",
                               op_id=op.id,
                               profit_pips=round(floating_pips, 1),
                               close_price=float(close_price),
                               needs_reposition=op.metadata.get("needs_reposition", False))
                    
                    return True  # BUG2 FIX: Return True for sync_count
                else:
                    logger.error("LAYER1-TRAILING: Failed to close position",
                                op_id=op.id,
                                error=close_result.error)
                    return False
            
            return False
        
        except Exception as e:
            logger.error("LAYER1-TRAILING: Error in adaptive trailing",
                        op_id=op.id,
                        exception=str(e))
            return False


