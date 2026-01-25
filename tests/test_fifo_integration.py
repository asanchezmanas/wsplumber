"""
Integration test for FIX-FIFO-BROKER: Closing neutralized positions.
Uses REAL SimulatedBroker and all components.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

sys.path.insert(0, 'src')
sys.path.insert(0, 'tests')

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, TickData, Price, Pips
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker


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


def make_tick(pair, price, ts):
    """Helper to create TickData with spread."""
    bid = Price(price)
    ask = Price(price + Decimal("0.00010"))
    spread = Pips(1.0)
    return TickData(pair=pair, bid=bid, ask=ask, timestamp=ts, spread_pips=spread)


async def run_equity_drain_test():
    print("=" * 60)
    print("INTEGRATION TEST: FIX-FIFO-BROKER Equity Drain")
    print("=" * 60)
    
    pair = CurrencyPair("EURUSD")
    mock = mock_settings()
    broker = SimulatedBroker(initial_balance=10000.0)
    
    # Create synthetic ticks
    base = Decimal("1.10000")
    ticks = []
    t0 = datetime(2015, 1, 1, 0, 0, 0)
    
    # P1: Rise
    for i in range(100):
        ticks.append(make_tick(pair, base + Decimal(str(i * 0.00002)), t0 + timedelta(minutes=i)))
    
    # P2: Drop then rise (HEDGE)
    for i in range(100):
        if i < 50:
            p = base + Decimal("0.00200") - Decimal(str(i * 0.00006))
        else:
            p = base - Decimal("0.00100") + Decimal(str((i-50) * 0.00008))
        ticks.append(make_tick(pair, p, t0 + timedelta(minutes=100+i)))
    
    # P3: Oscillate (collisions)
    for i in range(300):
        off = Decimal(str(0.0005 * (1 if (i // 15) % 2 == 0 else -1)))
        p = base + off + Decimal(str((i % 15) * 0.00003))
        ticks.append(make_tick(pair, p, t0 + timedelta(minutes=200+i)))
    
    # P4: Strong up (recovery TP)
    for i in range(200):
        ticks.append(make_tick(pair, base + Decimal("0.00100") + Decimal(str(i * 0.0005)), 
                              t0 + timedelta(minutes=500+i)))
    
    broker.ticks = ticks
    broker.current_tick_index = -1
    print(f"Created {len(ticks)} ticks")
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        repo = InMemoryRepository()
        trading = TradingService(broker=broker, repository=repo)
        risk = RiskManager()
        risk.settings = mock
        strategy = WallStreetPlumberStrategy()
        
        orch = CycleOrchestrator(trading, strategy, risk, repo)
        await orch.start([pair])
        
        tick_count = 0
        for i, tick in enumerate(ticks):
            broker.current_tick = tick
            broker.current_tick_index = i
            try:
                await orch.process_tick(tick)
                tick_count += 1
                if tick_count % 100 == 0:
                    gap = float(broker.equity - broker.balance)
                    print(f"[{tick_count}] Bal:{broker.balance:.2f} Eq:{broker.equity:.2f} Gap:{gap:.2f} Pos:{len(broker.open_positions)}")
            except Exception as e:
                print(f"Error at {tick_count}: {e}")
                import traceback
                traceback.print_exc()
                break
    
    print()
    print("=" * 60)
    gap = float(broker.equity - broker.balance)
    print(f"FINAL: Bal={broker.balance:.2f} Eq={broker.equity:.2f} Gap={gap:.2f} Pos={len(broker.open_positions)}")
    
    if abs(gap) < 200:
        print("SUCCESS: Gap < $200")
        return True
    else:
        print(f"FAIL: Gap={gap:.2f} > $200")
        return False


if __name__ == "__main__":
    result = asyncio.run(run_equity_drain_test())
    sys.exit(0 if result else 1)
