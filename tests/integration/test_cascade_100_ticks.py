# tests/integration/test_cascade_100_ticks.py
"""
TEST 2: Integration test with 100 controlled ticks.

This test uses synthetic tick data with a known gap to verify
that the cascade guards work in the real orchestrator flow.
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


def create_controlled_ticks(num_ticks: int = 100, gap_at_tick: int = 50, gap_pips: float = 60) -> list:
    """
    Create controlled tick data with a gap at a specific point.
    
    Args:
        num_ticks: Total number of ticks
        gap_at_tick: Tick number where gap occurs
        gap_pips: Size of gap in pips
    """
    ticks = []
    base_time = datetime(2015, 1, 15, 9, 0, 0)
    base_price = 1.2000
    
    for i in range(num_ticks):
        # Before gap: stable price
        if i < gap_at_tick:
            price = base_price
        # At gap: price jumps
        else:
            price = base_price + (gap_pips * 0.0001)
        
        spread = 0.0002  # Normal 2-pip spread
        
        ticks.append(TickData(
            pair=CurrencyPair("EURUSD"),
            timestamp=Timestamp(base_time + timedelta(minutes=i)),
            bid=Price(Decimal(str(price))),
            ask=Price(Decimal(str(price + spread))),
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
async def test_100_ticks_with_gap(mock_settings):
    """
    Run 100 ticks with a 60-pip gap at tick 50.
    
    Expected behavior:
    - Main cycle opens at tick 1
    - Gap triggers hedging or recovery flow
    - CASCADE GUARDS should prevent explosion
    - Total recovery cycles should be < 10
    """
    ticks = create_controlled_ticks(num_ticks=100, gap_at_tick=50, gap_pips=60)
    
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
    
    print(f"\n=== TEST 2: 100 TICKS WITH 60-PIP GAP ===")
    print(f"Ticks processed: {tick_count}")
    print(f"Main cycles: {len(main_cycles)}")
    print(f"Recovery cycles: {len(recovery_cycles)}")
    print(f"Closed recoveries: {closed_rec}")
    print(f"Final balance: {broker.balance}")
    
    # CRITICAL ASSERTIONS
    assert tick_count == 100, f"Should process all 100 ticks, got {tick_count}"
    assert len(recovery_cycles) <= 10, f"CASCADE BUG! {len(recovery_cycles)} recovery cycles (expected <= 10)"
    assert closed_rec <= 10, f"CASCADE BUG! {closed_rec} closed recoveries (expected <= 10)"
    
    print("[OK] TEST 2 PASSED - No cascade explosion in 100 ticks with gap")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
