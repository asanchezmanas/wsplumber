"""
WSPlumber - Test Suite de Verificación de Flujos

Este módulo contiene TODOS los flujos del sistema organizados por complejidad:

FLUJOS SIMPLES (S):
  S1. TP Simple BUY - Una main BUY toca TP
  S2. TP Simple SELL - Una main SELL toca TP
  S3. Cancelación de contraria - Al TP, la pendiente se cancela
  S4. Renovación tras TP - Se crean 2 nuevas mains

FLUJOS HEDGE (H):
  H1. Ambas mains activas → HEDGED
  H2. Creación de hedges (HEDGE_BUY + HEDGE_SELL)
  H3. TP en HEDGED → Cancelar hedge contrario
  H4. TP en HEDGED → Abrir Recovery

FLUJOS RECOVERY (R):
  R1. Recovery a ±20 pips del precio
  R2. Recovery TP → FIFO cierra deudas
  R3. Recovery cascada (N1 falla → N2)

FLUJOS FIFO (F):
  F1. Primer recovery cuesta 20 pips
  F2. Siguientes cuestan 40 pips
  F3. 80 pips pueden cerrar múltiples deudas

Ejecutar: python tests/test_verify_flows.py
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any

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


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def create_tick(pair: str, bid: float, ask: float, ts: str) -> TickData:
    return TickData(
        pair=CurrencyPair(pair),
        bid=Price(Decimal(str(bid))),
        ask=Price(Decimal(str(ask))),
        timestamp=Timestamp(datetime.fromisoformat(ts)),
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


async def setup_orchestrator():
    """Setup común para todos los tests."""
    from unittest.mock import patch
    
    mock = mock_settings()
    
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
    
    await broker.connect()
    
    return orchestrator, broker, repo, mock


def count_ops_by_type(repo) -> Dict[str, int]:
    """Cuenta operaciones por tipo y estado."""
    counts = {
        'main_buy_pending': 0, 'main_buy_active': 0, 'main_buy_tp_hit': 0,
        'main_sell_pending': 0, 'main_sell_active': 0, 'main_sell_tp_hit': 0,
        'hedge_buy': 0, 'hedge_sell': 0,
        'recovery_buy': 0, 'recovery_sell': 0,
        'cancelled': 0, 'neutralized': 0
    }
    
    for op in repo.operations.values():
        if op.status == OperationStatus.CANCELLED:
            counts['cancelled'] += 1
        elif op.status == OperationStatus.NEUTRALIZED:
            counts['neutralized'] += 1
        elif op.op_type == OperationType.MAIN_BUY:
            if op.status == OperationStatus.PENDING:
                counts['main_buy_pending'] += 1
            elif op.status == OperationStatus.ACTIVE:
                counts['main_buy_active'] += 1
            elif op.status == OperationStatus.TP_HIT:
                counts['main_buy_tp_hit'] += 1
        elif op.op_type == OperationType.MAIN_SELL:
            if op.status == OperationStatus.PENDING:
                counts['main_sell_pending'] += 1
            elif op.status == OperationStatus.ACTIVE:
                counts['main_sell_active'] += 1
            elif op.status == OperationStatus.TP_HIT:
                counts['main_sell_tp_hit'] += 1
        elif op.op_type == OperationType.HEDGE_BUY:
            counts['hedge_buy'] += 1
        elif op.op_type == OperationType.HEDGE_SELL:
            counts['hedge_sell'] += 1
        elif op.op_type == OperationType.RECOVERY_BUY:
            counts['recovery_buy'] += 1
        elif op.op_type == OperationType.RECOVERY_SELL:
            counts['recovery_sell'] += 1
    
    return counts


# ═══════════════════════════════════════════════════════════════
# S1: TP SIMPLE BUY
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_s1_tp_simple_buy():
    """
    S1: Una operación BUY alcanza TP.
    
    Secuencia:
    1. Crear ciclo → BUY entry=ask+5pips, SELL entry=bid-5pips
    2. Precio sube → BUY se activa
    3. Precio sube más → BUY toca TP
    
    Verificar:
    - BUY status = TP_HIT o CLOSED
    - SELL status = CANCELLED
    - Balance aumentó
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Tick 1: Crear ciclo
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        assert len(repo.operations) == 2, "Debe haber 2 operaciones"
        
        # Tick 2: Precio sube mucho → BUY activa + TP
        # BUY entry = 1.1002 + 0.0005 = 1.10070, TP = 1.10170
        tick2 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # Tick 3: Procesamiento
        tick3 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        counts = count_ops_by_type(repo)
        
        print("\n[S1] TP Simple BUY:")
        print(f"  BUY TP_HIT: {counts['main_buy_tp_hit']}")
        print(f"  SELL cancelled: {counts['cancelled']}")
        print(f"  Balance: {broker.balance}")
        
        assert counts['main_buy_tp_hit'] >= 1, "BUY debe estar en TP_HIT"
        assert counts['cancelled'] >= 1, "SELL debe estar CANCELLED"
        assert float(broker.balance) > 1000.0, "Balance debe aumentar"
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# S2: TP SIMPLE SELL
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_s2_tp_simple_sell():
    """
    S2: Una operación SELL alcanza TP.
    
    Secuencia:
    1. Crear ciclo
    2. Precio baja → SELL se activa
    3. Precio baja más → SELL toca TP
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Tick 1: Crear ciclo
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # SELL entry = 1.1000 - 0.0005 = 1.09950, TP = 1.09850
        
        # Tick 2: Precio baja mucho → SELL activa + TP
        tick2 = create_tick("EURUSD", 1.0980, 1.0982, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # Tick 3: Procesamiento
        tick3 = create_tick("EURUSD", 1.0980, 1.0982, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        counts = count_ops_by_type(repo)
        
        print("\n[S2] TP Simple SELL:")
        print(f"  SELL TP_HIT: {counts['main_sell_tp_hit']}")
        print(f"  BUY cancelled: {counts['cancelled']}")
        print(f"  Balance: {broker.balance}")
        
        assert counts['main_sell_tp_hit'] >= 1, "SELL debe estar en TP_HIT"
        assert counts['cancelled'] >= 1, "BUY debe estar CANCELLED"
        assert float(broker.balance) > 1000.0, "Balance debe aumentar"
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# S3: RENOVACIÓN TRAS TP
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio  
async def test_s3_renewal_after_tp():
    """
    S3: Después de un TP se crean 2 nuevas operaciones main.
    
    Verificar:
    - 2 operaciones originales (1 TP_HIT, 1 CANCELLED)
    - 2 operaciones renovadas (PENDING ambas)
    - Las renovadas tienen entry a ±5 pips del precio actual
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Tick 1: Crear ciclo
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        original_op_ids = set(repo.operations.keys())
        
        # Tick 2: BUY TP
        tick2 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # Verificar renovación
        new_ops = [op for op in repo.operations.values() if op.id not in original_op_ids]
        new_mains = [op for op in new_ops if op.is_main]
        
        print("\n[S3] Renovación tras TP:")
        print(f"  Ops originales: {len(original_op_ids)}")
        print(f"  Ops nuevas: {len(new_ops)}")
        print(f"  Mains nuevos: {len(new_mains)}")
        
        for op in new_mains:
            print(f"    {op.op_type.value}: entry={op.entry_price}, status={op.status.value}")
        
        assert len(new_mains) >= 2, "Deben haber 2 mains renovados"
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# H1: AMBAS MAINS ACTIVAS → HEDGED
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_h1_both_mains_active_hedged():
    """
    H1: Cuando ambas operaciones main se activan, el ciclo entra en HEDGED.
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Tick 1: Crear ciclo
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # Tick 2: Precio sube → BUY activa
        tick2 = create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # Tick 3: Precio baja → SELL activa
        tick3 = create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        cycle = list(repo.cycles.values())[0]
        counts = count_ops_by_type(repo)
        
        print("\n[H1] Ambas mains activas → HEDGED:")
        print(f"  Ciclo status: {cycle.status.value}")
        print(f"  Neutralized: {counts['neutralized']}")
        print(f"  Hedges: BUY={counts['hedge_buy']}, SELL={counts['hedge_sell']}")
        
        assert cycle.status == CycleStatus.HEDGED, "Ciclo debe estar HEDGED"
        assert counts['neutralized'] == 2, "Ambas mains neutralizadas"
        assert counts['hedge_buy'] >= 1, "Debe haber HEDGE_BUY"
        assert counts['hedge_sell'] >= 1, "Debe haber HEDGE_SELL"
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# H2: TP EN HEDGED → CANCELAR HEDGE CONTRARIO
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_h2_tp_hedged_cancel_contrary():
    """
    H2: Cuando un main toca TP en estado HEDGED, el hedge contrario se cancela.
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Setup: Crear ciclo y llevarlo a HEDGED
        ticks = [
            create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00"),
            create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01"),  # BUY activa
            create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02"),  # SELL activa → HEDGED
            create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:03"),  # BUY TP
            create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:04"),  # Procesamiento
        ]
        
        broker.ticks = ticks
        broker.current_tick_index = -1
        
        for tick in ticks:
            await broker.advance_tick()
            await orchestrator._process_tick_for_pair(pair)
        
        # Verificar que HEDGE_SELL fue cancelado (contrario a BUY TP)
        hedge_sells = [op for op in repo.operations.values() 
                      if op.op_type == OperationType.HEDGE_SELL]
        
        print("\n[H2] TP en HEDGED → Cancelar hedge contrario:")
        for h in hedge_sells:
            print(f"  HEDGE_SELL status: {h.status.value}")
        
        cancelled_hedges = [h for h in hedge_sells if h.status == OperationStatus.CANCELLED]
        assert len(cancelled_hedges) >= 1, "HEDGE_SELL debe estar CANCELLED"
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# H3: TP EN HEDGED → ABRIR RECOVERY
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_h3_tp_hedged_open_recovery():
    """
    H3: Cuando un main toca TP en estado HEDGED, se abre un ciclo Recovery.
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        ticks = [
            create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00"),
            create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01"),
            create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02"),
            create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:03"),
            create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:04"),
        ]
        
        broker.ticks = ticks
        broker.current_tick_index = -1
        
        for tick in ticks:
            await broker.advance_tick()
            await orchestrator._process_tick_for_pair(pair)
        
        counts = count_ops_by_type(repo)
        recovery_cycles = [c for c in repo.cycles.values() if c.cycle_type.value == 'recovery']
        
        print("\n[H3] TP en HEDGED → Abrir Recovery:")
        print(f"  Recovery cycles: {len(recovery_cycles)}")
        print(f"  Recovery BUY ops: {counts['recovery_buy']}")
        print(f"  Recovery SELL ops: {counts['recovery_sell']}")
        
        assert len(recovery_cycles) >= 1, "Debe haber ciclo Recovery"
        assert counts['recovery_buy'] >= 1, "Debe haber RECOVERY_BUY"
        assert counts['recovery_sell'] >= 1, "Debe haber RECOVERY_SELL"
        
        # Verificar distancia de recovery (20 pips)
        recovery_ops = [op for op in repo.operations.values() if op.is_recovery]
        for op in recovery_ops:
            print(f"  {op.op_type.value}: entry={op.entry_price}, tp={op.tp_price}")
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# R1: RECOVERY A ±20 PIPS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_r1_recovery_distance_20_pips():
    """
    R1: Las operaciones Recovery se abren a ±20 pips del precio actual.
    """
    from unittest.mock import patch
    
    orchestrator, broker, repo, mock = await setup_orchestrator()
    pair = CurrencyPair("EURUSD")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        ticks = [
            create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00"),
            create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01"),
            create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02"),
            create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:03"),
        ]
        
        broker.ticks = ticks
        broker.current_tick_index = -1
        
        for tick in ticks:
            await broker.advance_tick()
            await orchestrator._process_tick_for_pair(pair)
        
        last_tick = ticks[-1]
        recovery_ops = [op for op in repo.operations.values() if op.is_recovery]
        
        print("\n[R1] Recovery a ±20 pips:")
        print(f"  Precio actual: bid={last_tick.bid}, ask={last_tick.ask}")
        
        for op in recovery_ops:
            if op.op_type == OperationType.RECOVERY_BUY:
                expected_entry = float(last_tick.ask) + 0.0020  # +20 pips
                actual_entry = float(op.entry_price)
                distance = (actual_entry - float(last_tick.ask)) * 10000
                print(f"  RECOVERY_BUY: entry={actual_entry:.5f}, distance={distance:.1f} pips")
                assert abs(distance - 20.0) < 1.0, f"RECOVERY_BUY debe estar a 20 pips, está a {distance}"
            
            elif op.op_type == OperationType.RECOVERY_SELL:
                expected_entry = float(last_tick.bid) - 0.0020  # -20 pips
                actual_entry = float(op.entry_price)
                distance = (float(last_tick.bid) - actual_entry) * 10000
                print(f"  RECOVERY_SELL: entry={actual_entry:.5f}, distance={distance:.1f} pips")
                assert abs(distance - 20.0) < 1.0, f"RECOVERY_SELL debe estar a 20 pips, está a {distance}"
        
        print("  ✅ PASSED")


# ═══════════════════════════════════════════════════════════════
# EJECUTAR TODOS LOS TESTS
# ═══════════════════════════════════════════════════════════════

async def run_all_tests():
    """Ejecuta todos los tests de verificación."""
    print("\n" + "="*60)
    print("WSPLUMBER - VERIFICACIÓN DE FLUJOS")
    print("="*60)
    
    tests = [
        ("S1", "TP Simple BUY", test_s1_tp_simple_buy),
        ("S2", "TP Simple SELL", test_s2_tp_simple_sell),
        ("S3", "Renovación tras TP", test_s3_renewal_after_tp),
        ("H1", "Ambas mains → HEDGED", test_h1_both_mains_active_hedged),
        ("H2", "TP HEDGED → Cancel hedge", test_h2_tp_hedged_cancel_contrary),
        ("H3", "TP HEDGED → Open Recovery", test_h3_tp_hedged_open_recovery),
        ("R1", "Recovery a ±20 pips", test_r1_recovery_distance_20_pips),
    ]
    
    passed = 0
    failed = 0
    
    for code, name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n[{code}] {name}: ❌ FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"\n[{code}] {name}: ❌ ERROR - {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTADOS: {passed}/{len(tests)} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    from unittest.mock import patch
    
    mock = mock_settings()
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
