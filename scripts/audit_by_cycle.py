"""
WSPlumber - Cycle Audit Report (Stable Professional Version)

Generates clean, hierarchical reports grouped by cycle with advanced financial metrics.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, OperationType
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker

@dataclass
class CycleEvent:
    tick: int
    event_type: str
    description: str
    details: str = ""
    pips: float = 0.0
    surplus: float = 0.0
    balance: float = 10000.0
    equity: float = 10000.0
    op_id: str = ""
    ref_op_id: str = ""

@dataclass
class OperationRef:
    op_id: str
    op_type: str
    entry_price: float
    tp_price: float
    status: str
    linked_op: str = ""
    was_neutralized: bool = False

@dataclass
class CycleAudit:
    id: str
    name: str
    cycle_type: str
    created_tick: int = 0
    status: str = "pending"
    events: List[CycleEvent] = field(default_factory=list)
    mains: Dict[str, OperationRef] = field(default_factory=dict)
    hedges: Dict[str, OperationRef] = field(default_factory=dict)
    recoveries: Dict[str, OperationRef] = field(default_factory=dict)
    child_cycles: List['CycleAudit'] = field(default_factory=list)
    total_pips: float = 0.0
    parent_id: Optional[str] = None
    
    def add_event(self, tick: int, event_type: str, desc: str, 
                  details: str = "", pips: float = 0.0, 
                  surplus: float = 0.0,
                  balance: float = 10000.0,
                  equity: float = 10000.0,
                  op_id: str = "", ref_op_id: str = ""):
        self.events.append(CycleEvent(tick, event_type, desc, details, pips, surplus, balance, equity, op_id, ref_op_id))
        if pips != 0:
            self.total_pips += pips

class CycleAuditor:
    def __init__(self):
        self.cycles: Dict[str, CycleAudit] = {}
        self.cycle_counter = 0
        self.recovery_counter = 0
        self.closed_cycles_count = 0
        self.top_level_cycles: List[str] = [] # IDs of cycles with no parent
        self.tick = 0
        self.last_ops: Dict[str, dict] = {}
        self.last_balance = 10000.0
        self.equity_history = []
        self.max_drawdown = 0.0
        self.peak_equity = 10000.0
        
        # New Forensic Metrics
        self.total_main_tps = 0
        self.total_recoveries_opened = 0
        self.total_recoveries_closed = 0
        self.max_recovery_level = 0
        self.total_resolved_surplus = 0.0

    def get_cycle_name(self, cycle_id: str, cycle_type: str, parent_id: Optional[str] = None) -> str:
        """Generate readable cycle name. Recoveries start from 1 per parent."""
        if cycle_id in self.cycles:
            return self.cycles[cycle_id].name
            
        if cycle_type == "main":
            self.cycle_counter += 1
            return f"C{self.cycle_counter}"
        else:
            # Recovery: use per-parent counter
            if not hasattr(self, '_recovery_counters'):
                self._recovery_counters = defaultdict(int)
            
            parent_key = parent_id or "orphan"
            self._recovery_counters[parent_key] += 1
            return f"R{self._recovery_counters[parent_key]}"

    def get_op_short_name(self, op_type: str, op_id: str) -> str:
        type_map = {
            "main_buy": "M_B", "main_sell": "M_S",
            "hedge_buy": "H_B", "hedge_sell": "H_S",
            "recovery_buy": "R_B", "recovery_sell": "R_S"
        }
        return type_map.get(op_type, op_type.upper())

    def check(self, tick: int, repo, broker, balance: float, equity: float):
        self.tick = tick
        # Detect new cycles
        for c in repo.cycles.values():
            if c.id not in self.cycles:
                parent_id = getattr(c, 'parent_cycle_id', None)
                name = self.get_cycle_name(c.id, c.cycle_type.value, parent_id)
                
                audit = CycleAudit(
                    id=c.id, 
                    name=name, 
                    cycle_type=c.cycle_type.value, 
                    created_tick=tick, 
                    status=c.status.value,
                    parent_id=parent_id
                )
                self.cycles[c.id] = audit
                
                # Assign to parent or mark as top-level
                if parent_id and parent_id in self.cycles:
                    self.cycles[parent_id].child_cycles.append(audit)
                else:
                    self.top_level_cycles.append(c.id)

                audit.add_event(tick, "CYCLE_CREATED", f"Cycle {name} created", 
                                details=f"type={c.cycle_type.value}",
                                balance=balance, equity=equity)
                
                if c.cycle_type.value == "recovery":
                    self.total_recoveries_opened += 1
                    # Track depth from cycle ID or metadata if available
                    depth = getattr(c, 'tier', 1) 
                    if isinstance(depth, int) and depth > self.max_recovery_level:
                        self.max_recovery_level = depth

        # Detect cycle status changes
        for c in repo.cycles.values():
            if c.id in self.cycles:
                audit = self.cycles[c.id]
                if audit.status != c.status.value:
                    audit.add_event(tick, "STATUS_CHANGE", f"{audit.status.upper()} -> {c.status.value.upper()}",
                                    balance=balance, equity=equity)
                    audit.status = c.status.value
                    
                    if c.status.value == "closed":
                        if audit.cycle_type == "main":
                            self.total_main_tps += 1
                        elif audit.cycle_type == "recovery":
                            self.total_recoveries_closed += 1
                            # Accumulate surplus from resolved cycles
                            acc = getattr(c, 'accounting', None)
                            if acc:
                                self.total_resolved_surplus += float(getattr(acc, 'surplus_pips', 0.0))

        # Detect new operations and status changes
        for op in repo.operations.values():
            op_id, status, op_type, cycle_id = str(op.id), op.status.value, op.op_type.value, op.cycle_id
            if cycle_id not in self.cycles: continue
            audit = self.cycles[cycle_id]
            short_name = self.get_op_short_name(op_type, op_id)
            entry, tp = float(op.entry_price), float(op.tp_price or 0)
            
            if op_id not in self.last_ops:
                self.last_ops[op_id] = {"status": status, "cycle_id": cycle_id, "type": op_type}
                op_ref = OperationRef(op_id=op_id, op_type=op_type, entry_price=entry, tp_price=tp, status=status)
                if "main" in op_type:
                    audit.mains[op_id] = op_ref
                elif "hedge" in op_type:
                    linked = next((mid for mid, mref in audit.mains.items() if abs(mref.tp_price - entry) < 0.00001), "")
                    op_ref.linked_op = linked
                    audit.hedges[op_id] = op_ref
                    audit.add_event(tick, "HEDGE_CREATED", f"{short_name} order placed", 
                                    details=f"Entry: {entry}", balance=balance, equity=equity)
                elif "recovery" in op_type:
                    audit.recoveries[op_id] = op_ref
                    audit.add_event(tick, "OP_CREATED", f"{short_name} recovery placed", 
                                    details=f"Entry: {entry}", balance=balance, equity=equity)
            else:
                old_status = self.last_ops[op_id]["status"]
                if old_status != status:
                    if status == "active": audit.add_event(tick, "ACTIVATED", f"{short_name} active", balance=balance, equity=equity)
                    elif status == "neutralized": 
                        audit.add_event(tick, "NEUTRALIZED", f"{short_name} neutralized", balance=balance, equity=equity)
                        # Mark ref as neutralized
                        for d in [audit.mains, audit.hedges, audit.recoveries]:
                            if op_id in d: d[op_id].was_neutralized = True
                    elif status == "tp_hit" or status == "closed":
                        # Capture PNL even if we missed the intermediate 'tp_hit' state
                        pips = float(op.profit_pips or 0)
                            
                        surplus = 0.0
                        cycle_data = repo.cycles.get(cycle_id)
                        if cycle_data and hasattr(cycle_data, 'accounting'):
                            surplus = float(getattr(cycle_data.accounting, 'surplus_pips', 0.0))
                        
                        reason = op.metadata.get("close_reason", "tp_hit" if status == "tp_hit" else "manual")
                        
                        if status == "tp_hit":
                            audit.add_event(tick, "TP_HIT", f"{short_name} hit", pips=pips, surplus=surplus, 
                                          details=f"reason={reason}", balance=balance, equity=equity)
                        else:
                            # It closed. Was it a natural TP or a structural resolution?
                            if pips > 0:
                                if "resolution" in reason or "fifo" in reason:
                                    # Structural resolution according to docs/debug_reference.md
                                    audit.add_event(tick, "ATOMIC_FIFO", f"{short_name} consolidated", pips=pips, surplus=surplus, 
                                                  details=f"reason={reason} | Contributed to parent", balance=balance, equity=equity)
                                else:
                                    audit.add_event(tick, "TP_HIT", f"{short_name} tp_hit", pips=pips, surplus=surplus, 
                                                  details=f"reason={reason}", balance=balance, equity=equity)
                            else:
                                # Normal closure or debt unit liquidation
                                event_label = "DEBT_UNIT_LIQUIDATED" if "unit" in reason else "CLOSED"
                                audit.add_event(tick, event_label, f"{short_name} {event_label.lower()}", pips=pips, surplus=surplus, 
                                              details=f"reason={reason} | Debt settled", balance=balance, equity=equity)

                    elif status == "cancelled": audit.add_event(tick, "CANCELLED", f"{short_name} cancelled", balance=balance, equity=equity)
                    
                    self.last_ops[op_id]["status"] = status
                    # Sync ref
                    for d in [audit.mains, audit.hedges, audit.recoveries]:
                        if op_id in d: d[op_id].status = status

        # Financials
        self.equity_history.append(equity)
        if equity > self.peak_equity: self.peak_equity = equity
        dd = self.peak_equity - equity
        if dd > self.max_drawdown: self.max_drawdown = dd
        self.last_balance = balance

    def print_report(self, repo, final_balance: float, final_equity: float, output_file=None):
        def _render_cycle(audit, level, stream):
            indent = "    " * level
            connector = " " if level == 0 else " └─ "
            
            # 1. Header with precise identification
            cycle_data = repo.cycles.get(audit.id)
            tier_label = f"TIER: {audit.name}" if level > 0 else f"ROOT: {audit.name}"
            
            print(f"\n{indent}{connector}CYCLE: {audit.id:<40} | {tier_label:<10} | STATUS: {audit.status.upper():<12}", file=stream)
            print(f"{indent} {'='*110}", file=stream)
            
            # 2. PRO-LEVEL ACCOUNTING SHOWCASE (follows docs/debug_reference.md)
            if cycle_data and hasattr(cycle_data, 'accounting'):
                acc = cycle_data.accounting
                rem = float(getattr(acc, 'pips_remaining', 0.0))
                surp = float(getattr(acc, 'surplus_pips', 0.0))
                
                if level == 0: # Root Main Cycle
                    # SHOW DEBT
                    print(f"{indent}    DEBT STATUS: {rem:.1f} pips Owed | {surp:.1f} pips Surplus Carryover", file=stream)
                    if acc.debt_units:
                        print(f"{indent}    PENDING DEBT UNITS (FIFO):", file=stream)
                        for unit in acc.debt_units:
                            status_icon = "⏳" if unit.status == "active" else "✅"
                            print(f"{indent}      {status_icon} {unit.debt_type.upper():<18} | Value: {float(unit.pips_owed):>5.1f} pips | ID: {unit.id[:8]}", file=stream)
                else: # Recovery Cycle
                    # SHOW CONTRIBUTION
                    print(f"{indent}    PERFORMANCE: {audit.total_pips:+.1f} pips generated towards debt resolution", file=stream)
            
            # 3. Operations
            all_ops = list(audit.mains.values()) + list(audit.hedges.values()) + list(audit.recoveries.values())
            if all_ops:
                print(f"{indent}    OPERATIONS:", file=stream)
                for i, op in enumerate(all_ops):
                    op_conn = "    |-- " if i < len(all_ops)-1 else "    +-- "
                    
                    status_flag = f"[{op.status.upper()}]"
                    if op.was_neutralized:
                        status_flag = f"[NEUTRALIZED/{op.status.upper()}] 🛡️"
                    elif op.status == "active" and audit.status != "closed":
                        status_flag = "[RUNNING 🔵]"
                    
                    ticket = op.op_id.split('_')[-2] if '_' in op.op_id else op.op_id[:8]
                    short_type = self.get_op_short_name(op.op_type, '')
                    tp_str = f"{op.tp_price:.5f}" if op.tp_price and op.tp_price > 0 else "NONE"
                    print(f"{indent}{op_conn}{ticket:<8} {short_type:<6} Entry: {op.entry_price:.5f} | TP: {tp_str:<10} {status_flag}", file=stream)
            
            # 4. Events Chronological Timeline
            if audit.events:
                print(f"{indent}    EVENT TIMELINE:", file=stream)
                print(f"{indent}    {'-'*110}", file=stream)
                print(f"{indent}    {'TICK':<8} {'EVENT':<16} {'DESCRIPTION':<40} {'BALANCE':<12} {'EQUITY':<12} {'DETAILS'}", file=stream)
                print(f"{indent}    {'-'*140}", file=stream)
                for e in audit.events:
                    details_str = e.details
                    if e.pips != 0: details_str += f" | Pips: {e.pips:+.1f} pips"
                    if e.surplus != 0: details_str += f" | Surplus: {e.surplus:.1f} pips"
                    print(f"{indent}    #{e.tick:<7} {e.event_type:<16} {e.description:<40} {e.balance:<12.2f} {e.equity:<12.2f} {details_str}", file=stream)
                print(file=stream)
            
            # 5. Recursive Child Rendering
            if audit.child_cycles:
                for child in audit.child_cycles:
                    _render_cycle(child, level + 1, stream)

        def _render(stream):
            print("\n" + "#"*120, file=stream)
            print(" WSPLUMBER HIERARCHICAL AUDIT REPORT (PRO VERSION 3.0 - ARCHITECTURAL ALIGNMENT) ", file=stream)
            print("#"*120, file=stream)
            
            # Render each root tree independently
            for cid in self.top_level_cycles:
                _render_cycle(self.cycles[cid], 0, stream)
            
            print("\n" + "#"*120, file=stream)
            print(f" FINAL PORTFOLIO SUMMARY: Balance {final_balance:.2f} EUR | Equity {final_equity:.2f} EUR | Profit {final_equity-10000:+.2f} EUR | Max DD {self.max_drawdown:.2f} EUR | Peak {self.peak_equity:.2f} EUR", file=stream)
            
            # New Metrics Summary Section
            print(f" {'-'*118}", file=stream)
            print(f" FORENSIC PERFORMANCE SUMMARY:", file=stream)
            print(f"   - Main TPs:           {self.total_main_tps:<10} | Surplus (Carryover): {self.total_resolved_surplus:+.1f} pips", file=stream)
            print(f"   - Recoveries:         {self.total_recoveries_closed}/{self.total_recoveries_opened} (Closed/Total) | Max Depth: Tier {self.max_recovery_level}", file=stream)
            
            active_cycles = len(self.top_level_cycles) - self.total_main_tps
            print(f"   - Active Cycles:      {active_cycles:<10} | Current Tick: #{self.tick}", file=stream)
            print("#"*120, file=stream)

        import io
        try:
            # Try to use a UTF-8 wrapper for stdout to handle emojis/special chars
            safe_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            _render(safe_stdout)
            safe_stdout.detach() # Don't close the underlying buffer
        except Exception:
            # Fallback to normal stdout if buffering fails
            _render(sys.stdout)
            
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f: _render(f)

async def run_audit(bars: int, scenario_path: str, quiet: bool = False):
    logging.getLogger('wsplumber').setLevel(logging.WARNING)
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    orchestrator = CycleOrchestrator(TradingService(broker, repo), WallStreetPlumberStrategy(), RiskManager(), repo)
    
    path_obj = Path(scenario_path)
    if not path_obj.exists(): return None
    
    if "ohlc" in scenario_path.lower(): broker.load_m1_csv(scenario_path, CurrencyPair("EURUSD"), max_bars=bars)
    else: broker.load_csv(scenario_path)
    
    await broker.connect()
    auditor = CycleAuditor()
    tick_count = 0
    
    # Hide noisy broker prints if needed
    orig_stdout = sys.stdout
    if quiet: sys.stdout = open(os.devnull, 'w')
    
    while True:
        tick = await broker.advance_tick()
        if not tick or (bars > 0 and tick_count >= bars): break
        await orchestrator.process_tick(tick)
        tick_count += 1
        acc = await broker.get_account_info()
        auditor.check(tick_count, repo, broker, float(acc.value["balance"]), float(acc.value["equity"]))

    if quiet: sys.stdout = orig_stdout
    
    acc = await broker.get_account_info()
    if not quiet:
        auditor.print_report(repo, float(acc.value["balance"]), float(acc.value["equity"]), output_file=f"audit_report_{path_obj.stem}.txt")
    
    return {"pnl": float(acc.value["equity"]) - 10000.0}

async def main():
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    path = sys.argv[2] if len(sys.argv) > 2 else "tests/scenarios/eurusd_2015_full.parquet"
    await run_audit(bars, path)

if __name__ == "__main__":
    asyncio.run(main())
