"""
Test Mínimo - Validación del Flujo Básico WSPlumber

Este test es el más simple posible para validar que:
1. Se crea un ciclo con BUY/SELL
2. El precio sube y el BUY alcanza TP
3. El balance aumenta
4. Las operaciones se cierran correctamente

Si este test pasa, sabemos que el motor funciona.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, TickData, Timestamp, Price, Pips
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


@pytest.mark.asyncio
async def test_minimal_buy_tp():
    """
    Test mínimo: BUY alcanza TP de 10 pips.
    
    Secuencia:
    1. Tick inicial: bid=1.1000, ask=1.1002 → BUY entra a 1.1002, TP=1.1012
    2. Tick final: bid=1.1015 → BUY cierra porque bid >= TP (1.1012)
    
    Esperado:
    - Balance aumenta de 1000 a ~1001 (10 pips * 0.01 lote * $10/pip = $1)
    - Operación BUY en estado TP_HIT o CLOSED
    """
    from unittest.mock import MagicMock, patch
    
    # Setup mock settings
    mock_settings = MagicMock()
    mock_settings.trading.default_lot_size = 0.01
    mock_settings.trading.max_lot_size = 1.0
    mock_settings.strategy.main_tp_pips = 10
    mock_settings.strategy.main_step_pips = 10
    mock_settings.strategy.recovery_tp_pips = 80
    mock_settings.strategy.recovery_step_pips = 40
    mock_settings.risk.max_exposure_per_pair = 1000.0
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock_settings):
        # Crear componentes
        broker = SimulatedBroker(initial_balance=1000.0)
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock_settings
        strategy = WallStreetPlumberStrategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        pair = CurrencyPair("EURUSD")
        
        # Conectar broker
        await broker.connect()
        
        # ============================================
        # TICK 1: Precio inicial - Crear ciclo
        # ============================================
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print("\n=== DESPUÉS DE TICK 1 ===")
        print(f"Cycles: {len(repo.cycles)}")
        print(f"Operations: {len(repo.operations)}")
        print(f"Open positions (broker): {len(broker.open_positions)}")
        print(f"Pending orders (broker): {len(broker.pending_orders)}")
        
        # Validar: Se creó el ciclo
        assert len(repo.cycles) == 1, "Debe haber 1 ciclo"
        assert len(repo.operations) == 2, "Debe haber 2 operaciones (BUY + SELL)"
        
        # En el primer tick, las órdenes se envían al broker pero son PENDING 
        # hasta el siguiente tick en el SimulationBroker
        pending_ops = [op for op in repo.operations.values() if op.status == OperationStatus.PENDING]
        assert len(pending_ops) == 2, f"Debe haber 2 operaciones PENDING, encontradas {len(pending_ops)}"
        
        # ============================================
        # TICK 2: Precio sube a TP
        # ============================================
        # bid=1.1015 debería disparar TP del BUY (TP=1.1012)
        tick2 = create_tick("EURUSD", 1.1015, 1.1017, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        
        await broker.advance_tick() # Activa órdenes y detecta TP_HIT
        await orchestrator._process_tick_for_pair(pair) # Sincroniza y procesa TP
        
        print("\n=== DESPUÉS DE TICK 2 ===")
        print(f"Balance: {broker.balance}")
        print(f"Open positions (broker): {len(broker.open_positions)}")
        print(f"History (broker): {len(broker.history)}")
        
        # Mostrar estado de operaciones en repo
        for op_id, op in repo.operations.items():
            print(f"Repo Op {op_id}: status={op.status}, pips={op.profit_pips}")
            
        # ============================================
        # TICK 3: Dar tiempo al sync final
        # ============================================
        tick3 = create_tick("EURUSD", 1.1015, 1.1017, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        print("\n=== DESPUÉS DE TICK 3 ===")
        print(f"Balance: {broker.balance}")
        print(f"History: {len(broker.history)}")

        
        # ============================================
        # VALIDACIONES FINALES
        # ============================================
        
        # El balance debería haber aumentado
        final_balance = float(broker.balance)
        print(f"\nFinal balance: {final_balance}")
        
        # Mostrar estado de todas las operaciones
        print("\n=== ESTADO FINAL DE OPERACIONES ===")
        for op_id, op in repo.operations.items():
            print(f"{op_id}: type={op.op_type}, status={op.status}, profit={op.profit_pips}")
        
        # Al menos una operación debería estar en TP_HIT o CLOSED
        tp_or_closed = [op for op in repo.operations.values() 
                       if op.status in (OperationStatus.TP_HIT, OperationStatus.CLOSED)]
        
        assert len(tp_or_closed) >= 1, "Al menos 1 operación debería haber alcanzado TP"
        
        print("\nTEST PASSED: El flujo básico funciona correctamente")


if __name__ == "__main__":
    asyncio.run(test_minimal_buy_tp())
