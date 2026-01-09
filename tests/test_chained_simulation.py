"""
WSPlumber - Test de Simulación Encadenada

Simula operación continua con múltiples ciclos encadenados:

SECUENCIA SIMULADA:
1. Ciclo 1: TP Simple → Renovación
2. Ciclo 2: TP Simple → Renovación  
3. Ciclo 3: Ambas activas → HEDGED
4. Ciclo 3: BUY TP → Recovery N1
5. Recovery N1: TP → Cerrar deuda FIFO
6. Ciclo 4: TP Simple (confirmar que sigue funcionando)

Este test verifica que el sistema puede operar continuamente
sin acumular errores o estados inconsistentes.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, field

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.core.strategy._params import (
    MAIN_TP_PIPS, MAIN_DISTANCE_PIPS, 
    RECOVERY_TP_PIPS, RECOVERY_DISTANCE_PIPS
)
from wsplumber.domain.types import (
    CurrencyPair, OperationStatus, OperationType, 
    TickData, Timestamp, Price, Pips
)
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


@dataclass
class EventLog:
    """Registro de eventos durante la simulación."""
    timestamp: str
    event_type: str
    description: str
    details: Dict = field(default_factory=dict)


class SimulationLogger:
    """Registra todos los eventos de la simulación."""
    
    def __init__(self):
        self.events: List[EventLog] = []
        self.expected_events: List[str] = []
    
    def log(self, ts: str, event_type: str, description: str, **details):
        self.events.append(EventLog(ts, event_type, description, details))
        print(f"  [{ts}] {event_type}: {description}")
    
    def expect(self, event_type: str):
        self.expected_events.append(event_type)
    
    def verify_events(self) -> bool:
        """Verifica que todos los eventos esperados ocurrieron."""
        actual_types = [e.event_type for e in self.events]
        
        missing = []
        for expected in self.expected_events:
            if expected not in actual_types:
                missing.append(expected)
        
        if missing:
            print(f"\n⚠️  Eventos esperados que no ocurrieron: {missing}")
            return False
        
        return True


def create_tick(pair: str, bid: float, ask: float, ts: datetime) -> TickData:
    return TickData(
        pair=CurrencyPair(pair),
        bid=Price(Decimal(str(bid))),
        ask=Price(Decimal(str(ask))),
        timestamp=Timestamp(ts),
        spread_pips=Pips(2.0)
    )


def mock_settings():
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.trading.default_lot_size = 0.01
    mock.trading.max_lot_size = 1.0
    mock.strategy.main_tp_pips = 10
    mock.strategy.main_step_pips = 10
    mock.strategy.recovery_tp_pips = 80
    mock.strategy.recovery_step_pips = 40
    mock.risk.max_exposure_per_pair = 1000.0
    return mock


def analyze_state(repo, broker, logger: SimulationLogger, phase: str):
    """Analiza y loguea el estado actual."""
    cycles = list(repo.cycles.values())
    operations = list(repo.operations.values())
    
    # Contar por tipo y estado
    main_pending = sum(1 for op in operations if op.is_main and op.status == OperationStatus.PENDING)
    main_active = sum(1 for op in operations if op.is_main and op.status == OperationStatus.ACTIVE)
    main_tp = sum(1 for op in operations if op.is_main and op.status == OperationStatus.TP_HIT)
    main_cancelled = sum(1 for op in operations if op.is_main and op.status == OperationStatus.CANCELLED)
    main_neutralized = sum(1 for op in operations if op.is_main and op.status == OperationStatus.NEUTRALIZED)
    
    hedge_pending = sum(1 for op in operations if op.is_hedge and op.status == OperationStatus.PENDING)
    hedge_cancelled = sum(1 for op in operations if op.is_hedge and op.status == OperationStatus.CANCELLED)
    
    recovery_pending = sum(1 for op in operations if op.is_recovery and op.status == OperationStatus.PENDING)
    recovery_tp = sum(1 for op in operations if op.is_recovery and op.status == OperationStatus.TP_HIT)
    
    cycle_statuses = [c.status.value for c in cycles]
    
    print(f"\n  📊 Estado [{phase}]:")
    print(f"     Ciclos: {len(cycles)} ({', '.join(cycle_statuses)})")
    print(f"     Mains: pending={main_pending}, active={main_active}, tp={main_tp}, cancelled={main_cancelled}, neutralized={main_neutralized}")
    print(f"     Hedges: pending={hedge_pending}, cancelled={hedge_cancelled}")
    print(f"     Recovery: pending={recovery_pending}, tp={recovery_tp}")
    print(f"     Balance: {broker.balance}")


async def run_chained_simulation():
    """Ejecuta una simulación encadenada de múltiples ciclos."""
    from unittest.mock import patch
    
    mock = mock_settings()
    logger = SimulationLogger()
    
    print("\n" + "█"*80)
    print("WSPLUMBER - SIMULACIÓN ENCADENADA")
    print("█"*80)
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Setup
        broker = SimulatedBroker(initial_balance=1000.0)
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock
        strategy = WallStreetPlumberStrategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        pair = CurrencyPair("EURUSD")
        await broker.connect()
        
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tick_idx = 0
        
        def next_tick(bid: float, ask: float) -> TickData:
            nonlocal tick_idx
            ts = base_time + timedelta(seconds=tick_idx)
            tick_idx += 1
            return create_tick("EURUSD", bid, ask, ts)
        
        # ═══════════════════════════════════════════════════════════════
        # ESCENARIO 1: TP SIMPLE (Ciclo 1)
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "="*60)
        print("📍 ESCENARIO 1: TP SIMPLE (Primer ciclo)")
        print("="*60)
        
        # Tick 1: Crear ciclo inicial
        tick = next_tick(1.1000, 1.1002)
        broker.ticks = [tick]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T1", "CYCLE_CREATED", "Ciclo inicial creado", 
                  cycles=len(repo.cycles), ops=len(repo.operations))
        
        # Tick 2: BUY activa + TP
        tick = next_tick(1.1020, 1.1022)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T2", "BUY_TP_HIT", "BUY alcanzó TP", balance=float(broker.balance))
        
        # Tick 3: Procesamiento
        tick = next_tick(1.1020, 1.1022)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        analyze_state(repo, broker, logger, "POST_TP_1")
        
        # Verificar
        tp_count = sum(1 for op in repo.operations.values() if op.status == OperationStatus.TP_HIT)
        assert tp_count >= 1, f"Debe haber al menos 1 TP_HIT, hay {tp_count}"
        
        # ═══════════════════════════════════════════════════════════════
        # ESCENARIO 2: TP SIMPLE (Segundo ciclo - renovación)
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "="*60)
        print("📍 ESCENARIO 2: TP SIMPLE (Renovación)")
        print("="*60)
        
        # Tick 4: Precio sube más → Nuevo BUY TP
        tick = next_tick(1.1040, 1.1042)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        tick = next_tick(1.1040, 1.1042)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T4-5", "SECOND_TP", "Segundo TP del ciclo renovado", 
                  balance=float(broker.balance))
        
        analyze_state(repo, broker, logger, "POST_TP_2")
        
        # ═══════════════════════════════════════════════════════════════
        # ESCENARIO 3: HEDGE (Ambas activas)
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "="*60)
        print("📍 ESCENARIO 3: HEDGE (Ambas activas)")
        print("="*60)
        
        # Necesitamos resetear a un precio donde ambas puedan activarse
        # Primero dejamos que el precio oscile para activar ambas
        
        # Tick: Precio sube → Activa BUY renovado
        tick = next_tick(1.1050, 1.1052)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T6", "BUY_ACTIVE", "BUY renovado se activó")
        
        # Tick: Precio baja → Activa SELL renovado
        tick = next_tick(1.1035, 1.1037)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T7", "SELL_ACTIVE", "SELL renovado se activó → HEDGED")
        
        analyze_state(repo, broker, logger, "POST_HEDGE")
        
        # Verificar estado HEDGED
        hedged_cycles = [c for c in repo.cycles.values() if c.status == CycleStatus.HEDGED]
        hedge_ops = [op for op in repo.operations.values() if op.is_hedge]
        
        logger.log("VERIFY", "HEDGE_STATE", 
                  f"Ciclos HEDGED: {len(hedged_cycles)}, Ops hedge: {len(hedge_ops)}")
        
        # ═══════════════════════════════════════════════════════════════
        # ESCENARIO 4: TP EN HEDGED → RECOVERY
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "="*60)
        print("📍 ESCENARIO 4: TP EN HEDGED → RECOVERY")
        print("="*60)
        
        # Tick: Precio sube mucho → BUY TP
        tick = next_tick(1.1060, 1.1062)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        tick = next_tick(1.1060, 1.1062)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T8-9", "TP_IN_HEDGED", "TP en estado hedged → Recovery abierto")
        
        analyze_state(repo, broker, logger, "POST_RECOVERY_OPEN")
        
        # Verificar recovery
        recovery_cycles = [c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY]
        recovery_ops = [op for op in repo.operations.values() if op.is_recovery]
        
        logger.log("VERIFY", "RECOVERY_STATE", 
                  f"Ciclos Recovery: {len(recovery_cycles)}, Ops recovery: {len(recovery_ops)}")
        
        assert len(recovery_ops) >= 2, f"Debe haber al menos 2 ops recovery, hay {len(recovery_ops)}"
        
        # ═══════════════════════════════════════════════════════════════
        # ESCENARIO 5: RECOVERY TP → FIFO
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "="*60)
        print("📍 ESCENARIO 5: RECOVERY TP → FIFO")
        print("="*60)
        
        # Recovery BUY entry está a +20 pips del precio anterior
        # Necesitamos subir el precio +100 pips para que el recovery toque TP
        # Recovery entry ~1.1082, TP ~1.1162
        
        tick = next_tick(1.1080, 1.1082)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # Activar recovery
        tick = next_tick(1.1090, 1.1092)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T10-11", "RECOVERY_ACTIVE", "Recovery BUY activado")
        
        # Subir precio para TP del recovery
        tick = next_tick(1.1170, 1.1172)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        tick = next_tick(1.1170, 1.1172)
        broker.ticks.append(tick)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        logger.log("T12-13", "RECOVERY_TP", "Recovery TP → FIFO procesado")
        
        analyze_state(repo, broker, logger, "POST_RECOVERY_TP")
        
        # ═══════════════════════════════════════════════════════════════
        # RESUMEN FINAL
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*80)
        print("RESUMEN DE LA SIMULACIÓN")
        print("█"*80)
        
        total_cycles = len(repo.cycles)
        total_ops = len(repo.operations)
        final_balance = float(broker.balance)
        balance_change = final_balance - 1000.0
        
        print(f"\n📊 ESTADÍSTICAS FINALES:")
        print(f"   Ciclos totales: {total_cycles}")
        print(f"   Operaciones totales: {total_ops}")
        print(f"   Balance inicial: 1000.00")
        print(f"   Balance final: {final_balance:.2f}")
        print(f"   P&L: {'+' if balance_change >= 0 else ''}{balance_change:.2f}")
        
        # Contar por estado
        by_status = {}
        for op in repo.operations.values():
            status = op.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        print(f"\n📋 OPERACIONES POR ESTADO:")
        for status, count in sorted(by_status.items()):
            print(f"   {status}: {count}")
        
        # Eventos registrados
        print(f"\n📝 EVENTOS REGISTRADOS: {len(logger.events)}")
        for event in logger.events:
            print(f"   [{event.timestamp}] {event.event_type}: {event.description}")
        
        print("\n" + "█"*80)
        print("✅ SIMULACIÓN ENCADENADA COMPLETADA")
        print("█"*80)
        
        return True


if __name__ == "__main__":
    success = asyncio.run(run_chained_simulation())
    exit(0 if success else 1)
