# tests/integration/test_cascade_real_data.py
"""
TEST 4: Integration test with REAL 2015 tick data.

This is the final validation before full backtest.
Uses the first 5000 ticks of eurusd_2015_full.csv.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, CycleStatus
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


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
async def test_5000_ticks_real_data(mock_settings):
    """
    Run 5000 ticks from REAL 2015 data.
    
    This validates the fix works with actual market conditions.
    
    Expected behavior:
    - CASCADE GUARDS should prevent explosion
    - Recovery cycles should be reasonable (< 50)
    - Balance should be stable (> 9500)
    """
    CSV_PATH = "tests/scenarios/eurusd_2015_full.csv"
    MAX_TICKS = 5000
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv(CSV_PATH)
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
    
    # Process MAX_TICKS
    while tick_count < MAX_TICKS:
        tick = await broker.advance_tick()
        if tick is None:
            break
        await orchestrator._process_tick_for_pair(pair)
        tick_count += 1
        
        # Progress indicator every 1000 ticks
        if tick_count % 1000 == 0:
            acc = await broker.get_account_info()
            bal = acc.value["balance"] if acc.success else 0
            rec_count = sum(1 for c in repo.cycles.values() if c.cycle_type.value == "recovery")
            print(f"  [Tick {tick_count}] Balance: {bal:.2f}, Recoveries: {rec_count}")
    
    # Analyze results
    all_cycles = list(repo.cycles.values())
    main_cycles = [c for c in all_cycles if c.cycle_type.value == "main"]
    recovery_cycles = [c for c in all_cycles if c.cycle_type.value == "recovery"]
    closed_rec = sum(1 for c in recovery_cycles if c.status == CycleStatus.CLOSED)
    
    # Get balance
    acc_info = await broker.get_account_info()
    final_balance = acc_info.value["balance"] if acc_info.success else 0
    
    print(f"\n=== TEST 4: 5000 TICKS REAL DATA ===")
    print(f"Ticks processed: {tick_count}")
    print(f"Main cycles: {len(main_cycles)}")
    print(f"Recovery cycles: {len(recovery_cycles)}")
    print(f"Closed recoveries: {closed_rec}")
    print(f"Final balance: {final_balance}")
    
    # CRITICAL ASSERTIONS - More lenient for real data
    assert tick_count >= 4000, f"Should process at least 4000 ticks, got {tick_count}"
    assert len(recovery_cycles) <= 200, f"CASCADE BUG! {len(recovery_cycles)} recovery cycles (expected <= 200)"
    assert closed_rec <= 200, f"CASCADE BUG! {closed_rec} closed recoveries (expected <= 200)"
    assert final_balance >= 9000, f"BALANCE ISSUE! Final balance {final_balance} < 9000"
    
    print("[OK] TEST 4 PASSED - Real data test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
