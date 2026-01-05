from typing import Dict, List, Optional
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.interfaces.ports import IRepository
from wsplumber.domain.types import (
    CurrencyPair, Result, CycleId, OperationId, 
    BrokerTicket, OperationStatus
)

class InMemoryRepository(IRepository):
    """
    Implementación en memoria de IRepository para testing y backtesting rápido.
    """
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
        found = [c for c in self.cycles.values() if c.status.name != "CLOSED"]
        if pair:
            found = [c for c in found if c.pair == pair]
        return Result.ok(found)

    async def get_cycles_by_status(self, statuses, pair=None) -> Result[List[Cycle]]:
        status_names = [s.name if hasattr(s, 'name') else s for s in statuses]
        found = [c for c in self.cycles.values() if c.status.name in status_names]
        if pair:
            found = [c for c in found if c.pair == pair]
        return Result.ok(found)

    async def save_operation(self, operation: Operation) -> Result[OperationId]:
        self.operations[operation.id] = operation
        return Result.ok(operation.id)

    async def get_operation(self, operation_id) -> Result[Optional[Operation]]:
        return Result.ok(self.operations.get(operation_id))

    async def get_all_cycles(self) -> List[Cycle]:
        return list(self.cycles.values())

    async def get_all_operations(self) -> List[Operation]:
        return list(self.operations.values())

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
