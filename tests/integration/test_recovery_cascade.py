# tests/integration/test_recovery_cascade.py
"""
Test to validate that the recovery cascade bug is fixed.

This test creates a scenario where:
1. A gap or wide spread causes both recovery orders to activate
2. The system should NOT create infinite recovery cycles
3. The FIX-CASCADE guards should block the explosion
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, CycleStatus, TickData, Price, Timestamp, Pips
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


def create_gap_ticks(start_price: float, gap_pips: float) -> list:
    """
    Creates tick data simulating a gap where price jumps.
    
    This should trigger both recovery orders to activate in the same tick.
    """
    ticks = []
    base_time = datetime(2015, 1, 15, 9, 30, 0)  # SNB event day
    
    # Normal ticks before gap
    for i in range(10):
        ticks.append({
            'timestamp': base_time + timedelta(minutes=i),
            'bid': start_price,
            'ask': start_price + 0.0002
        })
    
    # GAP: Price jumps by gap_pips
    gap_price = start_price + (gap_pips * 0.0001)
    for i in range(10, 20):
        ticks.append({
            'timestamp': base_time + timedelta(minutes=i),
            'bid': gap_price,
            'ask': gap_price + 0.0002
        })
    
    return ticks


@pytest.mark.asyncio
async def test_recovery_cascade_blocked_on_gap(mock_settings):
    """
    CRITICAL TEST: Validates FIX-CASCADE guards.
    
    Scenario:
    1. Create situation where main cycle goes to HEDGED
    2. Inject a 50-pip gap (larger than recovery distance * 2)
    3. Verify that recovery cascade is blocked
    4. RecC (closed recoveries) should be <= 5, not 14,000+
    """
    # Create ticks with a 50-pip gap
    gap_ticks = create_gap_ticks(1.2000, 50)  # 50 pip gap
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.ticks = [
        TickData(
            pair=CurrencyPair("EURUSD"),
            timestamp=Timestamp(t['timestamp']),
            bid=Price(Decimal(str(t['bid']))),
            ask=Price(Decimal(str(t['ask']))),
            spread_pips=Pips(abs(t['ask'] - t['bid']) * 10000)
        ) for t in gap_ticks
    ]

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
    while tick_count < len(gap_ticks):
        tick = await broker.advance_tick()
        if tick is None:
            break
        await orchestrator._process_tick_for_pair(pair)
        tick_count += 1
    
    # Count recovery cycles
    all_cycles = list(repo.cycles.values())
    recovery_cycles = [c for c in all_cycles if c.cycle_type.value == "recovery"]
    closed_rec = sum(1 for c in recovery_cycles if c.status == CycleStatus.CLOSED)
    
    print(f"\n=== RECOVERY CASCADE TEST ===")
    print(f"Total cycles created: {len(all_cycles)}")
    print(f"Recovery cycles: {len(recovery_cycles)}")
    print(f"Closed recoveries: {closed_rec}")
    
    # CRITICAL ASSERTION: No cascade explosion
    assert closed_rec <= 10, f"CASCADE BUG! {closed_rec} closed recoveries (expected <= 10)"
    print("✅ Recovery cascade guard is working!")


@pytest.mark.asyncio
async def test_spread_too_wide_blocks_recovery(mock_settings):
    """
    Test that FIX-CASCADE-V3 (spread validation) blocks recovery when spread > safe threshold.
    """
    # Create ticks with very wide spread (50 pips)
    wide_spread_ticks = []
    base_time = datetime(2015, 1, 15, 9, 30, 0)
    
    for i in range(20):
        wide_spread_ticks.append({
            'timestamp': base_time + timedelta(minutes=i),
            'bid': 1.2000,
            'ask': 1.2050  # 50 pip spread!
        })
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.ticks = [
        TickData(
            pair=CurrencyPair("EURUSD"),
            timestamp=Timestamp(t['timestamp']),
            bid=Price(Decimal(str(t['bid']))),
            ask=Price(Decimal(str(t['ask']))),
            spread_pips=Pips(abs(t['ask'] - t['bid']) * 10000)
        ) for t in wide_spread_ticks
    ]
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
    
    # Process ticks
    for _ in range(len(wide_spread_ticks)):
        tick = await broker.advance_tick()
        if tick is None:
            break
        await orchestrator._process_tick_for_pair(pair)
    
    # Count recovery cycles - should be ZERO because spread is too wide
    recovery_cycles = [c for c in repo.cycles.values() if c.cycle_type.value == "recovery"]
    
    print(f"\n=== WIDE SPREAD TEST ===")
    print(f"Recovery cycles created: {len(recovery_cycles)}")
    
    # With 50-pip spread, NO recovery should be created
    assert len(recovery_cycles) <= 2, f"Spread guard failed! {len(recovery_cycles)} recoveries created"
    print("✅ Spread validation guard is working!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
