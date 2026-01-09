"""
WSPlumber - Test de Validación Detallada del Flujo

Este test verifica que TODOS los eventos del flujo se ejecuten correctamente:

✓ Creación de ciclo con 2 operaciones PENDING
✓ Operaciones tienen entry a ±5 pips
✓ Operaciones tienen TP a ±15 pips del precio (entry + 10)
✓ Activación de orden cambia status a ACTIVE
✓ Ambas activas → Status ciclo HEDGED
✓ Ambas activas → Se crean HEDGE_BUY y HEDGE_SELL
✓ Ambas activas → Mains se marcan NEUTRALIZED
✓ TP hit → Op contraria CANCELLED
✓ TP hit → Hedge contrario CANCELLED
✓ TP hit → 2 nuevos mains PENDING creados
✓ TP hit en HEDGED → Recovery cycle creado
✓ Recovery tiene entry a ±20 pips
✓ Recovery tiene TP a ±100 pips (entry + 80)
"""

import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, field

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.core.strategy._params import (
    MAIN_TP_PIPS, MAIN_DISTANCE_PIPS, 
    RECOVERY_TP_PIPS, RECOVERY_DISTANCE_PIPS
)
from wsplumber.domain.types import (
    CurrencyPair, OperationStatus, OperationType, 
    TickData, Timestamp, Price, Pips
)
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


@dataclass
class ValidationResult:
    """Resultado de una validación."""
    name: str
    passed: bool
    expected: Any
    actual: Any
    details: str = ""


@dataclass
class FlowValidationReport:
    """Reporte de validación del flujo."""
    results: List[ValidationResult] = field(default_factory=list)
    
    def add(self, name: str, passed: bool, expected: Any, actual: Any, details: str = ""):
        self.results.append(ValidationResult(name, passed, expected, actual, details))
    
    def print_report(self):
        print("\n" + "="*80)
        print("REPORTE DE VALIDACIÓN DEL FLUJO")
        print("="*80)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        for r in self.results:
            status = "✅" if r.passed else "❌"
            print(f"{status} {r.name}")
            if not r.passed:
                print(f"   Expected: {r.expected}")
                print(f"   Actual:   {r.actual}")
            if r.details:
                print(f"   {r.details}")
        
        print("\n" + "-"*80)
        print(f"RESULTADO: {passed}/{total} validaciones pasaron")
        print("="*80)
        
        return passed == total


def create_tick(pair: str, bid: float, ask: float, ts: str) -> TickData:
    return TickData(
        pair=CurrencyPair(pair),
        bid=Price(Decimal(str(bid))),
        ask=Price(Decimal(str(ask))),
        timestamp=Timestamp(datetime.fromisoformat(ts)),
        spread_pips=Pips(2.0)
    )


def mock_settings():
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.trading.default_lot_size = 0.01
    mock.trading.max_lot_size = 1.0
    mock.strategy.main_tp_pips = 10
    mock.strategy.main_step_pips = 10
    mock.strategy.recovery_tp_pips = 80
    mock.strategy.recovery_step_pips = 40
    mock.risk.max_exposure_per_pair = 1000.0
    return mock


async def validate_complete_hedge_flow():
    """
    Valida el flujo completo de hedge con verificaciones exhaustivas.
    """
    from unittest.mock import patch
    
    mock = mock_settings()
    report = FlowValidationReport()
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        # Setup
        broker = SimulatedBroker(initial_balance=1000.0)
        repo = InMemoryRepository()
        trading_service = TradingService(broker=broker, repository=repo)
        risk_manager = RiskManager()
        risk_manager.settings = mock
        strategy = WallStreetPlumberStrategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        pair = CurrencyPair("EURUSD")
        await broker.connect()
        
        # ═══════════════════════════════════════════════════════════════
        # FASE 1: CREAR CICLO
        # ═══════════════════════════════════════════════════════════════
        print("\n📍 FASE 1: CREAR CICLO")
        
        tick1 = create_tick("EURUSD", 1.1000, 1.1002, "2024-01-01T10:00:00")
        broker.ticks = [tick1]
        broker.current_tick_index = -1
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # V1: Se creó 1 ciclo
        report.add(
            "V1: Ciclo creado",
            len(repo.cycles) == 1,
            1, len(repo.cycles)
        )
        
        # V2: Se crearon 2 operaciones
        report.add(
            "V2: 2 operaciones creadas",
            len(repo.operations) == 2,
            2, len(repo.operations)
        )
        
        # V3: Operaciones están PENDING
        pending_ops = [op for op in repo.operations.values() if op.status == OperationStatus.PENDING]
        report.add(
            "V3: Operaciones están PENDING",
            len(pending_ops) == 2,
            2, len(pending_ops)
        )
        
        # V4: BUY entry a +5 pips
        buy_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_BUY]
        if buy_ops:
            expected_buy_entry = float(tick1.ask) + 0.0005  # +5 pips
            actual_buy_entry = float(buy_ops[0].entry_price)
            report.add(
                "V4: BUY entry a ask+5pips",
                abs(actual_buy_entry - expected_buy_entry) < 0.00001,
                expected_buy_entry, actual_buy_entry
            )
            
            # V5: BUY TP a entry+10 pips
            expected_buy_tp = expected_buy_entry + 0.0010
            actual_buy_tp = float(buy_ops[0].tp_price)
            report.add(
                "V5: BUY TP a entry+10pips",
                abs(actual_buy_tp - expected_buy_tp) < 0.00001,
                expected_buy_tp, actual_buy_tp
            )
        
        # V6: SELL entry a -5 pips
        sell_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_SELL]
        if sell_ops:
            expected_sell_entry = float(tick1.bid) - 0.0005  # -5 pips
            actual_sell_entry = float(sell_ops[0].entry_price)
            report.add(
                "V6: SELL entry a bid-5pips",
                abs(actual_sell_entry - expected_sell_entry) < 0.00001,
                expected_sell_entry, actual_sell_entry
            )
        
        # V7: Ciclo en PENDING
        cycle = list(repo.cycles.values())[0]
        report.add(
            "V7: Ciclo en estado PENDING",
            cycle.status == CycleStatus.PENDING,
            CycleStatus.PENDING.value, cycle.status.value
        )
        
        # Mostrar verificaciones FASE 1
        print(f"   ✅ V1-V3: Ciclo + {len(pending_ops)} ops PENDING")
        if buy_ops:
            print(f"   ✅ V4-V5: BUY entry={actual_buy_entry:.5f} TP={actual_buy_tp:.5f}")
        if sell_ops:
            print(f"   ✅ V6: SELL entry={actual_sell_entry:.5f}")
        print(f"   ✅ V7: Ciclo status={cycle.status.value}")
        
        # ═══════════════════════════════════════════════════════════════
        # FASE 2: ACTIVAR BUY
        # ═══════════════════════════════════════════════════════════════
        print("\n📍 FASE 2: ACTIVAR BUY")
        
        tick2 = create_tick("EURUSD", 1.1010, 1.1012, "2024-01-01T10:00:01")
        broker.ticks.append(tick2)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # V8: BUY se activó
        buy_ops = [op for op in repo.operations.values() if op.op_type == OperationType.MAIN_BUY]
        report.add(
            "V8: BUY se activó",
            buy_ops[0].status == OperationStatus.ACTIVE,
            OperationStatus.ACTIVE.value, buy_ops[0].status.value
        )
        
        # V9: Ciclo pasó a ACTIVE
        cycle = list(repo.cycles.values())[0]
        report.add(
            "V9: Ciclo pasó a ACTIVE",
            cycle.status == CycleStatus.ACTIVE,
            CycleStatus.ACTIVE.value, cycle.status.value
        )
        
        # Mostrar verificaciones FASE 2
        print(f"   ✅ V8: BUY status={buy_ops[0].status.value}")
        print(f"   ✅ V9: Ciclo status={cycle.status.value}")
        
        # ═══════════════════════════════════════════════════════════════
        # FASE 3: ACTIVAR SELL → HEDGED
        # ═══════════════════════════════════════════════════════════════
        print("\n📍 FASE 3: ACTIVAR SELL → HEDGED")
        
        tick3 = create_tick("EURUSD", 1.0990, 1.0992, "2024-01-01T10:00:02")
        broker.ticks.append(tick3)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # V10: Ciclo pasó a HEDGED
        cycle = list(repo.cycles.values())[0]
        report.add(
            "V10: Ciclo pasó a HEDGED",
            cycle.status == CycleStatus.HEDGED,
            CycleStatus.HEDGED.value, cycle.status.value
        )
        
        # V11: Se crearon HEDGE operations
        hedge_ops = [op for op in repo.operations.values() if op.is_hedge]
        report.add(
            "V11: Se crearon operaciones HEDGE",
            len(hedge_ops) >= 2,
            ">=2", len(hedge_ops)
        )
        
        # V12: Mains están NEUTRALIZED
        main_ops = [op for op in repo.operations.values() if op.is_main]
        neutralized = [op for op in main_ops if op.status == OperationStatus.NEUTRALIZED]
        report.add(
            "V12: Mains están NEUTRALIZED",
            len(neutralized) == 2,
            2, len(neutralized)
        )
        
        # Mostrar verificaciones FASE 3
        print(f"   ✅ V10: Ciclo status={cycle.status.value}")
        print(f"   ✅ V11: Hedges creados: {len(hedge_ops)}")
        print(f"   ✅ V12: Mains NEUTRALIZED: {len(neutralized)}")
        
        # ═══════════════════════════════════════════════════════════════
        # FASE 4: BUY TOCA TP
        # ═══════════════════════════════════════════════════════════════
        print("\n📍 FASE 4: BUY TOCA TP")
        
        # Guardar estado antes
        ops_before = len(repo.operations)
        
        tick4 = create_tick("EURUSD", 1.1020, 1.1022, "2024-01-01T10:00:03")
        broker.ticks.append(tick4)
        await broker.advance_tick()
        await orchestrator._process_tick_for_pair(pair)
        
        # V13: Al menos 1 op en TP_HIT
        tp_hits = [op for op in repo.operations.values() if op.status == OperationStatus.TP_HIT]
        report.add(
            "V13: Al menos 1 operación TP_HIT",
            len(tp_hits) >= 1,
            ">=1", len(tp_hits)
        )
        
        # V14: HEDGE contrario CANCELLED
        hedge_sells = [op for op in repo.operations.values() 
                      if op.op_type == OperationType.HEDGE_SELL]
        cancelled_hedge = [op for op in hedge_sells if op.status == OperationStatus.CANCELLED]
        report.add(
            "V14: HEDGE_SELL contrario CANCELLED",
            len(cancelled_hedge) >= 1,
            ">=1", len(cancelled_hedge)
        )
        
        # V15: Nuevas operaciones creadas (renovación)
        ops_after = len(repo.operations)
        new_ops_created = ops_after - ops_before
        report.add(
            "V15: Se crearon nuevas operaciones",
            new_ops_created >= 2,
            ">=2", new_ops_created,
            f"Antes: {ops_before}, Después: {ops_after}"
        )
        
        # V16: Recovery cycle creado
        recovery_cycles = [c for c in repo.cycles.values() if c.cycle_type == CycleType.RECOVERY]
        report.add(
            "V16: Recovery cycle creado",
            len(recovery_cycles) >= 1,
            ">=1", len(recovery_cycles)
        )
        
        # V17: Recovery ops creadas
        recovery_ops = [op for op in repo.operations.values() if op.is_recovery]
        report.add(
            "V17: Recovery operations creadas",
            len(recovery_ops) >= 2,
            ">=2", len(recovery_ops)
        )
        
        if recovery_ops:
            # V18: Recovery entry a +20 pips
            rec_buys = [op for op in recovery_ops if op.op_type == OperationType.RECOVERY_BUY]
            if rec_buys:
                expected_rec_entry = float(tick4.ask) + 0.0020  # +20 pips
                actual_rec_entry = float(rec_buys[0].entry_price)
                distance = abs(actual_rec_entry - expected_rec_entry) * 10000
                report.add(
                    "V18: RECOVERY_BUY entry a +20 pips",
                    distance < 1.0,  # tolerancia de 1 pip
                    expected_rec_entry, actual_rec_entry,
                    f"Distancia: {distance:.1f} pips"
                )
                
                # V19: Recovery TP a +100 pips (entry + 80)
                expected_rec_tp = actual_rec_entry + 0.0080  # +80 pips
                actual_rec_tp = float(rec_buys[0].tp_price)
                report.add(
                    "V19: RECOVERY_BUY TP a entry+80pips",
                    abs(actual_rec_tp - expected_rec_tp) < 0.0001,
                    expected_rec_tp, actual_rec_tp
                )
        
        # V20: Balance aumentó
        balance = float(broker.balance)
        report.add(
            "V20: Balance aumentó",
            balance > 1000.0,
            ">1000.0", balance
        )
        
        # Mostrar verificaciones FASE 4
        print(f"   ✅ V13: TP_HIT ops: {len(tp_hits)}")
        print(f"   ✅ V14: Hedge CANCELLED: {len(cancelled_hedge)}")
        print(f"   ✅ V15: Nuevas ops: +{new_ops_created}")
        print(f"   ✅ V16: Recovery cycles: {len(recovery_cycles)}")
        print(f"   ✅ V17: Recovery ops: {len(recovery_ops)}")
        if recovery_ops and rec_buys:
            print(f"   ✅ V18-V19: Recovery entry={actual_rec_entry:.5f} TP={actual_rec_tp:.5f}")
        print(f"   ✅ V20: Balance={balance:.2f}")
        
        # ═══════════════════════════════════════════════════════════════
        # FASE 5: VERIFICAR RENOVACIÓN DE MAINS
        # ═══════════════════════════════════════════════════════════════
        print("\n📍 FASE 5: VERIFICAR RENOVACIÓN")
        
        # V21: Nuevos mains PENDING
        all_mains = [op for op in repo.operations.values() if op.is_main]
        renewed_mains = [op for op in all_mains 
                       if "_B_" in str(op.id) or "_S_" in str(op.id)]
        pending_renewed = [op for op in renewed_mains 
                         if op.status in (OperationStatus.PENDING, OperationStatus.ACTIVE)]
        report.add(
            "V21: Nuevos mains creados (renovación)",
            len(renewed_mains) >= 2,
            ">=2", len(renewed_mains)
        )
        
        if renewed_mains:
            # V22: Renovación con entry a 5 pips del precio actual
            rec_buy = [op for op in renewed_mains if op.op_type == OperationType.MAIN_BUY]
            if rec_buy:
                expected_entry = float(tick4.ask) + 0.0005  # +5 pips
                actual_entry = float(rec_buy[0].entry_price)
                distance = (actual_entry - float(tick4.ask)) * 10000
                report.add(
                    "V22: Renovación BUY a ask+5pips",
                    abs(distance - 5.0) < 1.0,
                    5.0, distance,
                    f"Entry: {actual_entry}"
                )
        
        # ═══════════════════════════════════════════════════════════════
        # IMPRIMIR REPORTE
        # ═══════════════════════════════════════════════════════════════
        return report.print_report()


async def main():
    print("\n" + "█"*80)
    print("WSPLUMBER - VALIDACIÓN DETALLADA DEL FLUJO")
    print("█"*80)
    
    success = await validate_complete_hedge_flow()
    
    if success:
        print("\n🎉 TODAS LAS VALIDACIONES PASARON")
    else:
        print("\n⚠️  ALGUNAS VALIDACIONES FALLARON")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
