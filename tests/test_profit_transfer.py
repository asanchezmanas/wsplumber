import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.domain.entities.cycle import Cycle, CycleStatus, CycleType
from wsplumber.domain.entities.operation import Operation, OperationStatus, OperationType
from wsplumber.domain.entities.debt import DebtUnit
from wsplumber.domain.types import Price, Result, TickData, RecoveryId

@pytest.mark.asyncio
async def test_recovery_profit_transfer_to_parent():
    # 1. Setup Mock infrastructure
    trading_service = MagicMock()
    trading_service.broker = MagicMock()
    trading_service.close_operation = AsyncMock(return_value=Result.ok(True))
    trading_service.sync_all_active_positions = AsyncMock(return_value=Result.ok([]))
    
    strategy = MagicMock()
    risk_manager = MagicMock()
    repository = MagicMock()
    repository.get_operation = AsyncMock()
    repository.save_operation = AsyncMock()
    repository.save_cycle = AsyncMock()
    repository.get_operations_by_cycle = AsyncMock()
    repository.get_all_cycles = AsyncMock(return_value=Result.ok([]))
    repository.get_active_operations = AsyncMock(return_value=Result.ok([]))
    
    orchestrator = CycleOrchestrator(trading_service, strategy, risk_manager, repository)
    
    # 2. Create Parent Cycle with Debt
    parent = Cycle(id="PARENT_001", pair="EURUSD", cycle_type=CycleType.MAIN, status=CycleStatus.IN_RECOVERY)
    # Add 20 pips debt unit
    unit = DebtUnit(id="D1", source_cycle_id="PARENT_001", pips_owed=Decimal("20.0"))
    parent.accounting.debt_units.append(unit)
    parent.accounting.pips_remaining = 20.0
    
    # 3. Create Recovery Cycle linked to parent
    recovery = Cycle(id="REC_001", pair="EURUSD", cycle_type=CycleType.RECOVERY, status=CycleStatus.ACTIVE)
    recovery.parent_cycle_id = "PARENT_001"
    
    # Mock repository to return these cycles
    repository.get_cycle = AsyncMock(side_effect=lambda x: Result.ok(parent) if x == "PARENT_001" else Result.ok(recovery))
    
    # Recovery Op that hit TP (80 pips profit)
    op_rec = Operation(
        id="REC_001_B", cycle_id="REC_001", pair="EURUSD", 
        op_type=OperationType.RECOVERY_BUY, status=OperationStatus.TP_HIT,
        profit_pips=80.0
    )
    repository.get_operations_by_cycle.return_value = Result.ok([op_rec])
    
    # 4. Mock tick
    tick = TickData(pair="EURUSD", bid=Price(Decimal("1.1000")), ask=Price(Decimal("1.1001")), timestamp=datetime.now(), spread_pips=1.0)
    
    # 5. Execute _handle_recovery_tp
    await orchestrator._handle_recovery_tp(recovery, tick, trigger_op_id="REC_001_B")
    
    # 6. Assertions
    # Parent should have 0 debt and 60 surplus (80 profit - 20 debt)
    assert parent.accounting.pips_remaining == 0.0
    assert parent.accounting.surplus_pips == 60.0 # 80 - 20
    assert parent.status == CycleStatus.CLOSED
    
    # Parent should have been saved
    assert repository.save_cycle.called
    
    print("\n Verification Successful: Profit transferred and Parent debt settled!")

if __name__ == "__main__":
    asyncio.run(test_recovery_profit_transfer_to_parent())
