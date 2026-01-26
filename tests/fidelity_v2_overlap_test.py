import asyncio
from decimal import Decimal
from datetime import datetime
from tests.fixtures.simulated_broker import SimulatedBroker
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, TickData, Timestamp, Price, Pips

async def test_overlap_patience():
    print("\n--- TEST: OVERLAP PATIENCE (BE) ---")
    broker = SimulatedBroker()
    await broker.connect()
    repo = InMemoryRepository()
    orchestrator = CycleOrchestrator(
        TradingService(broker, repo),
        WallStreetPlumberStrategy(),
        RiskManager(),
        repo
    )
    pair = CurrencyPair("EURUSD")

    # 1. Setup ticks in broker
    ticks = [
        TickData(pair, Price(Decimal("1.1000")), Price(Decimal("1.1001")), Timestamp(datetime.now()), Pips(1.0)), # Tick 0: Start
        TickData(pair, Price(Decimal("1.1006")), Price(Decimal("1.1007")), Timestamp(datetime.now()), Pips(1.0)), # Tick 1: MB active
        TickData(pair, Price(Decimal("1.0994")), Price(Decimal("1.0995")), Timestamp(datetime.now()), Pips(1.0)), # Tick 2: MS active (Hedge)
        TickData(pair, Price(Decimal("1.1016")), Price(Decimal("1.1017")), Timestamp(datetime.now()), Pips(1.0)), # Tick 3: MB TP -> Recovery
        TickData(pair, Price(Decimal("1.1050")), Price(Decimal("1.1051")), Timestamp(datetime.now()), Pips(1.0)), # Tick 4: REC_B profit, REC_S trail
        TickData(pair, Price(Decimal("1.1040")), Price(Decimal("1.1041")), Timestamp(datetime.now()), Pips(1.0)), # Tick 5: Trigger REC_S -> Overlap
    ]
    broker.ticks = ticks
    broker.current_tick_index = -1

    # Tick 1: Start cycle
    await orchestrator.process_tick(await broker.advance_tick())
    c_id = next(iter(repo.cycles))
    print(f"Cycle created: {c_id}")

    # Tick 2: Trigger MB
    await orchestrator.process_tick(await broker.advance_tick())
    
    # Tick 3: Trigger MS (Hedge)
    await orchestrator.process_tick(await broker.advance_tick())
    
    # Tick 4: MB TP -> Recovery starts
    await orchestrator.process_tick(await broker.advance_tick())
    active_cycles = await repo.get_active_cycles(pair)
    rec_cycle = next((c for c in active_cycles.value if c.cycle_type.value == "recovery"), None)
    if rec_cycle:
        print(f"Recovery Cycle Created: {rec_cycle.id}")
        ops = await repo.get_operations_by_cycle(rec_cycle.id)
        print(f"REC Ops after TICK 4: {[(o.op_type.value, o.status.value, float(o.entry_price)) for o in ops.value]}")
    
    # Tick 5: Move price to 1.1050 (REC_B should trail REC_S)
    await orchestrator.process_tick(await broker.advance_tick())
    if rec_cycle:
        ops = await repo.get_operations_by_cycle(rec_cycle.id)
        print(f"REC Ops after TICK 5: {[(o.op_type.value, o.status.value, float(o.entry_price)) for o in ops.value]}")
    
    # Tick 6: Drop price to 1.1040 (Trigger REC_S)
    await orchestrator.process_tick(await broker.advance_tick())
    if rec_cycle:
        ops = await repo.get_operations_by_cycle(rec_cycle.id)
        print(f"REC Ops after TICK 6: {[(o.op_type.value, o.status.value, float(o.entry_price)) for o in ops.value]}")
    
    # locked_profit = 1.1045 - 1.1016 = 29 pips (< 50)
    
    # Check states
    cycles = await repo.get_active_cycles(pair)
    rec_cycle = next((c for c in cycles.value if c.cycle_type.value == "recovery"), None)
    if not rec_cycle:
        print("FAILED: No recovery cycle found")
        return

    ops_res = await repo.get_operations_by_cycle(rec_cycle.id)
    active_ops = [op for op in ops_res.value if op.status.value == "active"]
    print(f"Active Ops in recovery: {len(active_ops)}")
    for op in active_ops:
        print(f"  Op: {op.op_type.value}, Entry: {op.actual_entry_price}, SL: {op.sl_price}, Metadata: {op.metadata.get('overlap_be')}")
        if op.metadata.get("overlap_be"):
            print("SUCCESS: BE Protection applied instead of closing")

if __name__ == "__main__":
    asyncio.run(test_overlap_patience())
