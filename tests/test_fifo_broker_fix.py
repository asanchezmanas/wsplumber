"""
Test for FIX-FIFO-BROKER-V1: Closing neutralized positions.

This test simulates the equity drain scenario:
1. Create a MAIN cycle with operations
2. Create recovery cycles that collide (both ops active)
3. Mark recovery ops as NEUTRALIZED with broker tickets
4. Trigger a recovery TP with surplus
5. Verify that _sync_and_close_neutralized_fifo closes the neutralized pairs
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, 'src')

from wsplumber.domain.entities.cycle import Cycle, CycleStatus, CycleType, CycleAccounting
from wsplumber.domain.entities.operation import Operation, OperationStatus, OperationType
from wsplumber.domain.types import CurrencyPair, Pips, LotSize, BrokerTicket, TickData, Price, Result


class TestFIFOBrokerFix:
    """Test suite for the FIFO broker neutralized position closing."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_trading_service(self):
        """Create a mock trading service."""
        trading = AsyncMock()
        trading.close_operation = AsyncMock(return_value=Result.ok({"closed": True}))
        return trading
    
    @pytest.fixture
    def main_cycle(self):
        """Create a MAIN cycle with accounting."""
        cycle = Cycle(
            id="CYC_EURUSD_TEST_MAIN",
            pair=CurrencyPair("EURUSD"),
            cycle_type=CycleType.MAIN,
            status=CycleStatus.IN_RECOVERY
        )
        # Add initial debt (20 pips from Main+Hedge neutralization)
        from wsplumber.domain.entities.debt import DebtUnit
        unit = DebtUnit(
            id="INIT_TEST",
            source_cycle_id=cycle.id,
            source_operation_ids=["MAIN_BUY", "HEDGE_SELL"],
            pips_owed=Decimal("20.0")
        )
        cycle.accounting.debt_units.append(unit)
        cycle.accounting.total_debt_pips = 20.0
        cycle.accounting.pips_remaining = 20.0
        return cycle

    @pytest.fixture
    def recovery_cycle_with_neutralized_ops(self, main_cycle):
        """Create a recovery cycle with neutralized operations."""
        recovery = Cycle(
            id="REC_EURUSD_TEST_1",
            pair=CurrencyPair("EURUSD"),
            cycle_type=CycleType.RECOVERY,
            status=CycleStatus.ACTIVE,
            parent_cycle_id=main_cycle.id
        )
        
        # Create neutralized operations (both activated = collision)
        buy_op = Operation(
            id="REC_EURUSD_TEST_1_B",
            cycle_id=recovery.id,
            pair=CurrencyPair("EURUSD"),
            op_type=OperationType.RECOVERY_BUY,
            entry_price=Price(Decimal("1.10000")),
            tp_price=None,  # TP removed on collision
            lot_size=LotSize(Decimal("0.1")),
            status=OperationStatus.NEUTRALIZED,
            broker_ticket=BrokerTicket("1001")
        )
        buy_op.created_at = datetime.now() - timedelta(hours=1)
        
        sell_op = Operation(
            id="REC_EURUSD_TEST_1_S",
            cycle_id=recovery.id,
            pair=CurrencyPair("EURUSD"),
            op_type=OperationType.RECOVERY_SELL,
            entry_price=Price(Decimal("1.10200")),
            tp_price=None,
            lot_size=LotSize(Decimal("0.1")),
            status=OperationStatus.NEUTRALIZED,
            broker_ticket=BrokerTicket("1002")
        )
        sell_op.created_at = datetime.now() - timedelta(hours=1)
        
        return recovery, [buy_op, sell_op]
    
    @pytest.mark.asyncio
    async def test_finds_neutralized_ops_with_tickets(
        self, mock_repository, mock_trading_service, main_cycle, recovery_cycle_with_neutralized_ops
    ):
        """Test that the function finds neutralized ops with broker tickets."""
        recovery, ops = recovery_cycle_with_neutralized_ops
        
        # Setup repository mocks
        mock_repository.get_all_cycles = AsyncMock(return_value=Result.ok([main_cycle, recovery]))
        mock_repository.get_operations_by_cycle = AsyncMock(return_value=Result.ok(ops))
        mock_repository.get_cycle = AsyncMock(return_value=Result.ok(recovery))
        mock_repository.save_cycle = AsyncMock(return_value=Result.ok(True))
        
        # Import the orchestrator
        from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
        
        # Create orchestrator with mocks
        orchestrator = CycleOrchestrator(
            trading_service=mock_trading_service,
            strategy=MagicMock(),
            risk_manager=MagicMock(),
            repository=mock_repository
        )
        
        # Call the function with surplus > 0
        available_pips = 20.0
        closed_count = await orchestrator._sync_and_close_neutralized_fifo(main_cycle, available_pips)
        
        # Verify: should find and close 1 pair
        assert closed_count == 1, f"Expected 1 pair closed, got {closed_count}"
        
        # Verify close_operation was called twice (once per op)
        assert mock_trading_service.close_operation.call_count == 2
    
    @pytest.mark.asyncio
    async def test_does_not_close_if_no_surplus(
        self, mock_repository, mock_trading_service, main_cycle, recovery_cycle_with_neutralized_ops
    ):
        """Test that function returns 0 if surplus is 0 or negative."""
        recovery, ops = recovery_cycle_with_neutralized_ops
        
        # Setup repository mocks
        mock_repository.get_all_cycles = AsyncMock(return_value=Result.ok([main_cycle, recovery]))
        mock_repository.get_operations_by_cycle = AsyncMock(return_value=Result.ok(ops))
        
        from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
        
        orchestrator = CycleOrchestrator(
            trading_service=mock_trading_service,
            strategy=MagicMock(),
            risk_manager=MagicMock(),
            repository=mock_repository
        )
        
        # Call with surplus = 0
        closed_count = await orchestrator._sync_and_close_neutralized_fifo(main_cycle, 0.0)
        
        # Should not close anything
        assert closed_count == 0
        assert mock_trading_service.close_operation.call_count == 0
    
    @pytest.mark.asyncio
    async def test_ignores_neutralized_without_ticket(
        self, mock_repository, mock_trading_service, main_cycle
    ):
        """Test that ops without broker_ticket are ignored."""
        recovery = Cycle(
            id="REC_EURUSD_TEST_2",
            pair=CurrencyPair("EURUSD"),
            cycle_type=CycleType.RECOVERY,
            status=CycleStatus.ACTIVE,
            parent_cycle_id=main_cycle.id
        )
        
        # Ops WITHOUT broker tickets
        ops = [
            Operation(
                id="REC_EURUSD_TEST_2_B",
                cycle_id=recovery.id,
                pair=CurrencyPair("EURUSD"),
                op_type=OperationType.RECOVERY_BUY,
                entry_price=Price(Decimal("1.10000")),
                tp_price=None,
                lot_size=LotSize(Decimal("0.1")),
                status=OperationStatus.NEUTRALIZED,
                broker_ticket=None  # No ticket!
            ),
            Operation(
                id="REC_EURUSD_TEST_2_S",
                cycle_id=recovery.id,
                pair=CurrencyPair("EURUSD"),
                op_type=OperationType.RECOVERY_SELL,
                entry_price=Price(Decimal("1.10200")),
                tp_price=None,
                lot_size=LotSize(Decimal("0.1")),
                status=OperationStatus.NEUTRALIZED,
                broker_ticket=None  # No ticket!
            )
        ]
        
        mock_repository.get_all_cycles = AsyncMock(return_value=Result.ok([main_cycle, recovery]))
        mock_repository.get_operations_by_cycle = AsyncMock(return_value=Result.ok(ops))
        
        from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
        
        orchestrator = CycleOrchestrator(
            trading_service=mock_trading_service,
            strategy=MagicMock(),
            risk_manager=MagicMock(),
            repository=mock_repository
        )
        
        # Call with surplus > 0
        closed_count = await orchestrator._sync_and_close_neutralized_fifo(main_cycle, 50.0)
        
        # Should not close anything (no tickets)
        assert closed_count == 0
        assert mock_trading_service.close_operation.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
