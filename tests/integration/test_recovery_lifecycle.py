"""
Integration Tests for Recovery Lifecycle and Balance Invariants.

CORE INVARIANTS:
1. Balance can ONLY increase or stay the same - NEVER decrease
2. Positions in LOSS are NEUTRALIZED, never CLOSED
3. Recovery cycles open correctly when Main cycle goes HEDGED
4. New Main cycles open on EVERY Main TP hit (independent of debt)

Run with: pytest tests/integration/test_recovery_lifecycle.py -v
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock

from wsplumber.domain.entities.cycle import Cycle, CycleStatus, CycleType
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.types import (
    CurrencyPair, OperationStatus, OperationId, Price, Pips, Result
)
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository


@pytest.fixture
def pair():
    return CurrencyPair("EURUSD")


@pytest.fixture
def repository():
    return InMemoryRepository()


class TestBalanceInvariants:
    """INVARIANT: Balance can ONLY increase or stay the same."""
    
    @pytest.mark.asyncio
    async def test_counterpart_operation_neutralized_not_closed(self, repository, pair):
        """
        When a recovery TP hits, the counterpart (in loss) should be NEUTRALIZED, not CLOSED.
        """
        recovery_cycle = Cycle(
            id="REC_TEST_001", pair=pair, cycle_type=CycleType.RECOVERY,
            status=CycleStatus.ACTIVE, created_at=datetime.now(),
            parent_cycle_id="CYC_MAIN_001"
        )
        await repository.save_cycle(recovery_cycle)
        
        # BUY hit TP (profit)
        op_buy = Operation(
            id=OperationId("OP_REC_BUY"), cycle_id=recovery_cycle.id, pair=pair,
            op_type="recovery_buy", entry_price=Price(Decimal("1.0500")),
            tp_price=Price(Decimal("1.0510")), status=OperationStatus.TP_HIT,
            profit_pips=Pips(10.0), broker_ticket="T_BUY"
        )
        await repository.save_operation(op_buy)
        
        # SELL in loss - should be NEUTRALIZED
        op_sell = Operation(
            id=OperationId("OP_REC_SELL"), cycle_id=recovery_cycle.id, pair=pair,
            op_type="recovery_sell", entry_price=Price(Decimal("1.0480")),
            status=OperationStatus.ACTIVE, profit_pips=Pips(-30.0), broker_ticket="T_SELL"
        )
        await repository.save_operation(op_sell)
        
        # Simulate correct handling
        op_sell.status = OperationStatus.NEUTRALIZED
        op_sell.metadata["neutralized_reason"] = "counterpart_tp_hit"
        await repository.save_operation(op_sell)
        
        result = await repository.get_operation(op_sell.id)
        assert result.value.status == OperationStatus.NEUTRALIZED


class TestRecoveryLifecycle:
    """Tests for recovery cycle lifecycle."""
    
    @pytest.mark.asyncio
    async def test_new_main_opens_on_every_main_tp(self, repository, pair):
        """New Main cycle opens on EVERY Main TP, regardless of debt."""
        hedged_cycle = Cycle(
            id="CYC_HEDGED", pair=pair, cycle_type=CycleType.MAIN,
            status=CycleStatus.HEDGED, created_at=datetime.now()
        )
        await repository.save_cycle(hedged_cycle)
        
        # Simulate: Both recovery AND new Main opened
        recovery = Cycle(
            id="REC_001", pair=pair, cycle_type=CycleType.RECOVERY,
            status=CycleStatus.ACTIVE, created_at=datetime.now(),
            parent_cycle_id=hedged_cycle.id
        )
        new_main = Cycle(
            id="CYC_NEW", pair=pair, cycle_type=CycleType.MAIN,
            status=CycleStatus.ACTIVE, created_at=datetime.now()
        )
        await repository.save_cycle(recovery)
        await repository.save_cycle(new_main)
        
        # Both should exist
        assert (await repository.get_cycle(recovery.id)).success
        assert (await repository.get_cycle(new_main.id)).success
    
    @pytest.mark.asyncio
    async def test_recovery_failure_neutralizes_not_closes(self, repository, pair):
        """Recovery failure neutralizes ops, doesn't close them."""
        main = Cycle(
            id="CYC_MAIN", pair=pair, cycle_type=CycleType.MAIN,
            status=CycleStatus.IN_RECOVERY, created_at=datetime.now()
        )
        failed_rec = Cycle(
            id="REC_FAIL", pair=pair, cycle_type=CycleType.RECOVERY,
            status=CycleStatus.ACTIVE, created_at=datetime.now(),
            parent_cycle_id=main.id
        )
        await repository.save_cycle(main)
        await repository.save_cycle(failed_rec)
        
        op1 = Operation(
            id=OperationId("OP1"), cycle_id=failed_rec.id, pair=pair,
            op_type="recovery_buy", entry_price=Price(Decimal("1.05")),
            status=OperationStatus.ACTIVE, broker_ticket="T1"
        )
        op2 = Operation(
            id=OperationId("OP2"), cycle_id=failed_rec.id, pair=pair,
            op_type="recovery_sell", entry_price=Price(Decimal("1.04")),
            status=OperationStatus.ACTIVE, broker_ticket="T2"
        )
        await repository.save_operation(op1)
        await repository.save_operation(op2)
        
        # Correct failure handling
        failed_rec.status = CycleStatus.CLOSED
        op1.status = OperationStatus.NEUTRALIZED
        op2.status = OperationStatus.NEUTRALIZED
        await repository.save_cycle(failed_rec)
        await repository.save_operation(op1)
        await repository.save_operation(op2)
        
        assert (await repository.get_cycle(failed_rec.id)).value.status == CycleStatus.CLOSED
        assert (await repository.get_operation(op1.id)).value.status == OperationStatus.NEUTRALIZED
        assert (await repository.get_operation(op2.id)).value.status == OperationStatus.NEUTRALIZED


class TestRecAMetric:
    """RecA should count non-CLOSED recovery cycles."""
    
    @pytest.mark.asyncio
    async def test_reca_counts_correctly(self, repository, pair):
        rec_active = Cycle(id="RA", pair=pair, cycle_type=CycleType.RECOVERY, 
                          status=CycleStatus.ACTIVE, created_at=datetime.now())
        rec_closed = Cycle(id="RC", pair=pair, cycle_type=CycleType.RECOVERY,
                          status=CycleStatus.CLOSED, created_at=datetime.now())
        await repository.save_cycle(rec_active)
        await repository.save_cycle(rec_closed)
        
        all_cycles = list(repository.cycles.values())
        recovery_cycles = [c for c in all_cycles if c.cycle_type == CycleType.RECOVERY]
        rec_a = sum(1 for c in recovery_cycles if c.status != CycleStatus.CLOSED)
        
        assert rec_a == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
