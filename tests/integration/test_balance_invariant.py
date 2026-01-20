"""
Test Balance Invariant: Balance can ONLY increase or stay the same.

This test processes real tick data and verifies that the balance never decreases.
If balance decreases at any point, it means a position was closed at a loss,
which violates the core principle of the Wall Street Plumber system.

Run with: pytest tests/integration/test_balance_invariant.py -v -s
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
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
async def test_balance_never_decreases(mock_settings):
    """
    INVARIANT TEST: Balance can only increase or stay the same.
    
    This test runs through tick data and asserts that at no point
    does the balance decrease (which would indicate a loss being realized).
    """
    # Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv('tests/scenarios/eurusd_2015_full.csv')
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
    
    # Track balance history
    balance_history = []
    previous_balance = Decimal("10000.0")
    tick_count = 0
    max_ticks = 2000  # Limit for test speed
    
    # Process ticks
    while tick_count < max_ticks:
        tick = await broker.advance_tick()
        if tick is None:
            break
            
        await orchestrator._process_tick_for_pair(pair)
        tick_count += 1
        
        # Check balance
        acc_info = await broker.get_account_info()
        current_balance = acc_info.value["balance"]
        
        # CRITICAL ASSERTION: Balance must never decrease
        if current_balance < previous_balance:
            balance_history.append({
                "tick": tick_count,
                "previous": previous_balance,
                "current": current_balance,
                "diff": current_balance - previous_balance
            })
        
        previous_balance = current_balance
    
    # Final assertion
    if balance_history:
        print("\n=== BALANCE DECREASE VIOLATIONS ===")
        for violation in balance_history:
            print(f"Tick {violation['tick']}: {violation['previous']} -> {violation['current']} ({violation['diff']})")
        
    assert len(balance_history) == 0, f"Balance decreased {len(balance_history)} times! See log above."
    print(f"\n✅ Processed {tick_count} ticks with no balance decrease.")
    print(f"Final balance: {previous_balance}")


@pytest.mark.asyncio
async def test_recovery_cycles_are_opened(mock_settings):
    """
    Test that recovery cycles are actually opened when a Main goes HEDGED.
    
    RecA (active recoveries) should be > 0 at some point during processing.
    """
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv('tests/scenarios/eurusd_2015_full.csv')
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
    
    max_reca = 0
    tick_count = 0
    max_ticks = 2000
    
    from wsplumber.domain.entities.cycle import CycleType, CycleStatus
    
    while tick_count < max_ticks:
        tick = await broker.advance_tick()
        if tick is None:
            break
            
        await orchestrator._process_tick_for_pair(pair)
        tick_count += 1
        
        # Calculate RecA
        recovery_cycles = [c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY]
        rec_a = sum(1 for c in recovery_cycles if c.status != CycleStatus.CLOSED)
        
        if rec_a > max_reca:
            max_reca = rec_a
    
    print(f"\n=== RECOVERY CYCLE TEST ===")
    print(f"Processed {tick_count} ticks")
    print(f"Max RecA observed: {max_reca}")
    print(f"Total recovery cycles created: {len([c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY])}")
    
    # At least one recovery should have been opened at some point
    assert max_reca > 0 or tick_count < 100, "No active recoveries observed - recovery system may be broken"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
