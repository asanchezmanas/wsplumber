"""Debug script to trace balance drops."""
import asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker

async def debug():
    settings = MagicMock()
    settings.trading.default_lot_size = 0.01
    settings.trading.max_lot_size = 1.0
    settings.strategy.main_tp_pips = 10
    settings.strategy.main_step_pips = 10
    settings.strategy.recovery_tp_pips = 80
    settings.strategy.recovery_step_pips = 40
    settings.risk.max_exposure_per_pair = 1000.0
    
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv('tests/scenarios/eurusd_2015_full.csv')
    await broker.connect()
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=settings):
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = settings
        strategy = Strategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
    
    pair = CurrencyPair('EURUSD')
    prev_balance = Decimal('10000.0')
    prev_history_len = 0
    
    for i in range(100):
        tick = await broker.advance_tick()
        if not tick:
            break
        await orchestrator._process_tick_for_pair(pair)
        
        acc = await broker.get_account_info()
        current = acc.value['balance']
        
        if current < prev_balance:
            diff = current - prev_balance
            print(f'TICK {i+1}: Balance {prev_balance} -> {current} (DROP {diff})')
            # Show what closed since last tick
            if len(broker.history) > prev_history_len:
                for h in broker.history[prev_history_len:]:
                    op_id = h.get('operation_id', 'unknown')
                    order_type = h.get('order_type', 'unknown')
                    profit = h.get('profit_pips', 0)
                    print(f'  CLOSED: {op_id} type={order_type} pnl={profit:.1f} pips')
        prev_balance = current
        prev_history_len = len(broker.history)
    
    print(f'\nFinal balance: {prev_balance}')

if __name__ == '__main__':
    asyncio.run(debug())
