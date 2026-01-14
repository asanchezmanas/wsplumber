"""
Test de Validación de Equity Determinístico v2

Ejecuta el orquestador REAL contra un escenario controlado.
Calcula equity de forma independiente y compara con el broker.

Uso:
    python scripts/test_equity_validation.py
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from dataclasses import dataclass
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, TickData, Price, Timestamp, Pips
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from datetime import datetime


@dataclass
class TrackedPosition:
    """Posición para cálculo independiente."""
    ticket: str
    direction: str
    entry_price: float
    lot_size: float
    status: str
    pnl_frozen: float = 0.0


class IndependentCalculator:
    """Calcula balance/equity independientemente del broker."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.positions: Dict[str, TrackedPosition] = {}
    
    def calculate_equity(self, bid: float, ask: float) -> float:
        floating = 0.0
        for pos in self.positions.values():
            if pos.status == 'closed':
                continue
            if pos.status == 'neutralized':
                floating += pos.pnl_frozen
            else:
                if pos.direction == 'buy':
                    pips = (bid - pos.entry_price) * 10000
                else:
                    pips = (pos.entry_price - ask) * 10000
                floating += pips * pos.lot_size * 10.0
        return self.balance + floating
    
    def sync_with_broker(self, broker, bid: float, ask: float):
        """Sincroniza estado desde el broker."""
        # Nuevas posiciones
        for ticket, pos in broker.open_positions.items():
            t = str(ticket)
            if t not in self.positions:
                self.positions[t] = TrackedPosition(
                    ticket=t,
                    direction='buy' if pos.order_type.is_buy else 'sell',
                    entry_price=float(pos.entry_price),
                    lot_size=float(pos.lot_size),
                    status='active'
                )
            # Neutralización
            if pos.status == OperationStatus.NEUTRALIZED and self.positions[t].status == 'active':
                p = self.positions[t]
                if p.direction == 'buy':
                    pips = (bid - p.entry_price) * 10000
                else:
                    pips = (p.entry_price - ask) * 10000
                p.pnl_frozen = pips * p.lot_size * 10.0
                p.status = 'neutralized'
        
        # Cierres (en historial)
        for h in broker.history:
            t = str(h.get('ticket', ''))
            if t in self.positions and self.positions[t].status != 'closed':
                self.balance += h.get('profit_money', 0)
                self.positions[t].status = 'closed'


async def run_test():
    print("=" * 80)
    print("TEST DE VALIDACIÓN DE EQUITY")
    print("=" * 80)
    
    # Setup
    repo = InMemoryRepository()
    broker = SimulatedBroker(initial_balance=10000.0, repository=repo)
    trading_service = TradingService(broker, repo)
    strategy = WallStreetPlumberStrategy()
    risk_manager = RiskManager()
    pair = CurrencyPair("EURUSD")
    
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        strategy=strategy,
        risk_manager=risk_manager,
        repository=repo
    )
    
    await broker.connect()
    calc = IndependentCalculator(10000.0)
    
    # Escenario: ticks diseñados para probar flujos específicos
    ticks_data = [
        # Tick 1-3: Crear ciclo y activar BUY
        (1.1000, 1.1002, "Inicio"),
        (1.1006, 1.1008, "BUY debería activar @ ~1.1005"),
        (1.1010, 1.1012, "BUY en profit"),
        # Tick 4: BUY toca TP
        (1.1016, 1.1018, "BUY TP @ ~1.1015"),
        # Tick 5-7: Nuevo ciclo, SELL activa
        (1.1010, 1.1012, "Nuevo ciclo creado"),
        (1.1004, 1.1006, "SELL debería activar @ ~1.1005"),
        (1.0994, 1.0996, "SELL en profit"),
        # Tick 8: SELL toca TP
        (1.0984, 1.0986, "SELL TP @ ~1.0995"),
        # Tick 9-11: Escenario HEDGE
        (1.1000, 1.1002, "Nuevo ciclo"),
        (1.1008, 1.1010, "BUY activa"),
        (1.0992, 1.0994, "SELL activa = HEDGED"),
        # Tick 12-14: Movimiento extremo (hedged debe ser estable)
        (1.0900, 1.0902, "Movimiento 100 pips - HEDGE TEST"),
        (1.0800, 1.0802, "Movimiento 200 pips - HEDGE TEST"),
        (1.0700, 1.0702, "Movimiento 300 pips - HEDGE TEST"),
    ]
    
    print(f"\n{'Tick':>4} | {'Bid':>8} | {'Evento':30} | {'Broker Eq':>10} | {'Calc Eq':>10} | {'Diff':>8} | {'Status'}")
    print("-" * 100)
    
    problems_found = []
    
    for i, (bid, ask, event) in enumerate(ticks_data):
        tick = TickData(
            pair=pair,
            bid=Price(Decimal(str(bid))),
            ask=Price(Decimal(str(ask))),
            timestamp=Timestamp(datetime.now()),
            spread_pips=Pips((ask - bid) * 10000)
        )
        
        # Actualizar broker y procesar
        broker.current_tick = tick
        broker.current_tick_index = i
        
        # CRÍTICO: Llamar al orquestador para procesar este tick
        await orchestrator._process_tick_for_pair(pair)
        await broker._process_executions(tick)
        
        # Sincronizar calculadora y calcular
        calc.sync_with_broker(broker, bid, ask)
        
        acc = await broker.get_account_info()
        broker_eq = acc.value['equity']
        calc_eq = calc.calculate_equity(bid, ask)
        diff = broker_eq - calc_eq
        
        status = "✓" if abs(diff) < 1.0 else "✗ DIFF"
        
        print(f"{i+1:4d} | {bid:8.4f} | {event:30} | {broker_eq:10.2f} | {calc_eq:10.2f} | {diff:8.2f} | {status}")
        
        if abs(diff) >= 1.0:
            problems_found.append((i+1, event, diff))
        
        # Detalles si hay posiciones
        if broker.open_positions and i in [2, 6, 10, 11, 12, 13]:
            for t, p in broker.open_positions.items():
                print(f"     └─ Pos {t}: {p.order_type.value} @ {p.entry_price}, "
                      f"P&L: {p.current_pnl_pips:.1f} pips, Status: {p.status.value}")
    
    print("=" * 80)
    
    # Resumen
    total_ops = len(repo.operations)
    closed_ops = sum(1 for o in repo.operations.values() if o.status == OperationStatus.CLOSED or o.status == OperationStatus.TP_HIT)
    
    print(f"\nResumen:")
    print(f"  Operaciones totales: {total_ops}")
    print(f"  Operaciones cerradas: {closed_ops}")
    print(f"  Posiciones abiertas en broker: {len(broker.open_positions)}")
    print(f"  Balance final broker: {(await broker.get_account_info()).value['balance']:.2f}")
    print(f"  Balance final calc: {calc.balance:.2f}")
    
    if problems_found:
        print(f"\n❌ Se encontraron {len(problems_found)} discrepancias:")
        for tick, event, diff in problems_found:
            print(f"   Tick {tick}: {event} → Diff: ${diff:.2f}")
        return False
    else:
        print("\n✅ NO hay discrepancias entre broker y cálculo independiente.")
        return True


if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)
