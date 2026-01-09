"""
WSPlumber - Reporte de Trazabilidad de Backtest

Genera un reporte detallado de cada evento durante el backtest:
- Apertura de ciclos
- Activación de operaciones
- TPs alcanzados
- Transiciones a HEDGED
- Apertura de Recovery
- Cierre de ciclos
- P&L por operación
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, OperationType
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


@dataclass
class TraceEvent:
    tick_num: int
    timestamp: str
    event_type: str
    description: str
    cycle_id: str = ""
    op_id: str = ""
    pips: float = 0.0
    balance: float = 0.0


class BacktestTracer:
    """Captura y reporta todos los eventos del backtest."""
    
    def __init__(self):
        self.events: List[TraceEvent] = []
        self.tick_num = 0
        self.last_balance = 10000.0
        self.last_cycles_count = 0
        self.last_ops_status: Dict[str, str] = {}
        self.cycle_stats: Dict[str, dict] = {}  # Stats por ciclo
    
    def check_changes(self, tick_num: int, timestamp: str, repo, broker, balance: float):
        """Detecta cambios comparando con el estado anterior."""
        self.tick_num = tick_num
        
        # Verificar nuevos ciclos
        cycles = list(repo.cycles.values())
        if len(cycles) > self.last_cycles_count:
            for c in cycles[self.last_cycles_count:]:
                self.events.append(TraceEvent(
                    tick_num=tick_num,
                    timestamp=timestamp,
                    event_type="CYCLE_OPEN",
                    description=f"Nuevo ciclo creado: {c.cycle_type.value}",
                    cycle_id=c.id[:30],
                    balance=balance
                ))
                self.cycle_stats[c.id] = {
                    'type': c.cycle_type.value,
                    'ops_opened': 0,
                    'ops_tp': 0,
                    'pips_won': 0.0,
                    'status': c.status.value
                }
            self.last_cycles_count = len(cycles)
        
        # Verificar cambios de estado de ciclos
        for c in cycles:
            if c.id in self.cycle_stats:
                old_status = self.cycle_stats[c.id]['status']
                new_status = c.status.value
                if old_status != new_status:
                    self.events.append(TraceEvent(
                        tick_num=tick_num,
                        timestamp=timestamp,
                        event_type="CYCLE_STATUS",
                        description=f"{old_status} → {new_status}",
                        cycle_id=c.id[:30],
                        balance=balance
                    ))
                    self.cycle_stats[c.id]['status'] = new_status
        
        # Verificar cambios de operaciones
        for op in repo.operations.values():
            old_status = self.last_ops_status.get(op.id, "")
            new_status = op.status.value
            
            if old_status == "" and new_status == "pending":
                # Nueva operación
                pips = float(op.profit_pips) if op.profit_pips else 0.0
                self.events.append(TraceEvent(
                    tick_num=tick_num,
                    timestamp=timestamp,
                    event_type="OP_OPEN",
                    description=f"{op.op_type.value} @ {float(op.entry_price):.5f}",
                    op_id=op.id[:35],
                    balance=balance
                ))
                
            elif old_status == "pending" and new_status == "active":
                self.events.append(TraceEvent(
                    tick_num=tick_num,
                    timestamp=timestamp,
                    event_type="OP_ACTIVE",
                    description=f"{op.op_type.value} activado",
                    op_id=op.id[:35],
                    balance=balance
                ))
                
            elif old_status in ("active", "neutralized", "pending") and new_status == "tp_hit":
                pips = float(op.profit_pips) if op.profit_pips else 0.0
                self.events.append(TraceEvent(
                    tick_num=tick_num,
                    timestamp=timestamp,
                    event_type="TP_HIT",
                    description=f"{op.op_type.value} TP +{pips:.1f} pips",
                    op_id=op.id[:35],
                    pips=pips,
                    balance=balance
                ))
                
            elif new_status == "cancelled" and old_status != "cancelled":
                self.events.append(TraceEvent(
                    tick_num=tick_num,
                    timestamp=timestamp,
                    event_type="OP_CANCEL",
                    description=f"{op.op_type.value} cancelado",
                    op_id=op.id[:35],
                    balance=balance
                ))
            
            self.last_ops_status[op.id] = new_status
        
        # Verificar cambio de balance
        if abs(balance - self.last_balance) > 0.01:
            diff = balance - self.last_balance
            if diff > 0:
                self.events.append(TraceEvent(
                    tick_num=tick_num,
                    timestamp=timestamp,
                    event_type="BALANCE_UP",
                    description=f"+{diff:.2f} EUR (Balance: {balance:.2f})",
                    balance=balance
                ))
            self.last_balance = balance
    
    def print_report(self, final_balance: float, final_equity: float):
        """Imprime el reporte de trazabilidad."""
        print("\n" + "="*80)
        print("📋 REPORTE DE TRAZABILIDAD DEL BACKTEST")
        print("="*80)
        
        # Eventos por tipo
        event_counts = {}
        for e in self.events:
            event_counts[e.event_type] = event_counts.get(e.event_type, 0) + 1
        
        print(f"\n📊 RESUMEN DE EVENTOS:")
        for et, count in sorted(event_counts.items()):
            print(f"   {et}: {count}")
        
        # Timeline de eventos importantes
        print(f"\n📜 TIMELINE (eventos clave):")
        print("-"*80)
        
        key_events = [e for e in self.events if e.event_type in 
                     ("CYCLE_OPEN", "CYCLE_STATUS", "TP_HIT", "BALANCE_UP")]
        
        for i, e in enumerate(key_events[:50]):  # Primeros 50 eventos clave
            if e.event_type == "TP_HIT":
                print(f"#{e.tick_num:5} | ✅ {e.event_type:12} | {e.description}")
            elif e.event_type == "BALANCE_UP":
                print(f"#{e.tick_num:5} | 💰 {e.event_type:12} | {e.description}")
            elif e.event_type == "CYCLE_STATUS":
                print(f"#{e.tick_num:5} | 🔄 {e.event_type:12} | {e.cycle_id[:20]} → {e.description}")
            else:
                print(f"#{e.tick_num:5} | 📍 {e.event_type:12} | {e.description}")
        
        if len(key_events) > 50:
            print(f"   ... y {len(key_events) - 50} eventos más")
        
        # Resultado final
        print("\n" + "="*80)
        print("📊 RESULTADO FINAL")
        print("="*80)
        print(f"Balance Inicial:  10,000.00 EUR")
        print(f"Balance Final:    {final_balance:,.2f} EUR")
        print(f"Equity Final:     {final_equity:,.2f} EUR")
        print(f"P&L Realizado:    {final_balance - 10000:+.2f} EUR")
        print(f"Flotante:         {final_equity - final_balance:+.2f} EUR")
        print("="*80)


async def run_traced_backtest(max_bars: int = 1000):
    """Ejecuta backtest con trazabilidad completa."""
    import logging
    logging.disable(logging.CRITICAL)
    
    print(f"\n🚀 Iniciando backtest con trazabilidad ({max_bars} barras)...")
    
    # Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    repo = InMemoryRepository()
    trading_service = TradingService(broker, repo)
    risk_manager = RiskManager()
    strategy = WallStreetPlumberStrategy()
    
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        strategy=strategy,
        risk_manager=risk_manager,
        repository=repo
    )
    
    pair = CurrencyPair("EURUSD")
    broker.load_m1_csv("2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv", pair, max_bars=max_bars)
    await broker.connect()
    
    tracer = BacktestTracer()
    tick_count = 0
    total_ticks = len(broker.ticks)
    last_pct = 0
    
    print(f"   Total ticks: {total_ticks}")
    
    while True:
        tick = await broker.advance_tick()
        if not tick:
            break
        
        await orchestrator.process_tick(tick)
        tick_count += 1
        
        # Obtener balance actual
        acc = await broker.get_account_info()
        balance = float(acc.value["balance"])
        
        # Detectar cambios
        ts = str(tick.timestamp)[:19]
        tracer.check_changes(tick_count, ts, repo, broker, balance)
        
        # Progreso
        pct = int(tick_count * 100 / total_ticks)
        if pct >= last_pct + 25:
            print(f"   {pct}% completado...")
            last_pct = pct
    
    # Resultados finales
    acc = await broker.get_account_info()
    final_balance = float(acc.value["balance"])
    final_equity = float(acc.value["equity"])
    
    tracer.print_report(final_balance, final_equity)
    
    return tracer


if __name__ == "__main__":
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    asyncio.run(run_traced_backtest(bars))
