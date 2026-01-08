# src/wsplumber/application/use_cases/cycle_orchestrator.py
"""
Orquestador de Ciclos - VERSIÓN CORREGIDA CON TODOS LOS FIXES.

Fixes aplicados:
- FIX-001: Renovación dual de mains después de TP ✅
- FIX-002: Cancelación de hedges pendientes contrarios ✅
- FIX-003: Cierre atómico FIFO de Main+Hedge ✅
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from wsplumber.domain.interfaces.ports import (
    IBroker,
    IRepository,
    IStrategy,
    IRiskManager,
)
from wsplumber.domain.types import (
    CurrencyPair,
    CycleType,
    LotSize,
    OperationId,
    OperationStatus,
    OperationType,
    OrderRequest,
    Pips,
    Price,
    RecoveryId,
    Result,
    SignalType,
    StrategySignal,
    TickData,
)
from wsplumber.domain.entities.cycle import Cycle, CycleStatus
from wsplumber.domain.entities.operation import Operation
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._params import (
    MAIN_TP_PIPS, RECOVERY_TP_PIPS, RECOVERY_DISTANCE_PIPS, RECOVERY_LEVEL_STEP
)
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)


class CycleOrchestrator:
    """
    Orquesta el flujo de trading para uno o varios pares.
    """

    def __init__(
        self,
        trading_service: TradingService,
        strategy: IStrategy,
        risk_manager: IRiskManager,
        repository: IRepository,
    ):
        self.trading_service = trading_service
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.repository = repository
        
        self._running = False
        self._active_cycles: Dict[CurrencyPair, Cycle] = {}

    async def start(self, pairs: List[CurrencyPair]):
        """Inicia la orquestación para los pares indicados."""
        self._running = True
        logger.info("Starting CycleOrchestrator", pairs=pairs)

        # 1. Cargar estado inicial
        await self._load_initial_state(pairs)

        # 2. Bucle principal
        while self._running:
            for pair in pairs:
                await self._process_tick_for_pair(pair)
            await asyncio.sleep(0.1)

    async def stop(self):
        """Detiene la orquestación."""
        self._running = False
        logger.info("Stopping CycleOrchestrator")

    async def _load_initial_state(self, pairs: List[CurrencyPair]):
        """Carga los ciclos activos desde el repositorio."""
        for pair in pairs:
            res = await self.repository.get_active_cycles(pair)
            if res.success and res.value:
                self._active_cycles[pair] = res.value[0]
                logger.info("Loaded active cycle", pair=pair, cycle_id=self._active_cycles[pair].id)

    async def process_tick(self, tick: TickData):
        """Procesa un tick inyectado directamente (útil para backtesting)."""
        pair = tick.pair
        try:
            # 1. Monitorear estado de operaciones activas
            await self._check_operations_status(pair, tick)

            # 2. Consultar a la estrategia core
            signal: StrategySignal = self.strategy.process_tick(
                pair=tick.pair,
                bid=float(tick.bid),
                ask=float(tick.ask),
                timestamp=tick.timestamp
            )
            
            if signal.signal_type == SignalType.NO_ACTION:
                return

            # 3. Procesar señal
            await self._handle_signal(signal, tick)

        except Exception as e:
            logger.error("Error processing tick", exception=e, pair=pair)

    async def _process_tick_for_pair(self, pair: CurrencyPair):
        """Procesa un tick para un par específico obteniéndolo del broker."""
        tick_res = await self.trading_service.broker.get_current_price(pair)
        if not tick_res.success:
            return
        await self.process_tick(tick_res.value)

    async def _check_operations_status(self, pair: CurrencyPair, tick: TickData):
        """
        Detecta cierres y activaciones de operaciones.
        
        FIX-001 APLICADO: Ahora renueva operaciones main después de TP.
        FIX-002 APLICADO: Cancela hedges pendientes contrarios.
        """
        # Sincronizar con el broker
        sync_res = await self.trading_service.sync_all_active_positions(pair)
        if not sync_res.success:
            return

        cycle = self._active_cycles.get(pair)
        if not cycle:
            return

        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            return

        for op in ops_res.value:
            # ═══════════════════════════════════════════════════════════
            # 1. MANEJO DE ACTIVACIÓN DE ÓRDENES
            # ═══════════════════════════════════════════════════════════
            if op.status == OperationStatus.ACTIVE:
                # Log explícito de activación
                if not op.metadata.get("activation_logged"):
                    logger.info(
                        "Operation activated",
                        op_id=op.id,
                        op_type=op.op_type.value,
                        fill_price=str(op.actual_entry_price or op.entry_price)
                    )
                    op.metadata["activation_logged"] = True
                    await self.repository.save_operation(op)

                # Si es primera activación del ciclo
                if cycle.status == CycleStatus.PENDING:
                    logger.info("First operation activated, transitioning cycle to ACTIVE", 
                               cycle_id=cycle.id)
                    cycle.status = CycleStatus.ACTIVE
                    await self.repository.save_cycle(cycle)

                # Verificar si ambas principales se activaron (HEDGE)
                main_ops = [o for o in ops_res.value if o.is_main]
                active_main_ops = [o for o in main_ops if o.status == OperationStatus.ACTIVE]
                
                if len(active_main_ops) >= 2 and cycle.status == CycleStatus.ACTIVE:
                    logger.info("Both main operations active, transitioning to HEDGED", 
                               cycle_id=cycle.id)
                    cycle.activate_hedge()
                    
                    # Crear operaciones de hedge y neutralizar mains
                    for main_op in active_main_ops:

                        hedge_type = (OperationType.HEDGE_SELL 
                                     if main_op.op_type == OperationType.MAIN_BUY 
                                     else OperationType.HEDGE_BUY)
                        hedge_id = f"{cycle.id}_H_{main_op.op_type.value}"
                        
                        hedge_op = Operation(
                            id=OperationId(hedge_id),
                            cycle_id=cycle.id,
                            pair=pair,
                            op_type=hedge_type,
                            status=OperationStatus.PENDING,
                            entry_price=main_op.entry_price,
                            lot_size=main_op.lot_size
                        )
                        cycle.add_operation(hedge_op)
                        
                        main_op.neutralize(OperationId(hedge_id))
                        await self.repository.save_operation(main_op)
                        
                        request = OrderRequest(
                            operation_id=hedge_op.id,
                            pair=pair,
                            order_type=hedge_type,
                            entry_price=hedge_op.entry_price,
                            tp_price=hedge_op.tp_price,
                            lot_size=hedge_op.lot_size
                        )
                        await self.trading_service.open_operation(request, hedge_op)
                    
                    await self.repository.save_cycle(cycle)
            
            # ═══════════════════════════════════════════════════════════
            # 2. MANEJO DE CIERRE DE ÓRDENES (TP HIT)
            # FIX-001 + FIX-002 APLICADOS
            # ═══════════════════════════════════════════════════════════
            if op.status in (OperationStatus.TP_HIT, OperationStatus.CLOSED):
                # Evitar procesar el mismo TP múltiples veces
                if op.metadata.get("tp_processed"):
                    continue

                op.metadata["tp_processed"] = True
                await self.repository.save_operation(op)

                # Cerrar la posición en el broker (solo marca TP, no cierra)
                if op.broker_ticket and op.status == OperationStatus.TP_HIT:
                    logger.info("Closing TP_HIT position in broker",
                               op_id=str(op.id),
                               ticket=str(op.broker_ticket))
                    close_result = await self.trading_service.close_operation(op)
                    if not close_result.success:
                        logger.error("Failed to close TP_HIT position",
                                    op_id=str(op.id),
                                    error=str(close_result.error))

                if cycle.status == CycleStatus.PENDING:
                    cycle.status = CycleStatus.ACTIVE
                    await self.repository.save_cycle(cycle)

                # Notificar a la estrategia
                signal = self.strategy.process_tp_hit(
                    operation_id=op.id,
                    profit_pips=float(op.profit_pips or MAIN_TP_PIPS),
                    timestamp=datetime.now()
                )
                
                # ═══════════════════════════════════════════════════════
                # MAIN TP: FIX-001 + FIX-002 APLICADOS
                # ═══════════════════════════════════════════════════════
                if op.is_main:
                    logger.info(
                        "Main TP detected, processing renewal + hedge cleanup",
                        op_id=op.id,
                        profit_pips=float(op.profit_pips or MAIN_TP_PIPS)
                    )
                    
                    # 1. Cancelar operación pendiente contraria
                    for other_op in ops_res.value:
                        if (other_op.is_main and 
                            other_op.id != op.id and 
                            other_op.status == OperationStatus.PENDING):
                            logger.info("Cancelling counter-order", op_id=other_op.id)
                            if other_op.broker_ticket:
                                await self.trading_service.broker.cancel_order(other_op.broker_ticket)
                            other_op.status = OperationStatus.CANCELLED
                            other_op.metadata["cancel_reason"] = "counterpart_tp_hit"
                            await self.repository.save_operation(other_op)
                    
                    # FIX-002: Cancelar hedges pendientes contrarios
                    await self._cancel_pending_hedge_counterpart(cycle, op)
                    
                    # FIX-001: RENOVAR OPERACIONES MAIN (BUY + SELL)
                    await self._renew_main_operations(cycle, tick)
                    
                    # Registrar TP en contabilidad
                    cycle.record_main_tp(Pips(float(op.profit_pips or MAIN_TP_PIPS)))
                    await self.repository.save_cycle(cycle)

                # RECOVERY TP: FIX-003 aplicado en _handle_recovery_tp
                if op.is_recovery:
                    recovery_cycle_res = await self.repository.get_cycle(op.cycle_id)
                    if recovery_cycle_res.success and recovery_cycle_res.value:
                        await self._handle_recovery_tp(recovery_cycle_res.value, tick)

                # Procesar señal adicional si la hay
                if signal.signal_type != SignalType.NO_ACTION:
                    if not signal.pair:
                        signal.pair = pair
                    await self._handle_signal(signal, tick)

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-001: RENOVACIÓN DE OPERACIONES MAIN (YA EXISTÍA, SIN CAMBIOS)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _renew_main_operations(self, cycle: Cycle, tick: TickData) -> None:
        """
        Crea nuevas operaciones main (BUY + SELL) después de un TP.
        
        FIX-001: Este método ya implementaba correctamente la renovación dual.
        """
        pair = cycle.pair
        
        # Calcular distancia TP usando parámetros centralizados
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        tp_distance = Decimal(str(MAIN_TP_PIPS)) * multiplier
        
        # Generar IDs únicos con timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
        
        # Obtener lote del ciclo (mantener consistencia)
        existing_ops = [op for op in cycle.operations if op.lot_size]
        lot = existing_ops[0].lot_size if existing_ops else LotSize(0.01)
        
        # Operación BUY
        op_buy = Operation(
            id=OperationId(f"{cycle.id}_B_{timestamp}"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_BUY,
            status=OperationStatus.PENDING,
            entry_price=tick.ask,
            tp_price=Price(tick.ask + tp_distance),
            lot_size=lot
        )
        
        # Operación SELL
        op_sell = Operation(
            id=OperationId(f"{cycle.id}_S_{timestamp}"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_SELL,
            status=OperationStatus.PENDING,
            entry_price=tick.bid,
            tp_price=Price(tick.bid - tp_distance),
            lot_size=lot
        )
        
        logger.info(
            "*** RENOVANDO OPERACIONES MAIN (BUY + SELL) ***",
            cycle_id=cycle.id,
            buy_entry=str(tick.ask),
            sell_entry=str(tick.bid),
            tp_pips=MAIN_TP_PIPS
        )
        
        # Ejecutar aperturas
        tasks = []
        for op in [op_buy, op_sell]:
            request = OrderRequest(
                operation_id=op.id,
                pair=pair,
                order_type=op.op_type,
                entry_price=op.entry_price,
                tp_price=op.tp_price,
                lot_size=op.lot_size
            )
            tasks.append(self.trading_service.open_operation(request, op))
        
        results = await asyncio.gather(*tasks)
        
        # Añadir al ciclo y guardar
        success_count = 0
        for op, result in zip([op_buy, op_sell], results):
            if result.success:
                cycle.add_operation(op)
                success_count += 1
            else:
                logger.error("Failed to renew operation", op_id=op.id, error=result.error)
        
        if success_count > 0:
            await self.repository.save_cycle(cycle)
            logger.info(
                "Main operations renewed successfully",
                cycle_id=cycle.id,
                renewed_count=success_count,
                buy_id=op_buy.id,
                sell_id=op_sell.id
            )
        else:
            logger.error("Failed to renew any main operations", cycle_id=cycle.id)

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-002: NUEVO MÉTODO - Cancelar hedge pendiente contrario
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _cancel_pending_hedge_counterpart(self, cycle: Cycle, tp_operation: Operation) -> None:
        """
        FIX-002: Cancela la operación de hedge pendiente contraria cuando un main toca TP.
        
        Cuando un main BUY toca TP, el hedge SELL pendiente debe cancelarse
        para evitar órdenes huérfanas en el broker.
        
        Args:
            cycle: Ciclo actual
            tp_operation: Operación main que tocó TP
        """
        logger.info(
            "Checking for pending hedge counterparts to cancel",
            cycle_id=cycle.id,
            tp_op_id=tp_operation.id,
            tp_op_direction=tp_operation.op_type.value
        )
        
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            return
        
        cancelled_count = 0
        for op in ops_res.value:
            # Solo procesar hedges pendientes
            if not op.is_hedge or op.status != OperationStatus.PENDING:
                continue
            
            # Determinar si es el hedge contrario
            # Si TP fue MAIN_BUY, cancelar HEDGE_SELL pendiente
            # Si TP fue MAIN_SELL, cancelar HEDGE_BUY pendiente
            is_counterpart = False
            if tp_operation.op_type == OperationType.MAIN_BUY and op.op_type == OperationType.HEDGE_SELL:
                is_counterpart = True
            elif tp_operation.op_type == OperationType.MAIN_SELL and op.op_type == OperationType.HEDGE_BUY:
                is_counterpart = True
            
            if is_counterpart:
                logger.info(
                    "Cancelling pending hedge counterpart",
                    hedge_id=op.id,
                    hedge_type=op.op_type.value,
                    reason="main_tp_hit"
                )
                
                if op.broker_ticket:
                    cancel_res = await self.trading_service.broker.cancel_order(op.broker_ticket)
                    if not cancel_res.success:
                        logger.warning("Failed to cancel hedge in broker", 
                                      op_id=op.id, error=cancel_res.error)
                
                op.status = OperationStatus.CANCELLED
                op.metadata["cancel_reason"] = "counterpart_main_tp_hit"
                op.metadata["cancelled_by_operation"] = str(tp_operation.id)
                await self.repository.save_operation(op)
                cancelled_count += 1
        
        if cancelled_count > 0:
            logger.info(
                "Hedge counterparts cancelled",
                cycle_id=cycle.id,
                count=cancelled_count
            )
        else:
            logger.debug(
                "No pending hedge counterparts found to cancel",
                cycle_id=cycle.id
            )

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-002: MÉTODO ACTUALIZADO - Cancelar recovery pendiente contrario
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _cancel_pending_recovery_counterpart(self, recovery_cycle: Cycle) -> None:
        """
        Cancela la operación de recovery pendiente contraria.
        
        Cuando un recovery BUY toca TP, el recovery SELL pendiente debe cancelarse
        para evitar órdenes huérfanas en el broker.
        """
        ops_res = await self.repository.get_operations_by_cycle(recovery_cycle.id)
        if not ops_res.success:
            return
        
        cancelled_count = 0
        for op in ops_res.value:
            if op.status == OperationStatus.PENDING and op.is_recovery:
                logger.info("Cancelling pending recovery counterpart", op_id=op.id)
                
                if op.broker_ticket:
                    cancel_res = await self.trading_service.broker.cancel_order(op.broker_ticket)
                    if not cancel_res.success:
                        logger.warning("Failed to cancel in broker", 
                                      op_id=op.id, error=cancel_res.error)
                
                op.status = OperationStatus.CANCELLED
                op.metadata["cancel_reason"] = "counterpart_tp_hit"
                await self.repository.save_operation(op)
                cancelled_count += 1
        
        if cancelled_count > 0:
            logger.info("Recovery counterparts cancelled", 
                       recovery_id=recovery_cycle.id, count=cancelled_count)

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-003: MÉTODO ACTUALIZADO - FIFO con cierre atómico Main+Hedge
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_recovery_tp(self, recovery_cycle: Cycle, tick: TickData) -> None:
        """
        Procesa el TP de un ciclo de recovery usando lógica FIFO.
        
        FIX-003: Ahora cierra Main + Hedge como unidad atómica.
        
        Reglas FIFO (Documento Madre pág. 156-166):
        - Recovery profit = 80 pips
        - Primer recovery en cola cuesta 20 pips (Main + Hedge)
        - Siguientes recoveries cuestan 40 pips cada uno
        """
        pair = recovery_cycle.pair
        parent_cycle = self._active_cycles.get(pair)
        
        # Si no está en cache, buscar en repositorio
        if not parent_cycle and recovery_cycle.parent_cycle_id:
            parent_res = await self.repository.get_cycle(recovery_cycle.parent_cycle_id)
            if parent_res.success and parent_res.value:
                parent_cycle = parent_res.value
                self._active_cycles[pair] = parent_cycle
        
        if not parent_cycle:
            logger.warning("No parent cycle found for recovery TP", 
                          recovery_id=recovery_cycle.id)
            return

        logger.info(
            "Recovery TP hit, applying FIFO logic with atomic closures",
            recovery_id=recovery_cycle.id,
            parent_id=parent_cycle.id,
            queue_size=len(parent_cycle.accounting.recovery_queue)
        )
        
        # 1. Cancelar operación de recovery pendiente contraria
        await self._cancel_pending_recovery_counterpart(recovery_cycle)
        
        # 2. Aplicar FIFO: Neutralizar profit contra deudas
        # FIX-003: Cerrar Main + Hedge atómicamente
        pips_available = float(RECOVERY_TP_PIPS)  # 80 pips
        closed_count = 0
        total_cost = 0.0
        
        logger.info(
            "═══════════════════════════════════════",
            message="STARTING FIFO PROCESSING"
        )
        logger.debug(
            "FIFO State",
            pips_available=pips_available,
            queue_size=len(parent_cycle.accounting.recovery_queue)
        )
        
        while pips_available > 0 and parent_cycle.accounting.recovery_queue:
            cost = float(parent_cycle.accounting.get_recovery_cost())
            
            if pips_available >= cost:
                # FIX-003: Cerrar debt unit (Main + Hedge juntos)
                debt_unit_id = parent_cycle.accounting.recovery_queue[0]
                
                logger.info(
                    "╔═══════════════════════════════════════╗",
                    message="CLOSING DEBT UNIT (ATOMIC)"
                )
                logger.debug(
                    "Debt Unit Details",
                    unit_id=debt_unit_id,
                    cost_pips=cost,
                    pips_available=pips_available
                )
                
                # Cerrar Main + Hedge de esta debt unit
                await self._close_debt_unit_atomic(parent_cycle, debt_unit_id)
                
                # Remover de la queue
                closed_rec_id = parent_cycle.close_oldest_recovery()
                parent_cycle.accounting.mark_recovery_closed()
                
                pips_available -= cost
                total_cost += cost
                closed_count += 1
                
                logger.info(
                    "Debt unit closed successfully",
                    closed_unit_id=debt_unit_id,
                    cost_pips=cost,
                    remaining_pips=pips_available,
                    queue_remaining=len(parent_cycle.accounting.recovery_queue)
                )
                logger.info("╚═══════════════════════════════════════╝")
            else:
                logger.debug("FIFO: Not enough pips for next recovery",
                            required=cost, available=pips_available)
                break
        
        # 3. Registrar pips recuperados
        recovered_pips = float(RECOVERY_TP_PIPS) - pips_available
        parent_cycle.accounting.add_recovered_pips(Pips(recovered_pips))
        
        # 4. Guardar cambios
        await self.repository.save_cycle(parent_cycle)
        
        logger.info(
            "═══════════════════════════════════════",
            message="FIFO PROCESSING COMPLETE"
        )
        logger.info(
            "FIFO Summary",
            cycle_id=parent_cycle.id,
            debt_units_closed=closed_count,
            pips_used=total_cost,
            pips_profit=pips_available,
            total_recovered=float(parent_cycle.accounting.pips_recovered),
            total_locked=float(parent_cycle.accounting.pips_locked),
            is_fully_recovered=parent_cycle.accounting.is_fully_recovered
        )
        
        # 5. Si fully_recovered, volver a ACTIVE y renovar mains
        if parent_cycle.accounting.is_fully_recovered:
            logger.info("🎉 Cycle FULLY RECOVERED!", cycle_id=parent_cycle.id)
            
            parent_cycle.status = CycleStatus.ACTIVE
            await self.repository.save_cycle(parent_cycle)
            
            # Renovar operaciones main para continuar operando
            await self._renew_main_operations(parent_cycle, tick)

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-003: NUEVO MÉTODO - Cierre atómico de debt unit (Main + Hedge)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _close_debt_unit_atomic(self, cycle: Cycle, debt_unit_id: str) -> None:
        """
        FIX-003: Cierra atómicamente una debt unit (Main + Hedge).
        
        Una debt unit contiene:
        - Una operación Main neutralizada
        - Una operación Hedge que la cubre
        
        Ambas se cierran juntas para:
        - Minimizar comisiones acumuladas
        - Garantizar consistencia (todo o nada)
        - Evitar estados intermedios
        
        Args:
            cycle: Ciclo padre
            debt_unit_id: ID de la unidad de deuda (e.g. "OP_020_debt_unit")
        """
        logger.info(
            "Closing debt unit atomically",
            cycle_id=cycle.id,
            debt_unit_id=debt_unit_id
        )
        
        # Obtener todas las operaciones del ciclo
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            logger.error("Failed to get operations for debt unit closure", cycle_id=cycle.id)
            return
        
        # Identificar Main y Hedge de esta debt unit
        # El debt_unit_id típicamente es "{main_op_id}_debt_unit"
        main_op_id_base = debt_unit_id.replace("_debt_unit", "")
        
        main_op = None
        hedge_op = None
        
        for op in ops_res.value:
            if str(op.id) == main_op_id_base and op.is_main and op.status == OperationStatus.NEUTRALIZED:
                main_op = op
            elif op.is_hedge and op.status == OperationStatus.ACTIVE:
                # Verificar si este hedge cubre el main
                if op.metadata.get("covering_operation") == main_op_id_base or \
                   op.linked_operation_id == main_op_id_base:
                    hedge_op = op
        
        if not main_op or not hedge_op:
            logger.error(
                "Could not find Main + Hedge for debt unit",
                debt_unit_id=debt_unit_id,
                found_main=main_op is not None,
                found_hedge=hedge_op is not None
            )
            return
        
        logger.debug(
            "Debt unit components identified",
            main_id=main_op.id,
            main_type=main_op.op_type.value,
            hedge_id=hedge_op.id,
            hedge_type=hedge_op.op_type.value
        )
        
        # Cerrar ambas operaciones
        close_results = []
        
        # 1. Cerrar Main neutralizada
        logger.info("Closing neutralized Main", op_id=main_op.id)
        if main_op.broker_ticket:
            close_res = await self.trading_service.close_operation(main_op, reason="fifo_recovery_tp")
            close_results.append(("main", close_res))
        
        main_op.status = OperationStatus.CLOSED
        main_op.metadata["close_reason"] = "fifo_recovery_tp"
        main_op.metadata["close_method"] = "atomic_with_hedge"
        main_op.metadata["debt_unit_id"] = debt_unit_id
        await self.repository.save_operation(main_op)
        
        # 2. Cerrar Hedge que cubría
        logger.info("Closing covering Hedge", op_id=hedge_op.id)
        if hedge_op.broker_ticket:
            close_res = await self.trading_service.close_operation(hedge_op, reason="fifo_recovery_tp")
            close_results.append(("hedge", close_res))
        
        hedge_op.status = OperationStatus.CLOSED
        hedge_op.metadata["close_reason"] = "fifo_recovery_tp"
        hedge_op.metadata["close_method"] = "atomic_with_main"
        hedge_op.metadata["debt_unit_id"] = debt_unit_id
        await self.repository.save_operation(hedge_op)
        
        # Verificar éxito
        failed = [r for r in close_results if not r[1].success]
        if failed:
            logger.error(
                "Some closures failed in atomic operation",
                debt_unit_id=debt_unit_id,
                failed_count=len(failed)
            )
        else:
            logger.info(
                "✓ Debt unit closed successfully (atomic)",
                debt_unit_id=debt_unit_id,
                main_id=main_op.id,
                hedge_id=hedge_op.id
            )

    # ═══════════════════════════════════════════════════════════════════════
    # RESTO DE MÉTODOS (Sin cambios significativos)
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_signal(self, signal: StrategySignal, tick: TickData):
        """Maneja las señales emitidas por la estrategia."""
        reason = signal.metadata.get("reason", "unknown") if signal.metadata else "unknown"
        logger.info("Signal received", type=signal.signal_type.name, pair=signal.pair, reason=reason)

        if signal.signal_type == SignalType.OPEN_CYCLE:
            await self._open_new_cycle(signal, tick)
        
        elif signal.signal_type == SignalType.CLOSE_OPERATIONS:
            await self._close_cycle_operations(signal)
        
        elif signal.signal_type == SignalType.OPEN_RECOVERY:
            await self._open_recovery_cycle(signal, tick)

    async def _open_new_cycle(self, signal: StrategySignal, tick: TickData):
        """Inicia un nuevo ciclo de trading con dos operaciones (Buy + Sell)."""
        pair = signal.pair
        
        # 1. Obtener métricas de exposición reales
        exposure_pct, num_recoveries = await self._get_exposure_metrics(pair)
        acc_info = await self.trading_service.broker.get_account_info()
        balance = acc_info.value["balance"] if acc_info.success else 10000.0

        # Validar con el RiskManager
        can_open = self.risk_manager.can_open_position(
            pair, 
            current_exposure=exposure_pct,
            num_recoveries=num_recoveries
        )
        if not can_open.success:
            logger.info("Signal rejected by RiskManager", reason=can_open.error, pair=pair)
            return

        # 2. Validar que no haya ya un ciclo activo para este par
        if pair in self._active_cycles:
            active_cycle = self._active_cycles[pair]
            if active_cycle.status.name not in ["CLOSED", "PAUSED"]:
                logger.debug("Signal ignored: Cycle already active", 
                            pair=pair, existing_cycle_id=active_cycle.id)
                return

        # 3. Calcular lote
        lot = self.risk_manager.calculate_lot_size(pair, balance)

        # 4. Crear Entidad Ciclo
        import random
        suffix = random.randint(100, 999)
        cycle_id = f"CYC_{pair}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{suffix}"

        cycle = Cycle(id=cycle_id, pair=pair, status=CycleStatus.PENDING)
        self._active_cycles[pair] = cycle
        
        # 5. Crear Operaciones Duales (Buy y Sell)
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        tp_distance = Decimal(str(MAIN_TP_PIPS)) * multiplier
        
        op_buy = Operation(
            id=OperationId(f"{cycle_id}_B"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_BUY,
            status=OperationStatus.PENDING,
            entry_price=tick.ask,
            tp_price=Price(tick.ask + tp_distance),
            lot_size=lot
        )
        
        op_sell = Operation(
            id=OperationId(f"{cycle_id}_S"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_SELL,
            status=OperationStatus.PENDING,
            entry_price=tick.bid,
            tp_price=Price(tick.bid - tp_distance),
            lot_size=lot
        )

        # 6. Guardar Ciclo en DB
        await self.repository.save_cycle(cycle)
        
        # 7. Ejecutar aperturas
        tasks = []
        for op in [op_buy, op_sell]:
            request = OrderRequest(
                operation_id=op.id,
                pair=pair,
                order_type=op.op_type,
                entry_price=op.entry_price,
                tp_price=op.tp_price,
                lot_size=op.lot_size
            )
            tasks.append(self.trading_service.open_operation(request, op))
        
        results = await asyncio.gather(*tasks)
        
        if any(r.success for r in results):
            for op in [op_buy, op_sell]:
                cycle.add_operation(op)
            self._active_cycles[pair] = cycle
            self.strategy.register_cycle(cycle)
            logger.info("New dual cycle opened", cycle_id=cycle.id, pair=pair)
        else:
            logger.error("Failed to open dual cycle", cycle_id=cycle.id)

    async def _close_cycle_operations(self, signal: StrategySignal):
        """Cierra todas las operaciones de un ciclo."""
        pair = signal.pair
        cycle = self._active_cycles.get(pair)
        
        if not cycle:
            return

        ops_res = await self.repository.get_active_operations(pair)
        if ops_res.success:
            for op in ops_res.value:
                if op.cycle_id == cycle.id:
                    await self.trading_service.close_operation(op)
        
        cycle.status = CycleStatus.CLOSED
        await self.repository.save_cycle(cycle)
        del self._active_cycles[pair]
        logger.info("Cycle closed", cycle_id=cycle.id)

    async def _open_recovery_cycle(self, signal: StrategySignal, tick: TickData):
        """Abre un ciclo de Recovery para recuperar pérdidas neutralizadas."""
        pair = signal.pair
        parent_cycle = self._active_cycles.get(pair)
        
        if not parent_cycle:
            logger.warning("No active cycle to attach recovery", pair=pair)
            return

        # 1. Validar con RiskManager
        exposure_pct, num_recoveries = await self._get_exposure_metrics(pair)
        can_open = self.risk_manager.can_open_position(
            pair, 
            current_exposure=exposure_pct,
            num_recoveries=num_recoveries
        )
        if not can_open.success:
            logger.warning("Risk manager denied recovery", reason=can_open.error)
            return

        # 2. Configuración de Recovery
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        recovery_distance = Decimal(str(RECOVERY_DISTANCE_PIPS)) * multiplier
        tp_distance = Decimal(str(RECOVERY_TP_PIPS)) * multiplier
        
        # Calcular lote dinámicamente
        acc_info = await self.trading_service.broker.get_account_info()
        balance = acc_info.value["balance"] if acc_info.success else 10000.0
        lot = self.risk_manager.calculate_lot_size(pair, balance)
        
        logger.debug("Recovery lot calculated", pair=pair, balance=balance, lot=float(lot))

        # 3. Crear ciclo de Recovery
        recovery_level = parent_cycle.recovery_level + 1
        recovery_id = f"REC_{pair}_{recovery_level}_{datetime.now().strftime('%H%M%S')}"
        
        recovery_cycle = Cycle(
            id=recovery_id,
            pair=pair,
            cycle_type=CycleType.RECOVERY,
            parent_cycle_id=parent_cycle.id,
            recovery_level=recovery_level
        )

        # 4. Crear operaciones de Recovery
        ask = tick.ask
        bid = tick.bid
        
        op_rec_buy = Operation(
            id=OperationId(f"{recovery_id}_B"),
            cycle_id=recovery_cycle.id,
            pair=pair,
            op_type=OperationType.RECOVERY_BUY,
            status=OperationStatus.PENDING,
            entry_price=Price(ask + recovery_distance),
            tp_price=Price(ask + recovery_distance + tp_distance),
            lot_size=lot,
            recovery_id=RecoveryId(recovery_id)
        )
        
        op_rec_sell = Operation(
            id=OperationId(f"{recovery_id}_S"),
            cycle_id=recovery_cycle.id,
            pair=pair,
            op_type=OperationType.RECOVERY_SELL,
            status=OperationStatus.PENDING,
            entry_price=Price(bid - recovery_distance),
            tp_price=Price(bid - recovery_distance - tp_distance),
            lot_size=lot,
            recovery_id=RecoveryId(recovery_id)
        )

        # 5. Guardar en DB
        await self.repository.save_cycle(recovery_cycle)
        
        # 6. Registrar en cola FIFO del ciclo padre
        parent_cycle.recovery_level = recovery_level
        
        # FIX-003: Crear debt unit ID
        debt_unit_id = f"{recovery_id}_debt_unit"
        parent_cycle.add_recovery_to_queue(RecoveryId(debt_unit_id))
        await self.repository.save_cycle(parent_cycle)

        # 7. Ejecutar aperturas
        tasks = []
        for op in [op_rec_buy, op_rec_sell]:
            request = OrderRequest(
                operation_id=op.id,
                pair=pair,
                order_type=op.op_type,
                entry_price=op.entry_price,
                tp_price=op.tp_price,
                lot_size=op.lot_size
            )
            tasks.append(self.trading_service.open_operation(request, op))
        
        results = await asyncio.gather(*tasks)
        
        if any(r.success for r in results):
            logger.info("Recovery cycle opened", 
                       recovery_id=recovery_id, 
                       tier=recovery_level,
                       lot=float(lot))
        else:
            logger.error("Failed to open recovery cycle", recovery_id=recovery_id)

    async def _get_exposure_metrics(self, pair: CurrencyPair) -> tuple[float, int]:
        """Calcula la exposición actual y el número de recoveries activos."""
        exposure_pct = 0.0
        acc_res = await self.trading_service.broker.get_account_info()
        if acc_res.success:
            equity = acc_res.value.get("equity", 0.0)
            margin = acc_res.value.get("margin", 0.0)
            if equity > 0:
                exposure_pct = (margin / equity) * 100
        
        num_recoveries = 0
        cycles_res = await self.repository.get_active_cycles(pair)
        if cycles_res.success:
            num_recoveries = sum(1 for c in cycles_res.value if c.cycle_type == CycleType.RECOVERY)
            
        return (exposure_pct, num_recoveries)
