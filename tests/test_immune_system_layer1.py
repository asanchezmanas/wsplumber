import asyncio
import logging
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

# Configurar path para importar wsplumber
root = Path(__file__).parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "src"))

from wsplumber.domain.types import (
    CurrencyPair, StrategySignal, SignalType, OperationType, 
    OperationStatus, BrokerTicket, Price, LotSize
)
from wsplumber.infrastructure.logging.safe_logger import get_logger
from wsplumber.application.services.trading_service import TradingService
from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.core.strategy import WallStreetPlumberStrategy
from wsplumber.domain.entities.cycle import Cycle, CycleType, CycleStatus
from wsplumber.domain.entities.operation import Operation
from tests.fixtures.simulated_broker import SimulatedBroker, SimulatedPosition
import wsplumber.core.strategy._params as params

logger = get_logger(__name__, environment="development")

async def test_recovery_breakeven():
    print("\n" + "="*50)
    print("TEST: IMMUNE SYSTEM LAYER 1 V2 - DYNAMIC TRAILING")
    print("="*50)
    
    # 1. Configurar V2
    params.ENABLE_IMMUNE_SYSTEM = True
    params.BE_ACTIVATION_PIPS = 40.0
    params.BE_TRAILING_RATIO = 0.5
    params.BE_MIN_CAPTURE_PIPS = 10.0
    
    # 2. Setup Broker
    broker = SimulatedBroker()
    broker._connected = True
    
    csv_content = """timestamp,pair,bid,ask
2026-01-01T00:00:00,USDJPY,150.00,150.01
2026-01-01T00:01:00,USDJPY,150.45,150.46
2026-01-01T00:02:00,USDJPY,151.00,151.01
2026-01-01T00:03:00,USDJPY,150.50,150.51
2026-01-01T00:04:00,USDJPY,150.50,150.51
"""
    csv_path = "tests/scenarios/robustness/i01_recovery_be_v2.csv"
    with open(csv_path, "w") as f: f.write(csv_content)
    broker.load_csv(csv_path)
    
    # 3. Setup Mock Repo
    cycles = {}
    operations = {}
    
    repo = MagicMock()
    async def save_cycle(c): 
        cycles[c.id] = c
        return MagicMock(success=True)
    async def get_cycle(cid): 
        return MagicMock(success=True, value=cycles.get(cid))
    async def get_active_cycles(p):
        return MagicMock(success=True, value=[c for c in cycles.values() if str(c.pair) == str(p) and c.status != CycleStatus.CLOSED])
    async def save_operation(op):
        operations[op.id] = op
        return MagicMock(success=True)
    async def get_operations_by_cycle(cid):
        return MagicMock(success=True, value=[op for op in operations.values() if op.cycle_id == cid])
    async def get_active_operations(p):
        return MagicMock(success=True, value=[op for op in operations.values() if op.status in (OperationStatus.ACTIVE, OperationStatus.NEUTRALIZED)])
    async def get_pending_operations(p):
        return MagicMock(success=True, value=[op for op in operations.values() if op.status == OperationStatus.PENDING])

    repo.save_cycle = save_cycle
    repo.get_cycle = get_cycle
    repo.get_active_cycles = get_active_cycles
    repo.save_operation = save_operation
    repo.get_operations_by_cycle = get_operations_by_cycle
    repo.get_active_operations = get_active_operations
    repo.get_pending_operations = get_pending_operations

    # 4. Inyectar Ciclos y Operación
    pair = CurrencyPair("USDJPY")
    parent_id = str(uuid.uuid4())
    parent_cycle = Cycle(id=parent_id, pair=pair, cycle_type=CycleType.MAIN)
    parent_cycle.status = CycleStatus.IN_RECOVERY
    cycles[parent_id] = parent_cycle
    
    recovery_id = str(uuid.uuid4())
    recovery_cycle = Cycle(id=recovery_id, pair=pair, cycle_type=CycleType.RECOVERY)
    recovery_cycle.metadata["parent_cycle_id"] = parent_id
    cycles[recovery_id] = recovery_cycle
    
    op_id = str(uuid.uuid4())
    op = Operation(
        id=op_id, pair=pair, op_type=OperationType.RECOVERY_BUY,
        lot_size=LotSize(Decimal("0.1")), entry_price=Price(Decimal("150.00")),
        tp_price=Price(Decimal("150.80")), cycle_id=recovery_id
    )
    op.status = OperationStatus.ACTIVE
    op.broker_ticket = BrokerTicket(12345)
    op.actual_entry_price = Price(Decimal("150.00"))
    operations[op_id] = op
    
    broker.open_positions[op.broker_ticket] = SimulatedPosition(
        ticket=op.broker_ticket, operation_id=op.id, pair=pair,
        lot_size=op.lot_size, order_type=op.op_type,
        entry_price=op.entry_price, tp_price=op.tp_price, status=OperationStatus.ACTIVE,
        open_time=datetime.now()
    )

    # 5. Setup Orchestrator
    strategy = WallStreetPlumberStrategy()
    risk_manager = MagicMock()
    trading_service = TradingService(broker, repo)
    orchestrator = CycleOrchestrator(trading_service, strategy, risk_manager, repo)
    orchestrator._active_cycles = {pair: parent_cycle}

    print("\nStep 1: Running simulation...")
    tick_count = 0
    be_closed = False
    
    while True:
        tick = await broker.advance_tick()
        if not tick: break
        tick_count += 1
        await orchestrator.process_tick(tick)
        
        for o in operations.values():
            if o.metadata.get("close_reason") == "immune_breakeven":
                be_closed = True
                print(f"!!! BREAKEVEN HIT DETECTED at tick {tick_count} !!!")
                print(f"Operation: {o.id}, Profit: {o.profit_pips} pips")
        
        print(f"Tick {tick_count}: Bid={tick.bid}")
    
    print("\nStep 2: Analyzing results...")
    if be_closed:
        print("[SUCCESS] Immune System Layer 1 V2 correctly triggered.")
        print(f"Parent locked pips: {float(parent_cycle.accounting.pips_locked)}")
    else:
        print("[FAILURE] Immune System Layer 1 V2 was not triggered.")
    
    print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_recovery_breakeven())
