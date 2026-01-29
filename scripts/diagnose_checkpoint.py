import pickle
import os
from wsplumber.domain.entities.cycle import CycleStatus
from wsplumber.domain.entities.operation import OperationStatus

def analyze_checkpoint(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "rb") as f:
        state = pickle.load(f)
    
    repo = state["repo"]
    broker_balance = state["broker_balance"]
    
    print(f"--- Checkpoint Analysis: {path} ---")
    print(f"Broker Balance: {broker_balance}")
    print(f"Total Cycles: {len(repo.cycles)}")
    print(f"Total Operations: {len(repo.operations)}")
    
    active_cycles = [c for c in repo.cycles.values() if c.status == CycleStatus.ACTIVE]
    print(f"Active Cycles: {len(active_cycles)}")
    
    # Analyze debt in active cycles
    total_debt = 0.0
    cycles_with_debt = 0
    for c in active_cycles:
        if hasattr(c, 'accounting'):
            total_debt += float(c.accounting.pips_remaining)
            if c.accounting.pips_remaining > 0:
                cycles_with_debt += 1
                
    print(f"Cycles with Debt: {cycles_with_debt}")
    print(f"Total Owed Pips: {total_debt:.1f}")
    
    # Operation breakdown
    op_stats = {}
    for op in repo.operations.values():
        st = op.status.value
        op_stats[st] = op_stats.get(st, 0) + 1
    
    print("\nOperation Status Breakdown:")
    for st, count in op_stats.items():
        print(f" - {st}: {count}")

    # Find the oldest active cycle
    if active_cycles:
        oldest = min(active_cycles, key=lambda x: x.id)
        print(f"\nOldest Active Cycle: {oldest.id}")
        if hasattr(oldest, 'accounting'):
             print(f" - Owed: {oldest.accounting.pips_remaining}")
             print(f" - Surplus: {oldest.accounting.surplus_pips}")
             
        # List its operations
        ops = [o for o in repo.operations.values() if o.cycle_id == oldest.id]
        print(f" - Operations ({len(ops)}):")
        for o in ops:
            print(f"   * {o.id} | {o.op_type.value} | {o.status.value} | Entry: {o.entry_price} | TP: {o.tp_price}")

if __name__ == "__main__":
    analyze_checkpoint("week5.checkpoint")
