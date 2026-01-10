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
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    logging.basicConfig(level=numeric_level, format='%(message)s')
    
    # SILENCE INTERNAL LOGGERS
    logging.getLogger("wsplumber").setLevel(logging.CRITICAL)
    logging.getLogger("wsplumber.core").setLevel(logging.CRITICAL)
    logging.getLogger("wsplumber.application").setLevel(logging.CRITICAL)
    logging.getLogger("tests.fixtures.simulated_broker").setLevel(logging.CRITICAL)
    
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
                open_cycles = sum(1 for c in repo.cycles.values() if c.status != "closed")
                active_rec = sum(1 for c in repo.cycles.values() if c.cycle_type.value == "recovery" and c.status != "closed")
                total_pips = sum(c.total_pips for c in auditor.cycles.values())
                
                print(f" TICK #{tick_count:7,} | Bal: {balance:10.2f} | Eq: {equity:10.2f} | Pips: +{total_pips:7.1f} | Cycles: {open_cycles:3} | Rec: {active_rec:2}", flush=True)

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
