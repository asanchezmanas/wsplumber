"""
WSPlumber - Integrity Auditor
Detects mismatches between Repository (DB) and Broker (Market).
Finds orphans, zombies, and debt inconsistencies.
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Set

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, OperationType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker

class IntegrityAuditor:
    def __init__(self, repo: InMemoryRepository, broker: SimulatedBroker):
        self.repo = repo
        self.broker = broker
        self.anomalies = []

    async def run_audit(self):
        print("-" * 80)
        print("WSPLUMBER INTEGRITY AUDIT")
        print("-" * 80)

        # 1. Broker Positions vs Repo Operations
        broker_tickets = set(self.broker.open_positions.keys())
        broker_pending = set(self.broker.pending_orders.keys())
        all_broker_tickets = broker_tickets | broker_pending

        repo_active_ops = {op.broker_ticket: op for op in self.repo.operations.values() 
                           if op.status in (OperationStatus.ACTIVE, OperationStatus.NEUTRALIZED, OperationStatus.PENDING, OperationStatus.TP_HIT) 
                           and op.broker_ticket}
        
        # A. ORPHANS: Broker has them, Repo doesn't think they are active
        orphans = all_broker_tickets - set(repo_active_ops.keys())
        for ticket in orphans:
            pos = self.broker.open_positions.get(ticket) or self.broker.pending_orders.get(ticket)
            self.anomalies.append(f"[ERROR] ORPHAN TICKET: Broker has {ticket} ({pos.operation_id}) but Repo doesn't list it as active.")

        # B. ZOMBIES: Repo thinks they are active, Broker doesn't have them
        zombies = set(repo_active_ops.keys()) - all_broker_tickets
        for ticket in zombies:
            op = repo_active_ops[ticket]
            # Look in history
            h_entry = self.broker.history_dict.get(ticket)
            if h_entry:
                if op.status in (OperationStatus.TP_HIT, OperationStatus.CLOSED):
                    # It's fine, it hit TP and is in history
                    continue
                self.anomalies.append(f"[WARN] ZOMBIE OPERATION: Repo thinks {op.id} is {op.status.value}, but Broker closed it (Reason: {h_entry.get('status')}).")
            else:
                self.anomalies.append(f"[ERROR] LOST OPERATION: Repo thinks {op.id} is {op.status.value}, but Broker has no record of it (Ticket {ticket}).")

        # 2. Debt Unit Consistency
        for cycle in self.repo.cycles.values():
            for unit in cycle.accounting.debt_units:
                for op_id in unit.source_operation_ids:
                    if not op_id: continue
                    op_res = await self.repo.get_operation(op_id)
                    if not op_res.success:
                        self.anomalies.append(f"❌ DEBT INCONSISTENCY: Unit {unit.id} references non-existent op {op_id}")
                        continue
                    
                    op = op_res.value
                    if unit.status == "active" and op.status != OperationStatus.NEUTRALIZED:
                         self.anomalies.append(f"[ADVISORY] DEBT UNIT {unit.id} is active but op {op.id} is {op.status.value} (expected neutralized)")
                    
                    if unit.status == "active" and op.broker_ticket and op.broker_ticket not in all_broker_tickets:
                         # Look in history
                         h_entry = self.broker.history_dict.get(op.broker_ticket)
                         reason = h_entry.get("status") if h_entry else "unknown"
                         self.anomalies.append(f"[ERROR] DEBT FRAUD: Unit {unit.id} expects ticket {op.broker_ticket} to be open, but it was closed (Reason: {reason}).")

        # Report
        if not self.anomalies:
            print("[OK] INTEGRITY CHECK PASSED: Repository and Broker are in sync.")
        else:
            print(f"[FAIL] FOUND {len(self.anomalies)} ANOMALIES:")
            for a in self.anomalies:
                print(f"  {a}")
        print("-" * 80 + "\n")

async def run_integrity_test(bars=500, scenario="2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv"):
    print(f"Running integrity scan on {scenario} for {bars} bars...")
    
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    trading_service = TradingService(broker, repo)
    risk_manager = RiskManager()
    strategy = WallStreetPlumberStrategy()
    orchestrator = CycleOrchestrator(trading_service, strategy, risk_manager, repo)
    
    pair = CurrencyPair("EURUSD")
    broker.load_m1_csv(scenario, pair, max_bars=bars)
    await broker.connect()
    
    tick_count = 0
    while True:
        tick = await broker.advance_tick()
        if not tick: break
        await orchestrator.process_tick(tick)
        tick_count += 1
    
    auditor = IntegrityAuditor(repo, broker)
    await auditor.run_audit()

if __name__ == "__main__":
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    scenario = sys.argv[2] if len(sys.argv) > 2 else "2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv"
    asyncio.run(run_integrity_test(bars, scenario))
