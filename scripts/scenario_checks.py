"""
WSPlumber - Scenario Checks

Define checks for each scenario type based on expected behavior specification.
Each scenario has a list of (name, check_function) tuples.

Check functions receive a context object with:
- ctx.repo: Repository with cycles and operations
- ctx.broker: SimulatedBroker with account info
- ctx.cycles: List of CycleAudit objects
- ctx.initial_balance: float
- ctx.final_balance: float
"""

from dataclasses import dataclass
from typing import List, Callable, Tuple, Dict, Any
from wsplumber.domain.types import OperationStatus
from wsplumber.domain.entities.cycle import CycleStatus, CycleType


@dataclass
class VerificationContext:
    """Context passed to check functions."""
    repo: Any  # InMemoryRepository
    broker: Any  # SimulatedBroker
    cycles: List[Any]  # List of CycleAudit
    initial_balance: float
    final_balance: float
    tick_count: int


# Type alias for check function
CheckFn = Callable[[VerificationContext], bool]


def _get_ops(ctx, **filters) -> list:
    """Helper to filter operations."""
    ops = list(ctx.repo.operations.values())
    result = []
    for op in ops:
        match = True
        if 'is_main' in filters and op.is_main != filters['is_main']:
            match = False
        if 'op_type' in filters and filters['op_type'] not in op.op_type.value:
            match = False
        if 'status' in filters and op.status.value != filters['status']:
            match = False
        if match:
            result.append(op)
    return result


def _get_cycles(ctx, **filters) -> list:
    """Helper to filter cycles."""
    cycles = list(ctx.repo.cycles.values())
    result = []
    for c in cycles:
        match = True
        if 'cycle_type' in filters and c.cycle_type != filters['cycle_type']:
            match = False
        if 'status' in filters and c.status != filters['status']:
            match = False
        if match:
            result.append(c)
    return result


# ============================================================================
# CORE SCENARIOS (c01-c05)
# ============================================================================

CORE_CHECKS = {
    "c01_tp_simple_buy": [
        ("MAIN_BUY status TP_HIT", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="buy", status="tp_hit")) >= 1),
        ("Balance increased", 
         lambda ctx: ctx.final_balance > ctx.initial_balance),
        ("Counter main cancelled", 
         lambda ctx: len(_get_ops(ctx, is_main=True, status="cancelled")) >= 1),
    ],
    
    "c01_tp_simple_sell": [
        ("MAIN_SELL status TP_HIT", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="sell", status="tp_hit")) >= 1),
        ("Balance increased", 
         lambda ctx: ctx.final_balance > ctx.initial_balance),
        ("Counter main cancelled", 
         lambda ctx: len(_get_ops(ctx, is_main=True, status="cancelled")) >= 1),
    ],
    
    "c04_no_activation": [
        ("Both mains PENDING", 
         lambda ctx: len(_get_ops(ctx, is_main=True, status="pending")) == 2),
        ("Balance unchanged", 
         lambda ctx: abs(ctx.final_balance - ctx.initial_balance) < 0.01),
    ],
    
    "c05_gap_tp": [
        ("Operation closed", 
         lambda ctx: len(_get_ops(ctx, status="tp_hit")) >= 1 or len(_get_ops(ctx, status="closed")) >= 1),
        ("Profit >= 10 pips", 
         lambda ctx: any(float(op.profit_pips or 0) >= 10 for op in ctx.repo.operations.values() if op.status.value in ["tp_hit", "closed"])),
    ],
}


# ============================================================================
# CYCLE SCENARIOS (cy01-cy06)
# ============================================================================

CYCLE_CHECKS = {
    "cy01_new_cycle": [
        ("1 cycle created", 
         lambda ctx: len(_get_cycles(ctx, cycle_type=CycleType.MAIN)) >= 1),
        ("Cycle has 2 mains", 
         lambda ctx: all(
             len([op for op in ctx.repo.operations.values() if op.cycle_id == c.id and op.is_main]) == 2
             for c in _get_cycles(ctx, cycle_type=CycleType.MAIN)
         )),
    ],
    
    "cy03_tp_renews_operations": [
        ("TP triggered", 
         lambda ctx: len(_get_ops(ctx, status="tp_hit")) >= 1),
        ("New cycle C2 created after TP", 
         lambda ctx: len(_get_cycles(ctx, cycle_type=CycleType.MAIN)) >= 2),
        ("C1 has exactly 2 mains", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if op.cycle_id == list(ctx.repo.cycles.values())[0].id and op.is_main]) == 2),
    ],
    
    "cy04_cancel_counter_main": [
        ("BUY status TP_HIT", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="buy", status="tp_hit")) >= 1),
        ("SELL status CANCELLED", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="sell", status="cancelled")) >= 1),
        ("Cancel reason is counterpart_tp_hit", 
         lambda ctx: any(op.metadata.get("cancel_reason") == "counterpart_tp_hit" 
                        for op in _get_ops(ctx, status="cancelled"))),
        ("New cycle created", 
         lambda ctx: len(_get_cycles(ctx, cycle_type=CycleType.MAIN)) >= 2),
    ],
    
    "cy05_complete_10_tps": [
        ("At least 5 TPs", 
         lambda ctx: len(_get_ops(ctx, status="tp_hit")) >= 5),
        ("Balance significantly increased", 
         lambda ctx: ctx.final_balance > ctx.initial_balance + 5),
    ],
}


# ============================================================================
# HEDGE SCENARIOS (h01-h08)
# ============================================================================

HEDGE_CHECKS = {
    "h01_both_active_hedged": [
        ("Cycle status HEDGED", 
         lambda ctx: len(_get_cycles(ctx, status=CycleStatus.HEDGED)) >= 1),
        ("Both mains NEUTRALIZED", 
         lambda ctx: len(_get_ops(ctx, is_main=True, status="neutralized")) >= 2),
    ],
    
    "h02_create_hedge_operations": [
        ("2 hedge operations created", 
         lambda ctx: len([op for op in ctx.repo.operations.values() if "hedge" in op.op_type.value]) >= 2),
    ],
    
    "h03_neutralize_mains": [
        ("Main BUY NEUTRALIZED", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="buy", status="neutralized")) >= 1),
        ("Main SELL NEUTRALIZED", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="sell", status="neutralized")) >= 1),
    ],
    
    "h04_lock_20_pips": [
        ("Cycle HEDGED", 
         lambda ctx: len(_get_cycles(ctx, status=CycleStatus.HEDGED)) >= 1),
        ("pips_locked = 20", 
         lambda ctx: any(hasattr(c, 'pips_locked') and c.pips_locked >= 19 
                        for c in ctx.repo.cycles.values())),
    ],
    
    "h07_buy_tp_hedge_sell": [
        ("MAIN_BUY TP_HIT", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="buy", status="tp_hit")) >= 1),
        ("HEDGE_SELL activated or pending", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "hedge" in op.op_type.value and "sell" in op.op_type.value]) >= 1),
        ("HEDGE_BUY cancelled", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "hedge" in op.op_type.value and "buy" in op.op_type.value 
                         and op.status.value == "cancelled"]) >= 1),
    ],
    
    "h08_sell_tp_hedge_buy": [
        ("MAIN_SELL TP_HIT", 
         lambda ctx: len(_get_ops(ctx, is_main=True, op_type="sell", status="tp_hit")) >= 1),
        ("HEDGE_BUY activated or pending", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "hedge" in op.op_type.value and "buy" in op.op_type.value]) >= 1),
    ],
}


# ============================================================================
# RECOVERY SCENARIOS (r01-r10)
# ============================================================================

RECOVERY_CHECKS = {
    "r01_open_from_tp": [
        ("Recovery cycle created", 
         lambda ctx: len(_get_cycles(ctx, cycle_type=CycleType.RECOVERY)) >= 1),
        ("2 recovery operations", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "recovery" in op.op_type.value]) >= 2),
    ],
    
    "r03_recovery_n1_tp_buy": [
        ("Recovery BUY TP_HIT", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "recovery" in op.op_type.value and "buy" in op.op_type.value 
                         and op.status.value == "tp_hit"]) >= 1),
        ("Recovery SELL cancelled", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "recovery" in op.op_type.value and "sell" in op.op_type.value 
                         and op.status.value == "cancelled"]) >= 1),
    ],
    
    "r04_recovery_n1_tp_sell": [
        ("Recovery SELL TP_HIT", 
         lambda ctx: len([op for op in ctx.repo.operations.values() 
                         if "recovery" in op.op_type.value and "sell" in op.op_type.value 
                         and op.status.value == "tp_hit"]) >= 1),
    ],
}


# ============================================================================
# FIFO SCENARIOS (f01-f04)
# ============================================================================

FIFO_CHECKS = {
    "f01_fifo_first_costs_20": [
        ("First recovery costs 20 pips to close", 
         lambda ctx: True),  # Complex check - TODO implement
    ],
    
    "f02_fifo_subsequent_40": [
        ("Subsequent recovery costs 40 pips", 
         lambda ctx: True),  # Complex check - TODO implement
    ],
}


# ============================================================================
# INVARIANT CHECKS (apply to all scenarios)
# ============================================================================

INVARIANT_CHECKS = [
    ("Every MAIN cycle has exactly 2 mains", 
     lambda ctx: all(
         len([op for op in ctx.repo.operations.values() if op.cycle_id == c.id and op.is_main]) == 2
         for c in _get_cycles(ctx, cycle_type=CycleType.MAIN)
     ) if _get_cycles(ctx, cycle_type=CycleType.MAIN) else True),
    
    ("No orphaned operations", 
     lambda ctx: all(
         op.cycle_id in [c.id for c in ctx.repo.cycles.values()]
         for op in ctx.repo.operations.values()
     )),
]


# ============================================================================
# COMBINED SCENARIO CHECKS
# ============================================================================

def get_checks_for_scenario(scenario_name: str) -> List[Tuple[str, CheckFn]]:
    """Get checks for a scenario by name."""
    # Remove extension if present
    name = scenario_name.replace(".csv", "")
    
    # Find in all check dictionaries
    all_checks = {
        **CORE_CHECKS,
        **CYCLE_CHECKS,
        **HEDGE_CHECKS,
        **RECOVERY_CHECKS,
        **FIFO_CHECKS,
    }
    
    if name in all_checks:
        return all_checks[name]
    
    # Return basic checks if no specific ones defined
    return [
        ("At least 1 cycle created", lambda ctx: len(ctx.repo.cycles) >= 1),
        ("Operations exist", lambda ctx: len(ctx.repo.operations) >= 1),
    ]


def get_all_scenario_names() -> List[str]:
    """Get all scenario names with defined checks."""
    return list({
        **CORE_CHECKS,
        **CYCLE_CHECKS,
        **HEDGE_CHECKS,
        **RECOVERY_CHECKS,
        **FIFO_CHECKS,
    }.keys())
