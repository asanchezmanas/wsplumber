import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from fixtures.simulated_broker import SimulatedBroker

def mock_settings():
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.trading.default_lot_size = 0.01
    mock.trading.max_lot_size = 1.0
    mock.strategy.main_tp_pips = 10
    mock.strategy.main_step_pips = 10
    mock.strategy.recovery_tp_pips = 80
    mock.strategy.recovery_step_pips = 40
    mock.risk.max_exposure_per_pair = 1000.0
    return mock

async def run_2015_full():
    # optimized path
    pq_path = Path("tests/scenarios/eurusd_2015_full.parquet")
    csv_path = Path("tests/scenarios/eurusd_2015_full.csv")
    
    data_path = pq_path if pq_path.exists() else csv_path
    
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}")
        return

    print(f"\n--- RUNNING INTEGRITY BACKTEST: {data_path.name} ---")
    print(f"Logging to: eurusd_2015_full.log")
    
    # Configure logging to file
    import logging
    file_handler = logging.FileHandler("eurusd_2015_full.log", mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)  # ALWAYS log INFO and WARNING for debugging

    start_run = datetime.now()
    pair = CurrencyPair("EURUSD")
    mock = mock_settings()
    
    broker = SimulatedBroker(initial_balance=10000.0)
    print(f"Loading data into memory...")
    start_load = datetime.now()
    broker.load_csv(str(data_path))
    load_duration = (datetime.now() - start_load).total_seconds()
    print(f"Data ready in {load_duration:.2f}s")
    await broker.connect()
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock
        strategy = WallStreetPlumberStrategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        tick_count = 0
        update_freq = 1000  # More frequent updates for feel
        total_ticks = len(broker.ticks)
        
        try:
            while True:
                tick = await broker.advance_tick()
                if tick is None:
                    break
                await orchestrator._process_tick_for_pair(pair)
                tick_count += 1
                
                if tick_count % update_freq == 0:
                    percent = (tick_count / total_ticks) * 100
                    date_str = tick.timestamp.strftime("%Y-%m-%d %H:%M")
                    print(f"[{date_str}] {percent:5.1f}% | Bal: {broker.balance:10.2f} | Eq: {broker.equity:10.2f} | T: {tick_count}", end='\r')
                    
        except Exception as e:
            print(f"\nExecution failed: {e}")
            logging.error(f"Execution failed: {e}", exc_info=True)

    end_run = datetime.now()
    duration = end_run - start_run
    
    summary = f"""
\n--- RESULTS ---
Duration: {duration}
Total Ticks: {tick_count}
Initial Balance: 10000.00
Final Balance: {broker.balance:.2f}
Final Equity: {broker.equity:.2f}
Equity vs Balance: {broker.equity - broker.balance:.2f}
Open Positions in Broker: {len(broker.open_positions)}
"""
    print(summary)
    logging.info(summary)
    
    # Check for zombies
    open_tickets = list(broker.open_positions.keys())
    if open_tickets:
        msg = f"WARNING: Open positions detected at end of run: {open_tickets}"
        print(msg)
        logging.warning(msg)
    else:
        msg = "SUCCESS: No zombie positions remaining."
        print(msg)
        logging.info(msg)

if __name__ == "__main__":
    asyncio.run(run_2015_full())
