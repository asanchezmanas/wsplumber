
import asyncio
from datetime import datetime
from decimal import Decimal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import (
    CurrencyPair, CycleType, OperationStatus, OperationType, 
    Price, TickData, StrategySignal, SignalType, Pips, CycleStatus
)
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from wsplumber.infrastructure.logging.safe_logger import setup_logging

async def test_recovery_cascade():
    # Setup standard logging for the test
    setup_logging(level="DEBUG", environment="development")
    
    print("\n" + "="*80)
    print("TESTING RECOVERY CASCADE LOGIC")
    print("="*80)

    # 1. Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    trading_service = TradingService(broker, repo)
    risk_manager = RiskManager()
    strategy = WallStreetPlumberStrategy()
    
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        strategy=strategy,
        risk_manager=risk_manager,
        repository=repo
    )
    
    pair = CurrencyPair("EURUSD")
    await broker.connect()
    
    # helper for processing tick
    async def process_tick(price):
        tick = TickData(
            timestamp=datetime.now(),
            pair=pair,
            bid=Price(Decimal(str(price))),
            ask=Price(Decimal(str(price + 0.0002))),
            spread_pips=Pips(2.0)
        )
        broker.ticks.append(tick)
        await broker.advance_tick()
        print(f"Tick: {price} | Broker positions: {[p.status.name for p in broker.open_positions.values()]}")
        try:
            await orchestrator.process_tick(tick)
        except Exception as e:
            print(f"Error processing tick: {e}")
        return tick

    # --- SCENARIO START ---
    
    # 2. Open Cycle - FORCE SIGNAL if needed
    print("\n--- STEP 1: Opening New Cycle ---")
    
    # Force a signal because the strategy might not give one on first tick
    signal = StrategySignal(
        signal_type=SignalType.OPEN_CYCLE,
        pair=pair,
        metadata={"reason": "manual_test"}
    )
    await orchestrator._handle_signal(signal, await process_tick(1.1000))
    
    cycles = list(repo.cycles.values())
    main_cycle = cycles[0]
    print(f"Cycle created: {main_cycle.id}")
    print(f"Debt units: {main_cycle.accounting.debt_units}") # Should be [20.0]

    # 3. Activate Both (HEDGE)
    print("\n--- STEP 2: Activating Both (HEDGE) ---")
    await process_tick(1.1010) # Activates BUY (1.1010 > 1.1007)
    await process_tick(1.0990) # Activates SELL (1.0990 < 1.0995)
    
    # Now it should be HEDGED. 
    print(f"Cycle status: {main_cycle.status.name}") # Should be HEDGED
    
    # 4. SELL TP -> Transition to IN_RECOVERY
    print("\n--- STEP 3: SELL TP Hit -> Transition to IN_RECOVERY ---")
    # SELL entry was ~1.0993. TP should be ~1.0983.
    await process_tick(1.0980) 
    
    print(f"Cycle status: {main_cycle.status.name}") # Should be IN_RECOVERY
    # Should have opened a Recovery cycle (±20 pips from current price)
    
    # 5. Recovery Failure (Both active)
    print("\n--- STEP 4: Recovery Failure (Both Active) ---")
    # Find the recovery cycle
    recovery_cycles = [c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY]
    rec_cycle = recovery_cycles[0]
    print(f"Recovery cycle: {rec_cycle.id}")
    
    # Trigger activations for both recovery orders
    # Current price was ~1.0980. Recovery orders @ 1.1000 and 1.0960 approx.
    await process_tick(1.1010) # Activates REC_B
    await process_tick(1.0950) # Activates REC_S (Failure!)
    
    print("\nChecking debt after recovery failure:")
    print(f"Main Cycle Debt Units: {main_cycle.accounting.debt_units}") # Should be [20.0, 40.0]
    print(f"Net Pips: {main_cycle.accounting.net_pips}") # Should be -60.0

    # 6. Recovery TP (Successful recovery)
    print("\n--- STEP 5: Recovery TP Hit ---")
    # Finding REC_2
    rec_cycles_2 = [c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY and "REC_EURUSD_2" in c.id]
    if not rec_cycles_2:
        rec_cycles_2 = [c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY and c.id != rec_cycle.id]
    
    rec_cycle_2 = rec_cycles_2[0]
    print(f"Using Recovery cycle: {rec_cycle_2.id}")
    
    # Check current debt units BEFORE TP
    main_cycle = (await repo.get_cycle(main_cycle.id)).value
    print(f"Debt units BEFORE Step 5: {main_cycle.accounting.debt_units}")

    # Activate ONLY ONE side. 
    # From logs: REC_2 entries were ~1.1022 (B) and ~1.0982 (S)
    # Current price is 1.0950 from Step 4.
    print("Activating REC_2 SELL side at 1.1000...")
    await process_tick(1.1000) # Activates REC_2_S (1.1000 >= 1.0982)
    # REC_2_B (1.1022) stays pending (1.1000 < 1.1022)
    
    # Hit TP (1.0982 - 80 pips = 1.0902)
    print("Moving price to hit Recovery TP (80 pips) at 1.0890...")
    await process_tick(1.0890)
    
    print("\nProcessing results after Recovery TP (+80 pips):")
    main_cycle = (await repo.get_cycle(main_cycle.id)).value
    
    print(f"Main Cycle Status: {main_cycle.status.name}") 
    print(f"Main Cycle Debt Units: {main_cycle.accounting.debt_units}")
    print(f"Total Recovered: {main_cycle.accounting.pips_recovered}")
    print(f"Net Pips: {main_cycle.accounting.net_pips}")

    if main_cycle.status == CycleStatus.CLOSED:
        print("\nSUCCESS: Recovery Cascade logic verified correctly!")
    else:
        print("\nFAILURE: Cycle status is", main_cycle.status.name)

if __name__ == "__main__":
    asyncio.run(test_recovery_cascade())
