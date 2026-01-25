
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
from fixtures.simulated_broker import SimulatedBroker, SimulatedPosition

async def test_complex_fifo_multiple_compensations():
    print("\n>>> INICIANDO TEST AVANZADO: MÚLTIPLES COMPENSACIONES FIFO")
    
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
        orch = CycleOrchestrator(trading, strategy, mock_risk, repo)
        
        # 1. Crear un escenario de DEUDA PESADA (Total 100 pips)
        # Unidad 1: Main+Hedge (20 pips)
        # Unidad 2: Fallo Rect 1 (40 pips)
        # Unidad 3: Fallo Rect 2 (40 pips)
        cycle = Cycle(id="C_COMPLEX", pair=pair, status=CycleStatus.HEDGED)
        await repo.save_cycle(cycle)
        
        def add_pos(tid, oid, otype, price):
            broker.open_positions[tid] = SimulatedPosition(
                ticket=tid, operation_id=oid, pair=pair, 
                order_type=otype, entry_price=Price(price), 
                tp_price=Price(price + 0.0010), lot_size=LotSize(0.01), open_time=datetime.now()
            )
            return Operation(id=oid, cycle_id=cycle.id, pair=pair, op_type=otype, 
                             status=OperationStatus.NEUTRALIZED, broker_ticket=tid)

        # Inyectar Unidades formalmente
        from wsplumber.domain.entities.debt import DebtUnit
        
        # U1 (20)
        op1_a = add_pos("T1_A", "O1_A", OperationType.MAIN_SELL, 1.1000)
        op1_b = add_pos("T1_B", "O1_B", OperationType.HEDGE_BUY, 1.1002)
        u1 = DebtUnit(id="U1_20", source_cycle_id=cycle.id, source_operation_ids=[op1_a.id, op1_b.id], pips_owed=Decimal("20.0"))
        
        # U2 (40)
        op2_a = add_pos("T2_A", "O2_A", OperationType.RECOVERY_BUY, 1.1100)
        op2_b = add_pos("T2_B", "O2_B", OperationType.RECOVERY_SELL, 1.1060)
        u2 = DebtUnit(id="U2_40", source_cycle_id=cycle.id, source_operation_ids=[op2_a.id, op2_b.id], pips_owed=Decimal("40.0"))
        
        # U3 (40)
        op3_a = add_pos("T3_A", "O3_A", OperationType.RECOVERY_BUY, 1.1200)
        op3_b = add_pos("T3_B", "O3_B", OperationType.RECOVERY_SELL, 1.1160)
        u3 = DebtUnit(id="U3_40", source_cycle_id=cycle.id, source_operation_ids=[op3_a.id, op3_b.id], pips_owed=Decimal("40.0"))
        
        for op in [op1_a, op1_b, op2_a, op2_b, op3_a, op3_b]: await repo.save_operation(op)
        cycle.accounting.debt_units = [u1, u2, u3]
        cycle.accounting.total_debt_pips = 100.0
        cycle.accounting.pips_remaining = 100.0
        await repo.save_cycle(cycle)
        
        print(f"Estado inicial: {len(broker.open_positions)} posiciones en broker. Deuda: 100 pips.")
        
        # 2. Simular Recovery TP de 80 pips
        # Esto debería pagar U1(20) y U2(40) = 60 pips. 
        # Sobran 20 pips que reducen U3(40) a 20 pips.
        # RESULTADO: T3_A y T3_B deben seguir abiertos. T1 y T2 cerrados.
        rec_cycle = Cycle(id="REC_WIN", pair=pair, status=CycleStatus.IN_RECOVERY, cycle_type=CycleType.RECOVERY, parent_cycle_id=cycle.id)
        op_win = Operation(id="OP_WIN", cycle_id=rec_cycle.id, pair=pair, op_type=OperationType.RECOVERY_BUY, status=OperationStatus.TP_HIT, profit_pips=Pips(80.0))
        await repo.save_operation(op_win)
        await repo.save_cycle(rec_cycle)
        
        print("Ejecutando compensación de 80 pips...")
        tick = TickData(pair=pair, bid=Price(1.1000), ask=Price(1.1001), timestamp=datetime.now(), spread_pips=Pips(1.0))
        broker.current_tick = tick
        await orch._handle_recovery_tp(rec_cycle, tick)
        
        # 4. VERIFICACIONES
        print("\n>>> RESULTADOS:")
        cycle_final = (await repo.get_cycle(cycle.id)).value
        print(f"Deuda restante: {cycle_final.accounting.pips_remaining} pips")
        print(f"Unidades en cola: {len(cycle_final.accounting.debt_units)}")
        print(f"Posiciones en broker: {len(broker.open_positions)} (Esperado: 2 -> T3_A y T3_B)")
        
        # Aserciones
        # REGLA ATÓMICA: 80 profit - 20 (U1) - 40 (U2) = 20 Surplus.
        # U3 (40) NO SE TOCA porque no hay 40 pips de sobra.
        assert cycle_final.accounting.pips_remaining == 40.0
        assert len(cycle_final.accounting.debt_units) == 1
        assert cycle_final.accounting.debt_units[0].id == "U3_40"
        assert cycle_final.accounting.debt_units[0].pips_owed == Decimal("40.0")
        assert cycle_final.accounting.surplus_pips == 20.0
        
        # Verificar permanencia en broker
        assert "T1_A" not in broker.open_positions
        assert "T1_B" not in broker.open_positions
        assert "T2_A" not in broker.open_positions
        assert "T2_B" not in broker.open_positions
        assert "T3_A" in broker.open_positions
        assert "T3_B" in broker.open_positions
        
        print("\n>>> TEST EXITOSO: Compensación parcial correcta. Los 'zombis' de la U3 siguen vivos porque no han sido totalmente pagados.")

if __name__ == "__main__":
    asyncio.run(test_complex_fifo_multiple_compensations())
