# Recovery Cascade Logic - Detailed Specification
# Recovery Cascade Logic - Detailed Specification

## Overview

This document specifies the recovery cascade flow, which is fundamentally different from main operation flow.

---

## Key Difference: Main vs Recovery

| Aspect | Main Operations | Recovery Operations |
|--------|-----------------|---------------------|
| **Fail condition** | Both mains activate (HEDGED) | Opposite recovery activates |
| **Creates new cycle** | On TP hit | On TP hit OR on failure |
| **Position of next** | ±5 pips from current price | ±20 pips from entry of blocking op |
| **Debt per unit** | 20 pips (main + hedge) | 40 pips per failed recovery |

---

## Recovery Cascade Flow

### Step 1: Initial Recovery (R1)
```
Trigger: Main hits TP in HEDGED state
Position: ±20 pips from hedge entry (= main TP level)
```

### Step 2: Recovery Failure Detection
```
R1 FAILS when: R1_B activates → price reverses → R1_S activates (or vice versa)
Debt added: +40 pips
```

### Step 3: Renewal Position
```
New recovery (R2) placed at: ±20 pips from entry of the BLOCKING operation
- If R1_S blocked R1_B → R2 at ±20 pips from R1_S entry
- If R1_B blocked R1_S → R2 at ±20 pips from R1_B entry
```

### Step 4: Recovery Success (TP Hit)
```
Recovery touches TP: +80 pips profit
FIFO liquidation:
1. Pay main+hedge unit (20 pips) if unpaid
2. Pay oldest failed recovery (40 pips each)
3. Continue until profit exhausted or all debts paid
```

### Step 5: Cycle Close Condition
```
IF debt_remaining == 0 AND surplus >= 20 pips:
    CLOSE entire cycle (main + hedge + all neutralized recoveries)
ELSE:
    Open new recovery at ±20 pips from the TP that was just hit
```

---

## Example Walkthrough

```
1. Main+Hedge neutralized          → Debt: 20 pips
   R1 created at ±20 from hedge entry

2. R1_B activates → R1_S activates → Debt: 60 pips
   R2 created at ±20 from R1_S entry

3. R2_S activates → R2_B activates → Debt: 100 pips
   R3 created at ±20 from R2_B entry

4. R3_B activates → HITS TP (+80)  → FIFO:
   - Main+Hedge: 80-20=60 remaining ✓
   - R1: 60-40=20 remaining ✓
   - R2: 20<40, cannot close ✗
   R4 created at ±20 from R3_B TP

5. R4_B activates → R4_S activates → Debt: 40(R2)+40(R4)=80 pips
   R5 created at ±20 from R4_S entry

6. R5_S activates → HITS TP (+80)  → FIFO:
   - R2: 80-40=40 remaining ✓
   - R4: 40-40=0 remaining ✓
   Debt=0, surplus=0 → NOT >=20, must open R6
   R6 created at ±20 from R5_S TP

7. R6_S activates → HITS TP (+80)  → 
   Debt=0, surplus=80 → >=20 ✓
   CLOSE ENTIRE CYCLE
```

---

## Implementation Changes Required

### 1. Recovery Failure Detection
```python
# In _check_operations_status, for recovery operations:
if op.is_recovery and op.status == OperationStatus.ACTIVE:
    for other_op in recovery_ops:
        if other_op.id != op.id and other_op.status == OperationStatus.ACTIVE:
            # RECOVERY FAILED - both activated
            await self._handle_recovery_failure(cycle, op, other_op, tick)
```

### 2. Recovery Renewal Position
```python
def _get_recovery_renewal_position(self, blocking_op: Operation, tick: TickData):
    """Returns entry positions for new recovery at ±20 pips from blocking op entry"""
    entry = blocking_op.actual_entry or blocking_op.entry_price
    distance = Decimal("0.0020")  # 20 pips for non-JPY
    return {
        "buy_entry": entry + distance,
        "sell_entry": entry - distance
    }
```

### 3. Cycle Close Condition
```python
def _can_close_cycle(self, cycle: Cycle, surplus_pips: Decimal) -> bool:
    """Returns True if cycle can be fully closed"""
    return cycle.accounting.pips_remaining <= 0 and surplus_pips >= Decimal("20")
```

### 4. FIFO With Units
```python
def _process_fifo_liquidation(self, profit_pips: Decimal, debt_queue: List[DebtUnit]):
    """Process FIFO closing debt units (main+hedge=20, recovery=40 each)"""
    remaining = profit_pips
    for unit in debt_queue:
        if remaining >= unit.cost_pips:
            remaining -= unit.cost_pips
            unit.close()
        else:
            break
    return remaining  # surplus
```

---

## Files to Modify

1. [cycle_orchestrator.py](file:///c:/Users/Artur/wsplumber/src/wsplumber/application/use_cases/cycle_orchestrator.py) - Add recovery failure detection and renewal logic
2. [cycle.py](file:///c:/Users/Artur/wsplumber/scripts/audit_by_cycle.py) - Add debt tracking for recovery units
3. [audit_by_cycle.py](file:///c:/Users/Artur/wsplumber/scripts/audit_by_cycle.py) - Show recovery cascade in timeline

---

## Documentation Status

| Document | Has This Logic? |
|----------|-----------------|
| [ws_plumber_system.md](file:///c:/Users/Artur/wsplumber/docs/ws_plumber_system.md) | Partial (Escenario 4) |
| [debug_reference.md](file:///c:/Users/Artur/wsplumber/docs/debug_reference.md) | Basic FIFO info |
| [expted_behavior_specification_fixed.md](file:///c:/Users/Artur/wsplumber/docs/expted_behavior_specification_fixed.md) | Needs update |
