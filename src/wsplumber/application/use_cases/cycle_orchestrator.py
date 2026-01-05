# src/wsplumber/application/use_cases/cycle_orchestrator.py
"""
Orquestador de Ciclos.

El corazón del sistema. Procesa ticks de mercado, consulta a la estrategia,
valida con el gestor de riesgo y ejecuta a través del TradingService.
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
    OperationStatus,
    OperationType,
    OrderRequest,
    Pips,
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

        # 2. Bucle principal (ejemplo simplificado)
        # En una implementación real, esto podría ser por eventos o polling rápido
        while self._running:
            for pair in pairs:
                await self._process_tick_for_pair(pair)
            
            # Pequeña pausa para no saturar CPU en este ejemplo
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
                # Tomamos el último ciclo activo (debería haber solo uno por par en el diseño actual)
                self._active_cycles[pair] = res.value[0]
                logger.info("Loaded active cycle", pair=pair, cycle_id=self._active_cycles[pair].id)

    async def process_tick(self, tick: TickData):
        """Procesa un tick inyectado directamente (útil para backtesting)."""
        pair = tick.pair
        try:
            # 1. Monitorear estado de operaciones activas (detección de activación y TP)
            await self._check_operations_status(pair, tick)

            # 2. Consultar a la estrategia core (Secreto)
            signal: StrategySignal = self.strategy.process_tick(
                pair=tick.pair,
                bid=float(tick.bid),
                ask=float(tick.ask),
                timestamp=tick.timestamp
            )
            
            # Solo para debug
            current_cycle = self._active_cycles.get(pair)
            if current_cycle:
                logger.debug("Cycle status checked", cycle_id=current_cycle.id, status=current_cycle.status, signal=signal.signal_type)

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
        Detecta cierres de operaciones y notifica a la estrategia.
        """
        # Sincronizar con el broker
        sync_res = await self.trading_service.sync_all_active_positions(pair)
        if not sync_res.success:
            return

        # Si hubo cambios o simplemente para asegurar consistencia,
        # consultamos las operaciones activas en el REPO antes y después.
        # Una implementación más robusta compararía snapshots.
        
        # Obtenemos el ciclo activo para este par
        cycle = self._active_cycles.get(pair)
        if not cycle:
            return

        # Buscamos operaciones que estaban activas en el ciclo pero ya no lo están
        # (Esto es una simplificación; en prod usaríamos eventos o historial)
        ops_res = await self.repository.get_operations_by_cycle(cycle.id)
        if not ops_res.success:
            return

        for op in ops_res.value:
            # 1. Manejo de ACTIVACIÓN de órdenes
            if op.status == OperationStatus.ACTIVE:
                # Si es la primera activación de un ciclo PENDING, pasar a ACTIVE
                if cycle.status == CycleStatus.PENDING:
                    logger.info("First operation activated, transitioning cycle to ACTIVE", cycle_id=cycle.id)
                    cycle.status = CycleStatus.ACTIVE
                    await self.repository.save_cycle(cycle)

                # Verificar si ambas principales se activaron para pasar a HEDGED
                main_ops = [o for o in ops_res.value if o.is_main]
                active_main_ops = [o for o in main_ops if o.status == OperationStatus.ACTIVE]
                
                if len(active_main_ops) >= 2 and cycle.status == CycleStatus.ACTIVE:
                    logger.info("Both main operations active, transitioning cycle to HEDGED", cycle_id=cycle.id)
                    cycle.activate_hedge()
                    
                    # ABRIR OPERACIONES DE HEDGE REALES Y NEUTRALIZAR MAINS
                    hedge_tasks = []
                    for main_op in main_ops:
                        hedge_type = OperationType.HEDGE_SELL if main_op.op_type == OperationType.MAIN_BUY else OperationType.HEDGE_BUY
                        hedge_id = f"{cycle.id}_H_{main_op.op_type.value}"
                        
                        hedge_op = Operation(
                            id=hedge_id,
                            cycle_id=cycle.id,
                            pair=pair,
                            op_type=hedge_type,
                            status=OperationStatus.PENDING,
                            entry_price=main_op.entry_price, # Precio ideal para hedge
                            lot_size=main_op.lot_size
                        )
                        cycle.add_operation(hedge_op)
                        
                        # Neutralizar la principal inmediatamente vinculándola al hedge
                        main_op.neutralize(hedge_id)
                        await self.repository.save_operation(main_op)
                        
                        request = OrderRequest(
                            operation_id=hedge_op.id,
                            pair=pair,
                            order_type=hedge_type,
                            entry_price=hedge_op.entry_price,
                            lot_size=hedge_op.lot_size
                        )
                        hedge_tasks.append(self.trading_service.open_operation(request, hedge_op))
                    
                    if hedge_tasks:
                        await asyncio.gather(*hedge_tasks)

                    await self.repository.save_cycle(cycle)
            
            # 2. Manejo de CIERRE de órdenes (TP Hit)
            if op.status == OperationStatus.TP_HIT or op.status == OperationStatus.CLOSED:
                # Si el ciclo estaba PENDING, activarlo (aunque ya esté cerrándose una orden)
                if cycle.status == CycleStatus.PENDING:
                    logger.info("Operation closed while PENDING, activating cycle", cycle_id=cycle.id)
                    cycle.status = CycleStatus.ACTIVE
                    await self.repository.save_cycle(cycle)

                # Notificar a la estrategia
                logger.info("Notifying strategy about operation closure", op_id=op.id, ticket=op.broker_ticket)
                signal = self.strategy.process_tp_hit(
                    operation_id=op.id,
                    profit_pips=float(op.profit_pips or 0),
                    timestamp=datetime.now()
                )
                
                # Si una principal toca TP, cancelar la contraria pendiente (Escenario 1)
                if op.is_main:
                    for other_op in ops_res.value:
                        if other_op.is_main and other_op.status == OperationStatus.PENDING:
                            logger.info("Cancelling counter-order", op_id=other_op.id, cycle_id=cycle.id)
                            if other_op.broker_ticket:
                                await self.trading_service.broker.cancel_order(other_op.broker_ticket)
                            other_op.status = OperationStatus.CANCELLED
                            await self.repository.save_operation(other_op)

                if signal.signal_type != SignalType.NO_ACTION:
                    # Sobrescribir el pair de la señal si viene vacío
                    if not signal.pair:
                        signal.pair = pair
                    await self._handle_signal(signal, tick)

    async def _handle_signal(self, signal: StrategySignal, tick: TickData):
        """Maneja las señales emitidas por la estrategia."""
        logger.info("Signal received", type=signal.signal_type, pair=signal.pair)

        if signal.signal_type == SignalType.OPEN_CYCLE:
            await self._open_new_cycle(signal, tick)
        
        elif signal.signal_type == SignalType.CLOSE_OPERATIONS:
            await self._close_cycle_operations(signal)
        
        elif signal.signal_type == SignalType.OPEN_RECOVERY:
            await self._open_recovery_cycle(signal, tick)
            
        # Manejo de renovación automática (Fase 2)
        # Cuando una main toca TP, se renueva el ciclo

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
            logger.warning("Risk manager denied cycle opening", reason=can_open.error, exposure=exposure_pct)
            return

        # 2. Validar que no haya ya un ciclo activo para este par
        if pair in self._active_cycles and self._active_cycles[pair].status.name not in ["CLOSED", "PAUSED"]:
            logger.debug("Skipping OPEN_CYCLE: Already active/pending", pair=pair)
            return

        # 3. Calcular lote
        lot = self.risk_manager.calculate_lot_size(pair, balance)

        # 4. Crear Entidad Ciclo
        # Usamos un ID con sufijo aleatorio para evitar colisiones en renovaciones rápidas
        import random
        suffix = random.randint(100, 999)
        cycle_id = f"CYC_{pair}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{suffix}"

        cycle = Cycle(id=cycle_id, pair=pair, status=CycleStatus.PENDING)
        self._active_cycles[pair] = cycle # Guardar en caché local
        
        # 4. Crear Operaciones Duales (Buy y Sell)
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        tp_distance = Decimal(str(MAIN_TP_PIPS)) * multiplier
        
        # Operación BUY
        op_buy = Operation(
            id=f"{cycle_id}_B",
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_BUY,
            status=OperationStatus.PENDING,
            entry_price=tick.ask,
            tp_price=tick.ask + tp_distance,
            lot_size=lot
        )
        
        # Operación SELL
        op_sell = Operation(
            id=f"{cycle_id}_S",
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_SELL,
            status=OperationStatus.PENDING,
            entry_price=tick.bid,
            tp_price=tick.bid - tp_distance,
            lot_size=lot
        )

        # 5. Guardar Ciclo en DB
        await self.repository.save_cycle(cycle)
        
        # 6. Ejecutar aperturas
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

        # En una implementación real, iteraríamos por las operaciones del ciclo
        # que están activas en el repositorio.
        ops_res = await self.repository.get_active_operations(pair)
        if ops_res.success:
            for op in ops_res.value:
                if op.cycle_id == cycle.id:
                    await self.trading_service.close_operation(op)
        
        # Actualizar estado del ciclo
        cycle.status = CycleStatus.CLOSED
        await self.repository.save_cycle(cycle)
        del self._active_cycles[pair]
        logger.info("Cycle closed", cycle_id=cycle.id)

    # ============================================
    # FASE 2: RENOVACIÓN Y RECOVERY
    # ============================================

    async def _renew_cycle(self, pair: CurrencyPair, tick: TickData):
        """
        Renueva el ciclo principal inmediatamente después de un TP.
        
        Según el Documento Madre (línea 115):
        'Cuando un ciclo principal toca TP, inmediatamente se abre otro nuevo'
        """
        logger.info("Renewing cycle after TP", pair=pair)
        
        # Crear señal de apertura y delegar
        signal = StrategySignal(
            signal_type=SignalType.OPEN_CYCLE,
            pair=pair,
            metadata={"reason": "auto_renewal"}
        )
        await self._open_new_cycle(signal, tick)

    async def _open_recovery_cycle(self, signal: StrategySignal, tick: TickData):
        """
        Abre un ciclo de Recovery para recuperar pérdidas neutralizadas.
        
        Según el Documento Madre (líneas 156-166):
        - TP a 80 pips
        - Posicionamiento a 20 pips del precio actual
        - Separación de 40 pips entre niveles
        """
        pair = signal.pair
        parent_cycle = self._active_cycles.get(pair)
        
        if not parent_cycle:
            logger.warning("No active cycle to attach recovery", pair=pair)
            return

        # 1. Obtener métricas de exposición reales
        exposure_pct, num_recoveries = await self._get_exposure_metrics(pair)

        # Validar con el RiskManager
        can_open = self.risk_manager.can_open_position(
            pair, 
            current_exposure=exposure_pct,
            num_recoveries=num_recoveries
        )
        if not can_open.success:
            logger.warning("Risk manager denied recovery opening", reason=can_open.error, exposure=exposure_pct)
            return

        # 2. Configuración de Recovery
        multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
        recovery_distance = Decimal(str(RECOVERY_DISTANCE_PIPS)) * multiplier
        tp_distance = Decimal(str(RECOVERY_TP_PIPS)) * multiplier
        lot = Decimal("0.01")  # En prod vendría del risk manager

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

        # 4. Crear operaciones de Recovery (Buy y Sell)
        # Según doc: 'Se coloca a 20 pips del precio actual'
        ask = tick.ask
        bid = tick.bid
        
        op_rec_buy = Operation(
            id=f"{recovery_id}_B",
            cycle_id=recovery_cycle.id,
            pair=pair,
            op_type=OperationType.RECOVERY_BUY,
            status=OperationStatus.PENDING,
            entry_price=ask + recovery_distance,
            tp_price=ask + recovery_distance + tp_distance,
            lot_size=lot,
            recovery_id=recovery_id
        )
        
        op_rec_sell = Operation(
            id=f"{recovery_id}_S",
            cycle_id=recovery_cycle.id,
            pair=pair,
            op_type=OperationType.RECOVERY_SELL,
            status=OperationStatus.PENDING,
            entry_price=bid - recovery_distance,
            tp_price=bid - recovery_distance - tp_distance,
            lot_size=lot,
            recovery_id=recovery_id
        )

        # 5. Guardar en DB
        await self.repository.save_cycle(recovery_cycle)
        
        # 6. Registrar en la cola FIFO del ciclo padre
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
            logger.info("Recovery cycle opened", recovery_id=recovery_id, level=recovery_level)
        else:
            logger.error("Failed to open recovery cycle", recovery_id=recovery_id)

    async def _handle_recovery_tp(self, recovery_cycle: Cycle, tick: TickData):
        """
        Maneja el evento de un Recovery que toca TP.
        Aplica la lógica FIFO para cerrar operaciones neutralizadas.
        """
        pair = recovery_cycle.pair
        parent_cycle = self._active_cycles.get(pair)
        
        if not parent_cycle:
            # Si no está en cache, intentar repo
            if recovery_cycle.parent_cycle_id:
                parent_res = await self.repository.get_cycle(recovery_cycle.parent_cycle_id)
                if parent_res.success:
                    parent_cycle = parent_res.value
        
        if not parent_cycle:
            logger.warning("No parent cycle found for recovery TP", recovery_id=recovery_cycle.id)
            return

        logger.info("Recovery TP hit, applying FIFO logic", recovery_id=recovery_cycle.id, parent_id=parent_cycle.id)
        
        # 1. Neutralizar profit contra deudas FIFO
        # RECOVERY_TP_PIPS (80) cierran deudas: 20 la primera, 40 las siguientes
        pips_available = float(RECOVERY_TP_PIPS)
        closed_count = 0
        
        while pips_available > 0 and parent_cycle.accounting.recovery_queue:
            cost = float(parent_cycle.accounting.get_recovery_cost())
            if pips_available >= cost:
                closed_rec_id = parent_cycle.close_oldest_recovery()
                logger.info("FIFO: Closing recovery debt", closed_rec_id=closed_rec_id, cost=cost, remaining_pips=pips_available-cost)
                pips_available -= cost
                closed_count += 1
            else:
                logger.info("FIFO: Not enough pips to close next recovery", cost=cost, available=pips_available)
                break
        
        # 2. Registrar progreso
        recovered_this_time = float(RECOVERY_TP_PIPS) - pips_available
        parent_cycle.accounting.add_recovered_pips(Pips(recovered_this_time))
        
        # 3. Guardar cambios
        await self.repository.save_cycle(parent_cycle)
        
        # 4. Verificar cierre total
        if parent_cycle.accounting.is_fully_recovered:
            logger.info("Cycle FULLY RECOVERED! Closing", cycle_id=parent_cycle.id)
            await self._close_cycle_operations(StrategySignal(signal_type=SignalType.CLOSE_OPERATIONS, pair=pair))

    # ============================================
    # UTILIDADES DE RIESGO
    # ============================================

    async def _get_exposure_metrics(self, pair: CurrencyPair) -> tuple[float, int]:
        """
        Calcula la exposición actual y el número de recoveries activos.
        
        Returns:
            Tuple (exposure_percentage, num_active_recoveries)
        """
        # 1. Exposición por margen (MT5)
        exposure_pct = 0.0
        acc_res = await self.trading_service.broker.get_account_info()
        if acc_res.success:
            equity = acc_res.value.get("equity", 0.0)
            margin = acc_res.value.get("margin", 0.0)
            if equity > 0:
                exposure_pct = (margin / equity) * 100
        
        # 2. Conteo de recoveries activos para este par
        num_recoveries = 0
        cycles_res = await self.repository.get_active_cycles(pair)
        if cycles_res.success:
            # Contamos cuántos ciclos de tipo RECOVERY hay activos
            # (El diseño actual asume un MAIN cycle que 'contiene' u 'orquesta' recoveries,
            # pero aquí contamos todos los ciclos secundarios activos)
            num_recoveries = sum(1 for c in cycles_res.value if c.cycle_type == CycleType.RECOVERY)
            
        logger.debug("Exposure metrics", pair=pair, exposure=exposure_pct, recoveries=num_recoveries)
        return (exposure_pct, num_recoveries)
