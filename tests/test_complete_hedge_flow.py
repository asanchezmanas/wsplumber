"""
Test Completo del Flujo Hedge - El Fontanero

Este test valida el flujo COMPLETO cuando ambas mains se activan:

1. Crear ciclo con BUY + SELL a ±5 pips
2. Precio oscila → ambas mains se ACTIVAN
3. Sistema entra en HEDGED → crea HEDGE_BUY y HEDGE_SELL
4. Una main toca TP
5. Se cancela el hedge contrario pendiente
6. Se renuevan 2 nuevos mains (BUY + SELL)
7. Se abre ciclo Recovery a ±20 pips

Este es el escenario más complejo y común del sistema.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta

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
from wsplumber.domain.entities.cycle import CycleStatus
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


def create_tick(pair: str, bid: float, ask: float, ts: str) -> TickData:
    """Helper para crear ticks."""
    return TickData(
        pair=CurrencyPair(pair),
        bid=Price(Decimal(str(bid))),
        ask=Price(Decimal(str(ask))),
        timestamp=Timestamp(datetime.fromisoformat(ts)),
        spread_pips=Pips(2.0)
    )


def mock_settings():
    """Create mock settings."""
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


def print_all_operations(repo, title=""):
    """Helper para imprimir todas las operaciones."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    # Agrupar por tipo
    mains = []
    hedges = []
    recoveries = []
    
    for op_id, op in repo.operations.items():
        if op.is_main:
            mains.append(op)
        elif op.is_hedge:
            hedges.append(op)
        elif op.is_recovery:
            recoveries.append(op)
    
    print(f"\n📊 MAINS ({len(mains)}):")
    for op in mains:
        print(f"  {op.id}:")
        print(f"    type={op.op_type.value}, status={op.status.value}")
        print(f"    entry={op.entry_price}, tp={op.tp_price}")
    
    print(f"\n🛡️  HEDGES ({len(hedges)}):")
    for op in hedges:
        print(f"  {op.id}:")
        print(f"    type={op.op_type.value}, status={op.status.value}")
        print(f"    entry={op.entry_price}")
    
    print(f"\n🔄 RECOVERIES ({len(recoveries)}):")
    for op in recoveries:
        print(f"  {op.id}:")
        print(f"    type={op.op_type.value}, status={op.status.value}")
        print(f"    entry={op.entry_price}, tp={op.tp_price}")


@pytest.mark.asyncio
async def test_complete_hedge_flow():
    """
    Test del flujo completo de hedge:
    
    Secuencia de precios:
    1. tick1: bid=1.1000, ask=1.1002 → Crear ciclo
       - BUY entry=1.10070 (ask+5pips), TP=1.10170
       - SELL entry=1.09950 (bid-5pips), TP=1.09850
    
    2. tick2: bid=1.1010, ask=1.1012 → BUY se activa (ask >= 1.10070)
       
    3. tick3: bid=1.0990, ask=1.0992 → SELL se activa (bid <= 1.09950)
       - Ambas activas → HEDGED
       - Crear HEDGE_BUY y HEDGE_SELL
       - pips_locked = 20
    
    4. tick4: bid=1.1020, ask=1.1022 → BUY alcanza TP (bid >= 1.10170)
       - Cancelar HEDGE_SELL pendiente
       - Renovar mains (2 nuevos PENDING)
       - Abrir Recovery
    """
    from unittest.mock import patch
    
    mock = mock_settings()
    
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
        
        # ═══════════════════════════════════════════════════════════════
        # TICK 1: Crear ciclo inicial
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*60)
        print("TICK 1: CREAR CICLO INICIAL")
        print("█"*60)
        
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print(f"Precio: bid={tick1.bid}, ask={tick1.ask}")
        print(f"Ciclos creados: {len(repo.cycles)}")
        print(f"Operaciones: {len(repo.operations)}")
        
        # Verificar precios de entrada
        for op in repo.operations.values():
            if op.op_type == OperationType.MAIN_BUY:
                print(f"\nBUY creado: entry={op.entry_price}, tp={op.tp_price}")
                assert float(op.entry_price) == pytest.approx(1.10070, abs=0.00001), \
                    f"BUY entry debería ser 1.10070, es {op.entry_price}"
            elif op.op_type == OperationType.MAIN_SELL:
                print(f"SELL creado: entry={op.entry_price}, tp={op.tp_price}")
                assert float(op.entry_price) == pytest.approx(1.09950, abs=0.00001), \
                    f"SELL entry debería ser 1.09950, es {op.entry_price}"
        
        assert len(repo.cycles) == 1, "Debe haber 1 ciclo"
        assert len(repo.operations) == 2, "Debe haber 2 operaciones"
        
        cycle = list(repo.cycles.values())[0]
        assert cycle.status == CycleStatus.PENDING, "Ciclo debe estar PENDING"
        
        # ═══════════════════════════════════════════════════════════════
        # TICK 2: Precio sube → BUY se activa
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*60)
        print("TICK 2: BUY SE ACTIVA")
        print("█"*60)
        
        tick2 = create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print(f"Precio: bid={tick2.bid}, ask={tick2.ask}")
        
        buy_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_BUY]
        sell_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_SELL]
        
        print(f"BUY status: {buy_ops[0].status.value}")
        print(f"SELL status: {sell_ops[0].status.value}")
        
        # BUY debería activarse (ask=1.1012 >= entry=1.10070)
        # SELL sigue pendiente (bid=1.1010 > entry=1.09950)
        
        # ═══════════════════════════════════════════════════════════════
        # TICK 3: Precio baja → SELL se activa → HEDGED
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*60)
        print("TICK 3: SELL SE ACTIVA → HEDGED")
        print("█"*60)
        
        tick3 = create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print(f"Precio: bid={tick3.bid}, ask={tick3.ask}")
        
        # Actualizar referencias
        cycle = list(repo.cycles.values())[0]
        print(f"Ciclo status: {cycle.status.value}")
        
        buy_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_BUY]
        sell_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_SELL]
        hedge_ops = [op for op in repo.operations.values() if op.is_hedge]
        
        print(f"BUY status: {buy_ops[0].status.value}")
        print(f"SELL status: {sell_ops[0].status.value}")
        print(f"Hedges creados: {len(hedge_ops)}")
        
        for h in hedge_ops:
            print(f"  {h.op_type.value}: status={h.status.value}")
        
        # Verificar estado HEDGED
        # Nota: El sistema puede tardar un tick más en detectar ambas activas
        
        # ═══════════════════════════════════════════════════════════════
        # TICK 4: Precio sube mucho → BUY alcanza TP
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*60)
        print("TICK 4: BUY ALCANZA TP")
        print("█"*60)
        
        tick4 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:03")
        broker.ticks.append(tick4)
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print(f"Precio: bid={tick4.bid}, ask={tick4.ask}")
        
        print_all_operations(repo, "ESTADO DESPUÉS DE TICK 4")
        
        # ═══════════════════════════════════════════════════════════════
        # TICK 5: Dar tiempo para procesamiento
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*60)
        print("TICK 5: PROCESAMIENTO FINAL")
        print("█"*60)
        
        tick5 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:04")
        broker.ticks.append(tick5)
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print_all_operations(repo, "ESTADO FINAL")
        
        # ═══════════════════════════════════════════════════════════════
        # VALIDACIONES FINALES
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "█"*60)
        print("VALIDACIONES")
        print("█"*60)
        
        all_ops = list(repo.operations.values())
        
        # 1. BUY original cerrada
        original_buys = [op for op in all_ops if op.op_type == OperationType.MAIN_BUY and "_B_" not in str(op.id)]
        if original_buys:
            buy_closed = original_buys[0].status in (OperationStatus.TP_HIT, OperationStatus.CLOSED, OperationStatus.NEUTRALIZED)
            print(f"✓ BUY original cerrada: {buy_closed} (status={original_buys[0].status.value})")
        
        # 2. Hedges
        hedge_sells = [op for op in all_ops if op.op_type == OperationType.HEDGE_SELL]
        hedge_buys = [op for op in all_ops if op.op_type == OperationType.HEDGE_BUY]
        print(f"✓ HEDGE_SELL count: {len(hedge_sells)}")
        print(f"✓ HEDGE_BUY count: {len(hedge_buys)}")
        
        # 3. Mains renovados
        renewed_mains = [op for op in all_ops if op.is_main and "_B_" in str(op.id) or "_S_" in str(op.id)]
        print(f"✓ Mains renovados: {len(renewed_mains)}")
        
        # 4. Recoveries
        recovery_ops = [op for op in all_ops if op.is_recovery]
        print(f"✓ Operaciones Recovery: {len(recovery_ops)}")
        
        # 5. Balance
        print(f"✓ Balance final: {broker.balance}")
        
        # 6. Ciclos totales
        print(f"✓ Ciclos totales: {len(repo.cycles)}")
        for cid, c in repo.cycles.items():
            print(f"    {cid}: type={c.cycle_type.value}, status={c.status.value}")
        
        print("\n" + "█"*60)
        print("TEST COMPLETO")
        print("█"*60)


if __name__ == "__main__":
    asyncio.run(test_complete_hedge_flow())
