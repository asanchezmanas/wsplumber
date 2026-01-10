"""
WSPlumber - Ejecutor de Todos los Escenarios CSV

Ejecuta los 69 escenarios de tests/scenarios/ y reporta resultados.
"""

import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Tuple

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, TickData, Timestamp, Price, Pips
from wsplumber.domain.entities.cycle import CycleStatus
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


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


def detect_pair_from_filename(filename: str) -> str:
    """Detecta el par del nombre del archivo."""
    upper = filename.upper()
    if "USDJPY" in upper or "_JPY" in upper:
        return "USDJPY"
    if "GBPUSD" in upper:
        return "GBPUSD"
    return "EURUSD"


async def run_scenario(csv_path: Path) -> Dict:
    """Ejecuta un escenario y retorna resultados."""
    from unittest.mock import patch
    
    pair_str = detect_pair_from_filename(csv_path.name)
    pair = CurrencyPair(pair_str)
    mock = mock_settings()
    
    broker = SimulatedBroker(initial_balance=1000.0)
    
    try:
        broker.load_csv(str(csv_path))
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to load CSV: {e}",
            'ticks': 0,
            'balance': 1000.0
        }
    
    if not broker.ticks:
        return {
            'success': False,
            'error': "No ticks in CSV",
            'ticks': 0,
            'balance': 1000.0
        }
    
    await broker.connect()
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
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
                'ticks': tick_count,
                'balance': float(broker.balance)
            }
        
        # Analizar resultados
        balance = float(broker.balance)
        cycles = len(repo.cycles)
        operations = len(repo.operations)
        
        tp_hits = sum(1 for op in repo.operations.values() 
                     if op.status in (OperationStatus.TP_HIT, OperationStatus.CLOSED))
        hedged = sum(1 for c in repo.cycles.values() 
                    if c.status == CycleStatus.HEDGED)
        recoveries = sum(1 for op in repo.operations.values() if op.is_recovery)
        
        return {
            'success': True,
            'error': None,
            'ticks': tick_count,
            'balance': balance,
            'balance_change': balance - 1000.0,
            'cycles': cycles,
            'operations': operations,
            'tp_hits': tp_hits,
            'hedged': hedged,
            'recoveries': recoveries
        }


async def run_all_scenarios():
    """Ejecuta todos los escenarios y genera reporte."""
    scenarios_dir = Path("tests/scenarios")
    
    if not scenarios_dir.exists():
        print(f"ERROR: {scenarios_dir} no existe")
        return
    
    csv_files = sorted(scenarios_dir.glob("*.csv"))
    
    print("\n" + "="*80)
    print("WSPLUMBER - EJECUCIÓN DE TODOS LOS ESCENARIOS")
    print("="*80)
    print(f"Total escenarios: {len(csv_files)}")
    print()
    
    results = []
    passed = 0
    failed = 0
    
    # Categorías para reporte
    categories = {
        'c': ('Core', []),
        'cy': ('Cycles', []),
        'h': ('Hedge', []),
        'r': ('Recovery', []),
        'f': ('FIFO', []),
        'e': ('Edge Cases', []),
        'j': ('JPY', []),
        'mm': ('Money Management', []),
        'mp': ('Multi-Pair', []),
        'rm': ('Risk Management', []),
    }
    
    for csv_path in csv_files:
        result = await run_scenario(csv_path)
        result['file'] = csv_path.name
        results.append(result)
        
        # Clasificar por categoría
        prefix = csv_path.stem.split('_')[0].lower()
        for cat_key in categories:
            if prefix.startswith(cat_key):
                categories[cat_key][1].append(result)
                break
        
        # Status
        if result['success'] and result.get('cycles', 0) > 0:
            status = "[OK]"
            passed += 1
        elif result['success']:
            status = "[--]"  # Ejecutó pero sin crear ciclos
            passed += 1
        else:
            status = "[FAIL]"
            failed += 1
        
        # Mostrar progreso
        balance_delta = result.get('balance_change', 0)
        balance_str = f"+{balance_delta:.2f}" if balance_delta >= 0 else f"{balance_delta:.2f}"
        
        print(f"{status} {csv_path.stem[:40]:<40} | ticks={result['ticks']:3} | bal={balance_str:>8} | ops={result.get('operations', 0):2}")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN POR CATEGORÍA")
    print("="*80)
    
    for cat_key, (cat_name, cat_results) in categories.items():
        if cat_results:
            cat_passed = sum(1 for r in cat_results if r['success'])
            cat_total = len(cat_results)
            print(f"{cat_name:20} | {cat_passed}/{cat_total} passed")
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{len(csv_files)} passed, {failed} failed")
    print("="*80)
    
    # Mostrar errores
    errors = [r for r in results if not r['success']]
    if errors:
        print("\nERRORS IN SCENARIOS:")
        for r in errors:
            print(f"  {r['file']}: {r['error']}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_scenarios())
