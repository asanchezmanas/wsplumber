
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

async def test_complex_fifo_mathematically_perfect():
    print("\n>>> INICIANDO TEST: ALTA FIDELIDAD MATEMÁTICA FIFO (ATÓMICO)")
    
    pair = CurrencyPair("EURUSD")
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    
    # Mock settings
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
        
        # DEFINICIÓN DE TICK DE CONTROL
        # Precio base: 1.1000
        tick = TickData(pair=pair, bid=Price(1.1000), ask=Price(1.1001), timestamp=datetime.now(), spread_pips=Pips(1.0))
        broker.current_tick = tick

        # 1. Crear Deuda de 100 pips REALISTA en el broker
        cycle = Cycle(id="C_PERFECT", pair=pair, status=CycleStatus.HEDGED)
        await repo.save_cycle(cycle)
        
        from wsplumber.domain.entities.debt import DebtUnit
        
        # U1 (20 pips): Main + Hedge
        t1_a_id, t1_b_id = "T1_A", "T1_B"
        broker.open_positions[t1_a_id] = SimulatedPosition(t1_a_id, "O1_A", pair, OperationType.MAIN_SELL, Price(1.1000), Price(1.0990), LotSize(0.01), datetime.now())
        broker.open_positions[t1_b_id] = SimulatedPosition(t1_b_id, "O1_B", pair, OperationType.HEDGE_BUY, Price(1.1020), Price(1.1030), LotSize(0.01), datetime.now())
        u1 = DebtUnit(id="U1_20", source_cycle_id=cycle.id, source_operation_ids=["O1_A", "O1_B"], pips_owed=Decimal("20.0"))
        
        # U2 (40 pips): Recovery Fallido
        t2_id = "T2"
        broker.open_positions[t2_id] = SimulatedPosition(t2_id, "O2", pair, OperationType.RECOVERY_BUY, Price(1.1040), Price(1.1120), LotSize(0.01), datetime.now())
        u2 = DebtUnit(id="U2_40", source_cycle_id=cycle.id, source_operation_ids=["O2"], pips_owed=Decimal("40.0"))
        
        # U3 (40 pips): Otro Recovery Fallido
        t3_id = "T3"
        broker.open_positions[t3_id] = SimulatedPosition(t3_id, "O3", pair, OperationType.RECOVERY_BUY, Price(1.1040), Price(1.1120), LotSize(0.01), datetime.now())
        u3 = DebtUnit(id="U3_40", source_cycle_id=cycle.id, source_operation_ids=["O3"], pips_owed=Decimal("40.0"))
        
        # Actualizar P&L en el broker
        await broker.update_pnl_only()
        
        # Persistir todo
        for pid in broker.open_positions:
            pos = broker.open_positions[pid]
            op = Operation(id=pos.operation_id, cycle_id=cycle.id, pair=pair, op_type=pos.order_type, status=OperationStatus.NEUTRALIZED, broker_ticket=pid)
            await repo.save_operation(op)
            
        cycle.accounting.debt_units = [u1, u2, u3]
        cycle.accounting.total_debt_pips = 100.0
        cycle.accounting.pips_remaining = 100.0
        await repo.save_cycle(cycle)
        
        print(f"Iniciado con {len(broker.open_positions)} posiciones. Deuda Contable: 100 pips.")
        
        # 2. Beneficio de Recovery: +80 pips
        rec_cycle = Cycle(id="REC_WIN", pair=pair, status=CycleStatus.IN_RECOVERY, cycle_type=CycleType.RECOVERY, parent_cycle_id=cycle.id)
        op_win = Operation(id="OP_WIN", cycle_id=rec_cycle.id, pair=pair, op_type=OperationType.RECOVERY_BUY, status=OperationStatus.TP_HIT, profit_pips=Pips(80.0))
        await repo.save_operation(op_win)
        await repo.save_cycle(rec_cycle)
        
        print("\nEjecutando compensación de 80 pips...")
        await orch._handle_recovery_tp(rec_cycle, tick)
        
        # 3. VERIFICACIONES
        cycle_final = (await repo.get_cycle(cycle.id)).value
        print(f"\n>>> RESULTADOS:")
        print(f"Deuda Pendiente (Unidades no pagadas): {cycle_final.accounting.pips_remaining} pips")
        print(f"Excedente Acumulado (Surplus): {cycle_final.accounting.surplus_pips} pips")
        print(f"Posiciones en Broker: {list(broker.open_positions.keys())}")
        
        # MATEMÁTICA ATÓMICA CORRECTA:
        # 80 beneficio - 20 (U1) - 40 (U2) = 20 surplus acumulado.
        # U3 (40) NO se cierra porque 20 < 40. Sigue debiéndose ENTERA (40 pips).
        assert cycle_final.accounting.pips_remaining == 40.0
        assert cycle_final.accounting.surplus_pips == 20.0
        assert "T3" in broker.open_positions
        assert "T1_A" not in broker.open_positions
        assert "T2" not in broker.open_positions
        
        print("\n>>> TEST EXITOSO: Deuda restante = 40 (Atómica). Surplus = 20. ¡Hazme caso a mi!")

if __name__ == "__main__":
    asyncio.run(test_complex_fifo_mathematically_perfect())
