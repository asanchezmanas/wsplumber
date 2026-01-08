"""
Tests parametrizados para los 62 escenarios de auditoría.

Cada test:
1. Carga CSV del escenario
2. Ejecuta backtest
3. Valida checks de la matriz

Uso:
    # Todos los tests
    pytest tests/test_scenarios/test_all_scenarios.py -v
    
    # Un escenario específico
    pytest tests/test_scenarios/test_all_scenarios.py::test_scenario[c01_tp_simple_buy]
"""

import pytest
import yaml
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, List

from wsplumber.core.backtest.backtest_engine import BacktestEngine
from wsplumber.domain.types import (
    OperationStatus, CycleStatus, OperationType,
    CurrencyPair
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="session")
def scenario_specs() -> Dict[str, Any]:
    """Carga especificaciones de escenarios."""
    specs_path = Path(__file__).parent.parent / "fixtures" / "scenario_specs.yaml"
    
    with open(specs_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
async def backtest_engine():
    """Crea engine de backtest limpio para cada test."""
    engine = BacktestEngine(initial_balance=10000.0)
    yield engine
    # Cleanup si es necesario
    if hasattr(engine.orchestrator, 'stop'):
        await engine.orchestrator.stop()


# ============================================
# COLECCIÓN DE ESCENARIOS
# ============================================

def collect_scenario_ids(specs: Dict[str, Any]) -> List[str]:
    """Extrae todos los IDs de escenarios del YAML."""
    scenario_ids = []
    
    categories = [
        'core', 'cycles', 'hedged', 'recovery', 
        'fifo', 'risk_management', 'money_management',
        'edge_cases', 'multi_pair', 'jpy_pairs'
    ]
    
    for category in categories:
        if category in specs:
            scenario_ids.extend(specs[category].keys())
    
    return scenario_ids


def get_all_scenario_params():
    """Genera parámetros para pytest.mark.parametrize."""
    specs_path = Path(__file__).parent.parent / "fixtures" / "scenario_specs.yaml"
    with open(specs_path, 'r', encoding='utf-8') as f:
        specs = yaml.safe_load(f)
    
    params = []
    categories = [
        'core', 'cycles', 'hedged', 'recovery', 
        'fifo', 'risk_management', 'money_management',
        'edge_cases', 'multi_pair', 'jpy_pairs'
    ]
    
    for category in categories:
        if category in specs:
            for scenario_id, spec in specs[category].items():
                params.append(pytest.param(scenario_id, category, spec, id=scenario_id))
    
    return params


# ============================================
# TEST PRINCIPAL
# ============================================

@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_id, category, spec", get_all_scenario_params())
async def test_scenario(backtest_engine, scenario_id, category, spec):
    """
    Ejecuta un escenario y valida sus checks.
    """
    # 1. Configurar engine (inicialmente clean)
    engine = backtest_engine
    
    # 2. Cargar CSV
    csv_path = Path(__file__).parent.parent / "scenarios" / f"{scenario_id}.csv"
    if not csv_path.exists():
        pytest.skip(f"CSV no encontrado para {scenario_id}")
    
    # 3. Ejecutar Backtest
    # Nota: Este es un placeholder. En la práctica se llamaría a engine.run_csv(csv_path)
    # Por ahora simulamos la carga de resultados para validación de estructura.
    
    # await engine.load_csv(csv_path)
    # await engine.run()
    
    # 4. Validar Checks
    validator = ScenarioValidator(engine)
    
    checks = spec.get('checks', [])
    for check_expr in checks:
        result = await validator.validate_check(check_expr)
        assert result is True, f"Check fallido en {scenario_id}: {check_expr}"


# ============================================
# HELPERS DE VALIDACIÓN
# ============================================

class ScenarioValidator:
    """Valida checks de escenarios contra el estado del sistema."""
    
    def __init__(self, engine: BacktestEngine):
        self.engine = engine
        self.repository = engine.repository
        self.broker = engine.broker
    
    async def validate_check(self, check_expr: str) -> bool:
        """
        Evalúa un check expression y retorna si pasa.
        """
        context = await self._build_evaluation_context()
        
        try:
            # Reemplazar operadores lógicos si es necesario o permitir eval puro
            result = eval(check_expr, {
                "OperationStatus": OperationStatus,
                "CycleStatus": CycleStatus,
                "OperationType": OperationType,
                "Decimal": Decimal
            }, context)
            return bool(result)
        except Exception as e:
            print(f"Error evaluando check '{check_expr}': {e}")
            return False
    
    async def _build_evaluation_context(self) -> Dict[str, Any]:
        """Construye contexto con variables para evaluar checks."""
        # Obtener datos del sistema
        cycles = await self.repository.get_all_cycles()
        operations = await self.repository.get_all_operations()
        account_info = await self.broker.get_account_info()
        
        # Variables de ayuda para los checks
        context = {
            "cycles": cycles,
            "operations": operations,
            "account": account_info,
            "broker": self.broker,
            "cycle": cycles[0] if cycles else None,
            "buy_op": next((op for op in operations if op.op_type == OperationType.MAIN_BUY), None),
            "sell_op": next((op for op in operations if op.op_type == OperationType.MAIN_SELL), None),
        }
        
        # Añadir referencias específicas si son necesarias (ej: main_buy, hedge_sell)
        for op in operations:
            if op.op_id:
                context[f"op_{op.op_id}"] = op
        
        return context
