from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation, OperationStatus, OperationType

@dataclass
class ForensicMetrics:
    # Cycle Tracking
    total_main_cycles_created: int = 0
    total_main_cycles_closed: int = 0
    total_recovery_cycles_created: int = 0
    total_recovery_cycles_closed: int = 0
    
    # Take Profits & Closures
    total_main_tps: int = 0
    total_recovery_tps: int = 0
    total_overlap_tps: int = 0
    total_smart_tps: int = 0
    total_recoveries_cancelled_by_debt: int = 0
    
    # Financials
    total_slippage_pips: float = 0.0
    total_theoretical_pips: float = 0.0
    total_actual_pips: float = 0.0
    incidents: List[str] = field(default_factory=list)

class ForensicAccountingService:
    """
    Advanced Forensic Audit Service to validate system laws (20/40/80).
    Now with Parent (Main) vs Child (Recovery) differentiation.
    """
    
    # Sacred Laws (Pips)
    MAIN_TP = 10.0
    RECOVERY_TP = 80.0

    def __init__(self):
        self.metrics = ForensicMetrics()

    def audit_operation(self, op: Operation):
        """Audits an individual operation for law deviations."""
        if op.status != OperationStatus.TP_HIT:
            return

        expected = 0.0
        op_type_str = str(op.op_type.value).lower()
        
        if "main" in op_type_str:
            expected = self.MAIN_TP
            self.metrics.total_main_tps += 1
        elif "recovery" in op_type_str:
            expected = self.RECOVERY_TP
            self.metrics.total_recovery_tps += 1
            
        real = float(op.profit_pips or 0.0)
        diff = real - expected
        
        self.metrics.total_actual_pips += real
        self.metrics.total_theoretical_pips += expected
        self.metrics.total_slippage_pips += diff

        if abs(diff) > 1.5:
            self.metrics.incidents.append(
                f"ALARM: Heavy Drift in {op.id} ({op_type_str}). Expected {expected}, got {real:.2f}. Diff: {diff:.2f}"
            )

    def register_cycle_event(self, event_type: str, details: str = "", cycle_type: str = "main"):
        """Registers high-level events for master statistics."""
        et = event_type.upper()
        dt = details.upper()
        msg = f"{et} | {dt}"
        
        is_recovery = (cycle_type.lower() == "recovery")

        if "CYCLE_CREATED" in et:
            if is_recovery: self.metrics.total_recovery_cycles_created += 1
            else: self.metrics.total_main_cycles_created += 1
        elif "CYCLE_CLOSED" in et:
            if is_recovery: self.metrics.total_recovery_cycles_closed += 1
            else: self.metrics.total_main_cycles_closed += 1
            
        # TP/Efficiency Detection
        if "OVERLAP" in msg:
            self.metrics.total_overlap_tps += 1
        elif "SMART" in msg or "TRAILING" in msg:
            self.metrics.total_smart_tps += 1
        elif any(k in msg for k in ["DEBT_SETTLED", "FIFO", "LIQUIDATE", "FULL_RESOLUTION", "FULL_RES"]):
            self.metrics.total_recoveries_cancelled_by_debt += 1

    def validate_laws(self, cycle: Cycle, operations: List[Operation]):
        """Validates that a cycle obeys the 20/40/80 laws."""
        if not operations: return
            
        pair = operations[0].pair
        multiplier = 100 if "JPY" in str(pair) else 10000

        # 1. Recovery TP Distance (80 pips)
        recoveries = [op for op in operations if "recovery" in str(op.op_type.value).lower()]
        for rec in recoveries:
            tp_dist = abs(float(rec.tp_price) - float(rec.entry_price))
            tp_pips = tp_dist * multiplier
            if abs(tp_pips - self.RECOVERY_TP) > 0.5:
                self.metrics.incidents.append(
                    f"LAW_VIOLATION: Recovery {rec.id} TP distance {tp_pips:.1f}p (Expected {self.RECOVERY_TP}p)"
                )

        # 2. Main/Hedge Imbalance (10 pips)
        mains = [op for op in operations if "main" in str(op.op_type.value).lower() and op.status != OperationStatus.CANCELLED]
        if len(mains) >= 2:
            dist = abs(float(mains[0].entry_price) - float(mains[1].entry_price)) * multiplier
            if abs(dist - 10.0) > 0.5:
                self.metrics.incidents.append(
                    f"LAW_VIOLATION: Main imbalance in cycle {cycle.id}. Dist: {dist:.1f}p (Expected 10.0p)"
                )

    def get_master_summary(self) -> str:
        m = self.metrics
        accuracy = 100.0
        if m.total_theoretical_pips != 0:
            accuracy = (m.total_actual_pips / m.total_theoretical_pips) * 100
            
        return f"""
==============================================================================================================
FORENSIC MASTER REPORT - SYSTEM INTEGRITY CHECK
==============================================================================================================
CYCLE DIFFERENTIATION:
- Main Cycles (Parent):      {m.total_main_cycles_created} Created | {m.total_main_cycles_closed} Closed | {m.total_main_cycles_created - m.total_main_cycles_closed} Active
- Recovery Cycles (Child):   {m.total_recovery_cycles_created} Created | {m.total_recovery_cycles_closed} Closed | {m.total_recovery_cycles_created - m.total_recovery_cycles_closed} Active

TAKE PROFIT & EFFICIENCY:
- Take Profits: {m.total_main_tps} Main | {m.total_recovery_tps} Recovery | {m.total_overlap_tps} Overlap | {m.total_smart_tps} Smart
- Efficiency:   {m.total_recoveries_cancelled_by_debt} Recoveries neutralized by early debt resolution (FIFO/Liquidated)

FINANCIAL INTEGRITY:
- Theoretical pips: {m.total_theoretical_pips:+.2f}
- Actual pips:      {m.total_actual_pips:+.2f}
- Execution Drift:  {m.total_slippage_pips:+.2f} pips (Slippage/Gaps)
- System Fidelity:  {accuracy:.2f}%

LOGIC INCIDENTS DETECTED: {len(m.incidents)}
{chr(10).join(['  ! ' + i for i in m.incidents[:50]])}
{ '  ... (and more)' if len(m.incidents) > 50 else ''}
==============================================================================================================
"""
