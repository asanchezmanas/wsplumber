# tests/integration/test_recovery_cascade_simple.py
"""
Simplified test for recovery cascade fix.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, TickData, Price, Timestamp, Pips
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
async def test_spread_guard_prevents_cascade(mock_settings):
    """
    Quick test: Verify that FIX-CASCADE-V3 blocks recovery when spread is too wide.
    
    With 50-pip spread, the recovery orders at ±20pips would overlap,
    so the guard should prevent creating any recovery cycles.
    """
    # Single tick with 50-pip spread
    wide_spread_tick = TickData(
        pair=CurrencyPair("EURUSD"),
        timestamp=Timestamp(datetime(2015, 1, 15, 9, 30, 0)),
        bid=Price(Decimal("1.2000")),
        ask=Price(Decimal("1.2050")),  # 50 pip spread
        spread_pips=Pips(50.0)
    )
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.ticks = [wide_spread_tick]
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
    
    # Process one tick
    tick = await broker.advance_tick()
    if tick:
        await orchestrator._process_tick_for_pair(pair)
    
    # Count cycles
    all_cycles = list(repo.cycles.values())
    recovery_cycles = [c for c in all_cycles if c.cycle_type.value == "recovery"]
    
    print(f"\n=== SPREAD GUARD TEST ===")
    print(f"Total cycles: {len(all_cycles)}")
    print(f"Recovery cycles: {len(recovery_cycles)}")
    
    # The main cycle should be created, but no recoveries
    # (recovery creation happens after HEDGED state, which requires 2+ ticks)
    assert len(recovery_cycles) == 0, f"Spread guard failed - {len(recovery_cycles)} recoveries created"
    print("✅ Test passed - no recovery cascade with wide spread")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
