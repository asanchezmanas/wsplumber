import asyncio
import uuid
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, CycleStatus
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from scripts.audit_by_cycle import CycleAuditor
from scripts.audit_scenario import AuditMetrics

@dataclass
class SimulationTask:
    task_id: str
    csv_path: str
    status: str = "pending"
    progress: float = 0.0
    tick_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

class SimulationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimulationManager, cls).__new__(cls)
            cls._instance.tasks = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def run_simulation(self, task_id: str, csv_path: str, initial_balance: float = 10000.0):
        task = self.tasks[task_id]
        task.status = "running"
        task.start_time = datetime.utcnow()
        
        try:
            path = Path(csv_path)
            if not path.exists():
                raise FileNotFoundError(f"Scenario file not found: {csv_path}")

            # Setup Engine (Reuse logic from audit_scenario.py)
            broker = SimulatedBroker(initial_balance=initial_balance)
            broker.load_csv(str(path))
            await broker.connect()

            repo = InMemoryRepository()
            trading_service = TradingService(broker, repo)
            risk_manager = RiskManager()
            strategy = WallStreetPlumberStrategy()
            
            # Mock settings (same as audit_scenario.py)
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
                metrics = AuditMetrics()
                tick_count = 0
                
                # Detect pair
                pair_str = "EURUSD"
                if "JPY" in csv_path.upper(): pair_str = "USDJPY"
                if "GBP" in csv_path.upper(): pair_str = "GBPUSD"
                pair = CurrencyPair(pair_str)

                # Simulation loop
                while True:
                    tick = await broker.advance_tick()
                    if not tick:
                        break
                    
                    await orchestrator._process_tick_for_pair(pair)
                    tick_count += 1
                    
                    acc = await broker.get_account_info()
                    balance = float(acc.value["balance"])
                    equity = float(acc.value["equity"])
                    
                    # Update auditor (Opt: Every 1 tick? Yes, for correctness in accounting)
                    auditor.check(tick_count, repo, broker, balance)
                    
                    # Update status periodically (every 1000 ticks)
                    if tick_count % 1000 == 0:
                        task.tick_count = tick_count
                        task.progress = (tick_count / 500000.0) * 100 # Approx for now
                        # We don't yield here to keep it fast, but task object is updated

                # Post-simulation
                task.status = "completed"
                task.end_time = datetime.utcnow()
                acc = await broker.get_account_info()
                task.result = {
                    "final_balance": float(acc.value["balance"]),
                    "final_equity": float(acc.value["equity"]),
                    "total_ticks": tick_count,
                    "report_file": f"audit_report_{path.stem}.txt",
                    "chart_file": f"audit_chart_{path.stem}.png"
                }
                
                # Generate final artifacts
                metrics.generate_chart(task.result["chart_file"])
                # We could redirect stdout here to save the report too

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.end_time = datetime.utcnow()

    def create_task(self, csv_path: str) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = SimulationTask(task_id=task_id, csv_path=csv_path)
        return task_id
