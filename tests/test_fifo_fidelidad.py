
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

async def test_fifo_atomic_full_fidelity():
    print("\n>>> INICIANDO TEST: FIDELIDAD TOTAL (UNIDADES ATÓMICAS + P&L REAL)")
    
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
        
        # PRECIO ACTUAL (BROKER): 1.1000
        tick = TickData(pair=pair, bid=Price(1.1000), ask=Price(1.1001), timestamp=datetime.now(), spread_pips=Pips(1.0))
        broker.current_tick = tick

        # CICLO PADRE
        cycle = Cycle(id="C_FIDELITY", pair=pair, status=CycleStatus.HEDGED)
        await repo.save_cycle(cycle)
        
        from wsplumber.domain.entities.debt import DebtUnit
        
        # --- UNIDAD 1: Main + Hedge (20 pips) ---
        # Main Sell @ 1.1001 (Ask de entrada) -> A 1.1001 (Ask actual) P&L = 0
        # Hedge Buy @ 1.1021 (Entry) -> A 1.1000 (Bid actual) P&L = -21 pips
        # Nota: Usamos entradas que sumen la deuda técnica del sistema.
        t1a, t1b = "T1A_M", "T1B_H"
        broker.open_positions[t1a] = SimulatedPosition(t1a, "O1A", pair, OperationType.MAIN_SELL, Price(1.1001), Price(1.0990), LotSize(0.01), datetime.now())
        broker.open_positions[t1b] = SimulatedPosition(t1b, "O1B", pair, OperationType.HEDGE_BUY, Price(1.1021), Price(1.1031), LotSize(0.01), datetime.now())
        u1 = DebtUnit(id="U1", source_cycle_id=cycle.id, source_operation_ids=["O1A", "O1B"], pips_owed=Decimal("20.0"))
        
        # --- UNIDAD 2: Recovery Fallido 1 (40 pips) ---
        # Rec Buy @ 1.1041. Rec Sell @ 1.1001.
        # A 1.1000/1.1001: Buy P&L = -41 pips. Sell P&L = 0. Total ~40
        t2a, t2b = "T2A_R1", "T2B_R1"
        broker.open_positions[t2a] = SimulatedPosition(t2a, "O2A", pair, OperationType.RECOVERY_BUY, Price(1.1041), Price(1.1121), LotSize(0.01), datetime.now())
        broker.open_positions[t2b] = SimulatedPosition(t2b, "O2B", pair, OperationType.RECOVERY_SELL, Price(1.1001), Price(1.0921), LotSize(0.01), datetime.now())
        u2 = DebtUnit(id="U2", source_cycle_id=cycle.id, source_operation_ids=["O2A", "O2B"], pips_owed=Decimal("40.0"))
        
        # --- UNIDAD 3: Recovery Fallido 2 (40 pips) ---
        t3a, t3b = "T3A_R2", "T3B_R2"
        broker.open_positions[t3a] = SimulatedPosition(t3a, "O3A", pair, OperationType.RECOVERY_BUY, Price(1.1041), Price(1.1121), LotSize(0.01), datetime.now())
        broker.open_positions[t3b] = SimulatedPosition(t3b, "O3B", pair, OperationType.RECOVERY_SELL, Price(1.1001), Price(1.0921), LotSize(0.01), datetime.now())
        u3 = DebtUnit(id="U3", source_cycle_id=cycle.id, source_operation_ids=["O3A", "O3B"], pips_owed=Decimal("40.0"))
        
        await broker.update_pnl_only()
        
        # Persistir
        for pid, pos in broker.open_positions.items():
            op = Operation(id=pos.operation_id, cycle_id=cycle.id, pair=pair, op_type=pos.order_type, status=OperationStatus.NEUTRALIZED, broker_ticket=pid)
            await repo.save_operation(op)
            
        cycle.accounting.debt_units = [u1, u2, u3]
        cycle.accounting.total_debt_pips = 100.0
        cycle.accounting.pips_remaining = 100.0
        await repo.save_cycle(cycle)
        
        print(f"Estado Inicial: 3 Unidades (100 pips total). {len(broker.open_positions)} tickets en broker.")
        
        # 2. Recovery Exitoso: +80 pips
        rec_cycle = Cycle(id="REC_TP", pair=pair, status=CycleStatus.IN_RECOVERY, cycle_type=CycleType.RECOVERY, parent_cycle_id=cycle.id)
        op_win = Operation(id="O_WIN", cycle_id=rec_cycle.id, pair=pair, op_type=OperationType.RECOVERY_BUY, status=OperationStatus.TP_HIT, profit_pips=Pips(80.0))
        await repo.save_operation(op_win)
        await repo.save_cycle(rec_cycle)
        
        print("\nEjecutando compensación de 80 pips...")
        await orch._handle_recovery_tp(rec_cycle, tick)
        
        # 3. VERIFICACIONES
        cycle_final = (await repo.get_cycle(cycle.id)).value
        print(f"\n>>> RESULTADOS:")
        print(f"Deuda Pendiente (Accounting): {cycle_final.accounting.pips_remaining} pips")
        print(f"Surplus Acumulado (Excedente): {cycle_final.accounting.surplus_pips} pips")
        print(f"Tickets restantes en Broker: {list(broker.open_positions.keys())}")
        
        # MATEMÁTICA ATÓMICA:
        # 80 beneficio - 20 (U1) - 40 (U2) = 20 surplus. 
        # U3 (40) NO se cierra.
        # Quedan abiertos los 2 tickets de la U3.
        assert cycle_final.accounting.pips_remaining == 40.0
        assert cycle_final.accounting.surplus_pips == 20.0
        assert len(broker.open_positions) == 2
        assert t3a in broker.open_positions
        assert t3b in broker.open_positions
        assert t1a not in broker.open_positions
        assert t2a not in broker.open_positions
        
        print("\n>>> TEST EXITOSO: Matemática Atómica y P&L Real vinculados correctamente.")

if __name__ == "__main__":
    asyncio.run(test_fifo_atomic_full_fidelity())
