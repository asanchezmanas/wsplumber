
import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, 'src')
sys.path.insert(0, 'tests')

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, TickData, Price, Pips, OperationStatus, OperationType, OrderRequest, LotSize, Result
from wsplumber.domain.entities.cycle import Cycle, CycleStatus, CycleType
from wsplumber.domain.entities.operation import Operation
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker

async def test_incremental_fifo_compensation():
    print("\n>>> INICIANDO TEST INCREMENTAL (V2): COMPENSACIÓN FIFO ATÓMICA")
    
    pair = CurrencyPair("EURUSD")
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    
    # Mock settings and Risk Manager
    mock_risk = MagicMock(spec=RiskManager)
    mock_risk.calculate_lot_size.return_value = LotSize(0.01)
    mock_risk.can_open_position.return_value = Result.ok(True)
    
    with patch('wsplumber.core.risk.risk_manager.get_settings') as mock_sett:
        mock_sett.return_value.strategy.main_tp_pips = 10
        mock_sett.return_value.strategy.recovery_tp_pips = 80
        mock_sett.return_value.trading.default_lot_size = 0.01
        
        trading = TradingService(broker=broker, repository=repo)
        strategy = WallStreetPlumberStrategy()
        
        # Inyectamos el mock_risk directamente en el orquestador
        orch = CycleOrchestrator(trading, strategy, mock_risk, repo)
        
        # 1. Crear un ciclo y forzar estado HEDGED con tickets reales
        cycle = Cycle(id="C_TEST", pair=pair, status=CycleStatus.HEDGED)
        await repo.save_cycle(cycle)
        
        # Crear dos operaciones neutralizadas
        op_main = Operation(id="OP_MAIN", cycle_id=cycle.id, pair=pair, op_type=OperationType.MAIN_SELL, status=OperationStatus.NEUTRALIZED, broker_ticket="T_MAIN")
        op_hedge = Operation(id="OP_HEDGE", cycle_id=cycle.id, pair=pair, op_type=OperationType.HEDGE_BUY, status=OperationStatus.NEUTRALIZED, broker_ticket="T_HEDGE")
        await repo.save_operation(op_main)
        await repo.save_operation(op_hedge)
        
        # Inyectar manualmente la unidad de deuda vinculada a estos tickets
        from wsplumber.domain.entities.debt import DebtUnit
        unit = DebtUnit(id="UNIT_20", source_cycle_id=cycle.id, source_operation_ids=["OP_MAIN", "OP_HEDGE"], pips_owed=Decimal("20.0"))
        cycle.accounting.debt_units.append(unit)
        cycle.accounting.total_debt_pips = 20.0
        cycle.accounting.pips_remaining = 20.0
        await repo.save_cycle(cycle) # CRITICAL: Save AFTER injecting debt
        
        # Simular que estas posiciones están BIEN en el broker usando la entidad real que espera SimulatedBroker
        from tests.fixtures.simulated_broker import SimulatedPosition
        broker.open_positions["T_MAIN"] = SimulatedPosition(
            ticket="T_MAIN", operation_id="OP_MAIN", pair=pair, 
            order_type=OperationType.MAIN_SELL, entry_price=Price(1.1000), 
            tp_price=Price(1.0990), lot_size=LotSize(0.01), open_time=datetime.now()
        )
        broker.open_positions["T_HEDGE"] = SimulatedPosition(
            ticket="T_HEDGE", operation_id="OP_HEDGE", pair=pair, 
            order_type=OperationType.HEDGE_BUY, entry_price=Price(1.1002), 
            tp_price=Price(1.1012), lot_size=LotSize(0.01), open_time=datetime.now()
        )
        
        print(f"Estado inicial: {len(broker.open_positions)} posiciones en broker, Deuda: {cycle.accounting.pips_remaining} pips")
        
        # 2. Simular un ciclo de Recovery que acaba de tocar TP
        recovery_cycle = Cycle(id="REC_TEST", pair=pair, status=CycleStatus.IN_RECOVERY, cycle_type=CycleType.RECOVERY, parent_cycle_id=cycle.id)
        # Operación que toca TP (+80 pips)
        op_rec_tp = Operation(id="OP_REC_TP", cycle_id=recovery_cycle.id, pair=pair, op_type=OperationType.RECOVERY_BUY, status=OperationStatus.TP_HIT, profit_pips=Pips(80.0))
        recovery_cycle.add_operation(op_rec_tp)
        await repo.save_operation(op_rec_tp)
        await repo.save_cycle(recovery_cycle)
        
        # 3. Ejecutar la lógica de orquestador para procesar el TP del recovery
        print("Ejecutando _handle_recovery_tp...")
        tick = TickData(pair=pair, bid=Price(1.1000), ask=Price(1.1001), timestamp=datetime.now(), spread_pips=Pips(1.0))
        await orch._handle_recovery_tp(recovery_cycle, tick)
        
        # 4. VERIFICACIONES
        print("\n>>> RESULTADOS:")
        cycle_final = (await repo.get_cycle(cycle.id)).value
        print(f"Pips restantes de deuda: {cycle_final.accounting.pips_remaining}")
        print(f"Surplus generado: {cycle_final.accounting.surplus_pips}")
        print(f"Posiciones en broker tras compensación: {len(broker.open_positions)}")
        
        assert cycle_final.accounting.pips_remaining == 0
        assert cycle_final.accounting.surplus_pips == 60
        assert "T_MAIN" not in broker.open_positions
        assert "T_HEDGE" not in broker.open_positions
        
        # Las operaciones en Repo deben estar CLOSED
        op_main_repo = (await repo.get_operation("OP_MAIN")).value
        assert op_main_repo.status == OperationStatus.CLOSED
        
        print("\n>>> TEST EXITOSO: Los tickets fueron cerrados únicamente tras ser compensados.")

if __name__ == "__main__":
    asyncio.run(test_incremental_fifo_compensation())
