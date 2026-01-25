import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch
import json

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker

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

async def run_stats_check(max_ticks=30000):
    csv_path = Path("tests/scenarios/eurusd_2015_full.csv")
    pair = CurrencyPair("EURUSD")
    mock = mock_settings()
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv(str(csv_path))
    await broker.connect()
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
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
        
        tick_count = 0
        try:
            while tick_count < max_ticks:
                tick = await broker.advance_tick()
                if tick is None:
                    break
                # Use standard loop instead of internal _process_tick_for_pair to be closer to reality
                await orchestrator.process_tick(tick)
                tick_count += 1
                
        except Exception as e:
            print(f"Error: {e}")

    # Final stats
    cycles_res = await repo.get_all_cycles()
    all_cycles = cycles_res.value if cycles_res.success else []
    resolved = [c for c in all_cycles if c.status.value == "closed"]
    active = [c for c in all_cycles if c.status.value != "closed"]

    stats = {
        "ticks_processed": tick_count,
        "balance": float(broker.balance),
        "equity": float(broker.equity),
        "cycles_resolved_count": len(resolved),
        "cycles_active_count": len(active),
        "drawdown": float(broker.balance - broker.equity)
    }

    with open("backtest_stats_summary.json", "w") as f:
        json.dump(stats, f, indent=4)
    
    print("Stats saved to backtest_stats_summary.json")

if __name__ == "__main__":
    asyncio.run(run_stats_check(30000))
