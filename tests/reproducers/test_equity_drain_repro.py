import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.domain.types import CurrencyPair, CycleStatus, OperationStatus
from tests.fixtures.simulated_broker import SimulatedBroker
from tests.integration.test_scenarios import InMemoryRepository

from tests.fixtures.simulated_broker import SimulatedBroker, SimulatedPosition

async def test_equity_drain_repro():
    print("\n--- REPRODUCER: EQUITY DRAIN ---")
    
    # 1. Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    from wsplumber.domain.types import TickData, Price, Timestamp, Pips, SignalType, StrategySignal
    pair = CurrencyPair("EURUSD")
    
    start_time = datetime(2022, 1, 1, 10, 0, 0)
    
    def get_tick(offset_seconds=0):
        return TickData(
            pair=pair,
            bid=Price(Decimal("1.1000")),
            ask=Price(Decimal("1.1001")),
            timestamp=Timestamp(start_time + timedelta(seconds=offset_seconds)),
            spread_pips=Pips(1.0)
        )

    tick0 = get_tick(0)
    broker.ticks = [get_tick(i) for i in range(1000)] # Increased ticks for more time
    broker.current_tick_index = 0
    broker.current_tick = tick0
    
    repo = InMemoryRepository()
    risk_mgr = RiskManager()
    strategy = WallStreetPlumberStrategy()
    trading_service = TradingService(broker=broker, repository=repo)
    orchestrator = CycleOrchestrator(trading_service, strategy, risk_mgr, repo)
    
    # Helper to convert Op to SimulatedPosition
    def to_pos(op, ticket):
        return SimulatedPosition(
            ticket=ticket,
            operation_id=str(op.id),
            pair=op.pair,
            order_type=op.op_type,
            entry_price=op.entry_price,
            tp_price=op.tp_price,
            lot_size=op.lot_size,
            open_time=datetime.now(), # This will be updated by broker later
            status=op.status
        )

    # 2. Open a Cycle and force Hedge (Level 0)
    print("\n[STEP 1] Opening Root Main cycle...")
    await orchestrator.process_tick(tick0)
    root_cycle = orchestrator._active_cycles[pair]
    
    # Force activation and hedge
    for op in root_cycle.main_operations:
        op.status = OperationStatus.ACTIVE
        op.broker_ticket = f"ROOT_{op.id}"
        broker.open_positions[op.broker_ticket] = to_pos(op, op.broker_ticket)
        await repo.save_operation(op)
        
    root_cycle.status = CycleStatus.HEDGED
    root_cycle.accounting.pips_locked = Pips(20.0)
    root_cycle.accounting.pips_remaining = 20.0
    root_cycle.accounting.debt_units = [20.0]
    await repo.save_cycle(root_cycle)
    
    # 3. Step 2: Simulate Recovery COLLISION (Level 1)
    print("\n[STEP 2] Simulating Recovery Collision (Failure)...")
    tick1 = get_tick(60) # Advance 1 minute
    broker.current_tick = tick1
    broker.current_tick_index = 60
    
    await orchestrator._handle_signal(StrategySignal(
        signal_type=SignalType.OPEN_RECOVERY,
        pair=pair,
        metadata={"reason": "test_collision", "parent_cycle": root_cycle.id}
    ), tick1)
    
    # Resolve the recovery cycle
    all_cycles = await repo.get_all_cycles()
    rec1 = next(c for c in all_cycles if c.id.startswith("REC") and c.recovery_level == 1)
    
    # Fetch operations from repo
    rec1_ops = (await repo.get_operations_by_cycle(rec1.id)).value
    
    # Force recovery collision: activate both ops
    for op in rec1_ops:
        op.status = OperationStatus.ACTIVE
        op.broker_ticket = f"REC1_{op.id}"
        broker.open_positions[op.broker_ticket] = to_pos(op, op.broker_ticket)
        await repo.save_operation(op)
    
    # Handle failure (marks rec1 as CLOSED and opens cycle for level 2)
    blocking_op = rec1_ops[1]
    tick2 = get_tick(120) # Advance again
    broker.current_tick = tick2
    broker.current_tick_index = 120
    await orchestrator._handle_recovery_failure(rec1, blocking_op, tick2)
    
    print(f"Rec1 Status: {rec1.status.value} (Should be CLOSED)")
    # Parent debt should be 20 (initial) + 40 (failed recovery) = 60
    print(f"Root Debt: {root_cycle.accounting.pips_remaining} (Should be 60.0)")
    
    # 4. Step 3: Simulate Successful Recovery (Level 2)
    print("\n[STEP 3] Simulating Successful Recovery TP...")
    # Find active Level 2 recovery (created by orchestrator in Step 2)
    all_cycles = await repo.get_all_cycles()
    rec2 = next(c for c in all_cycles if c.recovery_level == 2 and c.status == CycleStatus.ACTIVE)
    
    # Force TP hit on one op of rec2
    rec2_ops = (await repo.get_operations_by_cycle(rec2.id)).value
    tp_op = rec2_ops[0]
    tp_op.status = OperationStatus.ACTIVE 
    tp_op.broker_ticket = f"REC2_{tp_op.id}"
    tp_op.actual_entry_price = tp_op.entry_price
    
    # Mark TP HIT
    tp_op.status = OperationStatus.TP_HIT
    tp_op.actual_close_price = Price(Decimal(str(tp_op.entry_price)) + Decimal("0.0080")) if tp_op.is_buy else \
                               Price(Decimal(str(tp_op.entry_price)) - Decimal("0.0080"))
    
    broker.open_positions[tp_op.broker_ticket] = to_pos(tp_op, tp_op.broker_ticket)
    broker.open_positions[tp_op.broker_ticket].status = OperationStatus.TP_HIT
    broker.open_positions[tp_op.broker_ticket].actual_close_price = tp_op.actual_close_price
    
    await repo.save_operation(tp_op)
    
    # Check hierarchy before resolving
    all_cycles = await repo.get_all_cycles()
    print("\n--- BEFORE RESOLUTION ---")
    for c in all_cycles:
        p_res = await repo.get_operations_by_cycle(c.id)
        p_ops = p_res.value if p_res.success else []
        print(f"Cycle: {c.id} Status: {c.status.value} Parent: {c.parent_cycle_id}")
    
    # Handle Recovery TP (This should trigger Parent closure)
    tick3 = get_tick(180)
    broker.current_tick = tick3
    broker.current_tick_index = 180
    await orchestrator._handle_recovery_tp(rec2, tick3)
    
    # 5. FINAL VERIFICATION
    print("\n--- FINAL VERIFICATION ---")
    final_root = (await repo.get_cycle(root_cycle.id)).value
    print(f"Root Status: {final_root.status.value} (Should be CLOSED)")
    
    open_tickets = list(broker.open_positions.keys())
    print(f"Open Tickets in Broker: {open_tickets}")
    
    # The fix should close ROOT and REC1 positions.
    zombies = [t for t in open_tickets if "REC1" in t or "ROOT" in t or "REC2" in t]
    if zombies:
        print("\n--- REPO DIAGNOSTICS FOR ZOMBIES ---")
        all_ops = await repo.get_all_operations()
        for op in all_ops:
            if any(z in str(op.broker_ticket) for z in zombies):
                 print(f"OP IN REPO: id={op.id} cycle={op.cycle_id} status={op.status.value} ticket={op.broker_ticket}")
        
        print(f"FAILURE: Zombie positions found: {zombies}")
        return False
    elif final_root.status != CycleStatus.CLOSED:
        print(f"FAILURE: Root Main still open.")
        return False
    else:
        print("SUCCESS: All related positions closed.")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_equity_drain_repro())
    sys.exit(0 if success else 1)
