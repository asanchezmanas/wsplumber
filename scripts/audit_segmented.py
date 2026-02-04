"""
WSPlumber - Segmented Audit Script
Processes large Parquet datasets in manageable time-windows (Year, Month, Week).
"""

import asyncio
import sys
import os
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add src and scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
sys.path.insert(0, str(Path(__file__).parent))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, TickData, Price, Pips
from decimal import Decimal
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker
from audit_by_cycle import CycleAuditor

import pickle

def save_simulation_state(path, repo, broker, orchestrator, auditor):
    state = {
        "repo_cycles": repo.cycles,
        "repo_active_cycle_ids": repo._active_cycle_ids,
        "repo_operations": repo.operations,
        "repo_active_ids": repo._active_ids,
        "repo_pending_ids": repo._pending_ids,
        "broker_balance": broker.balance,
        "broker_positions": broker.open_positions,
        "broker_pending": broker.pending_orders,
        "broker_history": broker.history,
        "broker_ticket_counter": broker.ticket_counter,
        # Orchestrator doesn't need much state as it's mostly stateless or derived from repo
        "auditor_state": auditor
    }
    with open(path, "wb") as f:
        pickle.dump(state, f)
    print(f"Simulation state saved to {path}")

def load_simulation_state(path, repo, broker, orchestrator, auditor):
    with open(path, "rb") as f:
        state = pickle.load(f)
    
    if "repo" in state:
        # Compatibility with new format where entire repo is pickled
        restored_repo = state["repo"]
        repo.cycles = restored_repo.cycles
        repo._active_cycle_ids = getattr(restored_repo, "_active_cycle_ids", [])
        repo.operations = restored_repo.operations
        repo._active_ids = getattr(restored_repo, "_active_ids", [])
        repo._pending_ids = getattr(restored_repo, "_pending_ids", [])
    else:
        # Legacy format
        repo.cycles = state.get("repo_cycles", {})
        repo._active_cycle_ids = state.get("repo_active_cycle_ids", [])
        repo.operations = state.get("repo_operations", {})
        repo._active_ids = state.get("repo_active_ids", [])
        repo._pending_ids = state.get("repo_pending_ids", [])
    
    broker.balance = state["broker_balance"]
    broker.open_positions = state["broker_positions"]
    broker.pending_orders = state["broker_pending"]
    broker.history = state["broker_history"]
    broker.ticket_counter = state["broker_ticket_counter"]
    
    # Restore auditor
    if "auditor" in state:
        restored_auditor = state["auditor"]
    else:
        restored_auditor = state.get("auditor_state")
        
    if restored_auditor:
        for attr, value in restored_auditor.__dict__.items():
            setattr(auditor, attr, value)
        
    print(f"Simulation state loaded from {path}")

async def run_segmented_audit(args):
    parquet_path = Path(args.file)
    if not parquet_path.exists():
        print(f"Error: File {parquet_path} not found.")
        return

    print(f"Loading data from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    
    # Ensure timestamp column
    if 'timestamp' not in df.columns:
        if not isinstance(df.index, pd.DatetimeIndex):
            print("Error: Dataset must have a 'timestamp' column or datetime index.")
            return
        df['dt'] = df.index
    else:
        df['dt'] = pd.to_datetime(df['timestamp'])

    # Filtering
    mask = (df['dt'].dt.year == args.year)
    if args.month:
        mask &= (df['dt'].dt.month == args.month)
    if args.week:
        df['week'] = df['dt'].dt.isocalendar().week
        mask &= (df['week'] == args.week)

    filtered_df = df[mask].copy()
    if filtered_df.empty:
        print(f"No data found for Year={args.year}, Month={args.month}, Week={args.week}")
        return

    print(f"Processing {len(filtered_df)} ticks for segment {args.year}-{args.month or 'ALL'}-{args.week or 'ALL'}...")

    # Initialize components
    repo = InMemoryRepository()
    broker = SimulatedBroker(initial_balance=10000.0)
    trading_service = TradingService(broker, repo)
    strategy = WallStreetPlumberStrategy()
    risk_manager = RiskManager()
    
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        repository=repo,
        strategy=strategy,
        risk_manager=risk_manager
    )

    auditor = CycleAuditor()
    pair = CurrencyPair("EURUSD")
    await broker.connect()

    # Restoration from checkpoint
    if args.load_checkpoint:
        load_simulation_state(args.load_checkpoint, repo, broker, orchestrator, auditor)

    # Prepare ticks for broker
    broker_ticks = []
    for _, row in filtered_df.iterrows():
        multiplier = 100 if "JPY" in str(pair) else 10000
        spread_pips = (row['ask'] - row['bid']) * multiplier
        broker_ticks.append(TickData(
            pair=pair,
            bid=Price(Decimal(str(row['bid']))),
            ask=Price(Decimal(str(row['ask']))),
            timestamp=row['dt'],
            spread_pips=Pips(spread_pips)
        ))
    
    broker.ticks = broker_ticks
    broker.current_tick_index = -1

    # Run simulation
    tick_count = 0
    total_ticks = len(broker_ticks)
    
    while True:
        tick = await broker.advance_tick()
        if not tick:
            break
            
        tick_count += 1
        if tick_count % 1000 == 0:
            print(f"Progress: {tick_count}/{total_ticks} ticks...")

        await orchestrator.process_tick(tick)
        
        acc_info = await broker.get_account_info()
        balance = acc_info.unwrap()["balance"]
        equity = acc_info.unwrap()["equity"]
        auditor.check(tick_count, repo, broker, balance, equity)

    # Final report
    report_suffix = f"{args.year}_{args.month or '00'}"
    if args.week:
        report_suffix += f"_W{args.week:02}"
        
    output_file = f"audit_report_segmented_{report_suffix}.txt"
    auditor.print_report(repo, balance, equity, output_file=output_file)

    print(f"\nAudit complete! Report generated: {output_file}")
    print(f"Final Balance: {balance:.2f} | Final Equity: {equity:.2f} | Profit: {balance - 10000.0:.2f}")

    # Save checkpoint
    if args.save_checkpoint:
        save_simulation_state(args.save_checkpoint, repo, broker, orchestrator, auditor)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segmented Backtest Auditor")
    parser.add_argument("file", help="Path to Parquet file")
    parser.add_argument("--year", type=int, required=True, help="Year to audit")
    parser.add_argument("--month", type=int, help="Month to audit (1-12)")
    parser.add_argument("--week", type=int, help="Week number (ISO)")
    parser.add_argument("--save-checkpoint", help="Path to save the final simulation state")
    parser.add_argument("--load-checkpoint", help="Path to load an initial simulation state")
    
    args = parser.parse_args()
    asyncio.run(run_segmented_audit(args))
