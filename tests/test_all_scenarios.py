"""
WSPlumber - Test Runner para Todos los Escenarios

Ejecuta todos los escenarios generados y valida el comportamiento esperado.
Genera un reporte detallado de qué tests pasaron y cuáles fallaron.
"""

import pytest
import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy as Strategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, CycleStatus
from tests.fixtures.simulated_broker import SimulatedBroker
from tests.integration.test_scenarios import InMemoryRepository


@dataclass
class ScenarioTest:
    """Define un test de escenario con sus validaciones."""
    id: str
    name: str
    csv_file: str
    pair: str
    priority: str
    validations: List[Callable]


class ScenarioValidator:
    """Validador de estado del sistema después de ejecutar un escenario."""

    def __init__(self, broker, repo, orchestrator):
        self.broker = broker
        self.repo = repo
        self.orchestrator = orchestrator

    def validate_balance_increased(self, min_increase: float = 0.1) -> tuple[bool, str]:
        """Valida que el balance haya aumentado."""
        if self.broker.balance > Decimal("1000.0") + Decimal(str(min_increase)):
            return True, f"Balance: {self.broker.balance} > 1000.0"
        return False, f"Balance: {self.broker.balance} <= 1000.0"

    def validate_cycle_created(self) -> tuple[bool, str]:
        """Valida que se haya creado al menos un ciclo."""
        if len(self.repo.cycles) > 0:
            return True, f"Cycles: {len(self.repo.cycles)}"
        return False, "No cycles created"

    def validate_operations_created(self, min_ops: int = 2) -> tuple[bool, str]:
        """Valida que se hayan creado operaciones."""
        if len(self.repo.operations) >= min_ops:
            return True, f"Operations: {len(self.repo.operations)}"
        return False, f"Operations: {len(self.repo.operations)} < {min_ops}"

    def validate_tp_hit(self) -> tuple[bool, str]:
        """Valida que al menos una operación haya alcanzado TP."""
        tp_ops = [op for op in self.repo.operations.values()
                  if op.status == OperationStatus.TP_HIT]
        if tp_ops:
            return True, f"TP_HIT operations: {len(tp_ops)}"
        return False, "No TP_HIT operations"

    def validate_hedged_state(self) -> tuple[bool, str]:
        """Valida que el ciclo haya llegado a estado HEDGED."""
        hedged_cycles = [c for c in self.repo.cycles.values()
                         if c.status == CycleStatus.HEDGED]
        if hedged_cycles:
            return True, f"HEDGED cycles: {len(hedged_cycles)}"
        return False, "No HEDGED cycles"

    def validate_recovery_created(self) -> tuple[bool, str]:
        """Valida que se hayan creado operaciones de recovery."""
        recovery_ops = [op for op in self.repo.operations.values()
                       if op.is_recovery]
        if recovery_ops:
            return True, f"Recovery ops: {len(recovery_ops)}"
        return False, "No recovery operations"

    def validate_pips_locked(self, expected_pips: float) -> tuple[bool, str]:
        """Valida que los pips bloqueados sean correctos."""
        for cycle in self.repo.cycles.values():
            if cycle.accounting.pips_locked > 0:
                pips = float(cycle.accounting.pips_locked)
                if abs(pips - expected_pips) < 1.0:  # Tolerancia de 1 pip
                    return True, f"Pips locked: {pips}"
                return False, f"Pips locked: {pips} != {expected_pips}"
        return False, "No pips locked"

    def validate_broker_positions_closed(self) -> tuple[bool, str]:
        """Valida que las posiciones en el broker se hayan cerrado."""
        if len(self.broker.history) > 0:
            return True, f"Closed positions: {len(self.broker.history)}"
        return False, "No positions closed in broker"

    def get_state_summary(self) -> str:
        """Retorna un resumen del estado del sistema."""
        summary = [
            f"\n=== ESTADO FINAL ===",
            f"Cycles: {len(self.repo.cycles)}",
            f"Operations: {len(self.repo.operations)}",
            f"Balance: {self.broker.balance}",
            f"Open positions: {len(self.broker.open_positions)}",
            f"History: {len(self.broker.history)}",
        ]

        for cycle_id, cycle in self.repo.cycles.items():
            summary.append(f"\nCycle {cycle_id}: status={cycle.status}")
            summary.append(f"  pips_locked={cycle.accounting.pips_locked}")
            summary.append(f"  pips_recovered={cycle.accounting.pips_recovered}")

        for op_id, op in self.repo.operations.items():
            summary.append(f"Op {op_id}: status={op.status}, "
                          f"profit={op.profit_pips} pips, is_recovery={op.is_recovery}")

        return "\n".join(summary)


class ScenarioTestRunner:
    """Ejecuta todos los escenarios y genera reportes."""

    def __init__(self):
        self.scenarios_dir = Path("tests/test_scenarios")
        self.results = []

    async def run_scenario(
        self,
        csv_file: str,
        pair: CurrencyPair,
        validations: List[Callable] = None
    ) -> dict:
        """Ejecuta un escenario y retorna los resultados."""

        # Setup
        broker = SimulatedBroker(initial_balance=1000.0)
        broker.load_csv(csv_file)
        await broker.connect()

        from unittest.mock import MagicMock, patch
        mock_settings = MagicMock()
        mock_settings.trading.default_lot_size = 0.01
        mock_settings.trading.max_lot_size = 1.0
        mock_settings.strategy.main_tp_pips = 10
        mock_settings.strategy.main_step_pips = 10
        mock_settings.strategy.recovery_tp_pips = 80
        mock_settings.strategy.recovery_step_pips = 40
        mock_settings.risk.max_exposure_per_pair = 1000.0

        with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock_settings):
            repo = InMemoryRepository()
            trading_service = TradingService(broker=broker, repository=repo)
            risk_manager = RiskManager()
            risk_manager.settings = mock_settings
            strategy = Strategy()

            orchestrator = CycleOrchestrator(
                trading_service=trading_service,
                strategy=strategy,
                risk_manager=risk_manager,
                repository=repo
            )

            # Execute
            tick_count = 0
            try:
                while True:
                    tick = await broker.advance_tick()
                    if tick is None:
                        break
                    await orchestrator._process_tick_for_pair(pair)
                    tick_count += 1
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'tick_count': tick_count
                }

            # Validate
            validator = ScenarioValidator(broker, repo, orchestrator)
            validation_results = []

            if validations:
                for validation_func in validations:
                    try:
                        passed, message = validation_func(validator)
                        validation_results.append({
                            'validation': validation_func.__name__,
                            'passed': passed,
                            'message': message
                        })
                    except Exception as e:
                        validation_results.append({
                            'validation': validation_func.__name__,
                            'passed': False,
                            'message': f"Exception: {str(e)}"
                        })

            all_passed = all(v['passed'] for v in validation_results) if validation_results else True

            return {
                'success': all_passed,
                'tick_count': tick_count,
                'validations': validation_results,
                'state_summary': validator.get_state_summary(),
                'broker_balance': float(broker.balance),
                'cycles_count': len(repo.cycles),
                'operations_count': len(repo.operations)
            }

    def generate_report(self):
        """Genera reporte HTML de los resultados."""
        report_path = "tests/test_scenarios/REPORT.md"

        passed = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# WSPlumber - Reporte de Escenarios de Test\n\n")
            f.write(f"**Total:** {len(self.results)} | ")
            f.write(f"**Passed:** {len(passed)} | ")
            f.write(f"**Failed:** {len(failed)}\n\n")

            if failed:
                f.write("## Tests Fallidos\n\n")
                for result in failed:
                    f.write(f"### {result['id']} - {result['name']} [{result['priority']}]\n")
                    f.write(f"- **Archivo:** `{result['csv_file']}`\n")
                    f.write(f"- **Error:** {result.get('error', 'Validations failed')}\n")
                    if 'validations' in result:
                        f.write(f"\n**Validaciones:**\n")
                        for val in result['validations']:
                            status = "[OK]" if val['passed'] else "[FAIL]"
                            f.write(f"- {status} {val['validation']}: {val['message']}\n")
                    f.write("\n")

            f.write("## Tests Exitosos\n\n")
            for result in passed:
                f.write(f"- [{result['priority']}] {result['id']} - {result['name']}\n")

        print(f"\n[REPORT] Generado: {report_path}")


# ============================================================
# DEFINICIÓN DE TESTS POR ESCENARIO
# ============================================================

@pytest.mark.asyncio
async def test_scenario_1_1_tp_buy():
    """1.1 - TP Simple BUY"""
    runner = ScenarioTestRunner()

    result = await runner.run_scenario(
        "tests/test_scenarios/scenario_1_1_tp_buy.csv",
        CurrencyPair("EURUSD"),
        validations=[
            lambda v: v.validate_balance_increased(0.9),  # Al menos +0.9 EUR
            lambda v: v.validate_cycle_created(),
            lambda v: v.validate_tp_hit(),
            lambda v: v.validate_broker_positions_closed(),
        ]
    )

    if not result['success']:
        print(result['state_summary'])
        pytest.fail(f"Scenario failed: {result}")

    assert result['success'], "Todas las validaciones deben pasar"


@pytest.mark.asyncio
async def test_scenario_1_2_tp_sell():
    """1.2 - TP Simple SELL"""
    runner = ScenarioTestRunner()

    result = await runner.run_scenario(
        "tests/test_scenarios/scenario_1_2_tp_sell.csv",
        CurrencyPair("EURUSD"),
        validations=[
            lambda v: v.validate_balance_increased(0.9),
            lambda v: v.validate_cycle_created(),
            lambda v: v.validate_tp_hit(),
        ]
    )

    if not result['success']:
        print(result['state_summary'])

    assert result['success']


@pytest.mark.asyncio
async def test_scenario_2_1_both_active_hedged():
    """2.1 - Ambas activas → HEDGED"""
    runner = ScenarioTestRunner()

    result = await runner.run_scenario(
        "tests/test_scenarios/scenario_2_1_both_active_hedged.csv",
        CurrencyPair("EURUSD"),
        validations=[
            lambda v: v.validate_cycle_created(),
            lambda v: v.validate_hedged_state(),
            lambda v: v.validate_pips_locked(20.0),
            lambda v: v.validate_operations_created(4),  # BUY, SELL, HEDGE_BUY, HEDGE_SELL
        ]
    )

    if not result['success']:
        print(result['state_summary'])

    assert result['success']


@pytest.mark.asyncio
async def test_scenario_3_1_buy_tp_hedge_sell():
    """3.1 - BUY TP → Hedge SELL activa → Recovery"""
    runner = ScenarioTestRunner()

    result = await runner.run_scenario(
        "tests/test_scenarios/scenario_3_1_buy_tp_hedge_sell_activates.csv",
        CurrencyPair("EURUSD"),
        validations=[
            lambda v: v.validate_cycle_created(),
            lambda v: v.validate_tp_hit(),
            lambda v: v.validate_recovery_created(),
        ]
    )

    if not result['success']:
        print(result['state_summary'])

    assert result['success']


@pytest.mark.asyncio
async def test_scenario_5_1_recovery_n1_tp():
    """5.1 - Recovery N1 TP exitoso"""
    runner = ScenarioTestRunner()

    result = await runner.run_scenario(
        "tests/test_scenarios/scenario_5_1_recovery_n1_tp.csv",
        CurrencyPair("EURUSD"),
        validations=[
            lambda v: v.validate_balance_increased(5.0),  # +60 pips neto ≈ +6 EUR
            lambda v: v.validate_recovery_created(),
            lambda v: v.validate_tp_hit(),
        ]
    )

    if not result['success']:
        print(result['state_summary'])

    assert result['success']


@pytest.mark.asyncio
async def test_scenario_11_1_usdjpy_tp():
    """11.1 - USDJPY TP correcto"""
    runner = ScenarioTestRunner()

    result = await runner.run_scenario(
        "tests/test_scenarios/scenario_11_1_usdjpy_tp.csv",
        CurrencyPair("USDJPY"),
        validations=[
            lambda v: v.validate_balance_increased(0.9),
            lambda v: v.validate_cycle_created(),
            lambda v: v.validate_tp_hit(),
        ]
    )

    if not result['success']:
        print(result['state_summary'])

    assert result['success']


# ============================================================
# TEST SUITE COMPLETO - Ejecuta todos los escenarios
# ============================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_all_critical_scenarios():
    """Ejecuta todos los escenarios críticos y genera reporte."""
    runner = ScenarioTestRunner()

    scenarios = [
        ("1.1", "tp_buy", "scenario_1_1_tp_buy.csv", "EURUSD", "CRITICA",
         [lambda v: v.validate_balance_increased(0.9), lambda v: v.validate_tp_hit()]),

        ("1.2", "tp_sell", "scenario_1_2_tp_sell.csv", "EURUSD", "CRITICA",
         [lambda v: v.validate_balance_increased(0.9), lambda v: v.validate_tp_hit()]),

        ("2.1", "hedged", "scenario_2_1_both_active_hedged.csv", "EURUSD", "CRITICA",
         [lambda v: v.validate_hedged_state(), lambda v: v.validate_pips_locked(20.0)]),

        ("3.1", "hedge_sell_recovery", "scenario_3_1_buy_tp_hedge_sell_activates.csv", "EURUSD", "CRITICA",
         [lambda v: v.validate_tp_hit(), lambda v: v.validate_recovery_created()]),

        ("5.1", "recovery_tp", "scenario_5_1_recovery_n1_tp.csv", "EURUSD", "CRITICA",
         [lambda v: v.validate_balance_increased(5.0), lambda v: v.validate_recovery_created()]),
    ]

    for id, name, csv, pair, priority, validations in scenarios:
        print(f"\n[TEST] {id} - {name} [{priority}]")

        csv_path = f"tests/test_scenarios/{csv}"
        result = await runner.run_scenario(csv_path, CurrencyPair(pair), validations)

        runner.results.append({
            'id': id,
            'name': name,
            'csv_file': csv,
            'priority': priority,
            **result
        })

        if result['success']:
            print(f"[OK] {id} passed")
        else:
            print(f"[FAIL] {id} failed")
            print(result['state_summary'])

    runner.generate_report()

    # Verificar que todos los críticos pasaron
    failed = [r for r in runner.results if not r['success']]
    if failed:
        print(f"\n[ERROR] {len(failed)} tests fallaron")
        for f in failed:
            print(f"  - {f['id']}: {f.get('error', 'Validations failed')}")
        pytest.fail(f"{len(failed)} critical scenarios failed")
