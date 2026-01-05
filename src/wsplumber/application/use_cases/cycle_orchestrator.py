# src/wsplumber/application/use_cases/cycle_orchestrator.py
"""
Orquestador de Ciclos.

El corazón del sistema. Procesa ticks de mercado, consulta a la estrategia,
valida con el gestor de riesgo y ejecuta a través del TradingService.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from wsplumber.domain.interfaces.ports import (
    IBroker,
    IRepository,
    IStrategy,
    IRiskManager,
)
from wsplumber.domain.types import (
    CurrencyPair,
    OrderRequest,
    Result,
    SignalType,
    StrategySignal,
    TickData,
)
from wsplumber.domain.entities.cycle import Cycle, CycleStatus
from wsplumber.domain.entities.operation import Operation
from wsplumber.application.services.trading_service import TradingService
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

    async def _process_tick_for_pair(self, pair: CurrencyPair):
        """Procesa un tick para un par específico."""
        try:
            # 1. Obtener tick del broker
            tick_res = await self.trading_service.broker.get_current_price(pair)
            if not tick_res.success:
                return

            tick: TickData = tick_res.value

            # 2. Consultar a la estrategia core (Secreto)
            signal: StrategySignal = self.strategy.process_tick(
                pair=tick.pair,
                bid=float(tick.bid),
                ask=float(tick.ask),
                timestamp=tick.timestamp
            )

            if signal.signal_type == SignalType.NO_ACTION:
                return

            # 3. Monitorear estado de operaciones activas (detección de TP)
            await self._check_operations_status(pair)

            # 4. Procesar señal
            await self._handle_signal(signal, tick)

        except Exception as e:
            logger.error("Error processing tick", exception=e, pair=pair)

    async def _check_operations_status(self, pair: CurrencyPair):
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
            if op.status == OperationStatus.CLOSED or op.status == OperationStatus.TP_HIT:
                # Notificar a la estrategia
                logger.info("Operation closed, notifying strategy", op_id=op.id, ticket=op.broker_ticket)
                signal = self.strategy.process_tp_hit(
                    operation_id=op.id,
                    profit_pips=float(op.profit_pips or 0),
                    timestamp=datetime.now()
                )
                if signal.signal_type != SignalType.NO_ACTION:
                    await self._handle_signal(signal, TickData(pair=pair, bid=0, ask=0, timestamp=datetime.now()))

    async def _handle_signal(self, signal: StrategySignal, tick: TickData):
        """Maneja las señales emitidas por la estrategia."""
        logger.info("Signal received", type=signal.signal_type, pair=signal.pair)

        if signal.signal_type == SignalType.OPEN_CYCLE:
            await self._open_new_cycle(signal, tick)
        
        elif signal.signal_type == SignalType.CLOSE_OPERATIONS:
            await self._close_cycle_operations(signal)
            
        # ... otros tipos de señales (HEDGE, RECOVERY) se implementan aquí

    async def _open_new_cycle(self, signal: StrategySignal, tick: TickData):
        """Inicia un nuevo ciclo de trading con dos operaciones (Buy + Sell)."""
        pair = signal.pair
        
        # 1. Verificar riesgo (Simplificado)
        acc_info = await self.trading_service.broker.get_account_info()
        balance = acc_info.value["balance"] if acc_info.success else 10000.0

        # Para un nuevo ciclo abrimos 2 operaciones, validamos exposición base
        can_open = self.risk_manager.can_open_position(pair, current_exposure=0.0) 
        if not can_open.success:
            logger.warning("Risk manager denied cycle opening", reason=can_open.error)
            return

        # 2. Calcular lote
        lot = self.risk_manager.calculate_lot_size(pair, balance)

        # 3. Crear Entidad Ciclo
        # Usamos un ID descriptivo o UUID
        cycle_id = f"CYC_{pair}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cycle = Cycle(id=cycle_id, pair=pair)
        
        # 4. Crear Operaciones Duales (Buy y Sell)
        # La estrategia dice: TP a 10 pips. 
        # NOTA: En una implementación real, esto vendría parametrizado o del core.
        tp_distance = 0.0010 # 10 pips
        
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
            self._active_cycles[pair] = cycle
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
