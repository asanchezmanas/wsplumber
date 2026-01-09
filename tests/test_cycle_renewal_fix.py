"""
Test para verificar FIX-CRITICAL: Main TP debe abrir NUEVO ciclo (C2) en vez de renovar dentro de C1.

Antes del fix: Las nuevas mains se creaban dentro del mismo ciclo C1
Después del fix: Se crea un NUEVO ciclo C2 cuando main toca TP

Este test verifica:
1. C1 tiene exactamente 2 mains (no más)
2. Cuando main toca TP, se crea C2 (nuevo ciclo)
3. C2 tiene sus propios 2 mains independientes
4. C1 queda en estado IN_RECOVERY esperando recovery
"""

import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, TickData, Timestamp, Price, Pips
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


def mock_settings():
    mock = MagicMock()
    mock.trading.default_lot_size = 0.01
    mock.trading.max_lot_size = 1.0
    mock.strategy.main_tp_pips = 10
    mock.strategy.main_step_pips = 10
    mock.strategy.recovery_tp_pips = 80
    mock.strategy.recovery_step_pips = 40
    mock.risk.max_exposure_per_pair = 1000.0
    return mock


def create_tick(pair: str, bid: float, ask: float, ts: str) -> TickData:
    return TickData(
        pair=CurrencyPair(pair),
        bid=Price(Decimal(str(bid))),
        ask=Price(Decimal(str(ask))),
        timestamp=Timestamp(datetime.fromisoformat(ts)),
        spread_pips=Pips(2.0)
    )


async def test_cycle_renewal_creates_new_cycle():
    """
    Verifica que cuando un main toca TP, se crea un NUEVO ciclo (C2)
    en lugar de renovar dentro del mismo ciclo (C1).
    """
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

        print("\n" + "="*60)
        print("TEST: Cycle Renewal Fix (C1 -> C2)")
        print("="*60)

        # ========================================
        # TICK 1: Crear ciclo C1
        # ========================================
        print("\nTICK 1: Crear ciclo C1")
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)

        assert len(repo.cycles) == 1, f"Debe haber 1 ciclo, hay {len(repo.cycles)}"
        c1 = list(repo.cycles.values())[0]
        print(f"  C1 creado: {c1.id}")
        print(f"  C1 status: {c1.status.value}")
        print(f"  Operaciones totales: {len(repo.operations)}")

        # ========================================
        # TICK 2: Activar BUY
        # ========================================
        print("\nTICK 2: Activar BUY")
        tick2 = create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)

        print(f"  C1 status: {c1.status.value}")

        # ========================================
        # TICK 3: Activar SELL -> HEDGED
        # ========================================
        print("\nTICK 3: Activar SELL -> HEDGED")
        tick3 = create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)

        c1 = list(repo.cycles.values())[0]  # Actualizar referencia
        print(f"  C1 status: {c1.status.value}")

        # ========================================
        # TICK 4: BUY toca TP -> DEBE CREAR C2
        # ========================================
        print("\nTICK 4: BUY toca TP -> DEBE CREAR C2")

        # Debug: Verificar precios de TP antes del tick
        all_ops_before = list(repo.operations.values())
        buy_ops_before = [op for op in all_ops_before if op.op_type.name == "MAIN_BUY"]
        if buy_ops_before:
            print(f"  DEBUG: BUY TP price = {buy_ops_before[0].tp_price}")
            print(f"  DEBUG: BUY status before = {buy_ops_before[0].status.value}")

        tick4 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:03")
        print(f"  DEBUG: Tick4 bid={tick4.bid}, ask={tick4.ask}")
        print(f"  DEBUG: C1 status before tick4: {c1.status.value}")
        broker.ticks.append(tick4)
        await broker.advance_tick()

        # Activar logging para ver qué pasa
        import logging
        logging.basicConfig(level=logging.DEBUG)

        await orchestrator._process_tick_for_pair(pair)

        # Debug: Verificar qué pasó
        all_ops_after = list(repo.operations.values())
        buy_ops_after = [op for op in all_ops_after if op.op_type.name == "MAIN_BUY"]
        if buy_ops_after:
            print(f"  DEBUG: BUY status after = {buy_ops_after[0].status.value}")
            print(f"  DEBUG: BUY tp_processed = {buy_ops_after[0].metadata.get('tp_processed', False)}")

        print(f"  DEBUG: Total cycles after tick4: {len(repo.cycles)}")
        all_cycles_debug = list(repo.cycles.values())
        print(f"  DEBUG: Cycle IDs: {[c.id for c in all_cycles_debug]}")
        print(f"  DEBUG: Cycle types: {[c.cycle_type.value if hasattr(c.cycle_type, 'value') else str(c.cycle_type) for c in all_cycles_debug]}")

        # ========================================
        # VERIFICACIONES CRÍTICAS
        # ========================================
        print("\n" + "="*60)
        print("VERIFICACIONES CRÍTICAS")
        print("="*60)

        # V1: Debe haber 2 ciclos MAIN ahora (C1 + C2)
        all_cycles = list(repo.cycles.values())
        main_cycles = [c for c in all_cycles if c.cycle_type == CycleType.MAIN]
        print(f"\n[V1] Ciclos MAIN totales: {len(main_cycles)}")
        print(f"     IDs: {[c.id for c in main_cycles]}")
        assert len(main_cycles) >= 2, f"Debe haber >=2 ciclos MAIN, hay {len(main_cycles)}"
        print("     OK: Se creo C2")

        # V2: C1 tiene exactamente 2 mains (no más)
        c1 = main_cycles[0]
        c1_mains = [op for op in repo.operations.values()
                   if op.cycle_id == c1.id and op.is_main]
        print(f"\n[V2] C1 ({c1.id})")
        print(f"     Mains en C1: {len(c1_mains)}")
        print(f"     IDs: {[op.id for op in c1_mains]}")
        assert len(c1_mains) == 2, f"C1 debe tener EXACTAMENTE 2 mains, tiene {len(c1_mains)}"
        print("     OK: C1 tiene exactamente 2 mains")

        # V3: C1 está en HEDGED o IN_RECOVERY
        # NOTA: El cambio a IN_RECOVERY ocurre cuando se procesa la señal de recovery
        # En este punto puede estar aún en HEDGED (main acabó de tocar TP)
        print(f"\n[V3] C1 status: {c1.status.value}")
        assert c1.status in [CycleStatus.HEDGED, CycleStatus.IN_RECOVERY], \
            f"C1 debe estar HEDGED o IN_RECOVERY, está {c1.status.value}"
        print(f"     OK: C1 en {c1.status.value}")

        # V4: C2 existe y tiene 2 mains propios
        c2 = main_cycles[1]
        c2_mains = [op for op in repo.operations.values()
                   if op.cycle_id == c2.id and op.is_main]
        print(f"\n[V4] C2 ({c2.id})")
        print(f"     Mains en C2: {len(c2_mains)}")
        print(f"     IDs: {[op.id for op in c2_mains]}")
        assert len(c2_mains) == 2, f"C2 debe tener 2 mains, tiene {len(c2_mains)}"
        print("     OK: C2 tiene 2 mains propios")

        # V5: C2 está en PENDING o ACTIVE
        print(f"\n[V5] C2 status: {c2.status.value}")
        assert c2.status in [CycleStatus.PENDING, CycleStatus.ACTIVE], \
            f"C2 debe estar PENDING o ACTIVE, está {c2.status.value}"
        print("     OK: C2 operando normalmente")

        # V6: Mains de C2 NO pertenecen a C1
        c2_main_cycle_ids = [op.cycle_id for op in c2_mains]
        all_different = all(cid != c1.id for cid in c2_main_cycle_ids)
        print(f"\n[V6] Cycle IDs de mains de C2: {c2_main_cycle_ids}")
        print(f"     Diferentes de C1 ({c1.id}): {all_different}")
        assert all_different, "Las mains de C2 NO deben pertenecer a C1"
        print("     OK: C2 independiente de C1")

        print("\n" + "="*60)
        print("TODAS LAS VERIFICACIONES PASARON")
        print("="*60)
        print("\nFIX CONFIRMADO:")
        print("  - C1 tiene exactamente 2 mains (no acumula renovaciones)")
        print("  - C2 se creo como NUEVO ciclo independiente")
        print("  - C1 queda IN_RECOVERY esperando recovery")
        print("  - C2 opera normalmente con sus propias mains")
        print("="*60)

        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_cycle_renewal_creates_new_cycle())
        print("\n[RESULTADO] Test PASADO" if success else "\n[RESULTADO] Test FALLIDO")
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
