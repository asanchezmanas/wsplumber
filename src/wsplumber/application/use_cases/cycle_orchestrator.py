# src/wsplumber/application/use_cases/cycle_orchestrator.py
"""
Orquestador de Ciclos - VERSIÓN CORREGIDA CON TODOS LOS FIXES.

Fixes aplicados:
- FIX-001: Renovación dual de mains después de TP ✅ [DEPRECATED - Ver FIX-CRITICAL]
- FIX-002: Cancelación de hedges pendientes contrarios ✅
- FIX-003: Cierre atómico FIFO de Main+Hedge ✅
- FIX-CRITICAL: Main TP abre NUEVO CICLO (C2) en vez de renovar dentro de C1 ✅
  * C1 queda en IN_RECOVERY esperando que Recovery compense deuda
  * C2 (nuevo ciclo) permite seguir generando flujo de mains
  * Cada ciclo tiene exactamente 2 mains (no más)
"""

from __future__ import annotations

import asyncio
import random
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
from wsplumber.domain.entities.debt import DebtUnit  # PHASE 4: Shadow tracking
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._params import (
    MAIN_TP_PIPS, MAIN_DISTANCE_PIPS, RECOVERY_TP_PIPS, RECOVERY_DISTANCE_PIPS, RECOVERY_LEVEL_STEP
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
            logger.error("Error processing tick", _exception=e, pair=pair)

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

        # FIX: Monitoreamos TODOS los ciclos activos para este par (Principal + Recoveries)
        cycles_res = await self.repository.get_active_cycles(pair)
        
        # FIX-OPEN-FIRST-CYCLE: Si no hay ciclos activos, abrir el primero
        if not cycles_res.success or not cycles_res.value:
            # Solo abrir si no hay ya uno en cache
            if pair not in self._active_cycles:
                # Obtener tick actual del broker
                tick_res = await self.trading_service.broker.get_current_price(pair)
                if tick_res.success and tick_res.value:
                    signal = StrategySignal(
                        signal_type=SignalType.OPEN_CYCLE,
                        pair=pair,
                        metadata={"reason": "no_active_cycle_in_repo"}
                    )
                    await self._open_new_cycle(signal, tick_res.value)
            return

        for cycle in cycles_res.value:
            # FIX-CACHE-OVERWRITE: Solo sincronizar cache con ciclos ACTIVE/HEDGED
            # No sobrescribir con ciclos IN_RECOVERY/CLOSED que pueden disparar TP
            if cycle.cycle_type == CycleType.MAIN and cycle.status in (CycleStatus.ACTIVE, CycleStatus.HEDGED, CycleStatus.PENDING):
                self._active_cycles[pair] = cycle

            ops_res = await self.repository.get_operations_by_cycle(cycle.id)
            if not ops_res.success:
                continue
            
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
                        
                        # PHASE 4b: Shadow tracking for initial debt
                        # Calculate real debt from actual main operation prices
                        main_buy = next((o for o in active_main_ops if o.is_buy), None)
                        main_sell = next((o for o in active_main_ops if o.is_sell), None)
                        if main_buy and main_sell:
                            # Real distance between mains = actual loss when neutralized
                            buy_entry = main_buy.actual_entry_price or main_buy.entry_price
                            sell_entry = main_sell.actual_entry_price or main_sell.entry_price
                            multiplier = 100 if "JPY" in str(pair) else 10000
                            real_distance = abs(float(buy_entry) - float(sell_entry)) * multiplier
                            
                            debt = DebtUnit.from_neutralization(
                                cycle_id=str(cycle.id),
                                losing_main_id=str(main_sell.id),  # Placeholder - actual loser determined at TP
                                losing_main_entry=Decimal(str(sell_entry)),
                                losing_main_close=Decimal(str(buy_entry)),  # Neutralized at other main's entry
                                winning_main_id=str(main_buy.id),
                                hedge_id="pending",  # Will be set when hedge created
                                pair=str(pair)
                            )
                            cycle.accounting.shadow_add_debt(debt)
                            logger.debug("Shadow accounting: initial debt added at HEDGED",
                                        real_debt=float(debt.pips_owed),
                                        theoretical=20.0,
                                        difference=float(debt.pips_owed) - 20.0)
                        
                        # Crear operaciones de hedge y neutralizar mains
                        # CONCEPTO: Hedges de CONTINUACIÓN (del mismo lado)
                        # - HEDGE_BUY se crea al TP del MAIN_BUY → cuando BUY toca TP, HEDGE_BUY continúa
                        # - HEDGE_SELL se crea al TP del MAIN_SELL → cuando SELL toca TP, HEDGE_SELL continúa
                        # Esto "bloquea" la pérdida del main opuesto que queda abierto
                        for main_op in active_main_ops:

                            # Hedge del MISMO lado que el main (continuación)
                            if main_op.op_type == OperationType.MAIN_BUY:
                                # Para MAIN_BUY: crear HEDGE_BUY al TP del BUY
                                hedge_type = OperationType.HEDGE_BUY
                                hedge_entry = main_op.tp_price  # TP del MAIN_BUY
                            else:
                                # Para MAIN_SELL: crear HEDGE_SELL al TP del SELL
                                hedge_type = OperationType.HEDGE_SELL
                                hedge_entry = main_op.tp_price  # TP del MAIN_SELL
                            
                            hedge_id = f"{cycle.id}_H_{main_op.op_type.value}"

                            hedge_op = Operation(
                                id=OperationId(hedge_id),
                                cycle_id=cycle.id,
                                pair=pair,
                                op_type=hedge_type,
                                status=OperationStatus.PENDING,
                                entry_price=hedge_entry,  # TP del main del mismo lado
                                lot_size=main_op.lot_size,
                                linked_operation_id=OperationId(str(main_op.id))  # FIX-FIFO: Vincular hedge con su main
                            )
                            # FIX-FIFO: Establecer metadata de vinculación para búsqueda FIFO
                            hedge_op.metadata["covering_operation"] = str(main_op.id)
                            hedge_op.metadata["debt_unit_id"] = "INITIAL_UNIT"
                            cycle.add_operation(hedge_op)
                            
                            # NOTE: Do NOT neutralize mains here - they stay active
                            # until one of them hits TP. At that point, the OTHER main
                            # gets neutralized in the TP_HIT handling section below.
                            
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

                    # VERIFICACIÓN DE FALLO DE RECOVERY
                    # Un recovery falla cuando AMBAS órdenes se activan (se bloquea a 40 pips)
                    if op.is_recovery and op.status == OperationStatus.ACTIVE:
                        recovery_ops = [o for o in ops_res.value if o.is_recovery]
                        active_recovery_ops = [o for o in recovery_ops if o.status == OperationStatus.ACTIVE]
                        
                        if len(active_recovery_ops) >= 2:
                            # Evitar procesar el fallo múltiples veces para el mismo ciclo
                            if not cycle.metadata.get("failure_processed"):
                                logger.warning("Recovery failure detected (both active)", cycle_id=cycle.id)
                                cycle.metadata["failure_processed"] = True
                                await self.repository.save_cycle(cycle)
                                
                                # Llamar al manejador de fallos (pasa el 'op' actual como el que bloqueó)
                                await self._handle_recovery_failure(cycle, op, tick)
                
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
                        
                        # FIX-CRITICAL: Neutralize ACTIVE opposite main to prevent TP hit
                        # When in HEDGED state and one main hits TP, the other main
                        # should be neutralized so it can never hit its own TP
                        if cycle.status == CycleStatus.HEDGED:
                            for other_op in ops_res.value:
                                if (other_op.is_main and 
                                    other_op.id != op.id and 
                                    other_op.status == OperationStatus.ACTIVE):
                                    logger.info("Neutralizing opposite main after TP hit", op_id=other_op.id)
                                    other_op.neutralize(op.id)
                                    await self.repository.save_operation(other_op)
                                    # Update broker position to NEUTRALIZED to prevent TP
                                    if other_op.broker_ticket:
                                        await self.trading_service.broker.update_position_status(
                                            other_op.broker_ticket,
                                            OperationStatus.NEUTRALIZED
                                        )
                            
                            # Transition to IN_RECOVERY and open recovery cycle
                            cycle.start_recovery()
                            cycle.metadata["just_transitioned"] = True  # FIX-IN-RECOVERY-SKIP
                            await self.repository.save_cycle(cycle)
                            logger.info("Cycle transitioned to IN_RECOVERY", cycle_id=cycle.id)
                            
                            # Open recovery cycle to compensate FIFO debt
                            recovery_signal = StrategySignal(
                                signal_type=SignalType.OPEN_CYCLE,
                                pair=cycle.pair,
                                metadata={"reason": "recovery_after_hedge_tp", "parent_cycle": cycle.id}
                            )
                            await self._open_recovery_cycle(recovery_signal, tick)
                        
                        # FIX-002: Cancelar hedges pendientes contrarios
                        await self._cancel_pending_hedge_counterpart(cycle, op)

                        # Registrar TP en contabilidad
                        cycle.record_main_tp(Pips(float(op.profit_pips or MAIN_TP_PIPS)))
                        
                        # FIX-CYCLE-EXPLOSION: Transicionar C1 ANTES de abrir C2
                        # Esto evita que C1 quede huérfano en estado ACTIVE/HEDGED
                        if cycle.status == CycleStatus.ACTIVE:
                            # Solo 1 main estaba activo y tocó TP → ciclo se cierra (sin deuda)
                            # Cancelar el main pendiente contrario
                            for other_op in ops_res.value:
                                if other_op.is_main and other_op.id != op.id and other_op.status == OperationStatus.PENDING:
                                    other_op.status = OperationStatus.CANCELLED
                                    other_op.metadata["cancel_reason"] = "counterpart_tp_hit"
                                    await self.repository.save_operation(other_op)
                            
                            cycle.status = CycleStatus.CLOSED
                            cycle.closed_at = datetime.now()
                            cycle.metadata["close_reason"] = "single_main_tp_no_debt"
                            cycle.metadata["just_transitioned"] = True  # FIX-IN-RECOVERY-SKIP
                            logger.info("Cycle closed (single main TP, no debt)", cycle_id=cycle.id)
                        
                        # (HEDGED case already handled above at line 359-362)
                        
                        await self.repository.save_cycle(cycle)
                        
                        # FIX-IN-RECOVERY-SKIP: Solo abrir nuevo ciclo si este ciclo ACABA de
                        # transicionar a IN_RECOVERY o CLOSED. Si ya estaba en IN_RECOVERY antes,
                        # significa que ya se procesó anteriormente y no debe abrir más ciclos.
                        # Los ciclos IN_RECOVERY pueden tener TPs de mains pendientes del momento de transición.
                        if cycle.status == CycleStatus.IN_RECOVERY and not cycle.metadata.get("just_transitioned"):
                            logger.info("Skipping renewal: cycle was already IN_RECOVERY",
                                       cycle_id=cycle.id)
                        elif cycle.status == CycleStatus.CLOSED and not cycle.metadata.get("just_transitioned"):
                            logger.info("Skipping renewal: cycle was already CLOSED",
                                       cycle_id=cycle.id)
                        else:
                            # Marcar que la transición se procesó
                            cycle.metadata["just_transitioned"] = False
                            await self.repository.save_cycle(cycle)
                            
                            # FIX-SAME-TICK-GUARD-V2: Solo abrir nuevo ciclo si:
                            # 1. No hay ningún ciclo en cache, O
                            # 2. El ciclo en cache es ESTE mismo ciclo (que acabamos de transicionar)
                            if pair in self._active_cycles:
                                cached_cycle = self._active_cycles[pair]
                                if cached_cycle.id != cycle.id:
                                    logger.info("Skipping renewal: another cycle already opened this tick",
                                                existing_cycle=cached_cycle.id,
                                                current_cycle=cycle.id)
                                else:
                                    del self._active_cycles[pair]
                                    signal_open_cycle = StrategySignal(
                                        signal_type=SignalType.OPEN_CYCLE,
                                        pair=cycle.pair,
                                        metadata={"reason": "renewal_after_main_tp", "parent_cycle": cycle.id}
                                    )
                                    await self._open_new_cycle(signal_open_cycle, tick)
                            else:
                                signal_open_cycle = StrategySignal(
                                    signal_type=SignalType.OPEN_CYCLE,
                                    pair=cycle.pair,
                                    metadata={"reason": "renewal_after_main_tp", "parent_cycle": cycle.id}
                                )
                                await self._open_new_cycle(signal_open_cycle, tick)

                        logger.info(
                            "[OK] Main TP processed",
                            old_cycle=cycle.id,
                            old_cycle_status=cycle.status.value
                        )

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
    # DEPRECATED: Método obsoleto - Ya NO se usa
    # FIX-CRITICAL aplicado: Ahora se usa _open_new_cycle en lugar de renovar dentro del mismo ciclo
    # ═══════════════════════════════════════════════════════════════════════

    async def _renew_main_operations_DEPRECATED(self, cycle: Cycle, tick: TickData) -> None:
        """
        Crea nuevas operaciones main (BUY + SELL) después de un TP.
        
        FIX-001: Este método ahora incluye una guarda para evitar renovaciones duplicadas
        en el mismo tick si ya hay operaciones pendientes.
        """
        pair = cycle.pair
        
        logger.info(
            "🔄 _renew_main_operations CALLED",
            cycle_id=cycle.id,
            cycle_status=cycle.status.value if cycle.status else "None",
            tick_price=str(tick.bid)
        )
        
        # GUARD: Evitar renovaciones duplicadas si ya hay pendientes
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if ops_res.success:
            all_ops = ops_res.value
            pending_mains = [op for op in all_ops if op.is_main and op.status == OperationStatus.PENDING]
            active_mains = [op for op in all_ops if op.is_main and op.status == OperationStatus.ACTIVE]
            
            logger.info(
                "🔍 GUARD CHECK: Existing operations",
                cycle_id=cycle.id,
                total_ops=len(all_ops),
                pending_mains=len(pending_mains),
                active_mains=len(active_mains),
                pending_ids=[op.id for op in pending_mains][:3],
                active_ids=[op.id for op in active_mains][:3]
            )
            
            if pending_mains or active_mains:
                logger.info(
                    "⏹️ RENEWAL SKIPPED: Cycle already has main operations",
                    cycle_id=cycle.id,
                    pending_count=len(pending_mains),
                    active_count=len(active_mains)
                )
                return
        else:
            logger.warning("Failed to get operations for guard check", cycle_id=cycle.id)
        

        
        # Calcular distancias usando parámetros centralizados
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        entry_distance = Decimal(str(MAIN_DISTANCE_PIPS)) * multiplier  # 5 pips
        tp_distance = Decimal(str(MAIN_TP_PIPS)) * multiplier  # 10 pips
        
        # Generar IDs únicos con timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]
        
        # Obtener lote del ciclo (mantener consistencia)
        existing_ops = [op for op in cycle.operations if op.lot_size]
        lot = existing_ops[0].lot_size if existing_ops else LotSize(0.01)
        
        # Calcular precios de entrada a 5 pips de distancia (BUY_STOP / SELL_STOP)
        buy_entry_price = Price(tick.ask + entry_distance)
        sell_entry_price = Price(tick.bid - entry_distance)
        
        # Operación BUY_STOP: entry a ask+5pips, TP a entry+10pips
        op_buy = Operation(
            id=OperationId(f"{cycle.id}_B_{timestamp}"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_BUY,
            status=OperationStatus.PENDING,
            entry_price=buy_entry_price,
            tp_price=Price(buy_entry_price + tp_distance),
            lot_size=lot
        )
        
        # Operación SELL_STOP: entry a bid-5pips, TP a entry-10pips
        op_sell = Operation(
            id=OperationId(f"{cycle.id}_S_{timestamp}"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_SELL,
            status=OperationStatus.PENDING,
            entry_price=sell_entry_price,
            tp_price=Price(sell_entry_price - tp_distance),
            lot_size=lot
        )
        
        logger.info(
            "*** RENOVANDO OPERACIONES MAIN (BUY + SELL) ***",
            cycle_id=cycle.id,
            buy_entry=str(buy_entry_price),
            sell_entry=str(sell_entry_price),
            entry_distance_pips=MAIN_DISTANCE_PIPS,
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
        # Primero buscar por propiedad de clase, luego fallback a metadata
        parent_id = getattr(recovery_cycle, 'parent_cycle_id', None) or recovery_cycle.metadata.get("parent_cycle_id")
        parent_cycle = None
        
        if parent_id:
            parent_res = await self.repository.get_cycle(parent_id)
            if parent_res.success and parent_res.value:
                parent_cycle = parent_res.value
        
        # Fallback a cache activo si no hay metadata (no debería pasar)
        if not parent_cycle:
            parent_cycle = self._active_cycles.get(pair)
        
        if not parent_cycle:
            logger.warning("No parent group found for correction target reached", 
                          correction_id=recovery_cycle.id)
            return

        logger.info(
            "Recovery TP hit, applying FIFO logic with atomic closures",
            recovery_id=recovery_cycle.id,
            parent_id=parent_cycle.id,
            queue_size=len(parent_cycle.accounting.recovery_queue)
        )
        
        # 1. Cancelar operación de recovery pendiente contraria
        await self._cancel_pending_recovery_counterpart(recovery_cycle)
        
        # 2. Aplicar FIFO usando la nueva lógica de unidades de deuda
        # Almacenamos el estado previo de la primera unidad para saber si se liquidó
        had_initial_debt = len(parent_cycle.accounting.debt_units) > 0 and parent_cycle.accounting.debt_units[0] == 20.0
        
        surplus = parent_cycle.accounting.process_recovery_tp(float(RECOVERY_TP_PIPS))
        
        # PHASE 4: Shadow tracking with REAL profit value
        # Get the actual profit pips from the recovery operation that hit TP
        recovery_ops = [op for op in (await self.repository.get_operations_by_cycle(recovery_cycle.id)).value 
                       if op.status == OperationStatus.TP_HIT]
        if recovery_ops:
            real_profit = float(recovery_ops[0].realized_pips)
            shadow_result = parent_cycle.accounting.shadow_process_recovery(real_profit)
            logger.debug("Shadow accounting: recovery processed", 
                        real_profit=real_profit,
                        theoretical=float(RECOVERY_TP_PIPS),
                        difference=real_profit - float(RECOVERY_TP_PIPS),
                        shadow_debt_remaining=shadow_result.get("shadow_debt_remaining", 0))
        
        # 3. Aplicar cierres atómicos para las unidades que se hayan liquidado
        # Si la unidad de 20 pips ya no está en la cola, procedemos al cierre atómico de Main+Hedge
        if had_initial_debt and (not parent_cycle.accounting.debt_units or parent_cycle.accounting.debt_units[0] != 20.0):
            logger.info("Initial debt unit (20 pips) liquidated. Closing parent Main+Hedge atomically.")
            await self._close_debt_unit_atomic(parent_cycle, "INITIAL_UNIT")
        
        logger.info(
            "FIFO Processing Results",
            cycle_id=parent_cycle.id,
            total_recovered=float(parent_cycle.accounting.pips_recovered),
            pips_remaining_debt=float(parent_cycle.accounting.pips_remaining),
            surplus_pips=surplus
        )

        # FIX-MAIN-OPERATIONS-CLOSURE: Cerrar operaciones main cuando la deuda se paga completamente
        # Este es el fix CRÍTICO para las posiciones zombie de main cycles
        if parent_cycle.accounting.pips_remaining == 0:
            logger.info("FIX-MAIN-OPERATIONS: Debt fully paid, closing parent cycle main operations",
                       parent_id=parent_cycle.id,
                       debt_remaining=parent_cycle.accounting.pips_remaining)

            parent_ops_result = await self.repository.get_operations_by_cycle(parent_cycle.id)
            if parent_ops_result.success:
                parent_ops = parent_ops_result.value
                logger.info("Parent operations fetched for closure",
                           parent_id=parent_cycle.id,
                           total_ops=len(parent_ops))

                main_closed_count = 0
                main_skipped_count = 0

                for op in parent_ops:
                    # Solo cerrar operaciones MAIN (no recovery) que estén activas
                    if not op.is_recovery and op.broker_ticket:
                        if op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                            logger.info("Closing main operation after debt paid",
                                       op_id=op.id,
                                       ticket=op.broker_ticket,
                                       status=op.status.value,
                                       parent_id=parent_cycle.id)
                            close_result = await self.trading_service.close_operation(op)
                            if not close_result.success:
                                logger.error("Failed to close main operation",
                                           op_id=op.id,
                                           ticket=op.broker_ticket,
                                           error=close_result.error)
                            else:
                                main_closed_count += 1
                                logger.info("Main operation closed successfully after debt paid",
                                           op_id=op.id,
                                           ticket=op.broker_ticket)
                        else:
                            main_skipped_count += 1
                            logger.debug("Skipping main operation (already closed)",
                                        op_id=op.id,
                                        status=op.status.value)

                logger.info("Main operations closure summary after debt paid",
                           parent_id=parent_cycle.id,
                           closed=main_closed_count,
                           skipped=main_skipped_count)
            else:
                logger.error("Failed to get parent operations for closure",
                            parent_id=parent_cycle.id,
                            error=parent_ops_result.error)

        # 4. Condición de Cierre Atómico
        # El ciclo se cierra si NO hay deuda pendiente Y el excedente es >= 20 pips
        if parent_cycle.accounting.is_fully_recovered and surplus >= 20.0:
            logger.info("🎉 Cycle FULLY RESOLVED with surplus >= 20. Closing cycle.", 
                      cycle_id=parent_cycle.id, surplus=surplus)
            
            # Cerrar todas las operaciones restantes (neutralizadas)
            await self._close_cycle_operations_final(parent_cycle)
            
            parent_cycle.status = CycleStatus.CLOSED
            parent_cycle.closed_at = datetime.now()
            parent_cycle.metadata["close_reason"] = f"recovery_surplus_{surplus}"
            await self.repository.save_cycle(parent_cycle)
            
            # Remover del cache activo
            if pair in self._active_cycles:
                del self._active_cycles[pair]
        else:
            # NO se cumplen las condiciones de cierre.
            # Razón 1: Aún hay deuda pendiente.
            # Razón 2: Deuda=0 pero el excedente es < 20 pips.
            # En ambos casos: ABRIR NUEVO RECOVERY al nivel del TP actual.
            logger.info("Cycle NOT closed. Opening next recovery stage.", 
                      is_fully_recovered=parent_cycle.accounting.is_fully_recovered,
                      surplus=surplus)
            
            # La posición del nuevo recovery es ±20 pips del TP que se acaba de tocar
            # Buscamos la operación que tocó TP para obtener su precio de cierre
            tp_op = next((op for op in recovery_cycle.operations if op.status == OperationStatus.TP_HIT), None)
            reference_price = Price(tp_op.tp_price) if tp_op else tick.bid # Fallback
            
            signal = StrategySignal(
                signal_type=SignalType.OPEN_RECOVERY,
                pair=pair,
                metadata={"reason": "recovery_next_stage", "parent_cycle": parent_cycle.id}
            )
            await self._open_recovery_cycle(signal, tick, reference_price=reference_price)

            # Guardar estado del padre
            await self.repository.save_cycle(parent_cycle)

        # FIX-RECOVERY-CLOSURE: Cerrar el ciclo de recovery después de procesar su TP
        # Una vez que el recovery tocó TP y pagó la deuda al padre, debe cerrarse

        # CRÍTICO: Cerrar todas las operaciones del recovery en el broker
        logger.info("FIX-RECOVERY-CLOSURE: Attempting to close recovery operations",
                   recovery_id=recovery_cycle.id,
                   parent_id=parent_cycle.id)

        recovery_ops_result = await self.repository.get_operations_by_cycle(recovery_cycle.id)

        if not recovery_ops_result.success:
            logger.error("Failed to get recovery operations",
                        recovery_id=recovery_cycle.id,
                        error=recovery_ops_result.error)
        else:
            recovery_ops = recovery_ops_result.value
            logger.info("Recovery operations fetched",
                       recovery_id=recovery_cycle.id,
                       total_ops=len(recovery_ops),
                       op_statuses=[f"{op.id}:{op.status.value}" for op in recovery_ops])

            closed_count = 0
            skipped_count = 0

            for op in recovery_ops:
                # Solo cerrar operaciones que tengan ticket y no estén ya cerradas
                if op.broker_ticket and op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                    logger.info("Closing recovery operation in broker",
                               op_id=op.id,
                               ticket=op.broker_ticket,
                               status=op.status.value,
                               recovery_id=recovery_cycle.id)
                    close_result = await self.trading_service.close_operation(op)
                    if not close_result.success:
                        logger.error("Failed to close recovery operation",
                                   op_id=op.id,
                                   ticket=op.broker_ticket,
                                   error=close_result.error)
                    else:
                        closed_count += 1
                        logger.info("Recovery operation closed successfully",
                                   op_id=op.id,
                                   ticket=op.broker_ticket)
                else:
                    skipped_count += 1
                    logger.debug("Skipping recovery operation (already closed or no ticket)",
                                op_id=op.id,
                                status=op.status.value if op.status else "None",
                                has_ticket=bool(op.broker_ticket))

            logger.info("Recovery operations closure summary",
                       recovery_id=recovery_cycle.id,
                       total=len(recovery_ops),
                       closed=closed_count,
                       skipped=skipped_count)

        recovery_cycle.status = CycleStatus.CLOSED
        recovery_cycle.closed_at = datetime.now()
        recovery_cycle.metadata["close_reason"] = "tp_hit"
        await self.repository.save_cycle(recovery_cycle)

        logger.info(
            "Recovery cycle closed after TP hit",
            recovery_id=recovery_cycle.id,
            parent_id=parent_cycle.id
        )




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
            # Caso especial: INITIAL_UNIT o encontrar por ID
            is_target_main = (debt_unit_id == "INITIAL_UNIT" and op.is_main and op.status == OperationStatus.NEUTRALIZED) or \
                            (str(op.id) == main_op_id_base and op.is_main and op.status == OperationStatus.NEUTRALIZED)
            
            if is_target_main:
                main_op = op
                # FIX-FIFO: El hedge que cierra con un main neutralizado es del TIPO OPUESTO
                # Si main neutralizado es BUY → buscar HEDGE_SELL activo
                # Si main neutralizado is SELL → buscar HEDGE_BUY activo
                from wsplumber.domain.types import OperationType

                if main_op.op_type == OperationType.MAIN_BUY:
                    expected_hedge_type = OperationType.HEDGE_SELL
                elif main_op.op_type == OperationType.MAIN_SELL:
                    expected_hedge_type = OperationType.HEDGE_BUY
                else:
                    logger.error("Main op has unexpected type", op_type=main_op.op_type)
                    break

                # Buscar el hedge del tipo esperado (ACTIVE o TP_HIT)
                for hop in ops_res.value:
                    if hop.is_hedge and hop.op_type == expected_hedge_type and \
                       hop.status in (OperationStatus.ACTIVE, OperationStatus.TP_HIT, OperationStatus.CLOSED):
                        hedge_op = hop
                        break
                break
        
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
        logger.info("Closing neutralized Main", op_id=main_op.id, status=main_op.status)

        # FIX-FIFO-02: Solo intentar cerrar si NO está ya cerrada
        if main_op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
            if main_op.broker_ticket:
                close_res = await self.trading_service.close_operation(main_op, reason="fifo_recovery_tp")
                close_results.append(("main", close_res))

                # FIX-FIFO-02: Solo marcar como CLOSED si el cierre fue exitoso
                if not close_res.success:
                    logger.warning("Main close failed, skipping status update", op_id=main_op.id)
                else:
                    main_op.status = OperationStatus.CLOSED
                    main_op.metadata["close_reason"] = "fifo_recovery_tp"
                    main_op.metadata["close_method"] = "atomic_with_hedge"
                    main_op.metadata["debt_unit_id"] = debt_unit_id
                    await self.repository.save_operation(main_op)
        else:
            logger.info("Main already closed, skipping", op_id=main_op.id, status=main_op.status)

        # 2. Cerrar Hedge que cubría
        logger.info("Closing covering Hedge", op_id=hedge_op.id, status=hedge_op.status)

        # FIX-FIFO-02: Solo intentar cerrar si NO está ya cerrada
        if hedge_op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
            if hedge_op.broker_ticket:
                close_res = await self.trading_service.close_operation(hedge_op, reason="fifo_recovery_tp")
                close_results.append(("hedge", close_res))

                # FIX-FIFO-02: Solo marcar como CLOSED si el cierre fue exitoso
                if not close_res.success:
                    logger.warning("Hedge close failed, skipping status update", op_id=hedge_op.id)
                else:
                    hedge_op.status = OperationStatus.CLOSED
                    hedge_op.metadata["close_reason"] = "fifo_recovery_tp"
                    hedge_op.metadata["close_method"] = "atomic_with_main"
                    hedge_op.metadata["debt_unit_id"] = debt_unit_id
                    await self.repository.save_operation(hedge_op)
        else:
            logger.info("Hedge already closed, skipping", op_id=hedge_op.id, status=hedge_op.status)
        
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
        # NOTA: Si el ciclo está IN_RECOVERY, significa que ya cerró su main con TP
        # y debe permitir abrir nuevos ciclos mientras los recoveries se resuelven
        # NOTA 2: Si es una renovación (renewal_after_main_tp), permitir aunque esté HEDGED
        # porque el main acaba de tocar TP (el cambio a IN_RECOVERY ocurre después)
        if pair in self._active_cycles:
            active_cycle = self._active_cycles[pair]
            is_renewal = signal.metadata and signal.metadata.get("reason") == "renewal_after_main_tp"

            # Permitir si está IN_RECOVERY o CLOSED/PAUSED
            # FIX-CYCLE-EXPLOSION: Ya NO permitimos ACTIVE/HEDGED ni siquiera para renewals
            # El cache se limpia antes de llamar a esta función en caso de renewal
            allowed_states = ["CLOSED", "PAUSED", "IN_RECOVERY"]

            if active_cycle.status.name not in allowed_states:
                logger.info("Signal BLOCKED: Cycle already active",
                            pair=pair, existing_cycle_id=active_cycle.id,
                            cycle_status=active_cycle.status.name,
                            is_renewal=is_renewal)
                return

        # 3. Calcular lote
        lot = self.risk_manager.calculate_lot_size(pair, balance)

        # 4. Crear Entidad Ciclo
        suffix = random.randint(100, 999)
        cycle_id = f"CYC_{pair}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{suffix}"

        cycle = Cycle(id=cycle_id, pair=pair, status=CycleStatus.PENDING)
        self._active_cycles[pair] = cycle
        
        # 5. Crear Operaciones Duales (Buy y Sell) como órdenes pendientes
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        entry_distance = Decimal(str(MAIN_DISTANCE_PIPS)) * multiplier  # 5 pips
        tp_distance = Decimal(str(MAIN_TP_PIPS)) * multiplier  # 10 pips
        
        # BUY_STOP: entry a ask+5pips, TP a entry+10pips
        buy_entry_price = Price(tick.ask + entry_distance)
        op_buy = Operation(
            id=OperationId(f"{cycle_id}_B"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_BUY,
            status=OperationStatus.PENDING,
            entry_price=buy_entry_price,
            tp_price=Price(buy_entry_price + tp_distance),
            lot_size=lot
        )
        
        # SELL_STOP: entry a bid-5pips, TP a entry-10pips
        sell_entry_price = Price(tick.bid - entry_distance)
        op_sell = Operation(
            id=OperationId(f"{cycle_id}_S"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_SELL,
            status=OperationStatus.PENDING,
            entry_price=sell_entry_price,
            tp_price=Price(sell_entry_price - tp_distance),
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
                    # FIX-CLOSE-03: Solo cerrar si NO está ya cerrada
                    if op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
                        close_res = await self.trading_service.close_operation(op)
                        if not close_res.success:
                            logger.warning("Failed to close operation in cycle closure",
                                         op_id=op.id, error=close_res.error)
                    else:
                        logger.debug("Operation already closed, skipping", op_id=op.id)
        
        cycle.status = CycleStatus.CLOSED
        await self.repository.save_cycle(cycle)
        del self._active_cycles[pair]
        logger.info("Cycle closed", cycle_id=cycle.id)

    async def _open_recovery_cycle(self, signal: StrategySignal, tick: TickData, reference_price: Optional[Price] = None):
        """
        Abre un ciclo de Recovery para recuperar pérdidas neutralizadas.
        
        Args:
            signal: Señal de apertura
            tick: Datos actuales del mercado
            reference_price: Si se provee, se usa como base para los ±20 pips.
                           Si no, se usa el bid/ask actual.
        """
        pair = signal.pair
        
        # FIX: Resolver el parent_cycle correcto (puede estar en el signal o ser el activo)
        parent_id_from_signal = signal.metadata.get("parent_cycle")
        parent_cycle = None
        
        if parent_id_from_signal:
            parent_res = await self.repository.get_cycle(parent_id_from_signal)
            if parent_res.success and parent_res.value:
                parent_cycle = parent_res.value
                logger.debug("Parent cycle resolved from signal metadata", parent_id=parent_cycle.id)
                
        if not parent_cycle:
            parent_cycle = self._active_cycles.get(pair)
            if parent_cycle:
                logger.debug("Parent cycle resolved from active cache", parent_id=parent_cycle.id)
        
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

        # 4. Determinar base para precios (±20 pips)
        # Si hay reference_price, usamos ese (ej: entry de la op que bloqueó)
        # Si no, usamos el bid/ask actual (ej: para el primer recovery tras main TP)
        base_buy = reference_price if reference_price else tick.ask
        base_sell = reference_price if reference_price else tick.bid
        
        op_rec_buy = Operation(
            id=OperationId(f"{recovery_id}_B"),
            cycle_id=recovery_cycle.id,
            pair=pair,
            op_type=OperationType.RECOVERY_BUY,
            status=OperationStatus.PENDING,
            entry_price=Price(base_buy + recovery_distance),
            tp_price=Price(base_buy + recovery_distance + tp_distance),
            lot_size=lot,
            recovery_id=RecoveryId(recovery_id)
        )
        
        op_rec_sell = Operation(
            id=OperationId(f"{recovery_id}_S"),
            cycle_id=recovery_cycle.id,
            pair=pair,
            op_type=OperationType.RECOVERY_SELL,
            status=OperationStatus.PENDING,
            entry_price=Price(base_sell - recovery_distance),
            tp_price=Price(base_sell - recovery_distance - tp_distance),
            lot_size=lot,
            recovery_id=RecoveryId(recovery_id)
        )

        # 5. Guardar en DB
        await self.repository.save_cycle(recovery_cycle)
        
        # 6. Registrar en cola FIFO del ciclo padre
        parent_cycle.recovery_level = recovery_level
        
        # Sincronizar operaciones con el padre para que la estrategia las vea
        parent_cycle.add_recovery_operation(op_rec_buy)
        parent_cycle.add_recovery_operation(op_rec_sell)
        
        # FIX: Añadir ID a la cola para trazabilidad
        parent_cycle.add_recovery_to_queue(RecoveryId(recovery_id))
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
                       lot=float(lot),
                       ref_price=float(reference_price) if reference_price else "current")
        else:
            logger.error("Failed to open recovery cycle", recovery_id=recovery_id)

    async def _close_cycle_operations_final(self, cycle: Cycle):
        """
        Cierra TODAS las operaciones abiertas/neutralizadas de un ciclo al finalizar.
        Garantiza que no queden posiciones huérfanas en el broker.
        """
        logger.info("Closing all remaining operations for cycle resolution", cycle_id=cycle.id)
        
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            return
            
        tasks = []
        for op in ops_res.value:
            if op.status in (OperationStatus.ACTIVE, OperationStatus.NEUTRALIZED, OperationStatus.PENDING):
                logger.debug("Closing op during final resolution", op_id=op.id, status=op.status.value)
                
                # Para PENDING, cancelar
                if op.status == OperationStatus.PENDING:
                    if op.broker_ticket:
                        await self.trading_service.broker.cancel_order(op.broker_ticket)
                    op.status = OperationStatus.CANCELLED
                # FIX-CLOSE-03: Solo cerrar si NO está ya cerrada
                elif op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
                    # Para ACTIVE/NEUTRALIZED, cerrar en el broker
                    if op.broker_ticket:
                        tasks.append(self.trading_service.close_operation(op, reason="cycle_final_resolution"))
                    op.status = OperationStatus.CLOSED
                else:
                    logger.debug("Operation already closed, skipping in final resolution", op_id=op.id)
                
                op.metadata["close_reason"] = "cycle_final_resolution"
                await self.repository.save_operation(op)
        
        if tasks:
            await asyncio.gather(*tasks)
            logger.info(f"Closed {len(tasks)} active positions in broker")

    async def _handle_recovery_failure(self, failed_cycle: Cycle, blocking_op: Operation, tick: TickData):
        """
        Maneja el fallo de un ciclo recovery (ambas órdenes activadas).
        
        1. Identifica el ciclo principal (padre).
        2. Añade unidad de deuda de 40 pips al padre.
        3. Abre nuevo recovery a ±20 pips del entry de la operación que causó el bloqueo.
        """
        parent_id = failed_cycle.parent_cycle_id
        if not parent_id:
            logger.error("Failed recovery cycle has no parent", recovery_id=failed_cycle.id)
            return
            
        parent_res = await self.repository.get_cycle(parent_id)
        if not parent_res.success or not parent_res.value:
            logger.error("Could not find parent cycle for failed recovery", parent_id=parent_id)
            return
            
        parent_cycle = parent_res.value
        
        # 1. Registrar unidad de deuda de 40 pips (hardcoded)
        parent_cycle.accounting.add_recovery_failure_unit()
        
        # PHASE 4: Shadow tracking with REAL calculated value
        # Get both recovery operations that caused the failure
        failed_ops_res = await self.repository.get_operations_by_cycle(failed_cycle.id)
        if failed_ops_res.success:
            active_ops = [op for op in failed_ops_res.value if op.status == OperationStatus.ACTIVE]
            if len(active_ops) >= 2:
                buy_op = next((op for op in active_ops if op.is_buy), None)
                sell_op = next((op for op in active_ops if op.is_sell), None)
                if buy_op and sell_op:
                    debt = DebtUnit.from_recovery_failure(
                        cycle_id=parent_cycle.id,
                        recovery_buy_id=buy_op.id,
                        recovery_buy_entry=Decimal(str(buy_op.actual_entry_price or buy_op.entry_price)),
                        recovery_sell_id=sell_op.id,
                        recovery_sell_entry=Decimal(str(sell_op.actual_entry_price or sell_op.entry_price)),
                        pair=str(parent_cycle.pair)
                    )
                    parent_cycle.accounting.shadow_add_debt(debt)
                    logger.debug("Shadow accounting: recovery failure debt added",
                                real_debt=float(debt.pips_owed),
                                theoretical=40.0,
                                difference=float(debt.pips_owed) - 40.0)

                    # FIX: Remove TP from BOTH active recovery operations to prevent premature closure
                    # This "locks" the loss and prevents the market from hitting one TP
                    # and leaving the other side exposed to infinite loss.
                    logger.info("Removing TP from collided recovery operations to prevent equity drain", 
                                cycle_id=failed_cycle.id)
                    
                    for op in active_ops:
                        if op.broker_ticket:
                            # 1. Update in Broker
                            mod_res = await self.trading_service.broker.modify_position(
                                op.broker_ticket, 
                                new_tp=None, 
                                new_sl=op.sl_price
                            )
                            if mod_res.success:
                                logger.info("Removed TP from blocked recovery op", 
                                           ticket=op.broker_ticket, op_id=op.id)
                            else:
                                logger.error("Failed to remove TP from blocked recovery op", 
                                            ticket=op.broker_ticket, error=mod_res.error)
                        
                        # 2. Update in Repo
                        op.tp_price = None
                        op.metadata["tp_removed_on_collision"] = True
                        await self.repository.save_operation(op)
        
        logger.info("Added 40 pips debt unit due to recovery failure", 
                   parent_id=parent_cycle.id, failed_id=failed_cycle.id)
        await self.repository.save_cycle(parent_cycle)
        
        # 2. Abrir nuevo ciclo recovery (renovación por fallo)
        # La posición es ±20 pips del ENTRY de la operación que bloqueó (blocking_op)
        reference_price = Price(blocking_op.actual_entry_price or blocking_op.entry_price)
        
        signal = StrategySignal(
            signal_type=SignalType.OPEN_CYCLE,
            pair=parent_cycle.pair,
            metadata={"reason": "recovery_renewal_on_failure", "parent_cycle": parent_cycle.id}
        )
        
        await self._open_recovery_cycle(signal, tick, reference_price=reference_price)

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
