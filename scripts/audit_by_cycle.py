import sys
import asyncio
import logging
import os
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path

from wsplumber.domain.types import CurrencyPair, Price, Pips, OperationId
from wsplumber.domain.entities.operation import Operation, OperationType, OperationStatus
from wsplumber.domain.entities.cycle import Cycle, CycleType, CycleStatus
from tests.fixtures.simulated_broker import SimulatedBroker
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import StrategySignal, SignalType
from wsplumber.core.strategy._params import MAIN_TP_PIPS
from wsplumber.domain.services.forensic_accounting import ForensicAccountingService

import pickle
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("ws_audit")

def save_simulation_state(path, repo, broker, orchestrator, auditor):
    state = {
        "repo": repo,
        "broker_balance": broker.balance,
        "broker_positions": broker.open_positions,
        "broker_pending": broker.pending_orders,
        "broker_history": broker.history,
        "broker_ticket_counter": broker.ticket_counter,
        "auditor": auditor,
        "forensic": auditor.forensic
    }
    with open(path, "wb") as f:
        pickle.dump(state, f)
    logger.info(f"Simulation state saved to {path}")

def load_simulation_state(path, repo, broker, orchestrator, auditor):
    with open(path, "rb") as f:
        state = pickle.load(f)
    
    # Restore repo state
    repo.cycles = state["repo"].cycles
    repo._active_cycle_ids = state["repo"]._active_cycle_ids
    repo.operations = state["repo"].operations
    repo._active_ids = state["repo"]._active_ids
    repo._pending_ids = state["repo"]._pending_ids
    
    # Restore broker state
    broker.balance = state["broker_balance"]
    broker.open_positions = state["broker_positions"]
    broker.pending_orders = state["broker_pending"]
    broker.history = state["broker_history"]
    broker.ticket_counter = state["broker_ticket_counter"]
    
    # Restore auditor state
    for attr, value in state["auditor"].__dict__.items():
        if attr != 'forensic': # Don't overwrite the service instance itself
            setattr(auditor, attr, value)
            
    # Restore forensic metrics
    if "forensic" in state:
        for attr, value in state["forensic"].__dict__.items():
            setattr(auditor.forensic, attr, value)
        
    logger.info(f"Simulation state loaded from {path}")

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
    price: float = 0.0

@dataclass
class OperationRef:
    op_id: str
    op_type: str
    entry_price: float
    tp_price: float
    status: str
    was_neutralized: bool = False
    linked_op: str = ""

@dataclass
class CycleAudit:
    id: str
    name: str
    cycle_type: str
    created_tick: int
    status: str
    parent_id: Optional[str] = None
    mains: Dict[str, OperationRef] = field(default_factory=dict)
    hedges: Dict[str, OperationRef] = field(default_factory=dict)
    recoveries: Dict[str, OperationRef] = field(default_factory=dict)
    events: List[CycleEvent] = field(default_factory=list)
    child_cycles: List['CycleAudit'] = field(default_factory=list)
    total_pips: float = 0.0

    def add_event(self, tick: int, event_type: str, desc: str, 
                  details: str = "", pips: float = 0.0, 
                  surplus: float = 0.0,
                  balance: float = 10000.0,
                  equity: float = 10000.0,
                  op_id: str = "", ref_op_id: str = "",
                  price: float = 0.0):
        self.events.append(CycleEvent(tick, event_type, desc, details, pips, surplus, balance, equity, op_id, ref_op_id, price))
        if pips != 0:
            self.total_pips += pips

class CycleAuditor:
    def __init__(self, forensic_service: Optional[ForensicAccountingService] = None):
        self.cycles: Dict[str, CycleAudit] = {}
        self.top_level_cycles: List[str] = []
        self.last_ops: Dict[str, Dict] = {}
        self.tick = 0
        self.max_drawdown = 0.0
        self.peak_equity = 10000.0
        self.equity_history = []
        self.last_equity = 10000.0
        self.last_balance = 10000.0
        self.forensic = forensic_service or ForensicAccountingService()
        
        # Stats
        self.total_main_tps = 0
        self.total_recoveries_opened = 0
        self.total_recoveries_closed = 0
        self.total_resolved_surplus = 0.0
        self.max_recovery_level = 0

    def get_cycle_name(self, cycle_id: str, cycle_type: str, parent_id: Optional[str]) -> str:
        if cycle_type == "main":
            return f"C{len(self.top_level_cycles) + 1}"
        else:
            parent_audit = self.cycles.get(parent_id) if parent_id else None
            p_name = parent_audit.name if parent_audit else "UNK"
            return f"{p_name}_R{len(parent_audit.child_cycles) + 1 if parent_audit else '?'}"

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
                self.forensic.register_cycle_event("CYCLE_CREATED", cycle_type=c.cycle_type.value)
                
                if parent_id and parent_id in self.cycles:
                    self.cycles[parent_id].child_cycles.append(audit)
                else:
                    self.top_level_cycles.append(c.id)

                mid_p = float(broker.current_tick.mid if broker.current_tick else 0.0)
                audit.add_event(tick, "CYCLE_CREATED", f"Cycle {name} created", 
                                details=f"type={c.cycle_type.value}",
                                balance=balance, equity=equity, price=mid_p)
                
                if c.cycle_type.value == "recovery":
                    self.total_recoveries_opened += 1
                    depth = getattr(c, 'tier', 1) 
                    if isinstance(depth, int) and depth > self.max_recovery_level:
                        self.max_recovery_level = depth

        # Detect cycle status changes
        for c in repo.cycles.values():
            if c.id in self.cycles:
                audit = self.cycles[c.id]
                if audit.status != c.status.value:
                    mid_p = float(broker.current_tick.mid if broker.current_tick else 0.0)
                    rem = 0.0
                    if c.accounting:
                        rem = float(c.accounting.pips_remaining)
                    
                    if c.status.value == "closed":
                        self.forensic.register_cycle_event("CYCLE_CLOSED", str(getattr(c, 'metadata', {})), cycle_type=c.cycle_type.value)
                        # [FIX] Avoid calling async repo methods inside the sync auditor.check
                        ops = [o for o in repo.operations.values() if o.cycle_id == c.id]
                        self.forensic.validate_laws(c, ops)

                    audit.add_event(tick, "STATUS_CHANGE", f"{audit.status.upper()} -> {c.status.value.upper()}",
                                    balance=balance, equity=equity, price=mid_p, surplus=rem) # Use surplus slot for remaining
                    audit.status = c.status.value
                    
                    if c.status.value == "closed":
                        if audit.cycle_type == "main":
                            self.total_main_tps += 1
                        elif audit.cycle_type == "recovery":
                            self.total_recoveries_closed += 1
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
                                    details=f"Entry: {entry}", balance=balance, equity=equity, price=entry)
                elif "recovery" in op_type:
                    audit.recoveries[op_id] = op_ref
                    audit.add_event(tick, "OP_CREATED", f"{short_name} recovery placed", 
                                    details=f"Entry: {entry}", balance=balance, equity=equity, price=entry)
            else:
                old_status = self.last_ops[op_id]["status"]
                if old_status != status:
                    curr_mid = float(broker.current_tick.mid if broker.current_tick else 0.0)
                    current_price = float(op.actual_entry_price or op.entry_price or curr_mid)
                    if status == "active": 
                        audit.add_event(tick, "ACTIVATED", f"{short_name} active", balance=balance, equity=equity, price=current_price)
                    elif status == "neutralized": 
                        self.forensic.register_cycle_event("OP_NEUTRALIZED", f"{short_name}")
                        audit.add_event(tick, "NEUTRALIZED", f"{short_name} neutralized", balance=balance, equity=equity, price=current_price)
                        for d in [audit.mains, audit.hedges, audit.recoveries]:
                            if op_id in d: d[op_id].was_neutralized = True
                    elif status in ("tp_hit", "closed"):
                        pips = float(op.profit_pips or 0)
                        surplus = 0.0
                        cycle_data = repo.cycles.get(cycle_id)
                        if cycle_data and hasattr(cycle_data, 'accounting'):
                            surplus = float(getattr(cycle_data.accounting, 'surplus_pips', 0.0))
                        
                        reason = op.metadata.get("close_reason", "tp_hit" if status == "tp_hit" else "manual")
                        
                        if status == "tp_hit":
                            self.forensic.audit_operation(op)
                            audit.add_event(tick, "TP_HIT", f"{short_name} hit", pips=pips, surplus=surplus, 
                                          details=f"reason={reason} | Pips: {pips:+.1f} pips", balance=balance, equity=equity, 
                                          price=float(op.actual_close_price or op.tp_price or current_price))
                        else:
                            # PHASE 11: Differentiate Overlap and FIFO closures
                            if "overlap" in reason:
                                label = "OVERLAP_RESOLVED"
                                self.forensic.register_cycle_event("OVERLAP_PROFIT", f"{pips}")
                                details = f"reason=overlap | Captured: {pips:+.1f} pips"
                            elif "fifo" in reason or "liquidat" in reason:
                                label = "DEBT_SETTLED"
                                # Find liquidated units in cycle accounting
                                cycle_data = repo.cycles.get(cycle_id)
                                liq_details = ""

                                # Forensic Link: who triggered the liquidation?
                                trigger_id = op.metadata.get("liquidated_by_op_id", "")
                                if trigger_id:
                                    # Get short name for trigger op (ticket format)
                                    trigger_short = trigger_id.split('_')[-2] if '_' in trigger_id else trigger_id[:8]
                                    liq_details += f" | PAID_BY: #{trigger_short}"

                                if cycle_data and hasattr(cycle_data, 'accounting'):
                                    liq_units = cycle_data.accounting.liquidated_units
                                    if liq_units:
                                        unit_ids = [str(u.id) for u in liq_units]
                                        liq_details += f" | Units: {', '.join(unit_ids)}"
                                details = f"reason=fifo{liq_details}"
                            else:
                                label = "CLOSED"
                                if "smart" in reason.lower():
                                    self.forensic.register_cycle_event("SMART_EXIT")
                                details = f"reason={reason}"
                                
                            audit.add_event(tick, label, f"{short_name} {label.lower()}", pips=pips, surplus=surplus, 
                                          details=details, balance=balance, equity=equity, price=current_price)

                    elif status == "cancelled": audit.add_event(tick, "CANCELLED", f"{short_name} cancelled", balance=balance, equity=equity, price=current_price)
                    
                    self.last_ops[op_id]["status"] = status
                    for d in [audit.mains, audit.hedges, audit.recoveries]:
                        if op_id in d: d[op_id].status = status

        self.equity_history.append(equity)
        if equity > self.peak_equity: self.peak_equity = equity
        dd = self.peak_equity - equity
        if dd > self.max_drawdown: self.max_drawdown = dd
        self.last_balance = balance
        self.last_equity = equity

    def print_report(self, repo, final_balance: float, final_equity: float, output_file=None):
        import io
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except: pass
        
        def _render_cycle(audit, level, stream):
            indent = "    " * level
            connector = " " if level == 0 else " |-- "
            cycle_data = repo.cycles.get(audit.id)
            tier_label = f"TIER: {audit.name}" if level > 0 else f"ROOT: {audit.name}"
            
            print(f"\n{indent}{connector}CYCLE: {audit.id:<40} | {tier_label:<10} | STATUS: {audit.status.upper():<12}", file=stream)
            print(f"{indent} {'='*110}", file=stream)
            
            if cycle_data and hasattr(cycle_data, 'accounting'):
                acc = cycle_data.accounting
                rem = float(getattr(acc, 'pips_remaining', 0.0))
                surp = float(getattr(acc, 'surplus_pips', 0.0))
                if level == 0:
                    print(f"{indent}    DEBT STATUS: {rem:.1f} pips Owed | {surp:.1f} pips Surplus Carryover", file=stream)
                else:
                    print(f"{indent}    PERFORMANCE: {audit.total_pips:+.1f} pips generated", file=stream)
            
            all_ops = list(audit.mains.values()) + list(audit.hedges.values()) + list(audit.recoveries.values())
            if all_ops:
                print(f"{indent}    OPERATIONS:", file=stream)
                for i, op in enumerate(all_ops):
                    op_conn = "    |-- " if i < len(all_ops)-1 else "    +-- "
                    status_flag = f"[{op.status.upper()}]"
                    if op.was_neutralized: status_flag = f"[NEUTRALIZED/{op.status.upper()}] 🛡️"
                    ticket = op.op_id.split('_')[-2] if '_' in op.op_id else op.op_id[:8]
                    short_type = self.get_op_short_name(op.op_type, '')
                    tp_str = f"{op.tp_price:.5f}" if op.tp_price and op.tp_price > 0 else "NONE"
                    print(f"{indent}{op_conn}{ticket:<8} {short_type:<6} Entry: {op.entry_price:.5f} | TP: {tp_str:<10} {status_flag}", file=stream)
            
            if audit.events:
                print(f"{indent}    EVENT TIMELINE:", file=stream)
                print(f"{indent}    {'-'*110}", file=stream)
                print(f"{indent}    {'TICK':<8} {'EVENT':<16} {'PRICE':<10} {'DESCRIPTION':<30} {'BALANCE':<12} {'EQUITY':<12} {'DETAILS'}", file=stream)
                print(f"{indent}    {'-'*140}", file=stream)
                for e in audit.events:
                    details_str = e.details
                    if e.pips != 0: details_str += f" | Pips: {e.pips:+.1f} pips"
                    if e.surplus != 0: details_str += f" | Surplus: {e.surplus:.1f} pips"
                    price_str = f"{e.price:.5f}" if e.price > 0 else "-"
                    print(f"{indent}    #{e.tick:<7} {e.event_type:<16} {price_str:<10} {e.description:<30} {e.balance:<12.2f} {e.equity:<12.2f} {details_str}", file=stream)
                
                if audit.status == "closed":
                    print(f"{indent}    {'-'*110}", file=stream)
                    # PHASE 11: Absolute Traceability Narrative
                    closure_reason = getattr(cycle_data, 'metadata', {}).get("close_reason", "unknown")
                    pips = audit.total_pips
                    
                    print(f"{indent}    >>> CYCLE CLOSED FINALIZED <<<", file=stream)
                    print(f"{indent}    Reason: {closure_reason.upper()}", file=stream)
                    print(f"{indent}    Net Pips: {pips:+.1f} pips", file=stream)
                    
                    if audit.cycle_type == "recovery" and pips > 0:
                        print(f"{indent}    Debt Impact: This profit was used to reduce parent cycle debt via FIFO.", file=stream)
                    
                    print(f"{indent}    {'-'*110}", file=stream)
                print(file=stream)
            
            if audit.child_cycles:
                for child in audit.child_cycles:
                    _render_cycle(child, level + 1, stream)

        def _render(stream):
            print("\n" + "#"*120, file=stream)
            print(" WSPLUMBER HIERARCHICAL AUDIT REPORT (VERSION 3.1 - PHASE 11 FIDELITY) ", file=stream)
            print("#"*120, file=stream)
            for cid in self.top_level_cycles:
                _render_cycle(self.cycles[cid], 0, stream)
            print("\nSummary:", file=stream)
            print(f"Final Balance: {final_balance:.2f} | Equity: {final_equity:.2f} | Max DD: {self.max_drawdown:.2f}", file=stream)

        _render(sys.stdout)
        print(self.forensic.get_master_summary(), file=sys.stdout)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f: 
                _render(f)
                print(self.forensic.get_master_summary(), file=f)

async def run_audit(bars: int, scenario_path: str, quiet: bool = False, start_date=None, end_date=None, save_checkpoint=None, load_checkpoint=None):
    logging.getLogger('wsplumber').setLevel(logging.WARNING)
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    orchestrator = CycleOrchestrator(TradingService(broker, repo), WallStreetPlumberStrategy(), RiskManager(), repo)
    
    forensic = ForensicAccountingService()
    auditor = CycleAuditor(forensic_service=forensic)
    
    # Restore from checkpoint if provided
    if load_checkpoint and os.path.exists(load_checkpoint):
        load_simulation_state(load_checkpoint, repo, broker, orchestrator, auditor)
    
    path_obj = Path(scenario_path)
    if not path_obj.exists(): return None
    
    is_ohlc = False
    is_parquet = path_obj.suffix.lower() == '.parquet'
    
    if not is_parquet:
        with open(scenario_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().lower()
            is_ohlc = "open" in first_line and "high" in first_line and ("date" in first_line or "time" in first_line)
    
    if is_parquet:
        logger.info(f"Loading Parquet scenario: {scenario_path}")
        broker.load_csv(scenario_path, start_date=start_date, end_date=end_date)
    elif is_ohlc: 
        broker.load_m1_csv(scenario_path, CurrencyPair("EURUSD"), max_bars=bars)
    else: 
        # SimulatedBroker.load_csv handles filtering
        broker.load_csv(scenario_path, start_date=start_date, end_date=end_date)
    
    await broker.connect()
    tick_count = 0
    while True:
        # 1. Peek next tick to check for gaps BEFORE any simulation occurs
        next_tick = broker.peek_next_tick()
        if not next_tick: 
            tick = await broker.advance_tick()
        else:
            # Check gap with orchestrator's immune system
            is_allowed = await orchestrator._check_immune_system(next_tick.pair, next_tick)
            # Advance broker with the veto flag
            tick = await broker.advance_tick(is_allowed=is_allowed)
            
        if not tick or (bars > 0 and tick_count >= bars): break
        
        # 2. Process in orchestrator
        is_allowed = await orchestrator.process_tick(tick)
        tick_count += 1
        
        acc = await broker.get_account_info()
        balance = float(acc.value["balance"])
        equity = float(acc.value["equity"])
        
        if not is_allowed and hasattr(auditor, 'last_equity'):
            equity = auditor.last_equity
            
        auditor.check(tick_count, repo, broker, balance, equity)
    
    acc = await broker.get_account_info()
    out_name = f"audit_report_{path_obj.stem}_{start_date if start_date else 'full'}.txt"
    auditor.print_report(repo, float(acc.value["balance"]), float(acc.value["equity"]), output_file=out_name)
    
    # Save checkpoint if requested
    if save_checkpoint:
        save_simulation_state(save_checkpoint, repo, broker, orchestrator, auditor)
        
    return {"pnl": float(acc.value["equity"]) - 10000.0}

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit WSPlumber Cycles")
    parser.add_argument("path", help="Path to scenario (Parquet/CSV)")
    parser.add_argument("--bars", type=int, default=0, help="Max ticks to process (0=all)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--save-checkpoint", help="Path to save simulation state")
    parser.add_argument("--load-checkpoint", help="Path to load simulation state")
    
    args = parser.parse_args()
    await run_audit(
        args.bars, args.path, 
        start_date=args.start_date, 
        end_date=args.end_date,
        save_checkpoint=args.save_checkpoint,
        load_checkpoint=args.load_checkpoint
    )

if __name__ == "__main__":
    asyncio.run(main())
