"""
WSPlumber - Scenario Auditor
Usage: python scripts/audit_scenario.py tests/scenarios/r07_cascade_n1_n2_n3.csv
"""
import asyncio
import sys
import os
from pathlib import Path
from decimal import Decimal

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

async def audit_scenario(csv_path_str: str, log_level: str = "INFO"):
    import logging
    from pathlib import Path as LogPath
    
    csv_path = Path(csv_path_str)
    log_file = f"audit_logs_{csv_path.stem}.log"
    
    # Configure file handler to save ALL logs
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
    
    # Root logger writes to file
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Enable wsplumber loggers
    logging.getLogger("wsplumber").setLevel(logging.DEBUG)
    logging.getLogger("wsplumber.core").setLevel(logging.DEBUG)
    logging.getLogger("wsplumber.application").setLevel(logging.DEBUG)
    logging.getLogger("tests.fixtures.simulated_broker").setLevel(logging.DEBUG)
    
    print(f"[INFO] Logs will be saved to: {log_file}")

    
    csv_path = Path(csv_path_str)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return

    # Detect pair
    pair_str = "EURUSD"
    if "JPY" in csv_path_str.upper(): pair_str = "USDJPY"
    if "GBP" in csv_path_str.upper(): pair_str = "GBPUSD"
    pair = CurrencyPair(pair_str)

    # Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv(str(csv_path))
    await broker.connect()

    repo = InMemoryRepository()
    trading_service = TradingService(broker, repo)
    risk_manager = RiskManager()
    strategy = WallStreetPlumberStrategy()
    
    # Mock settings for risk manager/strategy
    from unittest.mock import MagicMock, patch
    mock = MagicMock()
    mock.trading.default_lot_size = 0.01
    mock.trading.max_lot_size = 1.0
    mock.strategy.main_tp_pips = 10
    mock.strategy.main_step_pips = 10
    mock.strategy.recovery_tp_pips = 80
    mock.strategy.recovery_step_pips = 40
    mock.risk.max_exposure_per_pair = 1000.0
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        risk_manager.settings = mock
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )

        auditor = CycleAuditor()
        tick_count = 0
        
        while True:
            tick = await broker.advance_tick()
            if not tick:
                break
            
            await orchestrator._process_tick_for_pair(pair)
            tick_count += 1
            
            acc = await broker.get_account_info()
            balance = float(acc.value["balance"])
            auditor.check(tick_count, repo, broker, balance)
            
            # PROGRESS LOGGING
            if tick_count % 1000 == 0:
                acc = await broker.get_account_info()
                equity = float(acc.value["equity"])
                
                # Count cycles by status
                open_cycles = sum(1 for c in repo.cycles.values() if c.status.value != "closed")
                closed_cycles = sum(1 for c in repo.cycles.values() if c.status.value == "closed")
                active_rec = sum(1 for c in repo.cycles.values() if c.cycle_type.value == "recovery" and c.status.value != "closed")
                
                # Count TPs by type
                main_tps = sum(1 for o in repo.operations.values() if o.is_main and o.status.value == "tp_hit")
                rec_tps = sum(1 for o in repo.operations.values() if o.is_recovery and o.status.value == "tp_hit")
                
                # Calculate DD
                dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
                
                total_pips = sum(c.total_pips for c in auditor.cycles.values())
                
                # Print header every 10k ticks
                if tick_count % 10000 == 0:
                    print(f"\n{'TICK':>10} | {'Balance':>10} | {'Equity':>10} | {'DD%':>6} | {'Pips':>8} | {'Open':>5}/{'':<5} | {'MainTP':>6} | {'RecTP':>6} | {'Rec':>4}", flush=True)
                    print("-"*100)
                
                print(f"{tick_count:>10,} | {balance:>10.2f} | {equity:>10.2f} | {dd_pct:>5.1f}% | {total_pips:>+8.1f} | {open_cycles:>5}/{closed_cycles:<5} | {main_tps:>6} | {rec_tps:>6} | {active_rec:>4}", flush=True)


        acc = await broker.get_account_info()
        
        # Determine output file
        report_name = f"audit_report_{csv_path.stem}.txt"
        print(f"\n[INFO] Saving audit report to: {report_name}")
        
        # Redirect stdout to file for the report
        with open(report_name, 'w', encoding='utf-8') as f:
            original_stdout = sys.stdout
            sys.stdout = f
            try:
                auditor.print_report(repo, float(acc.value["balance"]), float(acc.value["equity"]), repo)
            finally:
                sys.stdout = original_stdout
        
        print(f"[OK] Audit completed for {tick_count} ticks.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WSPlumber Scenario Auditor")
    parser.add_argument("csv_path", help="Path to scenario CSV")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(audit_scenario(args.csv_path, args.log_level))
    except KeyboardInterrupt:
        print("\n[INFO] Audit interrupted by user.")
        sys.exit(0)
