"""
WSPlumber - Cycle Audit Report

Generates detailed reports grouped by cycle showing:
- Main operation creation and activation
- Hedge creation with entry prices
- TP hits with P&L
- Cancellations with reasons
- Recovery operations
- FIFO debt compensation

Each event includes tick number for traceability.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, OperationType
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


@dataclass
class CycleEvent:
    """Single event in a cycle's lifecycle."""
    tick: int
    event_type: str
    description: str
    details: str = ""
    pips: float = 0.0
    op_id: str = ""
    ref_op_id: str = ""  # Referenced operation (e.g., linked hedge)


@dataclass
class OperationRef:
    """Operation reference with key details."""
    op_id: str
    op_type: str
    entry_price: float
    tp_price: float
    status: str
    linked_op: str = ""


@dataclass
class CycleAudit:
    """Audit data for a single cycle."""
    id: str
    name: str
    cycle_type: str
    created_tick: int = 0
    status: str = "pending"
    events: List[CycleEvent] = field(default_factory=list)
    mains: Dict[str, OperationRef] = field(default_factory=dict)
    hedges: Dict[str, OperationRef] = field(default_factory=dict)
    recoveries: Dict[str, OperationRef] = field(default_factory=dict)
    total_pips: float = 0.0
    pips_locked: float = 0.0
    
    def add_event(self, tick: int, event_type: str, desc: str, 
                  details: str = "", pips: float = 0.0, 
                  op_id: str = "", ref_op_id: str = ""):
        self.events.append(CycleEvent(tick, event_type, desc, details, pips, op_id, ref_op_id))
        if pips > 0:
            self.total_pips += pips


class CycleAuditor:
    """Auditor that tracks each cycle's complete lifecycle."""
    
    def __init__(self):
        self.cycles: Dict[str, CycleAudit] = {}
        self.cycle_counter = 0
        self.recovery_counter = 0
        self.tick = 0
        self.last_ops: Dict[str, dict] = {}
        self.last_cycles: Set[str] = set()
        self.last_balance = 10000.0
        
    def get_cycle_name(self, cycle_id: str, cycle_type: str) -> str:
        """Generate readable cycle name."""
        if cycle_id not in self.cycles:
            if cycle_type == "main":
                self.cycle_counter += 1
                name = f"C{self.cycle_counter}"
            else:
                self.recovery_counter += 1
                name = f"R{self.recovery_counter}"
            return name
        return self.cycles[cycle_id].name
    
    def get_op_short_name(self, op_type: str, op_id: str) -> str:
        """Generate short operation name."""
        type_map = {
            "main_buy": "M_B",
            "main_sell": "M_S",
            "hedge_buy": "H_B",
            "hedge_sell": "H_S",
            "recovery_buy": "R_B",
            "recovery_sell": "R_S"
        }
        return type_map.get(op_type, op_type.upper())
    
    def check(self, tick: int, repo, broker, balance: float):
        """Analyze changes and record events per cycle."""
        self.tick = tick
        
        # Detect new cycles
        for c in repo.cycles.values():
            if c.id not in self.cycles:
                name = self.get_cycle_name(c.id, c.cycle_type.value)
                self.cycles[c.id] = CycleAudit(
                    id=c.id,
                    name=name,
                    cycle_type=c.cycle_type.value,
                    created_tick=tick,
                    status=c.status.value
                )
                self.cycles[c.id].add_event(
                    tick, "CYCLE_CREATED", 
                    f"Cycle {name} created",
                    details=f"type={c.cycle_type.value}"
                )
        
        # Detect cycle status changes
        for c in repo.cycles.values():
            if c.id in self.cycles:
                audit = self.cycles[c.id]
                if audit.status != c.status.value:
                    old_status = audit.status
                    new_status = c.status.value
                    audit.add_event(
                        tick, "STATUS_CHANGE",
                        f"{old_status.upper()} -> {new_status.upper()}"
                    )
                    audit.status = new_status
        
        # Detect new operations and status changes
        for op in repo.operations.values():
            op_id = str(op.id)
            status = op.status.value
            op_type = op.op_type.value
            cycle_id = op.cycle_id
            
            if cycle_id not in self.cycles:
                continue
            
            audit = self.cycles[cycle_id]
            short_name = self.get_op_short_name(op_type, op_id)
            entry = float(op.entry_price)
            tp = float(op.tp_price) if op.tp_price else 0
            
            if op_id not in self.last_ops:
                # New operation
                self.last_ops[op_id] = {"status": status, "cycle_id": cycle_id, "type": op_type}
                
                op_ref = OperationRef(
                    op_id=op_id,
                    op_type=op_type,
                    entry_price=entry,
                    tp_price=tp,
                    status=status
                )
                
                if "main" in op_type:
                    audit.mains[op_id] = op_ref
                    audit.add_event(
                        tick, "MAIN_CREATED", 
                        f"{short_name} created PENDING",
                        details=f"entry={entry:.5f} tp={tp:.5f}",
                        op_id=op_id
                    )
                elif "hedge" in op_type:
                    # Find which main this hedge is linked to
                    linked_main = ""
                    if "buy" in op_type:
                        # H_B is at MAIN_BUY TP
                        for mid, mref in audit.mains.items():
                            if "buy" in mref.op_type and abs(mref.tp_price - entry) < 0.00001:
                                linked_main = mid
                                break
                    else:
                        # H_S is at MAIN_SELL TP
                        for mid, mref in audit.mains.items():
                            if "sell" in mref.op_type and abs(mref.tp_price - entry) < 0.00001:
                                linked_main = mid
                                break
                    
                    op_ref.linked_op = linked_main
                    audit.hedges[op_id] = op_ref
                    audit.add_event(
                        tick, "HEDGE_CREATED", 
                        f"{short_name} created PENDING",
                        details=f"entry={entry:.5f} linked_to={linked_main[:20] if linked_main else 'none'}",
                        op_id=op_id,
                        ref_op_id=linked_main
                    )
                elif "recovery" in op_type:
                    audit.recoveries[op_id] = op_ref
                    audit.add_event(
                        tick, "RECOVERY_CREATED", 
                        f"{short_name} created PENDING",
                        details=f"entry={entry:.5f} tp={tp:.5f}",
                        op_id=op_id
                    )
            else:
                # Status change
                old_status = self.last_ops[op_id]["status"]
                
                if old_status != status:
                    if old_status == "pending" and status == "active":
                        audit.add_event(tick, "ACTIVATED", f"{short_name} activated", op_id=op_id)
                        
                    elif old_status == "active" and status == "neutralized":
                        audit.add_event(tick, "NEUTRALIZED", f"{short_name} neutralized (hedged)", op_id=op_id)
                        
                    elif status == "tp_hit":
                        pips = float(op.profit_pips) if op.profit_pips else 0
                        audit.add_event(
                            tick, "TP_HIT", 
                            f"{short_name} TP hit",
                            details=f"+{pips:.1f} pips",
                            pips=pips,
                            op_id=op_id
                        )
                        
                    elif status == "cancelled":
                        reason = op.metadata.get("cancel_reason", "counterpart")
                        audit.add_event(
                            tick, "CANCELLED", 
                            f"{short_name} cancelled",
                            details=f"reason={reason}",
                            op_id=op_id
                        )
                    
                    # Update status in operation ref
                    if op_id in audit.mains:
                        audit.mains[op_id].status = status
                    elif op_id in audit.hedges:
                        audit.hedges[op_id].status = status
                    elif op_id in audit.recoveries:
                        audit.recoveries[op_id].status = status
                    
                    self.last_ops[op_id]["status"] = status
        
        # Detect balance change
        if balance > self.last_balance + 0.01:
            diff = balance - self.last_balance
            for cid, audit in self.cycles.items():
                for event in reversed(audit.events):
                    if event.tick == tick and event.event_type == "TP_HIT":
                        audit.add_event(tick, "REALIZED", f"+{diff:.2f} EUR")
                        break
            self.last_balance = balance
    
    def print_report(self, repo, final_balance: float, final_equity: float):
        """Print professional cycle-grouped report."""
        print()
        print("=" * 80)
        print("WSPLUMBER CYCLE AUDIT REPORT")
        print("=" * 80)
        
        sorted_cycles = sorted(self.cycles.values(), key=lambda c: c.created_tick)
        
        for audit in sorted_cycles:
            print(f"\n{'-'*100}")
            print(f"CYCLE: {audit.name} | Type: {audit.cycle_type.upper()} | ID: {audit.id[:40]}...")
            print(f"{'-'*100}")
            print(f"  Created at tick: #{audit.created_tick}")
            print(f"  Final status:    {audit.status.upper()}")
            
            # Show debt units if recovery is involved (from repo data)
            cycle_data = repo.cycles.get(audit.id)
            if cycle_data and hasattr(cycle_data.accounting, 'debt_units'):
                units = cycle_data.accounting.debt_units
                remaining = float(cycle_data.accounting.pips_remaining)
                print(f"  Debt Units:      [{', '.join([f'{u:.0f}' for u in units])}]")
                print(f"  Debt Remaining:  {remaining:.1f} pips")
            
            print(f"  Total P&L:       +{audit.total_pips:.1f} pips")
            print()
            
            # Operations summary with references
            print("  OPERATIONS:")
            print(f"  {'-'*60}")
            print(f"  {'Type':<8} {'Entry':>10} {'TP':>10} {'Status':<12} {'Linked To':<15}")
            print(f"  {'-'*60}")
            
            for op_id, op in audit.mains.items():
                short = self.get_op_short_name(op.op_type, op_id)
                linked = "-"
                status_str = op.status
                if status_str == "active" and audit.status != "closed":
                    status_str = "ACTIVE (Running)"
                print(f"  {short:<8} {op.entry_price:>10.5f} {op.tp_price:>10.5f} {status_str:<15} {linked:<15}")
            
            for op_id, op in audit.hedges.items():
                short = self.get_op_short_name(op.op_type, op_id)
                # Show short name for linked main
                linked = "-"
                if op.linked_op and op.linked_op in audit.mains:
                    linked_type = audit.mains[op.linked_op].op_type
                    linked = self.get_op_short_name(linked_type, op.linked_op)
                
                status_str = op.status
                if status_str == "active" and audit.status != "closed":
                    status_str = "ACTIVE (Running)"
                print(f"  {short:<8} {op.entry_price:>10.5f} {op.tp_price:>10.5f} {status_str:<15} {linked:<15}")
            
            for op_id, op in audit.recoveries.items():
                short = self.get_op_short_name(op.op_type, op_id)
                linked = "-"
                print(f"  {short:<8} {op.entry_price:>10.5f} {op.tp_price:>10.5f} {op.status:<12} {linked:<15}")
            print()
            
            # Event timeline
            print("  EVENT TIMELINE:")
            print(f"  {'-'*60}")
            print(f"  {'Tick':<8} {'Event':<18} {'Description':<30} {'Details'}")
            print(f"  {'-'*60}")
            
            for event in audit.events:
                tick_str = f"#{event.tick}"
                # Truncate long fields
                desc = event.description[:28] if len(event.description) > 28 else event.description
                details = event.details[:25] if len(event.details) > 25 else event.details
                print(f"  {tick_str:<6} {event.event_type:<14} {desc:<28} {details}")
            print()
            
            # Verification checks
            print("  VERIFICATION:")
            
            if audit.cycle_type == "main":
                mains_ok = len(audit.mains) == 2
                status = "[OK]" if mains_ok else "[FAIL]"
                print(f"    {status} Main operations: {len(audit.mains)}/2")
            
            hedged_events = [e for e in audit.events if "HEDGED" in e.description]
            if hedged_events:
                hedges_ok = len(audit.hedges) >= 2
                status = "[OK]" if hedges_ok else "[WARN]"
                print(f"    {status} Hedge operations: {len(audit.hedges)}/2 (cycle was HEDGED)")
                
                # Verify hedge entry prices
                for hid, hedge in audit.hedges.items():
                    if hedge.linked_op:
                        linked_main = audit.mains.get(hedge.linked_op)
                        if linked_main:
                            price_ok = abs(hedge.entry_price - linked_main.tp_price) < 0.00001
                            status = "[OK]" if price_ok else "[FAIL]"
                            short_h = self.get_op_short_name(hedge.op_type, hid)
                            short_m = self.get_op_short_name(linked_main.op_type, hedge.linked_op)
                            print(f"    {status} {short_h} entry={hedge.entry_price:.5f} matches {short_m} TP={linked_main.tp_price:.5f}")
            
            tp_events = [e for e in audit.events if e.event_type == "TP_HIT"]
            if tp_events:
                total_pips = sum(e.pips for e in tp_events)
                print(f"    [OK] TP hits: {len(tp_events)} (total +{total_pips:.1f} pips)")
        
        # Global summary
        print("\n" + "="*100)
        print("GLOBAL SUMMARY")
        print("="*100)
        
        main_cycles = [c for c in self.cycles.values() if c.cycle_type == "main"]
        recovery_cycles = [c for c in self.cycles.values() if c.cycle_type == "recovery"]
        
        print(f"  Main cycles:     {len(main_cycles)}")
        print(f"  Recovery cycles: {len(recovery_cycles)}")
        print(f"  Total P&L:       +{sum(c.total_pips for c in self.cycles.values()):.1f} pips")
        print(f"  Balance:         {self.last_balance:.2f} EUR -> {final_balance:.2f} EUR")
        print(f"  Equity:          {final_equity:.2f} EUR")
        print(f"  Floating:        {final_equity - final_balance:+.2f} EUR")
        
        # Global invariants
        print("\n  INVARIANT CHECKS:")
        all_main_have_2 = all(len(c.mains) == 2 for c in main_cycles)
        if all_main_have_2:
            print("    [OK] All MAIN cycles have exactly 2 main operations")
        else:
            problematic = [c.name for c in main_cycles if len(c.mains) != 2]
            print(f"    [FAIL] Cycles with mains != 2: {problematic}")
        
        print("="*100)


async def run_cycle_audit(max_bars: int = 500):
    """Execute backtest with cycle audit."""
    import logging
    import sys
    logging.disable(logging.CRITICAL)
    
    print(f"\nWSPlumber Cycle Audit ({max_bars} bars)", flush=True)
    print("-" * 40, flush=True)
    
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
    broker.load_m1_csv("2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv", pair, max_bars=max_bars)
    await broker.connect()
    
    auditor = CycleAuditor()
    tick_count = 0
    total_ticks = len(broker.ticks)
    
    print(f"Total ticks: {total_ticks}")
    
    while True:
        tick = await broker.advance_tick()
        if not tick:
            break
        
        await orchestrator.process_tick(tick)
        tick_count += 1
        
        acc = await broker.get_account_info()
        balance = float(acc.value["balance"])
        auditor.check(tick_count, repo, broker, balance)
    
    acc = await broker.get_account_info()
    final_balance = float(acc.value["balance"])
    final_equity = float(acc.value["equity"])
    
    auditor.print_report(repo, final_balance, final_equity)


if __name__ == "__main__":
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    asyncio.run(run_cycle_audit(bars))
