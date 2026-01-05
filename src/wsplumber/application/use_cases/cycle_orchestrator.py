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

            # 3. Procesar señal
            await self._handle_signal(signal, tick)

        except Exception as e:
            logger.error("Error processing tick", exception=e, pair=pair)

    async def _handle_signal(self, signal: StrategySignal, tick: TickData):
        """Maneja las señales emitidas por la estrategia."""
        logger.info("Signal received", type=signal.signal_type, pair=signal.pair)

        if signal.signal_type == SignalType.OPEN_CYCLE:
            await self._open_new_cycle(signal, tick)
        
        elif signal.signal_type == SignalType.CLOSE_OPERATIONS:
            await self._close_cycle_operations(signal)
            
        # ... otros tipos de señales (HEDGE, RECOVERY) se implementan aquí

    async def _open_new_cycle(self, signal: StrategySignal, tick: TickData):
        """Inicia un nuevo ciclo de trading."""
        pair = signal.pair
        
        # 1. Verificar riesgo
        # Simplificamos obteniendo un balance de cuenta ficticio o real
        acc_info = await self.trading_service.broker.get_account_info()
        balance = acc_info.value["balance"] if acc_info.success else 10000.0

        can_open = self.risk_manager.can_open_position(pair, current_exposure=0.0) # Placeholder
        if not can_open.success:
            logger.warning("Risk manager denied cycle opening", reason=can_open.error)
            return

        # 2. Calcular lote
        lot = self.risk_manager.calculate_lot_size(pair, balance)

        # 3. Crear Entidades
        # (Aquí se usaría un UUID generator real)
        cycle_id = f"{pair}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cycle = Cycle(id=cycle_id, pair=pair)
        
        op_id = f"{cycle_id}_MAIN"
        # En la estrategia el core decide el TP, aquí lo obtenemos del signal metadata o config
        tp_price = tick.ask + 0.0010 # Ejemplo 10 pips
        
        operation = Operation(
            id=op_id,
            cycle_id=cycle.id,
            pair=pair,
            op_type=signal.metadata.get("op_type", "main_buy"),
            status=OperationStatus.PENDING,
            entry_price=tick.ask,
            tp_price=tp_price,
            lot_size=lot
        )
        
        # 4. Ejecutar a través de TradingService
        request = OrderRequest(
            operation_id=operation.id,
            pair=pair,
            order_type=operation.op_type,
            entry_price=operation.entry_price,
            tp_price=operation.tp_price,
            lot_size=operation.lot_size
        )

        # Iniciar ciclo en DB primero
        await self.repository.save_cycle(cycle)
        
        # Abrir operación
        res = await self.trading_service.open_operation(request, operation)
        
        if res.success:
            self._active_cycles[pair] = cycle
            logger.info("New cycle opened and active", cycle_id=cycle.id)

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
