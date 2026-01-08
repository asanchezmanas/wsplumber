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

from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository


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
    broker.load_csv('tests/old_scenarios/scenario_tp_hit.csv')
    await broker.connect()  # Conectar el broker

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
        
    # 3. Debugging - Imprimir estado final
    print(f"\n=== ESTADO FINAL ===")
    print(f"Cycles: {len(repo.cycles)}")
    print(f"Operations: {len(repo.operations)}")
    print(f"Balance: {broker.balance}")
    print(f"Open positions: {len(broker.open_positions)}")
    print(f"History: {len(broker.history)}")

    for cycle_id, cycle in repo.cycles.items():
        print(f"\nCycle {cycle_id}: status={cycle.status}")

    for op_id, op in repo.operations.items():
        print(f"Op {op_id}: status={op.status}, profit={op.profit_pips} pips")

    # Assertions
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
    broker.load_csv('tests/old_scenarios/scenario_coverage.csv')
    await broker.connect()  # Conectar el broker

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
    broker.load_csv('tests/old_scenarios/scenario_recovery_win.csv')
    await broker.connect()  # Conectar el broker

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

