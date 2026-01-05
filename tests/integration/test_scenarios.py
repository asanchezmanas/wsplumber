import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import (
    CurrencyPair, Result, CycleId, OperationId, 
    BrokerTicket, OperationStatus
)
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.interfaces.ports import IRepository
from tests.fixtures.simulated_broker import SimulatedBroker
import logging

# Configurar logging para ver qué pasa durante el test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InMemoryRepository(IRepository):
    def __init__(self):
        self.cycles: Dict[CycleId, Cycle] = {}
        self.operations: Dict[OperationId, Operation] = {}
        self.outbox = []
        self.checkpoints = []

    async def save_cycle(self, cycle: Cycle) -> Result[CycleId]:
        self.cycles[cycle.id] = cycle
        return Result.ok(cycle.id)

    async def get_cycle(self, cycle_id: CycleId) -> Result[Optional[Cycle]]:
        return Result.ok(self.cycles.get(cycle_id))

    async def get_active_cycles(self, pair: Optional[CurrencyPair] = None) -> Result[List[Cycle]]:
        found = [c for c in self.cycles.values() if c.status != "closed"]
        if pair:
            found = [c for c in found if c.pair == pair]
        return Result.ok(found)

    async def get_cycles_by_status(self, statuses, pair=None) -> Result[List[Cycle]]:
        found = [c for c in self.cycles.values() if c.status in statuses]
        if pair:
            found = [c for c in found if c.pair == pair]
        return Result.ok(found)

    async def save_operation(self, operation: Operation) -> Result[OperationId]:
        self.operations[operation.id] = operation
        return Result.ok(operation.id)

    async def get_operation(self, operation_id) -> Result[Optional[Operation]]:
        return Result.ok(self.operations.get(operation_id))

    async def get_operations_by_cycle(self, cycle_id) -> Result[List[Operation]]:
        found = [o for o in self.operations.values() if o.cycle_id == cycle_id]
        return Result.ok(found)

    async def get_active_operations(self, pair=None) -> Result[List[Operation]]:
        found = [o for o in self.operations.values() if o.status == OperationStatus.ACTIVE]
        if pair:
            found = [o for o in found if o.pair == pair]
        return Result.ok(found)

    async def get_pending_operations(self, pair=None) -> Result[List[Operation]]:
        found = [o for o in self.operations.values() if o.status == OperationStatus.PENDING]
        if pair:
            found = [o for o in found if o.pair == pair]
        return Result.ok(found)

    async def get_operation_by_ticket(self, ticket) -> Result[Optional[Operation]]:
        for op in self.operations.values():
            if op.broker_ticket == ticket:
                return Result.ok(op)
        return Result.ok(None)

    async def save_checkpoint(self, state): return Result.ok("cp1")
    async def get_latest_checkpoint(self): return Result.ok(None)
    async def add_to_outbox(self, op_type, payload, idempotency_key): return Result.ok("msg1")
    async def get_pending_outbox_entries(self, limit=10): return Result.ok([])
    async def update_outbox_status(self, entry_id, status, error_message=None): return Result.ok(True)
    async def mark_outbox_processed(self, entry_id): return Result.ok(True)
    
    async def save_daily_metrics(self, metrics): return Result.ok(True)
    async def get_daily_metrics(self, days=30): return Result.ok([])
    
    async def create_alert(self, severity, alert_type, message, metadata=None): 
        return Result.ok("alert1")
    
    async def health_check(self): return Result.ok("OK")
    async def close(self): pass

    async def save_historical_rates(self, pair, timeframe, rates): return Result.ok(len(rates))
    async def save_historical_ticks(self, pair, ticks): return Result.ok(len(ticks))

@pytest.fixture
def mock_settings():
    from unittest.mock import MagicMock
    settings = MagicMock()
    # Mocking the nested structure if needed, or providing flat access
    settings.trading.default_lot_size = 0.01
    settings.trading.max_lot_size = 1.0
    settings.strategy.main_tp_pips = 10
    settings.strategy.main_step_pips = 10
    settings.strategy.recovery_tp_pips = 80
    settings.strategy.recovery_step_pips = 40
    settings.risk.max_exposure_per_pair = 1000.0
    return settings

# Helper para crear objetos de dominio si es necesario
@pytest.fixture
def cycle_factory():
    def _create(pair: CurrencyPair):
        return Cycle(
            id=CycleId(f"{pair}_001"),
            pair=pair,
            status=CycleStatus.ACTIVE,
            main_operations=[]
        )
    return _create

@pytest.mark.asyncio
async def test_scenario_tp_hit(mock_settings):
    # 1. Setup
    broker = SimulatedBroker(initial_balance=1000.0)
    broker.load_csv('tests/scenarios/scenario_tp_hit.csv')
    
    from unittest.mock import patch
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock_settings):
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock_settings
        strategy = Strategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
    
    pair = CurrencyPair("EURUSD")
    
    # 2. Execution Loop
    # Procesar todos los ticks del CSV
    while True:
        tick = await broker.advance_tick()
        if tick is None:
            break
        
        # El orquestador procesa el estado actual basándose en los ticks del broker
        await orchestrator._process_tick_for_pair(pair)
        
    # 3. Assertions
    # Deberíamos tener un ciclo cerrado o al menos una operación completada
    assert len(repo.cycles) > 0
    
    # Verificar que el balance aumentó (aprox $1 o más)
    assert broker.balance > Decimal("1000.0")
    # Aceptamos un rango debido a que el bid/ask puede cerrar un poco por encima del TP
    assert Decimal("1001.0") <= broker.balance <= Decimal("1002.0")

@pytest.mark.asyncio
async def test_scenario_coverage_basic(mock_settings):
    # 1. Setup
    broker = SimulatedBroker(initial_balance=1000.0)
    broker.load_csv('tests/scenarios/scenario_coverage.csv')
    
    from unittest.mock import patch
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock_settings):
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock_settings
        strategy = Strategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
    
    pair = CurrencyPair("EURUSD")
    
    # 2. Execution Loop
    while True:
        tick = await broker.advance_tick()
        if tick is None:
            break
        await orchestrator._process_tick_for_pair(pair)

    # 3. Assertions
    # Debe haber al menos un ciclo y operaciones creadas
    assert len(repo.cycles) > 0
    assert len(repo.operations) >= 2

@pytest.mark.asyncio
async def test_scenario_recovery_win(mock_settings):
    # 1. Setup
    broker = SimulatedBroker(initial_balance=1000.0)
    broker.load_csv('tests/scenarios/scenario_recovery_win.csv')
    
    from unittest.mock import patch
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock_settings):
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock_settings
        strategy = Strategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
    
    pair = CurrencyPair("EURUSD")
    
    # 2. Execution Loop
    while True:
        tick = await broker.advance_tick()
        if tick is None:
            break
        await orchestrator._process_tick_for_pair(pair)

    # 3. Assertions
    # Deberíamos tener al menos el ciclo principal y el de recovery
    assert len(repo.cycles) >= 2
    
    # Verificar que hay operaciones de recovery
    recoveries = [op for op in repo.operations.values() if op.is_recovery]
    assert len(recoveries) > 0
    
    # Verificar que el balance al final es positivo (neutralización exitosa + margen)
    # En este escenario el recovery gana 80 pips
    assert broker.balance > Decimal("1000.0")

