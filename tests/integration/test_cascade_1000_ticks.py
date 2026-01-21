# tests/integration/test_cascade_1000_ticks.py
"""
TEST 3: Stress test with 1000 ticks and multiple gaps.

This test creates a more realistic scenario with:
- Multiple gaps throughout the data
- Various gap sizes (30, 50, 80 pips)
- Validates CASCADE guards hold under stress
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, CycleStatus, TickData, Price, Timestamp, Pips
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


def create_stress_ticks(num_ticks: int = 1000) -> list:
    """
    Create 1000 ticks with multiple gaps:
    - Gap 1: 30 pips at tick 200
    - Gap 2: 50 pips at tick 500
    - Gap 3: 80 pips at tick 800
    """
    ticks = []
    base_time = datetime(2015, 1, 15, 9, 0, 0)
    base_price = 1.2000
    
    price = base_price
    
    for i in range(num_ticks):
        # Apply gaps at specific points
        if i == 200:
            price += 0.0030  # 30 pip gap
        elif i == 500:
            price -= 0.0050  # 50 pip gap (reversal)
        elif i == 800:
            price += 0.0080  # 80 pip gap
        
        spread = 0.0002  # Normal 2-pip spread
        
        ticks.append(TickData(
            pair=CurrencyPair("EURUSD"),
            timestamp=Timestamp(base_time + timedelta(minutes=i)),
            bid=Price(Decimal(str(round(price, 5)))),
            ask=Price(Decimal(str(round(price + spread, 5)))),
            spread_pips=Pips(spread * 10000)
        ))
    
    return ticks


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.trading.default_lot_size = 0.01
    settings.trading.max_lot_size = 1.0
    settings.strategy.main_tp_pips = 10
    settings.strategy.main_step_pips = 10
    settings.strategy.recovery_tp_pips = 80
    settings.strategy.recovery_step_pips = 40
    settings.risk.max_exposure_per_pair = 1000.0
    return settings


@pytest.mark.asyncio
async def test_1000_ticks_stress(mock_settings):
    """
    Run 1000 ticks with 3 gaps of increasing size.
    
    Expected behavior:
    - CASCADE GUARDS should prevent explosion
    - Total recovery cycles should be < 20
    - Balance should remain stable (not explode or crash)
    """
    ticks = create_stress_ticks(num_ticks=1000)
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.ticks = ticks
    await broker.connect()
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock_settings):
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock_settings
        strategy = Strategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
    
    pair = CurrencyPair("EURUSD")
    tick_count = 0
    
    # Process all ticks
    for _ in range(len(ticks)):
        tick = await broker.advance_tick()
        if tick is None:
            break
        await orchestrator._process_tick_for_pair(pair)
        tick_count += 1
    
    # Analyze results
    all_cycles = list(repo.cycles.values())
    main_cycles = [c for c in all_cycles if c.cycle_type.value == "main"]
    recovery_cycles = [c for c in all_cycles if c.cycle_type.value == "recovery"]
    closed_rec = sum(1 for c in recovery_cycles if c.status == CycleStatus.CLOSED)
    
    # Get balance
    acc_info = await broker.get_account_info()
    final_balance = acc_info.value["balance"] if acc_info.success else 0
    
    print(f"\n=== TEST 3: 1000 TICKS STRESS TEST ===")
    print(f"Ticks processed: {tick_count}")
    print(f"Main cycles: {len(main_cycles)}")
    print(f"Recovery cycles: {len(recovery_cycles)}")
    print(f"Closed recoveries: {closed_rec}")
    print(f"Final balance: {final_balance}")
    
    # CRITICAL ASSERTIONS
    assert tick_count == 1000, f"Should process all 1000 ticks, got {tick_count}"
    assert len(recovery_cycles) <= 20, f"CASCADE BUG! {len(recovery_cycles)} recovery cycles (expected <= 20)"
    assert closed_rec <= 20, f"CASCADE BUG! {closed_rec} closed recoveries (expected <= 20)"
    assert final_balance >= 9000, f"BALANCE CRASH! Final balance {final_balance} < 9000"
    
    print("[OK] TEST 3 PASSED - Stress test with 3 gaps completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
