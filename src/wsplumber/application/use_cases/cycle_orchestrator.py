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
from datetime import datetime, timedelta
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
from wsplumber.application.services.economic_calendar import EconomicCalendar
from wsplumber.core.strategy._params import (
    MAIN_TP_PIPS, MAIN_DISTANCE_PIPS, RECOVERY_TP_PIPS, RECOVERY_DISTANCE_PIPS, RECOVERY_LEVEL_STEP,
    LAYER1_MODE, TRAILING_LEVELS, TRAILING_MIN_LOCK, TRAILING_REPOSITION,
    LAYER2_MODE, EVENT_PROTECTION_WINDOW_PRE, EVENT_PROTECTION_WINDOW_POST, EVENT_CALENDAR,
    LAYER3_MODE, GAP_FREEZE_THRESHOLD_PIPS, GAP_CALM_DURATION_MINUTES, GAP_CALM_THRESHOLD_PIPS,
    LAYER1B_MODE, LAYER1B_ACTIVATION_PIPS, LAYER1B_BUFFER_PIPS, LAYER1B_MIN_MOVE_PIPS, LAYER1B_OVERLAP_THRESHOLD_PIPS,
    BE_BUFFER_PIPS
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
        self.calendar = EconomicCalendar()  # Dynamic calendar service
        
        self._running = False
        self._active_cycles: Dict[CurrencyPair, Cycle] = {}
        
        # State for Immune System L3 (Blind Gap Guard)
        self._last_prices: Dict[CurrencyPair, float] = {}
        self._calm_since: Dict[CurrencyPair, datetime] = {}

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

    async def process_tick(self, tick: TickData) -> bool:
        """Procesa un tick inyectado directamente (útil para backtesting)."""
        print(f"DEBUG: process_tick entry for {tick.pair} at {tick.timestamp}")
        pair = tick.pair
        
        # 1. PHASE 5: Immune System Guard
        # Retorna: (is_allowed_to_act, is_emergency_freeze)
        is_allowed, is_emergency = await self._check_immune_system(pair, tick)

        try:
            # A. GAP DETECTADO (is_emergency=True): 
            # El sistema se vuelve totalmente CIEGO. No sincronizamos con el broker
            # porque los precios del gap no son confiables para el sistema contable local.
            if is_emergency:
                logger.warning("FROZEN: Emergency freeze active (Blind Gap)", pair=pair)
                return False

            # B. SIEMPRE SINCRONIZAR (Vigilancia Activa)
            # A menos que estemos en un Gap Ciego, el sistema debe saber qué está pasando.
            # Noticia (is_allowed=False) pero NO es emergencia -> Sincronizamos.
            await self.trading_service.sync_all_active_positions(pair)

            # C. ESCUDO DE EVENTOS (is_allowed=False):
            # El monitoreo ya se hizo (sync), pero bloqueamos la toma de decisiones
            # y el trailing para evitar latigazos destructivos.
            if not is_allowed:
                return False

            # 2. Lógica de negocio avanzada (Solo si está permitido actuar)
            await self._check_operations_status(pair, tick, skip_sync=True)
            
            # 3. Consultar a la estrategia core (usando la versión moderna y sincronizada)
            # Fetch active cycles for this pair to pass to strategy
            active_cycles = await self.repository.get_active_cycles(pair)
            signals: List[StrategySignal] = await self.strategy.generate_signals(tick, active_cycles.value)
            
            if signals:
                print(f"DEBUG: Strategy produced {len(signals)} signals: {[s.signal_type for s in signals]}")
            
            if not signals:
                return True

            # 4. Procesar todas las señales generadas
            for signal in signals:
                await self._handle_signal(signal, tick)
            
            return True

        except Exception as e:
            logger.error("Error processing tick", _exception=e, pair=pair)
            return True

    async def _process_tick_for_pair(self, pair: CurrencyPair):
        """Procesa un tick para un par específico obteniéndolo del broker."""
        tick_res = await self.trading_service.broker.get_current_price(pair)
        if not tick_res.success:
            return
        await self.process_tick(tick_res.value)


    async def _check_immune_system(self, pair: CurrencyPair, tick: TickData) -> bool:
        """
        Garantiza la supervivencia ante Gaps y Noticias.
        Retorna True si la ejecución de señales puede continuar.
        """
        now = tick.timestamp
        if not now:
            return True

        # ═══════════════════════════════════════════════════════════
        # 1. LAYER 3: BLIND GAP GUARD (Emergency Freeze)
        # ═══════════════════════════════════════════════════════════
        if LAYER3_MODE == "ON":
            last_price = self._last_prices.get(pair)
            mid_price = tick.mid
            
            if last_price:
                multiplier = 100 if "JPY" in str(pair) else 10000
                jump_pips = abs(float(mid_price - last_price)) * multiplier
                
                # Caso Alpha: El mercado salta el umbral de pánico
                if jump_pips >= GAP_FREEZE_THRESHOLD_PIPS:
                    logger.warning("BLIND GAP DETECTED! Triggering emergency freeze", 
                                 pair=pair, jump_pips=jump_pips, threshold=GAP_FREEZE_THRESHOLD_PIPS)
                    self._calm_since[pair] = now
                    return False
                
                # Caso Beta: Estamos congelados y ocurre inestabilidad -> Reset de Calma
                elif pair in self._calm_since and jump_pips >= GAP_CALM_THRESHOLD_PIPS:
                    logger.info("SECURITY RESET: Instability detected during freeze", pair=pair)
                    self._calm_since[pair] = now

            self._last_prices[pair] = mid_price

            if pair in self._calm_since:
                calm_duration = now - self._calm_since[pair]
                if calm_duration >= timedelta(minutes=GAP_CALM_DURATION_MINUTES):
                    logger.info("DYNAMIC UNFREEZE: Market stabilized", pair=pair)
                    del self._calm_since[pair]
                else:
                    return False

        # ═══════════════════════════════════════════════════════════
        # 2. LAYER 2: EVENT GUARD (Scheduled)
        # ═══════════════════════════════════════════════════════════
        if LAYER2_MODE == "ON":
            event = self.calendar.is_near_critical_event(now, window_minutes=EVENT_PROTECTION_WINDOW_PRE)
            
            if event:
                event_key = f"{pair}_{event.timestamp.isoformat()}"
                
                # MONITOREO CONTINUO: Siempre llamamos al escudo durante el evento para BE reactivo
                await self._apply_event_shield(pair, tick)
                
                if getattr(self, "_active_shield_event", None) != event_key:
                    logger.info("Scheduled event active, initial shield applied", event=event.description)
                    self._active_shield_event = event_key
                
                # Bloqueamos el flujo normal de señales (Vivir peligrosamente: solo protect)
                return False 
            
            if hasattr(self, "_active_shield_event"):
                logger.info("Event window closed, normalizing system", pair=pair)
                await self._normalize_post_event(pair, tick)
                delattr(self, "_active_shield_event")

        return True

    async def _process_layer1b_trailing_counter(
        self, 
        active_op: Operation, 
        tick: TickData, 
        cycle: Cycle,
        all_ops: list
    ):
        """
        Layer 1B: Trail the pending counter-order when active recovery is in profit.
        
        When recovery is in profit > ACTIVATION threshold:
        1. Find the pending counter-order
        2. Calculate new entry price (current_price ± BUFFER)
        3. Reposition if move distance > MIN_MOVE
        4. If both active and close together (OVERLAP), close both atomically
        """
        # Only process active recoveries
        if not active_op.is_active or not active_op.is_recovery:
            return
        
        print(f"DEBUG: _process_layer1b_trailing_counter for {active_op.id}")
        
        # FIRST: Check for OVERLAP (both recoveries active)
        # This must happen regardless of profit level
        active_counter = None
        for op in all_ops:
            if op.is_recovery and op.is_active and op.id != active_op.id:
                active_counter = op
                break
        
        if active_counter:
            # Both active = OVERLAP scenario
            await self._handle_layer1b_overlap(active_op, active_counter, tick, cycle)
            return
        
        # Calculate current profit
        mid_price = float(tick.mid)
        entry_price = float(active_op.actual_entry_price or active_op.entry_price)
        multiplier = 10000 if "JPY" not in str(tick.pair) else 100
        
        if active_op.is_buy:
            profit_pips = (mid_price - entry_price) * multiplier
        else:
            profit_pips = (entry_price - mid_price) * multiplier
        

        
        # Only trail if profit >= activation threshold
        if profit_pips < LAYER1B_ACTIVATION_PIPS:
            return
        
        print(f"DEBUG L1: Trailing active for {active_op.id}! Profit={profit_pips:.1f} pips")
        
        # Find pending counter-order in same cycle
        pending_counter = None
        for op in all_ops:
            if op.is_recovery and op.is_pending:
                # Counter must be opposite direction
                if active_op.is_buy and op.is_sell:
                    pending_counter = op
                    break
                elif active_op.is_sell and op.is_buy:
                    pending_counter = op
                    break
        
        if not pending_counter:
            # No pending counter and no active counter - nothing to do
            return
        
        # Calculate new entry for pending counter
        pip_value = 0.0001 if "JPY" not in str(tick.pair) else 0.01
        buffer_distance = LAYER1B_BUFFER_PIPS * pip_value
        
        if pending_counter.is_buy:
            new_entry = mid_price + buffer_distance
        else:
            new_entry = mid_price - buffer_distance
        
        # Check if move is significant enough
        current_entry = float(pending_counter.entry_price)
        move_pips = abs(new_entry - current_entry) * multiplier
        
        if move_pips < LAYER1B_MIN_MOVE_PIPS:
            return
        
        # Reposition the pending order
        logger.info(
            "TRAILING_REPOSITION",
            op_id=pending_counter.id,
            from_price=current_entry,
            to_price=new_entry,
            active_profit_pips=profit_pips
        )
        
        # Update operation entry price
        pending_counter.metadata["original_entry_price"] = str(pending_counter.entry_price)
        pending_counter.metadata["trailing_repositions"] = pending_counter.metadata.get("trailing_repositions", 0) + 1
        pending_counter.entry_price = Price(Decimal(str(new_entry)))
        
        # Also update TP to maintain distance
        tp_distance = RECOVERY_TP_PIPS * pip_value
        if pending_counter.is_buy:
            pending_counter.tp_price = Price(Decimal(str(new_entry + tp_distance)))
        else:
            pending_counter.tp_price = Price(Decimal(str(new_entry - tp_distance)))
        
        await self.repository.save_operation(pending_counter)
        
        # Notify broker to modify the order (if broker supports it)
        if hasattr(self.trading_service.broker, 'modify_pending_order'):
            await self.trading_service.broker.modify_pending_order(
                pending_counter.broker_ticket,
                new_entry_price=Decimal(str(new_entry)),
                new_tp_price=pending_counter.tp_price
            )

    async def _handle_layer1b_overlap(
        self,
        op1: Operation,
        op2: Operation,
        tick: TickData,
        cycle: Cycle
    ):
        print(f"DEBUG: Entering _handle_layer1b_overlap for {op1.id} and {op2.id}")
        """
        Handle OVERLAP (Positive Hedge): Both recoveries active with positive net profit.
        Close both atomically and restart the cycle with updated debt.
        
        Definition of POSITIVE HEDGE:
        - Long move: Sell Entry > Buy Entry
        - Short move: Buy Entry < Sell Entry
        In both cases, net pips = (Sell Entry - Buy Entry) if Buy first, etc.
        """
        # Identify entries
        buy_op = op1 if op1.is_buy else op2
        sell_op = op1 if op1.is_sell else op2
        
        buy_entry = float(buy_op.actual_entry_price or buy_op.entry_price)
        sell_entry = float(sell_op.actual_entry_price or sell_op.entry_price)
        
        multiplier = 10000 if "JPY" not in str(tick.pair) else 100
        
        # Calculate locked profit distance
        # If sell_entry > buy_entry, we have a positive gap between them
        locked_profit = (sell_entry - buy_entry) * multiplier
        
        # If it's a "buy first" recovery and we are in profit...
        # Wait, the direction depends on which one was "main" vs "counter".
        # But mathematically, if Sell > Buy, they are "crossed" in profit territory.
        
        # Is this a POSITIVE HEDGE?
        is_positive_hedge = locked_profit > 0
        
        if not is_positive_hedge:
            # This is a regular "Hedge Negativo" (Neutralization), leave it alone.
            # It will be resolved by TP if the move continues.
            return
        
        # Skip if already processed
        if op1.metadata.get("overlap_closed") or op2.metadata.get("overlap_closed"):
            return

        # PHASE 11: PATIENCE & SMART EXIT STRATEGY
        from wsplumber.core.strategy._params import OVERLAP_MIN_PIPS, BE_BUFFER_PIPS
        # 1. Calculate debt to settle (from parent cycle)
        debt_to_settle = 0.0
        if cycle.parent_cycle_id:
            parent_res = await self.repository.get_cycle(cycle.parent_cycle_id)
            if parent_res.success and parent_res.value:
                debt_to_settle = float(parent_res.value.accounting.pips_remaining)

        # 2. Check Closure Conditions
        # Strategy A: Reach OVERLAP_MIN_PIPS (Patience)
        # Strategy B: Reach enough profit to settle ALL debt (Smart Exit)
        print(f"DEBUG: Overlap for {cycle.id}: profit={locked_profit}, min={OVERLAP_MIN_PIPS}, debt={debt_to_settle}")
        should_close = locked_profit >= OVERLAP_MIN_PIPS
        if not should_close and debt_to_settle > 0 and locked_profit >= debt_to_settle:
            print(f"DEBUG: SMART_EXIT triggered for {cycle.id}")
            logger.info(
                "SMART_EXIT: Profit sufficient to settle total debt",
                locked_profit=locked_profit,
                debt_to_settle=debt_to_settle,
                cycle_id=cycle.id
            )
            should_close = True

        if not should_close:
            # APPLY BREAK EVEN PROTECTION
            print(f"DEBUG: Entering BE branch for {cycle.id}. Metadata: op1_be={op1.metadata.get('overlap_be')}, op2_be={op2.metadata.get('overlap_be')}")
            if not op1.metadata.get("overlap_be") and not op2.metadata.get("overlap_be"):
                print(f"DEBUG: Applying BE protection for {cycle.id}")
                logger.info(
                    "OVERLAP_PATIENCE: Profit below target, moving to BE protection",
                    locked_profit=locked_profit,
                    target=min(OVERLAP_MIN_PIPS, debt_to_settle) if debt_to_settle > 0 else OVERLAP_MIN_PIPS,
                    cycle_id=cycle.id
                )
                
                # Apply BE to both
                for op in [buy_op, sell_op]:
                    # Multiplier for buffer
                    m = 0.01 if "JPY" in str(tick.pair) else 0.0001
                    buffer = BE_BUFFER_PIPS * m
                    entry = float(op.actual_entry_price or op.entry_price)
                    
                    # BE for BUY: Entry + buffer | BE for SELL: Entry - buffer
                    be_price = entry + buffer if op.is_buy else entry - buffer
                    
                    mod_res = await self.trading_service.broker.modify_position(
                        op.broker_ticket, new_sl=Price(Decimal(str(be_price)))
                    )
                    if mod_res.success:
                        op.sl_price = Price(Decimal(str(be_price)))
                        op.metadata["overlap_be"] = True
                        await self.repository.save_operation(op)
            
            return
        
        logger.info(
            "POSITIVE_HEDGE_DETECTED (Overlap)",
            buy_entry=buy_entry,
            sell_entry=sell_entry,
            locked_profit=locked_profit,
            cycle_id=cycle.id
        )
        
        # Close both positions atomically
        mid_price = float(tick.mid)
        net_pnl = locked_profit  # Net is exactly what we locked
        
        # Mark as closed - status will be finalized by close_operation
        op1.metadata["overlap_closed"] = True
        op2.metadata["overlap_closed"] = True
        
        await self.repository.save_operation(op1)
        await self.repository.save_operation(op2)
        
        # Close positions in broker with standardized reasons
        close_tasks = []
        if op1.broker_ticket:
            close_tasks.append(self.trading_service.close_operation(op1, reason="OVERLAP_PROFIT_RESOLUTION"))
        if op2.broker_ticket:
            close_tasks.append(self.trading_service.close_operation(op2, reason="OVERLAP_PROFIT_RESOLUTION"))
        
        if close_tasks:
            await asyncio.gather(*close_tasks)
        
        # Apply profit to debt and RESTART cycle logic
        if cycle.parent_cycle_id:
            parent_cycle_res = await self.repository.get_cycle(cycle.parent_cycle_id)
            if parent_cycle_res.success and parent_cycle_res.value:
                parent_cycle = parent_cycle_res.value
                
                # Use real profit for debt reduction on the PARENT
                parent_cycle.accounting.process_recovery_tp(net_pnl)
                shadow_result = parent_cycle.accounting.shadow_process_recovery(net_pnl)
                
                logger.info(
                    "OVERLAP_RESOLVED - Parent debt updated",
                    parent_id=parent_cycle.id,
                    profit=net_pnl,
                    debt_remaining=shadow_result.get("shadow_debt_remaining")
                )
                await self.repository.save_cycle(parent_cycle)
            else:
                logger.warning("Overlap detected but parent cycle not found", parent_id=cycle.parent_cycle_id)
                shadow_result = {}
        else:
            logger.warning("Overlap detected but cycle has no parent", cycle_id=cycle.id)
            shadow_result = {}
        # PHASE 11: FIX HIERARCHY BUG
        # Ensure the CURRENT cycle is marked as CLOSED after its profit has been applied.
        cycle.status = CycleStatus.CLOSED
        cycle.metadata["close_reason"] = f"overlap_profit_{locked_profit}"
        await self.repository.save_cycle(cycle)

        # If debt remains, open a new recovery immediately (Normalization)
        if shadow_result.get("shadow_debt_remaining", 0) > 0:
            logger.info("Debt remains after overlap, opening new recovery node", cycle_id=cycle.id)
            from wsplumber.domain.types import StrategySignal, SignalType
            signal = StrategySignal(
                signal_type=SignalType.OPEN_RECOVERY,
                pair=tick.pair,
                metadata={"parent_cycle": cycle.parent_cycle_id, "reason": "overlap_restart"}
            )
            await self._open_recovery_cycle(signal, tick)


    async def _check_operations_status(self, pair: CurrencyPair, tick: TickData, skip_sync: bool = False):
        """
        Detecta cierres y activaciones de operaciones.
        """
        # Sincronizar con el broker (a menos que ya se haya hecho en process_tick)
        if not skip_sync:
            sync_res = await self.trading_service.sync_all_active_positions(pair)
            if not sync_res.success:
                return

        # FIX: Monitoreamos TODOS los ciclos activos para este par (Principal + Recoveries)
        cycles_res = await self.repository.get_active_cycles(pair)
        print(f"DEBUG: get_active_cycles returned {len(cycles_res.value) if cycles_res.success else 'error'} active cycles")
        
        # FIX-OPEN-FIRST-CYCLE: Si no hay ciclos activos, abrir el primero
        if not cycles_res.success or not cycles_res.value:
            # Solo abrir si no hay ya uno en cache
            if pair not in self._active_cycles:
                print(f"DEBUG: Deciding to open first cycle for {pair}")
                # Obtener tick actual del broker
                tick_res = await self.trading_service.broker.get_current_price(pair)
                if tick_res.success and tick_res.value:
                    signal = StrategySignal(
                        signal_type=SignalType.OPEN_CYCLE,
                        pair=pair,
                        metadata={"reason": "no_active_cycle_in_repo"}
                    )
                    print(f"DEBUG: Calling _open_new_cycle for {pair}")
                    await self._open_new_cycle(signal, tick_res.value)
                else:
                    print(f"DEBUG: get_current_price failed during open first cycle: {tick_res.error}")
            else:
                print(f"DEBUG: Cycle for {pair} already in cache")
            return

        for cycle in cycles_res.value:
            # FIX-CACHE-OVERWRITE: Solo sincronizar cache con el ciclo MAIN activo
            if cycle.cycle_type == CycleType.MAIN and cycle.status != CycleStatus.CLOSED:
                self._active_cycles[pair] = cycle

            ops_res = await self.repository.get_operations_by_cycle(cycle.id)
            if not ops_res.success:
                continue
            
            # logger.debug(f"DEBUG: Cycle {cycle.id} Ops: {[(o.id, o.status.value) for o in ops_res.value]}")
            
            # PHASE 11: Robust state detection
            main_ops = [o for o in ops_res.value if o.is_main]
            triggered_mains = [o for o in main_ops if o.status in (OperationStatus.ACTIVE, OperationStatus.TP_HIT, OperationStatus.CLOSED)]
            active_mains = [o for o in main_ops if o.status == OperationStatus.ACTIVE]
            
            # Transition to ACTIVE if first op triggered
            if len(triggered_mains) >= 1 and cycle.status == CycleStatus.PENDING:
                logger.info("First operation triggered, transitioning cycle to ACTIVE", cycle_id=cycle.id)
                cycle.status = CycleStatus.ACTIVE
                await self.repository.save_cycle(cycle)

            # Transition to HEDGED if 2+ mains triggered
            if len(triggered_mains) >= 2 and cycle.status == CycleStatus.ACTIVE:
                logger.info("Both main operations triggered (Fast Hedge detected), transitioning to HEDGED", 
                        cycle_id=cycle.id)
                cycle.activate_hedge()
                
                # Shadow debt tracking
                m_buy = next((o for o in main_ops if o.is_buy), None)
                m_sell = next((o for o in main_ops if o.is_sell), None)
                if m_buy and m_sell:
                    b_entry = m_buy.actual_entry_price or m_buy.entry_price
                    s_entry = m_sell.actual_entry_price or m_sell.entry_price
                    multiplier = 100 if "JPY" in str(pair) else 10000
                    
                    from wsplumber.domain.entities.debt import DebtUnit
                    debt = DebtUnit.from_neutralization(
                        cycle_id=str(cycle.id),
                        losing_main_id=str(m_sell.id),
                        losing_main_entry=Decimal(str(s_entry)),
                        losing_main_close=Decimal(str(b_entry)),
                        winning_main_id=str(m_buy.id),
                        hedge_id="pending",
                        pair=str(pair)
                    )
                    cycle.accounting.shadow_add_debt(debt)

                # Ensure continuation hedges are created
                for main_op in main_ops:
                    hedge_type = OperationType.HEDGE_BUY if main_op.op_type == OperationType.MAIN_BUY else OperationType.HEDGE_SELL
                    hedge_id = f"{cycle.id}_H_{main_op.op_type.value}"
                    if not any(h.id == hedge_id for h in ops_res.value):
                        hedge_op = Operation(
                            id=OperationId(hedge_id),
                            cycle_id=cycle.id,
                            pair=pair,
                            op_type=hedge_type,
                            status=OperationStatus.PENDING,
                            entry_price=main_op.tp_price,
                            lot_size=main_op.lot_size
                        )
                        cycle.add_operation(hedge_op)
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

            # PHASE 15: Pre-emptive Collision Detection (Philosophy-Aligned)
            # Check for multiple active recovery operations BEFORE processing individual trailing stops.
            # This prevents a race condition (Flow 4) where trailing triggers on a position that should be neutralized.
            active_recovery_ops = [op for op in ops_res.value if op.status == OperationStatus.ACTIVE and op.is_recovery]
            
            if cycle.cycle_type == CycleType.RECOVERY and cycle.status == CycleStatus.ACTIVE and len(active_recovery_ops) >= 2:
                if not cycle.metadata.get("failure_processed") and not cycle.metadata.get("collision_detected"):
                    logger.warning("PRE-EMPTIVE COLLISION DETECTION triggered", cycle_id=cycle.id)
                    cycle.metadata["failure_processed"] = True
                    
                    # 1. Set global collision flag for this tick
                    if not hasattr(self, '_collision_tick'):
                        self._collision_tick = {}
                    tick_key = tick.timestamp.isoformat() if tick.timestamp else "unknown"
                    self._collision_tick[str(pair)] = tick_key
                    
                    await self.repository.save_cycle(cycle)
                    
                    # 2. Trigger Flow 4: Neutralize and open next level
                    # This removes TPs and marks ops as NEUTRALIZED in repo/broker
                    await self._handle_recovery_failure(cycle, active_recovery_ops[-1], tick)

                    # 3. FIFO Linkage: Create unit of debt
                    fail_op_ids = [str(op.id) for op in active_recovery_ops]
                    cycle.accounting.add_recovery_failure_unit(real_loss_pips=40.0, operation_ids=fail_op_ids)
                    logger.info("FIFO: Recovery bridge debt unit created at collision", operation_ids=fail_op_ids)
                    
                    # 4. Refresh operations to ensure the loop below sees them as NEUTRALIZED
                    ops_res = await self.repository.get_operations_by_cycle(cycle.id)
                    active_recovery_ops = [op for op in ops_res.value if op.status == OperationStatus.ACTIVE and op.is_recovery]

            for op in ops_res.value:
                # ═══════════════════════════════════════════════════════════
                # 1. MANEJO DE ACTIVACIÓN DE ÓRDENES
                # ═══════════════════════════════════════════════════════════
                if op.status == OperationStatus.ACTIVE:
                    if op.is_recovery:
                        active_recovery_ops.append(op)

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

                    if op.is_recovery and LAYER1_MODE == "ADAPTIVE_TRAILING":
                        trailing_result = await self._process_layer1_trailing(op, tick, cycle)
                        if trailing_result:
                            continue

                    # Layer 1B: Trail the pending counter-order
                    if op.is_recovery and LAYER1B_MODE == "ON":
                        await self._process_layer1b_trailing_counter(op, tick, cycle, ops_res.value)

                # ═══════════════════════════════════════════════════════════
                # 2. MANEJO DE CIERRE DE ÓRDENES (TP HIT)
                # ═══════════════════════════════════════════════════════════
                if op.status == OperationStatus.TP_HIT:
                    if op.metadata.get("tp_processed"):
                        continue

                    # Mark as processed
                    op.metadata["tp_processed"] = True
                    await self.repository.save_operation(op)

                    # Close at broker if it hit TP (and wasn't already closed by sync)
                    if op.broker_ticket and op.status == OperationStatus.TP_HIT and not op.metadata.get("broker_closed"):
                        logger.info("Closing position in broker", op_id=op.id, ticket=op.broker_ticket)
                        await self.trading_service.close_operation(op, reason="tp_hit")

                    if cycle.status == CycleStatus.PENDING:
                        cycle.status = CycleStatus.ACTIVE
                        await self.repository.save_cycle(cycle)

                    # Notify Strategy
                    self.strategy.process_tp_hit(
                        operation_id=op.id,
                        profit_pips=float(op.profit_pips or MAIN_TP_PIPS),
                        timestamp=datetime.now()
                    )
                    
                    if op.is_main:
                        # PHASE 11: Priority Cleanup Protocol
                        # 1. Branch A: Hedged TP (Pairing)
                        if cycle.status == CycleStatus.HEDGED:
                            logger.info("Rama B: Hedged TP detected, performing pairing", op_id=op.id, cycle_id=cycle.id)
                            for other_op in ops_res.value:
                                if other_op.is_main and other_op.id != op.id and other_op.status == OperationStatus.ACTIVE:
                                    other_op.neutralize(op.id)
                                    await self.repository.save_operation(other_op)
                                    if other_op.broker_ticket:
                                        await self.trading_service.broker.update_position_status(other_op.broker_ticket, OperationStatus.NEUTRALIZED)
                                        # Remove TP to prevent broker closing it
                                        await self.trading_service.broker.modify_position(other_op.broker_ticket, new_tp=None)
                                    
                                    # Neutralize the continuation hedge that just went active
                                    # (Note: In a hedge path, the TP hit for one main activates the hedge for that level)
                                    for hedge_op in ops_res.value:
                                        if hedge_op.is_hedge and hedge_op.status == OperationStatus.ACTIVE:
                                            hedge_op.neutralize(op.id)
                                            hedge_op.metadata["neutralized_as_cover"] = True
                                            await self.repository.save_operation(hedge_op)
                                            if hedge_op.broker_ticket:
                                                await self.trading_service.broker.update_position_status(hedge_op.broker_ticket, OperationStatus.NEUTRALIZED)
                                    
                                    # Link debt unit
                                    found_hedge_id = ""
                                    for h_op in ops_res.value:
                                        if h_op.is_hedge and h_op.metadata.get("neutralized_as_cover"):
                                            found_hedge_id = str(h_op.id)
                                            break

                                    from wsplumber.domain.entities.debt import DebtUnit
                                    initial_unit = DebtUnit(
                                        id=f"INIT_{cycle.id}_{datetime.now().strftime('%M%S')}",
                                        source_cycle_id=str(cycle.id),
                                        source_operation_ids=[str(other_op.id), found_hedge_id],
                                        pips_owed=Decimal("20.0"),
                                        debt_type="main_hedge"
                                    )
                                    cycle.accounting.debt_units.append(initial_unit)
                                    logger.info("FIFO: Pairing complete, debt unit created", unit_id=initial_unit.id)
                            
                            cycle.start_recovery()
                            await self.repository.save_cycle(cycle)
                            
                            recovery_signal = StrategySignal(
                                signal_type=SignalType.OPEN_CYCLE,
                                pair=cycle.pair,
                                metadata={"reason": "recovery_after_hedge_tp", "parent_cycle": cycle.id}
                            )
                            await self._open_recovery_cycle(recovery_signal, tick)

                        # 2. Branch B: Simple TP (Happy Path Cleanup)
                        else:
                            logger.info("Rama A: Simple TP detected, cleaning counter-orders before close", op_id=op.id, cycle_id=cycle.id)
                            # Cleanup counter mains (PENDING or ACTIVE residuary)
                            for other_op in ops_res.value:
                                if other_op.is_main and other_op.id != op.id:
                                    if other_op.status == OperationStatus.PENDING:
                                        if other_op.broker_ticket:
                                            await self.trading_service.broker.cancel_order(other_op.broker_ticket)
                                        other_op.status = OperationStatus.CANCELLED
                                        await self.repository.save_operation(other_op)
                                    elif other_op.status == OperationStatus.ACTIVE:
                                        # Emergency cleanup: this shouldn't happen if state machine is correct
                                        logger.warning("Emergency cleanup: closing active counter-main in simple cycle", op_id=other_op.id)
                                        if other_op.broker_ticket:
                                            await self.trading_service.close_operation(other_op, reason="CLEANUP_COUNTER_POSITIONS")

                        # 3. Finalize Cycle (Common Cleanup)
                        await self._cancel_pending_hedge_counterpart(cycle, op)
                        cycle.record_main_tp(Pips(float(op.profit_pips or MAIN_TP_PIPS)))
                        
                        if cycle.status == CycleStatus.ACTIVE:
                            cycle.status = CycleStatus.CLOSED
                            cycle.closed_at = datetime.now()
                            cycle.metadata["close_reason"] = "single_main_tp_finalized"
                        
                        await self.repository.save_cycle(cycle)
                        
                        # 4. Open NEW cycle (Renewal) - ALWAYS on Main TP
                        # Note: Debt recovery is handled by recovery cycles (opened above if HEDGED).
                        # New Main opening is INDEPENDENT of debt state.
                        renewal_signal = StrategySignal(
                            signal_type=SignalType.OPEN_CYCLE,
                            pair=cycle.pair,
                            metadata={"reason": "renewal_after_main_tp", "parent_cycle": cycle.id}
                        )
                        await self._open_new_cycle(renewal_signal, tick)

                    # 5. Handle Recovery TP
                    if op.is_recovery and op.status == OperationStatus.TP_HIT:
                        logger.warning("DIAG: Recovery TP detected entering handler",
                                      op_id=op.id, op_status=op.status.value, 
                                      trailing_closed=op.metadata.get("trailing_closed"))
                        if op.metadata.get("trailing_closed"):
                            # This is handled in _process_layer1_trailing but keeping hook
                            pass
                        else:
                            recovery_cycle_res = await self.repository.get_cycle(op.cycle_id)
                            if recovery_cycle_res.success and recovery_cycle_res.value:
                                await self._handle_recovery_tp(recovery_cycle_res.value, tick, trigger_op_id=op.id)

                # End of operation loop


                        
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
                                    print(f"DEBUG: Main TP Hit! Opening NEW CYCLE (Full recovery version) from {cycle.id}")
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
        
        # Calcular precios de entrada a 5 pips de distancia desde el MID
        # FIX: Usar MID como referencia, no ASK/BID, para mantener la distancia exacta
        buy_entry_price = Price(tick.mid + entry_distance)
        sell_entry_price = Price(tick.mid - entry_distance)
        
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
    # LAYER 1: TRAILING STOP PROFIT HANDLING
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_trailing_profit(self, op: Operation, tick: TickData) -> None:
        """
        Handle recovery operation closed by trailing stop.
        
        Applies proportional debt reduction based on the captured profit,
        and optionally opens a replacement recovery from current price.
        
        BUGS FIXED:
        - BUG7: Call FIX-MAIN-OPERATIONS if pips_remaining reaches 0
        - BUG8: Use Decimal consistently for debt_units
        - BUG9: Check parent status before reposition
        - BUG10: Use Decimal for comparison
        """
        trailing_profit = op.metadata.get("trailing_profit_pips", 0.0)
        needs_reposition = op.metadata.get("needs_reposition", False)
        reposition_price = op.metadata.get("reposition_price")
        
        logger.info("LAYER1: Processing trailing stop profit",
                   op_id=op.id,
                   trailing_profit=trailing_profit,
                   needs_reposition=needs_reposition)
        
        # Get the parent cycle to apply debt reduction
        recovery_cycle_res = await self.repository.get_cycle(op.cycle_id)
        if not recovery_cycle_res.success or not recovery_cycle_res.value:
            logger.error("LAYER1: Could not get recovery cycle for trailing", op_id=op.id)
            return
        
        recovery_cycle = recovery_cycle_res.value
        parent_id = recovery_cycle.metadata.get("parent_cycle_id")
        
        if not parent_id:
            logger.warning("LAYER1: Recovery has no parent cycle", recovery_id=recovery_cycle.id)
            return
        
        parent_cycle_res = await self.repository.get_cycle(parent_id)
        if not parent_cycle_res.success or not parent_cycle_res.value:
            logger.error("LAYER1: Could not get parent cycle", parent_id=parent_id)
            return
        
        parent_cycle = parent_cycle_res.value
        pair = parent_cycle.pair
        
        # Apply proportional debt reduction
        # Recovery TP = 80 pips, so if we captured 25 pips, that's 25/80 = 31.25% of a debt unit
        # BUG10 FIX: Use Decimal for comparison
        if trailing_profit > 0 and parent_cycle.accounting.pips_remaining > Decimal("0"):
            # Calculate reduction as proportion of full TP
            full_tp = Decimal("80.0")  # RECOVERY_TP_PIPS
            trailing_profit_dec = Decimal(str(trailing_profit))
            reduction_ratio = min(trailing_profit_dec / full_tp, Decimal("1.0"))
            
            # Apply to the first debt unit (FIFO)
            if parent_cycle.accounting.debt_units:
                # BUG8 FIX: Ensure debt_units are Decimal
                first_debt = Decimal(str(parent_cycle.accounting.debt_units[0]))
                debt_reduction = first_debt * reduction_ratio
                
                # Reduce the debt unit
                new_debt = first_debt - debt_reduction
                if new_debt <= Decimal("0"):
                    # Full unit paid off
                    parent_cycle.accounting.debt_units.pop(0)
                else:
                    # BUG8 FIX: Store as float for consistency with existing code
                    parent_cycle.accounting.debt_units[0] = float(new_debt)
                
                # Recalculate totals
                parent_cycle.accounting.pips_recovered += trailing_profit_dec
                parent_cycle.accounting.pips_remaining = float(sum(float(u.pips_owed) for u in parent_cycle.accounting.debt_units))
                
                await self.repository.save_cycle(parent_cycle)
                
                logger.info("LAYER1: Partial debt reduction applied",
                           parent_id=parent_cycle.id,
                           trailing_profit=trailing_profit,
                           reduction_ratio=round(float(reduction_ratio), 2),
                           debt_reduced=round(float(debt_reduction), 1),
                           remaining_debt=float(parent_cycle.accounting.pips_remaining),
                           debt_units_count=len(parent_cycle.accounting.debt_units),
                           total_recovered=float(parent_cycle.accounting.pips_recovered))
                
                # BUG7 FIX: If debt is fully paid, close main operations
                if parent_cycle.accounting.pips_remaining == Decimal("0"):
                    logger.info("LAYER1: Debt fully paid via trailing, closing main operations",
                               parent_id=parent_cycle.id)
                    
                    parent_ops_result = await self.repository.get_operations_by_cycle(parent_cycle.id)
                    if parent_ops_result.success:
                        main_closed = 0
                        for p_op in parent_ops_result.value:
                            if not p_op.is_recovery and p_op.broker_ticket:
                                if p_op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                                    close_result = await self.trading_service.close_operation(p_op, reason="FIFO_LIQUIDATION_DEBT_SETTLEMENT")
                                    if close_result.success:
                                        main_closed += 1
                        
                        logger.info("LAYER1: Main operations closed after trailing paid debt",
                                   parent_id=parent_cycle.id,
                                   closed_count=main_closed)
        
        # Cancel counterpart recovery operations (same as normal TP)
        await self._cancel_pending_recovery_counterpart(recovery_cycle)
        
        # Mark recovery cycle as closed
        recovery_cycle.status = CycleStatus.CLOSED
        recovery_cycle.closed_at = datetime.now()
        recovery_cycle.metadata["close_reason"] = "trailing_stop"
        recovery_cycle.metadata["trailing_profit_pips"] = trailing_profit
        await self.repository.save_cycle(recovery_cycle)
        
        # Close all recovery operations in broker (FIX-RECOVERY-CLOSURE)
        recovery_ops_result = await self.repository.get_operations_by_cycle(recovery_cycle.id)
        if recovery_ops_result.success:
            for r_op in recovery_ops_result.value:
                if r_op.broker_ticket and r_op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                    if r_op.id != op.id:  # Don't close the one that already closed by trailing
                        # FIX-BALANCE-LOSS: NEUTRALIZE instead of CLOSE to prevent realizing losses.
                        # These stay open in broker as "frozen debt" until FIFO liquidation.
                        r_op.status = OperationStatus.NEUTRALIZED
                        r_op.metadata["neutralized_reason"] = "counterpart_trailing_closed"
                        await self.repository.save_operation(r_op)
                        if r_op.broker_ticket:
                            await self.trading_service.broker.update_position_status(r_op.broker_ticket, OperationStatus.NEUTRALIZED)
                        logger.info("LAYER1: Neutralized counterpart recovery (frozen debt)", op_id=r_op.id)
        
        # Reposition: Open new recovery from current price if configured
        # BUG9 FIX: Only reposition if parent cycle is still active and has debt
        if needs_reposition and reposition_price:
            # Refresh parent cycle to get latest state
            parent_cycle_res = await self.repository.get_cycle(parent_id)
            if parent_cycle_res.success:
                parent_cycle = parent_cycle_res.value
                
                if (parent_cycle.status not in (CycleStatus.CLOSED, CycleStatus.CANCELLED) and
                    parent_cycle.accounting.pips_remaining > Decimal("0")):
                    
                    print(f"DEBUG L1: Opening REPOSITION RECOVERY for {parent_cycle.id}")
                    logger.info("LAYER1: Opening replacement recovery",
                               parent_id=parent_cycle.id,
                               reposition_price=reposition_price,
                               remaining_debt=float(parent_cycle.accounting.pips_remaining))
                        
                    signal = StrategySignal(
                        signal_type=SignalType.OPEN_RECOVERY,
                        pair=pair,
                        metadata={
                            "reason": "trailing_reposition",
                            "parent_cycle": parent_cycle.id,
                            "original_profit": trailing_profit
                        }
                    )
                    await self._open_recovery_cycle(signal, tick, reference_price=Price(Decimal(str(reposition_price))))
                else:
                    logger.info("LAYER1: Skipping reposition - parent closed or no debt",
                               parent_id=parent_cycle.id,
                               parent_status=parent_cycle.status.value,
                               remaining_debt=float(parent_cycle.accounting.pips_remaining))
        
        # Mark as processed
        op.metadata["trailing_processed"] = True
        await self.repository.save_operation(op)
        
        logger.info("LAYER1: Trailing profit handling complete",
                   op_id=op.id,
                   parent_id=parent_cycle.id,
                   needs_reposition=needs_reposition)

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-003: MÉTODO ACTUALIZADO - FIFO con cierre atómico Main+Hedge
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_recovery_tp(
        self, 
        recovery_cycle: Cycle, 
        tick: TickData, 
        trigger_op_id: str = None
    ) -> None:
        """
        Procesa el TP de un ciclo de recovery usando lógica FIFO.
        
        FIX-003: Ahora cierra Main + Hedge como unidad atómica.
        
        Reglas FIFO (Documento Madre pág. 156-166):
        - Recovery profit = 80 pips
        - Primer recovery en cola cuesta 20 pips (Main + Hedge)
        - Siguientes recoveries cuestan 40 pips cada uno
        """
        logger.warning("DIAG: ==== ENTERING _handle_recovery_tp ====",
                      recovery_cycle_id=recovery_cycle.id,
                      recovery_status=recovery_cycle.status.value)
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
        
        # PHASE 4: Shadow tracking with REAL profit value
        # Get the actual profit pips from the recovery operation that hit TP
        real_profit = float(RECOVERY_TP_PIPS) # Default
        recovery_ops = [op for op in (await self.repository.get_operations_by_cycle(recovery_cycle.id)).value 
                       if op.status == OperationStatus.TP_HIT]
        if recovery_ops:
            real_profit = float(recovery_ops[0].profit_pips)
            
        # DYNAMIC DEBT: Use real profit instead of hardcoded 80.0
        logger.info(f"FIFO: Crediting {real_profit} pips from {recovery_cycle.id} to parent {parent_cycle.id}")
        surplus = parent_cycle.accounting.process_recovery_tp(real_profit)
        
        # Immediate save to avoid memory/persistence sync issues
        await self.repository.save_cycle(parent_cycle)
        
        if recovery_ops:
            shadow_result = parent_cycle.accounting.shadow_process_recovery(real_profit)
            logger.debug("Shadow accounting: recovery processed", 
                        real_profit=real_profit,
                        theoretical=float(RECOVERY_TP_PIPS),
                        difference=real_profit - float(RECOVERY_TP_PIPS),
                        shadow_debt_remaining=shadow_result.get("shadow_debt_remaining", 0))
        
        # 3. Aplicar cierres atómicos para las unidades que se hayan liquidado
        # Extraemos las unidades que el FIFO marcó como liquidadas (totalmente pagadas)
        liquidated = parent_cycle.accounting.liquidated_units
        if liquidated:
            logger.info("FIFO: Liquidating debt units", 
                       count=len(liquidated), 
                       units=[u.id for u in liquidated])
            
            for unit in liquidated:
                # La regla de oro: Solo cerramos lo que tiene tickets vinculados
                for op_id in unit.source_operation_ids:
                    # Buscamos la operación para obtener el ticket del broker
                    op_res = await self.repository.get_operation(op_id)
                    if op_res.success and op_res.value:
                        op = op_res.value
                        if op.broker_ticket and op.status != OperationStatus.CLOSED and not op.metadata.get("broker_closed"):
                            logger.info("FIFO: Closing compensated position", 
                                       op_id=op.id, ticket=op.broker_ticket)
                            await self.trading_service.close_operation(op, reason="FIFO_LIQUIDATION_DEBT_SETTLEMENT")
                            op.status = OperationStatus.CLOSED
                            op.metadata["close_reason"] = f"liquidated_by_unit_{unit.id}"
                            if trigger_op_id:
                                op.metadata["liquidated_by_op_id"] = trigger_op_id
                            await self.repository.save_operation(op)
        
                            print(f"DEBUG FIFO: Cycle {parent_cycle.id} - Remaining Debt: {parent_cycle.accounting.pips_remaining} | Surplus: {surplus}")
        logger.info(
            "FIFO Processing Results",
            cycle_id=parent_cycle.id,
            total_recovered=float(parent_cycle.accounting.pips_recovered),
            pips_remaining_debt=float(parent_cycle.accounting.pips_remaining),
            surplus_pips=surplus
        )

        # 4. Condición de Cierre Atómico
        # El ciclo solo se cierra si la deuda es CERO y el excedente supera el umbral de seguridad.
        from wsplumber.core.strategy._params import RECOVERY_MIN_SURPLUS
        min_surplus = float(RECOVERY_MIN_SURPLUS)
        
        if parent_cycle.accounting.is_fully_recovered and surplus >= min_surplus:
            print(f"DEBUG: CYCLE {parent_cycle.id} FULLY RESOLVED! Surplus: {surplus}")
            logger.info("Cycle FULLY RESOLVED with sufficient surplus. Closing cycle.", 
                      cycle_id=parent_cycle.id, surplus=surplus, min_required=min_surplus)
            
            # Cerrar todas las operaciones restantes (neutralizadas)
            await self._close_cycle_operations_final(parent_cycle)
            
            parent_cycle.status = CycleStatus.CLOSED
            parent_cycle.closed_at = datetime.now()
            parent_cycle.metadata["close_reason"] = f"RECOVERY_TP_FULL_RESOLUTION_SURPLUS_{surplus}"
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
                # FIX-BALANCE-LOSS: Only "close" ops that already hit TP. Others get NEUTRALIZED.
                if op.broker_ticket and op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                    if op.status == OperationStatus.TP_HIT:
                        # This op hit TP - it's already closed in broker, just update status
                        op.status = OperationStatus.CLOSED
                        await self.repository.save_operation(op)
                        closed_count += 1
                        logger.info("Recovery operation TP confirmed closed", op_id=op.id)
                    else:
                        # FIX-BALANCE-LOSS: NEUTRALIZE instead of CLOSE to prevent realizing loss.
                        # These stay open in broker as "frozen debt" until FIFO liquidation.
                        op.status = OperationStatus.NEUTRALIZED
                        op.metadata["neutralized_reason"] = "counterpart_tp_hit"
                        await self.repository.save_operation(op)
                        if op.broker_ticket:
                            await self.trading_service.broker.update_position_status(op.broker_ticket, OperationStatus.NEUTRALIZED)
                        skipped_count += 1
                        logger.info("Recovery counterpart NEUTRALIZED (frozen debt)", op_id=op.id)
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
    # FIX-FIFO-BROKER-V1: Close neutralized positions using broker as truth
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _sync_and_close_neutralized_fifo(self, parent_cycle: Cycle, available_pips: float) -> int:
        """
        Close NEUTRALIZED positions from failed recoveries using available FIFO pips.
        
        Uses broker as source of truth - finds all neutralized positions with tickets,
        sorts by creation date (FIFO), and closes pairs atomically while pips are available.
        
        Args:
            parent_cycle: The MAIN cycle containing debt
            available_pips: Surplus pips available after FIFO processing
            
        Returns:
            Number of pairs (2 ops each) closed
        """
        if available_pips <= 0:  # Close if ANY surplus is available
            return 0
        
        # 1. Get ALL neutralized operations with broker tickets in this cycle tree
        all_neutralized = []
        
        # Get direct child recovery cycles
        all_cycles_res = await self.repository.get_all_cycles()
        if isinstance(all_cycles_res, list):
            all_cycles = all_cycles_res
        else:
            all_cycles = all_cycles_res.value if all_cycles_res.success else []
        
        child_recoveries = [c for c in all_cycles if c.parent_cycle_id == parent_cycle.id]
        
        logger.warning("DIAG-FIFO: Searching for neutralized ops",
                      parent_id=parent_cycle.id,
                      child_recovery_count=len(child_recoveries),
                      available_pips=available_pips)
        
        for recovery in child_recoveries:
            ops_res = await self.repository.get_operations_by_cycle(recovery.id)
            if ops_res.success:
                for op in ops_res.value:
                    if op.status == OperationStatus.NEUTRALIZED and op.broker_ticket:
                        all_neutralized.append(op)
                    elif op.status == OperationStatus.NEUTRALIZED:
                        logger.warning("DIAG-FIFO: Neutralized op WITHOUT broker_ticket",
                                      op_id=op.id, recovery_id=recovery.id)
        
        logger.warning("DIAG-FIFO: Found neutralized ops",
                      count=len(all_neutralized),
                      parent_id=parent_cycle.id)
        
        if len(all_neutralized) < 2:
            return 0  # Need at least one pair
        
        # 2. Sort by creation date (oldest first - FIFO)
        all_neutralized.sort(key=lambda x: x.created_at or datetime.min)
        
        # 3. Close pairs while we have pips (each recovery pair costs 40 pips)
        COST_PER_PAIR = 40.0
        pairs_closed = 0
        pips_remaining = available_pips
        
        # Group by cycle to close pairs from same recovery together
        ops_by_cycle = {}
        for op in all_neutralized:
            if op.cycle_id not in ops_by_cycle:
                ops_by_cycle[op.cycle_id] = []
            ops_by_cycle[op.cycle_id].append(op)
        
        for cycle_id, ops in ops_by_cycle.items():
            if len(ops) < 2:
                continue  # Need both ops of the pair
            
            # Close both ops atomically - no pips cost check, just close all neutralized
            op1, op2 = ops[0], ops[1]
            
            try:
                # Close in broker with standardized forensic reasons
                close1 = await self.trading_service.close_operation(op1, reason="FIFO_LIQUIDATION_DEBT_SETTLEMENT")
                close2 = await self.trading_service.close_operation(op2, reason="FIFO_LIQUIDATION_DEBT_SETTLEMENT")
                
                if close1.success and close2.success:
                    logger.info("FIX-FIFO-BROKER-V1: Closed neutralized recovery pair",
                               op1=op1.id, op2=op2.id, 
                               recovery_cycle=cycle_id)
                    pairs_closed += 1
                    
                    # Mark the recovery cycle as closed if all its ops are now closed
                    ops_res = await self.repository.get_operations_by_cycle(cycle_id)
                    if ops_res.success:
                        still_open = [o for o in ops_res.value 
                                     if o.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED, OperationStatus.TP_HIT)]
                        if not still_open:
                            recovery_cycle_res = await self.repository.get_cycle(cycle_id)
                            if recovery_cycle_res.success and recovery_cycle_res.value:
                                recovery_cycle = recovery_cycle_res.value
                                recovery_cycle.status = CycleStatus.CLOSED
                                recovery_cycle.closed_at = datetime.now()
                                recovery_cycle.metadata["close_reason"] = "fifo_liquidation"
                                await self.repository.save_cycle(recovery_cycle)
                else:
                    logger.warning("FIX-FIFO-BROKER-V1: Failed to close one or both ops",
                                  op1_success=close1.success, op2_success=close2.success)
            except Exception as e:
                logger.error("FIX-FIFO-BROKER-V1: Error closing neutralized pair",
                            error=str(e), op1=op1.id, op2=op2.id)
        
        return pairs_closed

    # ═══════════════════════════════════════════════════════════════════════
    # FIX-003: NUEVO MÉTODO - Cierre atómico de debt unit (Main + Hedge)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _close_debt_unit_atomic(self, cycle: Cycle, debt_unit_id: str, main_op_id: Optional[str] = None) -> None:
        """
        FIX-003: Cierra atómicamente una debt unit (Main + Hedge).
        
        Una debt unit contiene:
        - Una operación Main neutralizada
        - Una operación Hedge que la cubre
        
        Args:
            cycle: Ciclo padre
            debt_unit_id: ID de la unidad de deuda (e.g. "OP_020_debt_unit" o "INITIAL_UNIT")
            main_op_id: ID específico de la Main a cerrar (opcional)
        """
        logger.info(
            "Closing debt unit atomically",
            cycle_id=cycle.id,
            debt_unit_id=debt_unit_id,
            main_op_id=main_op_id
        )
        
        # Obtener todas las operaciones del ciclo
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            logger.error("Failed to get operations for debt unit closure", cycle_id=cycle.id)
            return
        
        # Identificar Main y Hedge de esta debt unit
        # El ID base de la Main suele estar en la metadata de la unidad de deuda
        # Pero si nos pasan el ID directamente lo usamos
        main_op_id_base = main_op_id or debt_unit_id.replace("_debt_unit", "")
        
        main_op = None
        hedge_op = None
        
        for op in ops_res.value:
            # Caso especial: INITIAL_UNIT (primera main neutralizada) o ID específico
            is_target_main = False
            if debt_unit_id == "INITIAL_UNIT":
                is_target_main = op.is_main and op.status == OperationStatus.NEUTRALIZED
            elif main_op_id:
                is_target_main = str(op.id) == main_op_id
            else:
                is_target_main = str(op.id) == main_op_id_base and op.is_main and op.status == OperationStatus.NEUTRALIZED
            
            if is_target_main:
                main_op = op
                # FIX-FIFO: El hedge que cierra con un main neutralizado es del TIPO OPUESTO
                # Si main neutralizado es BUY → buscar HEDGE_SELL activo
                # Si main neutralizado is SELL → buscar HEDGE_BUY activo
                from wsplumber.domain.types import OperationType

                if main_op.op_type == OperationType.MAIN_BUY:
                    # Si main neutralizado es BUY → buscar HEDGE_SELL activo (o MAIN_SELL para el Root)
                    expected_opposites = [OperationType.HEDGE_SELL, OperationType.MAIN_SELL]
                elif main_op.op_type == OperationType.MAIN_SELL:
                    # Si main neutralizado is SELL → buscar HEDGE_BUY activo (o MAIN_BUY para el Root)
                    expected_opposites = [OperationType.HEDGE_BUY, OperationType.MAIN_BUY]
                else:
                    logger.error("Main op has unexpected type", op_type=main_op.op_type)
                    break

                # Buscar el hedge/opuesto del tipo esperado (ACTIVE, TP_HIT o NEUTRALIZED)
                for hop in ops_res.value:
                    if hop.id != main_op.id and hop.op_type in expected_opposites and \
                       hop.status in (OperationStatus.ACTIVE, OperationStatus.TP_HIT, OperationStatus.NEUTRALIZED, OperationStatus.CLOSED):
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
            main_entry=float(main_op.entry_price) if main_op.entry_price else None,
            hedge_id=hedge_op.id,
            hedge_type=hedge_op.op_type.value,
            hedge_entry=float(hedge_op.entry_price) if hedge_op.entry_price else None
        )
        
        # Use atomic debt unit closure for correct P&L calculation
        # This ensures the net is exactly -20 pips (entry difference) regardless of when P&Ls were frozen
        if main_op.broker_ticket and hedge_op.broker_ticket:
            if main_op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT) and \
               hedge_op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
                
                close_res = await self.trading_service.broker.close_debt_unit(
                    main_op.broker_ticket, hedge_op.broker_ticket
                )
                
                if close_res.success:
                    logger.info("Debt unit closed atomically", 
                               net_pips=close_res.value.get("net_pips"),
                               main_id=main_op.id, hedge_id=hedge_op.id)
                    # ... (rest of logic)
                    
                    # Update operation states
                    main_op.status = OperationStatus.CLOSED
                    main_op.metadata["close_reason"] = "fifo_recovery_tp"
                    main_op.metadata["close_method"] = "atomic_debt_unit"
                    main_op.metadata["debt_unit_id"] = debt_unit_id
                    await self.repository.save_operation(main_op)
                    
                    hedge_op.status = OperationStatus.CLOSED
                    hedge_op.metadata["close_reason"] = "fifo_recovery_tp"  
                    hedge_op.metadata["close_method"] = "atomic_debt_unit"
                    hedge_op.metadata["debt_unit_id"] = debt_unit_id
                    await self.repository.save_operation(hedge_op)
                else:
                    logger.error("Failed to close debt unit atomically", 
                               error=close_res.error, debt_unit_id=debt_unit_id)
                    return
        else:
            logger.warning("Missing broker tickets for debt unit closure",
                          main_ticket=main_op.broker_ticket, hedge_ticket=hedge_op.broker_ticket)

    # ═══════════════════════════════════════════════════════════════════════
    # RESTO DE MÉTODOS (Sin cambios significativos)
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_signal(self, signal: StrategySignal, tick: TickData):
        """Maneja las señales emitidas por la estrategia."""
        reason = signal.metadata.get("reason", "unknown") if signal.metadata else "unknown"
        print(f"DEBUG: Signal received: {signal.signal_type.name} for {signal.pair} Reason: {reason}")
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
        print(f"DEBUG: _open_new_cycle entry for {pair} at {tick.timestamp}")
        
        # PHASE 5: Immune System Guard - Block new openings
        now = tick.timestamp or datetime.now()
        if pair in self._calm_since:
            print(f"DEBUG: _open_new_cycle BLOCKED by calm_since")
            logger.info("New cycle BLOCKED by emergency freeze", pair=pair)
            return
        
        # Check if we are in an event window (L2)
        is_shielded = False
        if LAYER2_MODE == "ON":
            for event_time_str, importance, desc in EVENT_CALENDAR:
                event_time = datetime.fromisoformat(event_time_str)
                pre_window = event_time - timedelta(minutes=EVENT_PROTECTION_WINDOW_PRE)
                post_window = event_time + timedelta(minutes=EVENT_PROTECTION_WINDOW_POST)
                if pre_window <= now <= post_window:
                    is_shielded = True
                    print(f"DEBUG: _open_new_cycle BLOCKED by shield: {desc}")
                    break
                    
        if is_shielded:
            logger.info("New cycle BLOCKED by scheduled event shield", pair=pair)
            return

        
        # 1. Obtener métricas de exposición reales
        exposure_pct, num_recoveries = await self._get_exposure_metrics(pair)
        acc_info = await self.trading_service.broker.get_account_info()
        balance = acc_info.value["balance"] if acc_info.success else 10000.0
        print(f"DEBUG: _open_new_cycle exposure={exposure_pct}, balance={balance}")

        # Validar con el RiskManager
        can_open = self.risk_manager.can_open_position(
            pair, 
            current_exposure=exposure_pct,
            num_recoveries=num_recoveries
        )
        if not can_open.success:
            print(f"DEBUG: _open_new_cycle BLOCKED by RiskManager: {can_open.error}")
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
        ts_str = now.strftime('%Y%m%d%H%M%S')
        cycle_id = f"CYC_{pair}_{ts_str}_{suffix}"

        cycle = Cycle(id=cycle_id, pair=pair, status=CycleStatus.PENDING)
        self._active_cycles[pair] = cycle
        
        # 5. Crear Operaciones Duales (Buy y Sell) como órdenes pendientes
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        entry_distance = Decimal(str(MAIN_DISTANCE_PIPS)) * multiplier  # 5 pips
        tp_distance = Decimal(str(MAIN_TP_PIPS)) * multiplier  # 10 pips
        
        # BUY_STOP: entry a mid+5pips, TP a entry+10pips
        # FIX: Usar MID como referencia para mantener distancia exacta de 5 pips
        # SUPPORT FORCED PRICE (Post-Event Reactivation)
        mid_val = tick.mid
        if signal.metadata and "forced_price" in signal.metadata:
            mid_val = float(signal.metadata["forced_price"])
            logger.info("OPEN-CYCLE: Using forced price from signal metadata", 
                        pair=pair, forced_price=mid_val, original_mid=tick.mid)
        
        mid_dec = Decimal(str(mid_val))
        buy_entry_price = Price(mid_dec + entry_distance)
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
        
        # SELL_STOP: entry a mid-5pips, TP a entry-10pips
        sell_entry_price = Price(mid_dec - entry_distance)
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
        print(f"DEBUG: _open_new_cycle saving cycle {cycle.id} to repository")
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
            print(f"DEBUG: _open_new_cycle adding task to open {op.id}")
            tasks.append(self.trading_service.open_operation(request, op))
        
            print(f"DEBUG: _open_new_cycle gathering {len(tasks)} tasks")
        results = await asyncio.gather(*tasks)
        print(f"DEBUG: _open_new_cycle gather results: {[r.success for r in results]}")
        
        if any(r.success for r in results):
            for op in [op_buy, op_sell]:
                cycle.add_operation(op)
            self._active_cycles[pair] = cycle
            self.strategy.register_cycle(cycle)
            logger.info("New dual cycle opened", cycle_id=cycle.id, pair=pair)
        else:
            print(f"DEBUG: _open_new_cycle FAILED TO OPEN ANY OPERATIONS")
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
                        close_res = await self.trading_service.close_operation(op, reason="CYCLE_CLOSURE_SIGNAL")
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
        now = tick.timestamp or datetime.now()
        
        # ═══════════════════════════════════════════════════════════
        # L2 GUARD: No abrir recoveries durante eventos protegidos
        # ═══════════════════════════════════════════════════════════
        if LAYER2_MODE == "ON":
            for event in EVENT_CALENDAR:
                event_time_str = event[0]
                event_dt = datetime.fromisoformat(event_time_str) if isinstance(event_time_str, str) else event_time_str
                
                from datetime import timedelta
                pre_window = event_dt - timedelta(minutes=EVENT_PROTECTION_WINDOW_PRE)
                post_window = event_dt + timedelta(minutes=EVENT_PROTECTION_WINDOW_POST)

                if now >= pre_window and now <= post_window:
                    logger.warning("RECOVERY BLOCKED by Layer 2 Event Shield", 
                                 pair=pair, event=event[2], time=now.isoformat())
                    return

        # 0. RESOLVE LIVE PARENT (Source of Truth)
        live_parent = self._active_cycles.get(pair)
        
        parent_id_from_signal = signal.metadata.get("parent_cycle") or signal.metadata.get("cycle_id")
        parent_cycle = None
        
        if parent_id_from_signal:
            if live_parent and live_parent.id == parent_id_from_signal:
                parent_cycle = live_parent
            else:
                p_res = await self.repository.get_cycle(parent_id_from_signal)
                if p_res.success and p_res.value:
                    parent_cycle = p_res.value
        
        if not parent_cycle:
            parent_cycle = live_parent
            
        if not parent_cycle:
            logger.error("Could not resolve parent cycle for recovery", pair=pair)
            return

        # FLAT HIERARCHY
        while parent_cycle.cycle_type == CycleType.RECOVERY:
            root_id = parent_cycle.parent_cycle_id
            if not root_id: break
            p_res = await self.repository.get_cycle(root_id)
            if not p_res.success or not p_res.value: break
            parent_cycle = p_res.value

        # ═══════════════════════════════════════════════════════════
        # FIX-CASCADE-V4: Check global collision flag
        # If a collision was detected this tick, block ALL new recoveries
        # EXCEPT if this is a replacement for a failure or a reposition
        # ═══════════════════════════════════════════════════════════
        current_tick_key = now.isoformat()
        reason = signal.metadata.get("reason", "")
        is_replacement = reason in ("recovery_renewal_on_failure", "trailing_reposition", "recovery_next_stage")
        
        if not is_replacement and hasattr(self, '_collision_tick') and self._collision_tick.get(str(pair)) == current_tick_key:
            logger.warning("FIX-CASCADE-V4: Recovery blocked (collision detected this tick)",
                         pair=str(pair), tick=current_tick_key)
            return

        # ═══════════════════════════════════════════════════════════
        # CIRCUIT BREAKER: Máximo 1 recovery por TICK (excepto renovaciones críticas)
        # ═══════════════════════════════════════════════════════════
        if not is_replacement and parent_cycle.metadata.get("last_recovery_tick") == current_tick_key:
            logger.warning("CIRCUIT BREAKER: Recovery blocked (already opened this tick)", 
                         parent_id=parent_cycle.id, tick=current_tick_key)
            return
        
        parent_cycle.metadata["last_recovery_tick"] = current_tick_key


        # GUARD: Only ONE active recovery per parent cycle at a time
        # This prevents explosion of recoveries when _open_recovery_cycle is called every tick
        existing_active_recoveries = [
            op for op in parent_cycle.recovery_operations
            if op.status in (OperationStatus.PENDING, OperationStatus.ACTIVE)
        ]
        
        if existing_active_recoveries:
            logger.debug("Skipping recovery creation - parent already has active recovery ops",
                        parent_id=parent_cycle.id, count=len(existing_active_recoveries))
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
        
        # ═══════════════════════════════════════════════════════════
        # FIX-CASCADE-V2: Global tick counter to prevent recovery explosions
        # Even if timestamp is the same, we track tick index globally
        # ═══════════════════════════════════════════════════════════
        if not hasattr(self, '_last_recovery_tick_idx'):
            self._last_recovery_tick_idx = {}
        
        tick_idx = tick.metadata.get("tick_idx") if hasattr(tick, 'metadata') and tick.metadata else hash(current_tick_key)
        if self._last_recovery_tick_idx.get(str(pair)) == tick_idx:
            logger.warning("FIX-CASCADE-V2: Recovery blocked (same tick index)", 
                         parent_id=parent_cycle.id, tick_idx=tick_idx)
            return
        
        self._last_recovery_tick_idx[str(pair)] = tick_idx
        
        # ═══════════════════════════════════════════════════════════
        # FIX-CASCADE-V3: Spread validation before placing orders
        # If spread is too wide, both orders would activate immediately
        # ═══════════════════════════════════════════════════════════
        current_spread = abs(float(tick.ask) - float(tick.bid))
        spread_pips = current_spread / float(multiplier)
        
        # If spread > 2x recovery distance, both orders would overlap
        max_safe_spread = float(RECOVERY_DISTANCE_PIPS) * 2 - 5  # 35 pips for 20-pip distance
        if spread_pips > max_safe_spread:
            logger.warning("FIX-CASCADE-V3: Recovery blocked (spread too wide)",
                         spread_pips=round(spread_pips, 1),
                         max_safe=max_safe_spread,
                         parent_id=parent_cycle.id)
            return
        
        # Calcular lote dinámicamente
        acc_info = await self.trading_service.broker.get_account_info()
        balance = acc_info.value["balance"] if acc_info.success else 10000.0
        lot = self.risk_manager.calculate_lot_size(pair, balance)
        
        logger.debug("Recovery lot calculated", pair=pair, balance=balance, lot=float(lot))


        # 3. Crear ciclo de Recovery
        recovery_level = parent_cycle.recovery_level + 1
        ts_str = (tick.timestamp or datetime.now()).strftime('%H%M%S')
        import random
        recovery_id = f"REC_{tick.pair}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"
        
        recovery_cycle = Cycle(
            id=recovery_id,
            pair=tick.pair,
            cycle_type=CycleType.RECOVERY,
            status=CycleStatus.PENDING,
            parent_cycle_id=parent_cycle.id
        )
        recovery_cycle.metadata["recovery_level"] = str(recovery_level)
        recovery_cycle.metadata["source"] = signal.metadata.get("reason", "unknown")
        recovery_cycle.metadata["parent_cycle_id"] = str(parent_cycle.id) # Redundancy for forensic link
        
        # FIX: Register cycle in Strategy Engine to ensure signal generation
        self.strategy.register_cycle(recovery_cycle)
        
        await self.repository.save_cycle(recovery_cycle)
        print(f"DEBUG: Saved Recovery Cycle {recovery_cycle.id} to repo")
        
        # 4. Determinar base para precios (±20 pips)
        # Si hay reference_price, usamos ese (ej: entry de la op que bloqueó)
        # Si no, usamos el bid/ask actual (ej: para el primer recovery tras main TP)
        base_buy = Decimal(str(reference_price)) if reference_price else Decimal(str(tick.ask))
        base_sell = Decimal(str(reference_price)) if reference_price else Decimal(str(tick.bid))
        
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
        
        # 1. Cerrar operaciones propias del ciclo
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            return
            
        tasks = []
        all_ops = ops_res.value
        
        # 2. LOCALIZAR Y CERRAR SUB-CICLOS DE RECOVERY (Recursividad)
        # Buscamos todos los ciclos en el repositorio que tengan a este como padre
        # Esto soluciona las "Zombie Operations"
        # 2. LOCALIZAR Y CERRAR TODOS LOS SUB-CICLOS DE RECOVERY (Recursividad Profunda)
        # FIX-ZOMBIE-DRAIN: Usamos get_cycles_by_status para encontrar TODOS los hijos, no solo los activos.
        # Un hijo puede estar "CLOSED" (fallido) pero tener posiciones neutralizadas en el broker.
        all_child_cycles_res = await self.repository.get_all_cycles() # Get all to be safe
        if isinstance(all_child_cycles_res, list): # InMemoryRepository returns List
             all_child_cycles = all_child_cycles_res
        else: # IRepository usually returns Result[List]
             all_child_cycles = all_child_cycles_res.value if all_child_cycles_res.success else []

        child_cycles = [c for c in all_child_cycles if c.parent_cycle_id == cycle.id]
        for child in child_cycles:
            logger.info("Closing child recovery cycle (including zombies)", 
                       child_id=child.id, 
                       parent_id=cycle.id,
                       status=child.status.value)
            # Llamada recursiva para cerrar el hijo (y sus posibles nietos)
            await self._close_cycle_operations_final(child)
            
            if child.status != CycleStatus.CLOSED:
                child.status = CycleStatus.CLOSED
                child.closed_at = datetime.now()
                await self.repository.save_cycle(child)

        # 3. Cerrar operaciones del ciclo actual
        # Intentar cierres atómicos para pares Main+Hedge primero
        active_mains = [op for op in all_ops if op.is_main and op.status in (OperationStatus.ACTIVE, OperationStatus.NEUTRALIZED)]
        
        for m_op in active_mains:
            # Intentar cerrar como unidad de deuda si hay un hedge correspondiente
            logger.info("Final resolution: attempting atomic closure for Main", op_id=m_op.id)
            await self._close_debt_unit_atomic(cycle, "FINAL_CLEANUP", main_op_id=str(m_op.id))
            
        # 4. Cerrar el resto de operaciones (singleton)
        # Refrescamos las operaciones tras los cierres atómicos
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if ops_res.success:
            all_ops = ops_res.value
            
        for op in all_ops:
            # FIX-ZOMBIE-DRAIN: Include CLOSED + TP_HIT in cleanup if ticket exists. 
            # If op has a ticket, it MUST be closed in the broker to vanish from the account.
            if op.broker_ticket and op.status != OperationStatus.CANCELLED:
                logger.info("Cleaning up terminal resolution position", 
                           op_id=op.id, status=op.status.value, ticket=op.broker_ticket)
                
                if op.status == OperationStatus.PENDING:
                    tasks.append(self.trading_service.broker.cancel_order(op.broker_ticket))
                    op.status = OperationStatus.CANCELLED
                else:
                    # ACTIVE, NEUTRALIZED, TP_HIT, or even CLOSED (if it's a zombie)
                    tasks.append(self.trading_service.close_operation(op, reason="cycle_final_resolution"))
                
                op.metadata["close_reason"] = "cycle_final_resolution"
                # State update and save will happen inside close_operation or when tasks are gathered
        
        if tasks:
            await asyncio.gather(*tasks)
            logger.info(f"Closed {len(tasks)} active positions in broker for cycle {cycle.id}")

    async def _handle_recovery_failure(self, failed_cycle: Cycle, blocking_op: Operation, tick: TickData):
        """
        Maneja el fallo de un ciclo recovery (ambas órdenes activadas).
        
        1. Identifica el ciclo principal (padre).
        2. Añade unidad de deuda de 40 pips al padre.
        3. Abre nuevo recovery a ±20 pips del entry de la operación que causó el bloqueo.
        """
        # FLAT HIERARCHY: Always attach to the root MAIN cycle
        root_cycle_id = failed_cycle.parent_cycle_id
        if not root_cycle_id:
            logger.error("Failed recovery cycle has no parent", recovery_id=failed_cycle.id)
            return

        # Fetch parent
        parent_res = await self.repository.get_cycle(root_cycle_id)
        if not parent_res.success or not parent_res.value:
            logger.error("Could not find parent cycle for failed recovery", parent_id=root_cycle_id)
            return
            
        parent_cycle = parent_res.value
        
        # If the parent is ANOTHER recovery, climb up to find the root MAIN
        while parent_cycle.cycle_type == CycleType.RECOVERY:
            logger.debug("Climbing hierarchy to find root MAIN", current_id=parent_cycle.id)
            next_parent_id = parent_cycle.parent_cycle_id
            if not next_parent_id: break
            
            p_res = await self.repository.get_cycle(next_parent_id)
            if not p_res.success or not p_res.value: break
            parent_cycle = p_res.value
        
        # 1. Registrar unidad de deuda con PIPS REALES (distancia entre entradas)
        real_loss = 40.0 # Default
        failed_ops_res = await self.repository.get_operations_by_cycle(failed_cycle.id)
        if failed_ops_res.success:
            active_ops = [op for op in failed_ops_res.value if op.status == OperationStatus.ACTIVE]
            if len(active_ops) >= 2:
                buy_op = next((op for op in active_ops if op.is_buy), None)
                sell_op = next((op for op in active_ops if op.is_sell), None)
                if buy_op and sell_op:
                    # Calcular distancia real entre entradas
                    buy_entry = buy_op.actual_entry_price or buy_op.entry_price
                    sell_entry = sell_op.actual_entry_price or sell_op.entry_price
                    multiplier = 100 if "JPY" in str(parent_cycle.pair) else 10000
                    real_loss = abs(float(buy_entry) - float(sell_entry)) * multiplier
        
        # DYNAMIC DEBT: Pass real pips to accounting
        parent_cycle.accounting.add_recovery_failure_unit(real_loss)
        
        # PHASE 4: Shadow tracking with REAL calculated value
        if failed_ops_res.success:
            active_ops = [op for op in failed_ops_res.value if op.status == OperationStatus.ACTIVE]
            if len(active_ops) >= 2:
                buy_op = next((op for op in active_ops if op.is_buy), None)
                sell_op = next((op for op in active_ops if op.is_sell), None)
                if buy_op and sell_op:
                    from decimal import Decimal
                    from wsplumber.domain.entities.debt import DebtUnit
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
        
        logger.info(f"Added {real_loss:.1f} pips debt unit due to recovery failure", 
                   parent_id=parent_cycle.id, failed_id=failed_cycle.id)
        await self.repository.save_cycle(parent_cycle)
        
        # ═══════════════════════════════════════════════════════════════════════
        # FIX-RECOVERY-BLOCK: Eliminar TPs y marcar NEUTRALIZED
        # ═══════════════════════════════════════════════════════════════════════
        if failed_ops_res.success:
            active_ops = [op for op in failed_ops_res.value if op.status == OperationStatus.ACTIVE]
            for op in active_ops:
                logger.info("FIX-RECOVERY-BLOCK: Neutralizing blocked recovery operation",
                           op_id=op.id, ticket=op.broker_ticket)
                
                # 1. Eliminar TP del broker para evitar cierre automático
                if op.broker_ticket:
                    try:
                        # FIX: Use modify_position for ACTIVE/NEUTRALIZED positions
                        await self.trading_service.broker.modify_position(
                            op.broker_ticket, 
                            new_tp=None
                        )
                        logger.info("Removed TP from blocked recovery", op_id=op.id)
                    except Exception as e:
                        logger.warning("Could not remove TP from blocked recovery", 
                                      op_id=op.id, error=str(e))
                    
                    # 2. Actualizar status en broker
                    try:
                        await self.trading_service.broker.update_position_status(
                            op.broker_ticket, 
                            OperationStatus.NEUTRALIZED
                        )
                    except Exception as e:
                        logger.warning("Could not update broker position status",
                                      op_id=op.id, error=str(e))
                
                # 3. Marcar como NEUTRALIZED en el repositorio
                op.status = OperationStatus.NEUTRALIZED
                op.metadata["neutralized_reason"] = "recovery_block"
                op.metadata["neutralized_at_tick"] = tick.timestamp.isoformat() if tick.timestamp else None
                await self.repository.save_operation(op)
        
        # ═══════════════════════════════════════════════════════════════════════
        # FIX-CASCADE-V5: Use CURRENT price for new recovery (not old entry)
        # This prevents the new recovery from immediately colliding again
        # ═══════════════════════════════════════════════════════════════════════
        mid_price = (tick.bid + tick.ask) / 2
        reference_price = Price(mid_price)
        logger.info("FIX-CASCADE-V5: Using current price for new recovery",
                   old_entry=float(blocking_op.actual_entry_price or blocking_op.entry_price),
                   current_price=float(mid_price))
        
        signal = StrategySignal(
            signal_type=SignalType.OPEN_CYCLE,
            pair=parent_cycle.pair,
            metadata={"reason": "recovery_renewal_on_failure", "parent_cycle": parent_cycle.id}
        )
        
        await self._open_recovery_cycle(signal, tick, reference_price=reference_price)

        # ═══════════════════════════════════════════════════════════════════════
        # FIX-CASCADE-V5: Do NOT mark cycle as CLOSED
        # The NEUTRALIZED positions must stay for FIFO liquidation when a future
        # recovery hits TP. Closing now would orphan them as zombies.
        # ═══════════════════════════════════════════════════════════════════════
        failed_cycle.metadata["collision_detected"] = True
        failed_cycle.metadata["waiting_for_fifo"] = True
        await self.repository.save_cycle(failed_cycle)
        logger.info("FIX-CASCADE-V5: Cycle kept active for FIFO, NOT marked CLOSED", 
                   cycle_id=failed_cycle.id)

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

    async def _process_layer1_trailing(self, op: Operation, tick: TickData, cycle: Cycle) -> bool:
        """
        LAYER 1: Adaptive Trailing Stop for Recovery Operations.
        
        Tracks maximum profit reached and applies progressive trailing stops
        to capture partial profits instead of letting them evaporate.
        
        Returns True if position was closed by trailing stop.
        """
        try:
            # DEBUG: Log every call to trace flow
            logger.info("LAYER1-DEBUG: Entry",
                       op_id=op.id,
                       op_status=op.status.value,
                       has_tp=op.tp_price is not None,
                       is_recovery=op.is_recovery)
            
            # Skip if already in a terminal state
            if op.status in (OperationStatus.CLOSED, OperationStatus.TP_HIT, OperationStatus.CANCELLED):
                logger.info("LAYER1-DEBUG: Skip (terminal status)", op_id=op.id, status=op.status.value)
                return False
            
            # Skip if TP was removed (neutralized collision)
            if op.tp_price is None:
                logger.info("LAYER1-DEBUG: Skip (no TP)", op_id=op.id)
                return False
            
            # 1. Calculate current floating pips using correct BID/ASK
            multiplier = 100 if "JPY" in str(op.pair) else 10000
            entry = float(op.actual_entry_price or op.entry_price)
            
            if op.is_buy:
                current_price = float(tick.bid)
                floating_pips = (current_price - entry) * multiplier
            else:
                current_price = float(tick.ask)
                floating_pips = (entry - current_price) * multiplier
            
            # 2. Track maximum profit reached
            max_profit = op.metadata.get("max_profit_pips", 0.0)
            prev_max = max_profit
            
            if floating_pips > max_profit:
                op.metadata["max_profit_pips"] = floating_pips
                max_profit = floating_pips
                await self.repository.save_operation(op)
                
                # Log significant profit milestones (every 10 pips)
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
            
            # 5. Check if we hit the trailing stop
            if trailing_stop > 0:
                # Update trailing metadata if level changed
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

                # Check if price hit trailing stop
                if floating_pips <= trailing_stop:
                    # Ensure minimum profit threshold (extra safety)
                    if floating_pips < TRAILING_MIN_LOCK:
                        return False

                    logger.info("LAYER1-TRAILING: TRAILING STOP HIT",
                               op_id=op.id,
                               pips=round(floating_pips, 1),
                               stop=trailing_stop,
                               level=active_level)
                    
                    close_res = await self.trading_service.close_operation(op, reason="TRAILING_STOP_HIT")
                    if close_res.success:
                        from decimal import Decimal
                        close_price = Price(Decimal(str(current_price)))
                        
                        # Mark as trailing-closed for proper handling
                        op.metadata["trailing_closed"] = True
                        op.metadata["trailing_profit_pips"] = floating_pips
                        # Note: close_v2 and save are already handled by close_operation, 
                        # but we re-save to capture our extra metadata
                        await self.repository.save_operation(op)
                        
                        logger.info("LAYER1-TRAILING: Position closed successfully",
                                   op_id=op.id,
                                   final_pips=round(floating_pips, 1))
                        
                        # Trigger partial debt reduction based on captured profit
                        await self._handle_trailing_profit(op, tick)
                        
                        return True
                    else:
                        logger.error(f"LAYER1-TRAILING: Failed to close position op={op.id} error={close_res.error}")
            
            return False
            
        except Exception as e:
            logger.error("LAYER1-TRAILING: Exception in trailing processing",
                        op_id=op.id,
                        _exception=e)
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # LAYER 2: EVENT GUARD IMPLEMENTATION
    # ═══════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════
    # IMMUNE SYSTEM METHODS (PHASE 5)
    # ═══════════════════════════════════════════════════════════════════════

    async def _check_immune_system(self, pair: CurrencyPair, tick: TickData) -> bool:
        """
        Verifica Layer 2 (Eventos) y Layer 3 (Gaps Ciegos).
        Retorna True si el procesamiento puede continuar, False si está congelado.
        """
        from wsplumber.core.strategy._params import (
            LAYER2_MODE, EVENT_CALENDAR, EVENT_PROTECTION_WINDOW_PRE, EVENT_PROTECTION_WINDOW_POST,
            LAYER3_MODE, GAP_FREEZE_THRESHOLD_PIPS, GAP_CALM_DURATION_MINUTES, GAP_CALM_THRESHOLD_PIPS
        )
        
        now = tick.timestamp or datetime.now()
        mid_price = float(tick.bid + tick.ask) / 2.0
        multiplier = 0.01 if "JPY" in str(pair) else 0.0001
        
        # ═══════════════════════════════════════════════════════════
        # 1. LAYER 3: BLIND GAP & DYNAMIC UNFREEZE (Quiet Period)
        # ═══════════════════════════════════════════════════════════
        allowed_v3 = True
        if LAYER3_MODE == "ON":
            last_price = self._last_prices.get(pair)
            
            if last_price:
                jump_pips = abs(mid_price - last_price) / multiplier
                
                # Caso Alpha: El mercado está saltando FUERTE (> 50 pips) -> Iniciamos Freeze
                if jump_pips >= GAP_FREEZE_THRESHOLD_PIPS:
                    logger.warning("BLIND GAP DETECTED! Triggering freeze", pair=pair, pips=jump_pips)
                    self._calm_since[pair] = now
                
                # Caso Beta: Estamos congelados y ocurre inestabilidad -> Reset de Calma
                elif pair in self._calm_since and jump_pips >= GAP_CALM_THRESHOLD_PIPS:
                    logger.info("SECURITY RESET: Instability detected during freeze", pair=pair)
                    self._calm_since[pair] = now

            self._last_prices[pair] = mid_price

            if pair in self._calm_since:
                calm_duration = now - self._calm_since[pair]
                if calm_duration >= timedelta(minutes=GAP_CALM_DURATION_MINUTES):
                    logger.info("DYNAMIC UNFREEZE: Market stabilized", pair=pair)
                    del self._calm_since[pair]
                else:
                    return False, True

        # ═══════════════════════════════════════════════════════════
        # 2. LAYER 2: EVENT GUARD (Scheduled)
        # ═══════════════════════════════════════════════════════════
        if LAYER2_MODE == "ON":
            event = self.calendar.is_near_critical_event(now, window_minutes=EVENT_PROTECTION_WINDOW_PRE)
            
            if event:
                event_key = f"{pair}_{event.timestamp.isoformat()}"
                if getattr(self, "_active_shield_event", None) != event_key:
                    logger.info("Scheduled event active, applying shield", event=event.description)
                    await self._apply_event_shield(pair, tick)
                    self._active_shield_event = event_key
                return False, False
            
            if hasattr(self, "_active_shield_event"):
                logger.info("Event window closed, normalizing system", pair=pair)
                await self._normalize_post_event(pair, tick)
                delattr(self, "_active_shield_event")

        # DEBUG PRINT
        event_status = self.calendar.is_near_critical_event(now, window_minutes=EVENT_PROTECTION_WINDOW_PRE) if LAYER2_MODE == "ON" else None
        print(f"DEBUG: Tick #{getattr(tick, 'index', '?')} | {tick.timestamp} | {tick.mid} | Allowed={not bool(event_status)}")
        
        return True, False

    # ═══════════════════════════════════════════════════════════════════════
    # LAYER 2: EVENT GUARD LOGIC (REFACTORED - HEDGE AWARE)
    # ═══════════════════════════════════════════════════════════════════════

    def _calculate_floating_pips(self, op: Operation, tick: TickData) -> float:
        """Calcula el beneficio/pérdida actual en pips."""
        multiplier = 100 if "JPY" in str(op.pair) else 10000
        entry = float(op.actual_entry_price or op.entry_price)
        current = float(tick.bid if op.is_buy else tick.ask)
        return (current - entry) * multiplier if op.is_buy else (entry - current) * multiplier

    async def _apply_event_shield(self, pair: CurrencyPair, tick: TickData):
        """
        EVENT-GUARD V3.1: Protección Estratégica ante Noticias.
        - BENEFICIO: Break Even (BE) + Cancelar opuesta.
        - PÉRDIDA (Bloqueo): Quitar TPs y deshabilitar Hedges de continuación.
        - PREVENTIVO: Cancelar Stop-Orders no activadas.
        """
        active_res = await self.repository.get_active_operations(pair)
        active_ops = active_res.value if active_res.success else []
        
        pending_res = await self.repository.get_pending_operations(pair)
        pending_ops = pending_res.value if pending_res.success else []

        # 1. ESCENARIO PREVENTIVO: Cancelar órdenes STOP que no han entrado
        # Excepción: Si ya hay un bloqueo (Lock) parcial, no queremos romperlo, pero el sistema 
        # prefiere cancelar órdenes ciegas para evitar activaciones con slippage.
        if not active_ops and pending_ops:
            logger.info("EVENT-GUARD: No active positions, cleaning pending orders", pair=pair)
            for op in pending_ops:
                if op.broker_ticket and op.status == OperationStatus.PENDING:
                    await self.trading_service.broker.cancel_order(op.broker_ticket)
                    op.status = OperationStatus.CANCELLED
                    op.metadata["cancel_reason"] = "event_shield_preventive"
                    await self.repository.save_operation(op)
            return

        # 2. ESCENARIO CON POSICIONES ACTIVAS
        # Agrupamos por ciclo para evaluar bloqueos
        cycles_id = list(set([op.cycle_id for op in active_ops]))
        
        for cycle_id in cycles_id:
            cycle_res = await self.repository.get_cycle(cycle_id)
            if not cycle_res.success: continue
            cycle = cycle_res.value
            
            ops_in_cycle = [op for op in active_ops if op.cycle_id == cycle_id]
            pending_in_cycle = [op for op in pending_ops if op.cycle_id == cycle_id]
            
            # CASO A: UNA SOLA POSICIÓN ACTIVA (Buscando Beneficio/BE)
            if len(ops_in_cycle) == 1:
                op = ops_in_cycle[0]
                floating_pips = self._calculate_floating_pips(op, tick)
                
                if floating_pips >= 0:
                    # Aplicar BE (impacto rápido o proactivo)
                    multiplier = 0.01 if "JPY" in str(pair) else 0.0001
                    be_price = float(op.actual_entry_price or op.entry_price) + (BE_BUFFER_PIPS * multiplier if op.is_buy else -BE_BUFFER_PIPS * multiplier)
                    
                    if not op.metadata.get("shield_be_activated"):
                        logger.info("EVENT-GUARD: Position in profit, applying BE", op_id=op.id, be=be_price)
                        await self.trading_service.broker.modify_position(op.broker_ticket, new_sl=Price(Decimal(str(be_price))))
                        op.sl_price = Price(Decimal(str(be_price)))
                        op.metadata["shield_be_activated"] = True
                        await self.repository.save_operation(op)
                    
                    # Cancelar la contraparte pendiente (Main opuesta o Recovery opuesto)
                    for p_op in pending_in_cycle:
                        if p_op.status == OperationStatus.PENDING:
                            logger.info("EVENT-GUARD: profit secured, cancelling counter-order", op_id=p_op.id)
                            await self.trading_service.broker.cancel_order(p_op.broker_ticket)
                            p_op.status = OperationStatus.CANCELLED
                            p_op.metadata["cancel_reason"] = "event_shield_profit_secured"
                            await self.repository.save_operation(p_op)
                else:
                    # CASO PÉRDIDA: Escudo de Bloqueo
                    if op.tp_price is not None:
                        logger.info("EVENT-GUARD: Position in loss, removing TP", op_id=op.id)
                        await self.trading_service.broker.modify_position(op.broker_ticket, new_tp=None)
                        op.tp_price = None
                        op.metadata["shield_tp_stripped"] = True
                        await self.repository.save_operation(op)
                        
                    # Deshabilitar Hedges (Meta) para evitar que entren nuevos durante la noticia
                    op.metadata["continuation_hedge_disabled"] = True
                    await self.repository.save_operation(op)
                    
                    # NOTA: La contraparte PENDING se MANTIENE para actuar como LOCK si el mercado sigue en contra.

            # CASO B: AMBAS ACTIVAS (Bloqueo/Lock)
            elif len(ops_in_cycle) >= 2:
                logger.info("EVENT-GUARD: Locked cycle detected, stripping triggers", cycle_id=cycle.id)
                
                # Quitar TPs para evitar cierres asimétricos durante la noticia
                for op in ops_in_cycle:
                    if op.tp_price is not None:
                        logger.info("EVENT-GUARD: Removing TP from locked op", op_id=op.id)
                        await self.trading_service.broker.modify_position(op.broker_ticket, new_tp=None)
                        op.tp_price = None
                        op.metadata["shield_tp_stripped"] = True
                        await self.repository.save_operation(op)
                
                # Si es un MAIN, quitar los HEDGES de continuación que estuvieran PENDING
                # Si es un RECOVERY bloqueado, quitar TPs.
                for p_op in pending_in_cycle:
                    if p_op.op_type in [OperationType.HEDGE_BUY, OperationType.HEDGE_SELL] or p_op.is_recovery:
                        logger.info("EVENT-GUARD: Removing continuation hedge/recovery during event", op_id=p_op.id)
                        await self.trading_service.broker.cancel_order(p_op.broker_ticket)
                        p_op.status = OperationStatus.CANCELLED
                        p_op.metadata["cancel_reason"] = "event_shield_lock_stripping"
                        await self.repository.save_operation(p_op)

            # Marcar ciclo como afectado por el escudo
            cycle.metadata["event_shield_activated"] = True
            await self.repository.save_cycle(cycle)

    async def _normalize_post_event(self, pair: CurrencyPair, tick: TickData):
        """
        Normalización Post-Noticia:
        - Reactiva ciclos que se perdieron o quedaron bloqueados.
        - Abre nuevas oportunidades en el PRECIO ACTUAL.
        """
        logger.info("EVENT-GUARD: Entering post-event normalization", pair=pair)
        
        # 0. Sincronizar primero para detectar cierres ocurridos durante el bloqueo (BE/TP)
        await self.trading_service.sync_all_active_positions(pair)
        
        active_cycles_res = await self.repository.get_active_cycles(pair)
        if not active_cycles_res.success: return

        for cycle in active_cycles_res.value:
            if not cycle.metadata.get("event_shield_activated"): continue
            
            ops_res = await self.repository.get_operations_by_cycle(cycle.id)
            all_ops = ops_res.value if ops_res.success else []
            active_ops = [op for op in all_ops if op.status == OperationStatus.ACTIVE]
            pending_ops = [op for op in all_ops if op.status == OperationStatus.PENDING]

            # 1. SI NO QUEDA NADA (Se cerró por BE o TP durante el evento)
            if not active_ops and not pending_ops:
                if cycle.cycle_type == CycleType.MAIN:
                    logger.info("EVENT-GUARD: Main resolved during news, opening new cycle padre", cycle_id=cycle.id)
                    signal = StrategySignal(
                        signal_type=SignalType.OPEN_CYCLE,
                        pair=pair,
                        metadata={"reason": "post_event_renewal", "forced_price": float(tick.mid)}
                    )
                    await self._open_new_cycle(signal, tick)
                    
                    cycle.status = CycleStatus.CLOSED
                    cycle.metadata["closed_reason"] = "resolved_during_event"
                    await self.repository.save_cycle(cycle)
            
            # 2. SI HAY UN LOCK (Ambas activas)
            elif len(active_ops) >= 2:
                # El bloqueo se mantiene. Marcamos como NEUTRALIZED para congelar P&L (Flow 4 manual)
                logger.info("EVENT-GUARD: Lock detected post-event, neutralizing and triggering recovery", cycle_id=cycle.id)
                
                for op in active_ops:
                    op.status = OperationStatus.NEUTRALIZED
                    op.tp_price = None # Asegurar que no tienen TP (Vigilancia Activa)
                    await self.repository.save_operation(op)
                    await self.trading_service.broker.update_position_status(op.broker_ticket, OperationStatus.NEUTRALIZED)
                    await self.trading_service.broker.modify_position(op.broker_ticket, new_tp=None)

                # Si es MAIN y está bloqueado, necesita Recovery
                if cycle.cycle_type == CycleType.MAIN:
                    cycle.status = CycleStatus.HEDGED
                    await self.repository.save_cycle(cycle)
                    
                    # Disparar Recovery desde el precio actual
                    signal = StrategySignal(
                        signal_type=SignalType.OPEN_RECOVERY,
                        pair=pair,
                        metadata={"parent_cycle": cycle.id, "reason": "post_event_lock_recovery"}
                    )
                    await self._open_recovery_cycle(signal, tick)
                
                # Si es RECOVERY y está bloqueado, lanza el siguiente nivel
                elif cycle.is_recovery:
                    cycle.status = CycleStatus.IN_RECOVERY
                    await self.repository.save_cycle(cycle)
                    
                    signal = StrategySignal(
                        signal_type=SignalType.OPEN_RECOVERY,
                        pair=pair,
                        metadata={"parent_cycle": cycle.parent_cycle_id, "reason": "post_event_recovery_cascade"}
                    )
                    await self._open_recovery_cycle(signal, tick)

            # 3. SI QUEDA UNA SOLA POSICIÓN (Sincronización de Cobertura)
            elif len(active_ops) == 1:
                op = active_ops[0]
                # Si no hay orden pendiente, el escudo canceló la contraparte por seguridad/profit.
                # Debemos reabrirla para que el ciclo no quede desprotegido.
                if not pending_ops:
                    # Restaurar protección usando el mismo ciclo para evitar bloqueos
                    await self._restore_cycle_protection(cycle, op, tick)
                    
                    # 3.2 RESTAURAR TP (Solo ahora que tenemos protección de nuevo)
                    if op.metadata.get("shield_tp_stripped"):
                        multiplier = Decimal("0.01") if "JPY" in str(op.pair) else Decimal("0.0001")
                        tp_pips = MAIN_TP_PIPS if cycle.cycle_type == CycleType.MAIN else RECOVERY_TP_PIPS
                        dist = Decimal(str(tp_pips)) * multiplier
                        entry = Decimal(str(op.actual_entry_price or op.entry_price))
                        new_tp = Price(entry + dist) if op.is_buy else Price(entry - dist)
                        
                        logger.info("EVENT-GUARD: Restoring stripped TP for single position", op_id=op.id, tp=float(new_tp))
                        await self.trading_service.broker.modify_position(op.broker_ticket, new_tp=new_tp)
                        op.tp_price = new_tp
                        op.metadata["shield_tp_stripped"] = False
                        await self.repository.save_operation(op)

            # Limpiar marcas
            cycle.metadata["event_shield_activated"] = False
            await self.repository.save_cycle(cycle)

    async def _restore_cycle_protection(self, cycle: Cycle, op: Operation, tick: TickData):
        """Restablece la orden de protección cancelada por el escudo en el precio actual."""
        pair = cycle.pair
        lot = op.lot_size
        
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        
        if cycle.cycle_type == CycleType.MAIN:
            dist_pips = MAIN_DISTANCE_PIPS
            tp_pips = MAIN_TP_PIPS
        else:
            dist_pips = RECOVERY_DISTANCE_PIPS
            tp_pips = RECOVERY_TP_PIPS
            
        entry_distance = Decimal(str(dist_pips)) * multiplier
        tp_distance = Decimal(str(tp_pips)) * multiplier
        
        mid_dec = Decimal(str(tick.mid))
        is_buy_new = not op.is_buy # Si tenemos Buy activa, necesitamos Sell Stop (y viceversa)
        
        if is_buy_new:
            # Necesitamos un Buy Stop arriba
            entry_price = Price(mid_dec + entry_distance)
            tp_price = Price(entry_price + tp_distance)
            op_type = OperationType.MAIN_BUY if cycle.cycle_type == CycleType.MAIN else OperationType.RECOVERY_BUY
        else:
            # Necesitamos un Sell Stop abajo
            entry_price = Price(mid_dec - entry_distance)
            tp_price = Price(entry_price - tp_distance)
            op_type = OperationType.MAIN_SELL if cycle.cycle_type == CycleType.MAIN else OperationType.RECOVERY_SELL
            
        new_op = Operation(
            id=OperationId(f"{cycle.id}_RST_{'B' if is_buy_new else 'S'}_{random.randint(10,99)}"),
            cycle_id=cycle.id,
            pair=pair,
            op_type=op_type,
            status=OperationStatus.PENDING,
            entry_price=entry_price,
            tp_price=tp_price,
            lot_size=lot
        )
        
        logger.info("Restoring counter-order post-event", 
                    cycle_id=cycle.id, op_id=new_op.id, entry=float(entry_price))
        
        # Guardar primero
        await self.repository.save_operation(new_op)
        
        request = OrderRequest(
            operation_id=new_op.id,
            pair=pair,
            order_type=new_op.op_type,
            entry_price=new_op.entry_price,
            tp_price=new_op.tp_price,
            lot_size=new_op.lot_size
        )
        
        result = await self.trading_service.open_operation(request, new_op)
        if result.success:
            cycle.add_operation(new_op)
            await self.repository.save_cycle(cycle)
