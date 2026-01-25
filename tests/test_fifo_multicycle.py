
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

async def test_fifo_multicycle_isolation():
    print("\n>>> INICIANDO TEST: AISLAMIENTO MULTI-CICLO (MISMO PAR)")
    
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
        broker._connected = True
        
        # 1. ESCENARIO 1: Ciclo C1 entra en Deuda (20 pips)
        c1 = Cycle(id="C1_DEBT", pair=pair, status=CycleStatus.IN_RECOVERY)
        from wsplumber.domain.entities.debt import DebtUnit
        u1 = DebtUnit(id="U1", source_cycle_id=c1.id, source_operation_ids=["O1_A", "O1_B"], pips_owed=Decimal("20.0"))
        c1.accounting.debt_units = [u1]
        c1.accounting.pips_remaining = 20.0
        await repo.save_cycle(c1)
        
        # Crear operaciones de C1 en repo
        o1_a = Operation(id="O1_A", cycle_id=c1.id, pair=pair, op_type=OperationType.MAIN_SELL, status=OperationStatus.NEUTRALIZED, broker_ticket="T1_A")
        o1_b = Operation(id="O1_B", cycle_id=c1.id, pair=pair, op_type=OperationType.HEDGE_BUY, status=OperationStatus.NEUTRALIZED, broker_ticket="T1_B")
        await repo.save_operation(o1_a)
        await repo.save_operation(o1_b)
        
        # Inyectar tickets de C1 en broker
        broker.open_positions["T1_A"] = SimulatedPosition("T1_A", "O1_A", pair, OperationType.MAIN_SELL, Price(1.1000), Price(1.0990), LotSize(0.01), datetime.now())
        broker.open_positions["T1_B"] = SimulatedPosition("T1_B", "O1_B", pair, OperationType.HEDGE_BUY, Price(1.1020), Price(1.1030), LotSize(0.01), datetime.now())
        
        print(f"C1 creado con 20 pips de deuda. Tickets: T1_A, T1_B")

        # 2. ESCENARIO 2: Se abre Ciclo C2 (Fresco) para el mismo par
        c2 = Cycle(id="C_FRESCO", pair=pair, status=CycleStatus.ACTIVE)
        # Operación BUY de C2 que va a tocar TP
        op_c2 = Operation(id="O_C2", cycle_id=c2.id, pair=pair, op_type=OperationType.MAIN_BUY, status=OperationStatus.ACTIVE, broker_ticket="T_C2", entry_price=Price(1.1000), tp_price=Price(1.1010))
        c2.add_operation(op_c2)
        await repo.save_operation(op_c2)
        await repo.save_cycle(c2)
        
        # Inyectar ticket de C2 en broker marcado como TP_HIT
        broker.open_positions["T_C2"] = SimulatedPosition(
            ticket="T_C2", operation_id="O_C2", pair=pair, 
            order_type=OperationType.MAIN_BUY, entry_price=Price(1.1000), 
            tp_price=Price(1.1010), lot_size=LotSize(0.01), open_time=datetime.now(),
            status=OperationStatus.TP_HIT, actual_close_price=Price(1.1010)
        )
        
        # Tick simulado
        tick = TickData(pair=pair, bid=Price(1.1010), ask=Price(1.1011), timestamp=datetime.now(), spread_pips=Pips(1.0))
        broker.current_tick = tick
        
        print("\nCiclo C2 (Fresco) toca TP (+10 pips). Procesando via process_tick...")
        
        # Simulamos que C2 toca TP y el orquestador lo procesa
        await orch.process_tick(tick)
        
        # 3. VERIFICACIONES DE AISLAMIENTO
        c1_final = (await repo.get_cycle("C1_DEBT")).value
        c2_final = (await repo.get_cycle("C_FRESCO")).value
        
        print("\n>>> RESULTADOS:")
        print(f"C2 Status: {c2_final.status.value} (Esperado: closed/active -> pending renewal)")
        # Nota: Al tocar TP, C2 se cierra y se abre uno nuevo
        print(f"C1 Deuda Restante: {c1_final.accounting.pips_remaining} pips (Esperado: 20.0)")
        print(f"Tickets C1 en broker: { [tid for tid in broker.open_positions if 'T1' in tid] } (Esperado: ['T1_A', 'T1_B'])")
        
        # Aserciones
        # C2 original debería estar CLOSED
        assert c2_final.status == CycleStatus.CLOSED or c2_final.status == CycleStatus.IN_RECOVERY, f"C2 status: {c2_final.status.value}"
        assert c1_final.accounting.pips_remaining == 20.0, "La deuda de C1 NO debería haberse reducido con el profit de C2"
        assert len([tid for tid in broker.open_positions if 'T1' in tid]) == 2, "Los tickets de C1 deben seguir abiertos"
        
        print("\n>>> TEST EXITOSO: Aislamiento confirmado. El profit de un ciclo fresco no toca la deuda de otros ciclos del mismo par.")

if __name__ == "__main__":
    asyncio.run(test_fifo_multicycle_isolation())
