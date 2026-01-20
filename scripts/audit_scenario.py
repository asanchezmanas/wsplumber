"""
WSPlumber - Scenario Auditor (Streaming Version)
Usage: python scripts/audit_scenario.py tests/scenarios/r07.csv --log-level INFO --log-suffix "_v1"
"""
import asyncio
import sys
import os
import csv
import logging
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from scripts.audit_by_cycle import CycleAuditor

async def audit_scenario(csv_path_str: str, log_level: str = "INFO", default_pair: str = "EURUSD", log_suffix: str = "", csv_interval: int = 100):
    csv_path = Path(csv_path_str)
    log_name = f"audit_logs_{csv_path.stem}{log_suffix}.log"
    
    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # File handler (Always DEBUG for the file)
    file_handler = logging.FileHandler(log_name, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Console handler - CRITICAL only (suppress JSON logs, only print() shows)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.CRITICAL)  # Only show critical errors
    root_logger.addHandler(console_handler)

    print(f"[INFO] Logs will be saved to: {log_name}")

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return

    # Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv(str(csv_path), default_pair=default_pair)
    await broker.connect()

    repo = InMemoryRepository()
    trading_service = TradingService(broker, repo)
    risk_manager = RiskManager()
    strategy = WallStreetPlumberStrategy()
    pair = CurrencyPair(default_pair)
    
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        strategy=strategy,
        risk_manager=risk_manager,
        repository=repo
    )

    auditor = CycleAuditor()
    tick_count = 0
    
    # CSV for dashboard visualization
    metrics_csv_path = f"audit_metrics_{csv_path.stem}{log_suffix}.csv"
    metrics_file = open(metrics_csv_path, 'w', newline='', encoding='utf-8')
    metrics_writer = csv.writer(metrics_file)
    metrics_writer.writerow(['tick', 'timestamp', 'balance', 'equity', 'dd_pct', 'active', 'hedged', 'in_recovery', 'closed', 'rec_active', 'rec_closed', 'mtp', 'rtp'])
    print(f"[INFO] Metrics CSV: {metrics_csv_path}")
    
    from wsplumber.core.strategy import _params
    print(f"\n[AUDIT] Starting processing: {csv_path.name}")
    print(f"[CONFIG] Layer 1 Mode: {getattr(_params, 'LAYER1_MODE', 'UNKNOWN')}")
    print(f"[CONFIG] Dynamic Debt: {getattr(_params, 'USE_DYNAMIC_DEBT', 'FALSE')}")
    print("-" * 140)
    print(f"{'TICK':>12} | {'Balance':>10} | {'Equity':>10} | {'DD%':>5} | {'Act':>4} | {'Hdg':>4} | {'InR':>4} | {'Clo':>4} | {'RecA':>5} | {'RecC':>5} | {'MTP':>5} | {'RTP':>5}")
    print("-" * 140)

    # RE-START GENERATOR TO BE SURE
    broker._tick_generator = broker._create_tick_generator()

    while True:
        tick = await broker.advance_tick()
        if not tick:
            break
        
        await orchestrator._process_tick_for_pair(pair)
        tick_count += 1
        
        # CSV metrics capture (configurable interval via --csv-interval)
        if tick_count % csv_interval == 0 or tick_count == 1:
            acc = await broker.get_account_info()
            bal = acc.value["balance"]
            eq = acc.value["equity"]
            dd = ((bal - eq) / bal * 100) if bal > 0 else 0
            all_c = repo.cycles.values()
            mc = [c for c in all_c if c.cycle_type.value == "main"]
            rc = [c for c in all_c if c.cycle_type.value == "recovery"]
            ts = tick.timestamp.isoformat() if hasattr(tick, 'timestamp') else datetime.now().isoformat()
            metrics_writer.writerow([
                tick_count, ts, f'{bal:.2f}', f'{eq:.2f}', f'{dd:.2f}',
                sum(1 for c in mc if c.status.value == "active"),
                sum(1 for c in mc if c.status.value == "hedged"),
                sum(1 for c in mc if c.status.value == "in_recovery"),
                sum(1 for c in mc if c.status.value == "closed"),
                sum(1 for c in rc if c.status.value != "closed"),
                sum(1 for c in rc if c.status.value == "closed"),
                sum(1 for o in repo.operations.values() if o.is_main and o.status.value == "tp_hit"),
                sum(1 for o in repo.operations.values() if o.is_recovery and o.status.value == "tp_hit")
            ])
            if tick_count % 1000 == 0:  # Flush every 1000 ticks for performance
                metrics_file.flush()
        
        # Periodic status update (uses csv_interval for console output)
        if tick_count % csv_interval == 0 or tick_count == 1:
            acc_info = await broker.get_account_info()
            balance = acc_info.value["balance"]
            equity = acc_info.value["equity"]
            
            # Stats from repo
            all_cycles = repo.cycles.values()
            main_cycles = [c for c in all_cycles if c.cycle_type.value == "main"]
            rec_cycles = [c for c in all_cycles if c.cycle_type.value == "recovery"]
            
            c_active = sum(1 for c in main_cycles if c.status.value == "active")
            c_hedged = sum(1 for c in main_cycles if c.status.value == "hedged")
            c_in_rec = sum(1 for c in main_cycles if c.status.value == "in_recovery")
            c_closed = sum(1 for c in main_cycles if c.status.value == "closed")
            
            active_rec = sum(1 for c in rec_cycles if c.status.value != "closed")
            closed_rec = sum(1 for c in rec_cycles if c.status.value == "closed")
            
            # Use repo.operations - count ops that closed (have close price)
            main_tps = sum(1 for o in repo.operations.values() 
                          if o.is_main and o.status.value in ("tp_hit", "closed") and o.actual_close_price is not None)
            rec_tps = sum(1 for o in repo.operations.values() 
                         if o.is_recovery and o.status.value in ("tp_hit", "closed") and o.actual_close_price is not None)

            
            dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
            
            print(f"{tick_count:>12,} | {balance:>10.2f} | {equity:>10.2f} | {dd_pct:>4.1f}% | {c_active:>4} | {c_hedged:>4} | {c_in_rec:>4} | {c_closed:>4} | {active_rec:>5} | {closed_rec:>5} | {main_tps:>5} | {rec_tps:>5}", flush=True)

    # Close metrics CSV
    metrics_file.close()
    print(f"[INFO] Metrics saved to: {metrics_csv_path}")

    # FINAL LEAK DETECTION
    active_ops = [op for op in repo.operations.values() if op.status.value in ("active", "neutralized")]
    if active_ops:
        print("\n[LEAK DETECTOR] Open operations found at end:")
        for op in active_ops:
            cycle = repo.cycles.get(op.cycle_id)
            c_status = cycle.status.value if cycle else "Unknown"
            print(f"  Op {op.id[:8]} | {op.op_type.value} {op.lot_size} | Cycle {op.cycle_id[:8]} ({c_status})")

    # Final Summary
    acc_info = await broker.get_account_info()
    final_balance = acc_info.value["balance"]
    final_equity = acc_info.value["equity"]
    
    report_name = f"audit_report_{csv_path.stem}{log_suffix}.txt"
    print(f"\n[INFO] Saving final report to: {report_name}")
    
    with open(report_name, 'w', encoding='utf-8') as f:
        original_stdout = sys.stdout
        sys.stdout = f
        try:
            auditor.print_report(repo, float(final_balance), float(final_equity))
        finally:
            sys.stdout = original_stdout
            
    print(f"[OK] Audit completed for {tick_count:,} ticks.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WSPlumber Scenario Auditor")
    parser.add_argument("csv_path", help="Path to scenario CSV")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--log-suffix", default="", help="Suffix for output files")
    parser.add_argument("--csv-interval", type=int, default=100, help="Write to CSV every N ticks (default: 100)")
    
    args = parser.parse_args()
    
    default_pair = "EURUSD"
    if "JPY" in args.csv_path.upper(): default_pair = "USDJPY"
    if "GBP" in args.csv_path.upper(): default_pair = "GBPUSD"

    async def run_now():
        await audit_scenario(args.csv_path, args.log_level, default_pair, args.log_suffix, args.csv_interval)

    try:
        asyncio.run(run_now())
    except KeyboardInterrupt:
        print("\n[INFO] Audit interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Audit failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
