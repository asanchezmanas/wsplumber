
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
import traceback

# Setup paths
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tests"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker
from wsplumber.domain.types import CurrencyPair, OperationStatus
from wsplumber.domain.entities.cycle import CycleAccounting

# Monkey-patch CycleAccounting to track surplus
_original_process = CycleAccounting.process_recovery_tp

def tracked_process_recovery_tp(self, realized_profit):
    print(f"DEBUG: process_recovery_tp called with {realized_profit:.2f}. Current Surplus: {self.surplus_pips:.2f}")
    # traceback.print_stack(limit=5)
    return _original_process(self, realized_profit)

CycleAccounting.process_recovery_tp = tracked_process_recovery_tp

async def run_scenario(name, path):
    print(f"\n\n{'='*20} SCENARIO: {name} {'='*20}")
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    orchestrator = CycleOrchestrator(TradingService(broker, repo), WallStreetPlumberStrategy(), RiskManager(), repo)
    
    broker.load_csv(path)
    await broker.connect()
    
    tick_count = 0
    while True:
        tick = await broker.advance_tick()
        if not tick: break
        tick_count += 1
        
        await orchestrator.process_tick(tick)
        
        all_cycles = await repo.get_all_cycles()
        root_cycle = next((c for c in all_cycles if c.cycle_type.value == "main"), None)
        
        if root_cycle:
            acc = root_cycle.accounting
            if acc.surplus_pips != 0:
                print(f"Tick #{tick_count} | Root {root_cycle.id} | Surplus: {acc.surplus_pips:.1f} | Debt: {acc.pips_remaining:.1f}")

async def main():
    await run_scenario("NO GAP", "tests/scenarios/truth/r03_no_gap.csv")
    await run_scenario("WITH GAP", "tests/scenarios/truth/r03_with_gap.csv")

if __name__ == "__main__":
    asyncio.run(main())
