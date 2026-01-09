"""
WSPlumber - Reporte de Trazabilidad Detallada

Genera un reporte claro con:
- Cada ciclo identificado (C1, C2, etc.)
- Cada operación con referencia al ciclo (C1_BUY, C1_SELL, etc.)
- P&L por ciclo
- Operaciones canceladas con contexto
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, OperationStatus, OperationType
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker


class CycleTracker:
    """Rastrea ciclos con nombres legibles."""
    
    def __init__(self):
        self.cycle_names: Dict[str, str] = {}
        self.cycle_counter = 0
        self.recovery_counter = 0
        self.cycle_pnl: Dict[str, float] = {}
        self.cycle_ops: Dict[str, List[str]] = {}
        self.op_counters: Dict[str, Dict[str, int]] = {}  # cycle -> {type -> count}
    
    def get_name(self, cycle_id: str, cycle_type: str) -> str:
        if cycle_id not in self.cycle_names:
            if cycle_type == "main":
                self.cycle_counter += 1
                name = f"C{self.cycle_counter}"
            else:
                self.recovery_counter += 1
                name = f"R{self.recovery_counter}"
            self.cycle_names[cycle_id] = name
            self.cycle_pnl[name] = 0.0
            self.cycle_ops[name] = []
            self.op_counters[name] = {}
        return self.cycle_names[cycle_id]
    
    def get_op_number(self, cycle_name: str, op_type: str) -> int:
        """Obtiene el número de operación para este tipo en este ciclo."""
        if cycle_name not in self.op_counters:
            self.op_counters[cycle_name] = {}
        if op_type not in self.op_counters[cycle_name]:
            self.op_counters[cycle_name][op_type] = 0
        self.op_counters[cycle_name][op_type] += 1
        return self.op_counters[cycle_name][op_type]
    
    def add_pnl(self, cycle_name: str, pips: float):
        if cycle_name in self.cycle_pnl:
            self.cycle_pnl[cycle_name] += pips
    
    def add_op(self, cycle_name: str, op_desc: str):
        if cycle_name in self.cycle_ops:
            self.cycle_ops[cycle_name].append(op_desc)


class DetailedTracer:
    """Trazador detallado con contexto completo."""
    
    def __init__(self):
        self.cycles = CycleTracker()
        self.events: List[str] = []
        self.tick = 0
        self.last_balance = 10000.0
        self.last_ops: Dict[str, dict] = {}  # op_id -> {status, cycle_name, type}
        self.last_cycles: Set[str] = set()
        self.total_pips = 0.0
    
    def get_op_short_name(self, op_id: str, op_type: str, cycle_name: str, is_new: bool = False) -> str:
        """Genera nombre corto para operación con numeración."""
        type_short = {
            "main_buy": "BUY",
            "main_sell": "SELL",
            "hedge_buy": "H_BUY",
            "hedge_sell": "H_SELL",
            "recovery_buy": "REC_BUY",
            "recovery_sell": "REC_SELL"
        }
        base = type_short.get(op_type, op_type.upper())
        
        # Solo numerar mains (BUY/SELL), no hedges ni recovery
        if is_new and base in ("BUY", "SELL"):
            num = self.cycles.get_op_number(cycle_name, base)
            return f"{cycle_name}_{base}_{num}"
        
        return f"{cycle_name}_{base}"
    
    def log(self, msg: str, prefix: str = ""):
        self.events.append(f"#{self.tick:5} | {prefix}{msg}")
    
    def check(self, tick: int, repo, broker, balance: float):
        self.tick = tick
        
        # Detectar nuevos ciclos
        for c in repo.cycles.values():
            if c.id not in self.last_cycles:
                self.last_cycles.add(c.id)
                name = self.cycles.get_name(c.id, c.cycle_type.value)
                self.log(f"📍 NUEVO CICLO: {name} ({c.cycle_type.value})", "")
        
        # Detectar cambios en operaciones
        for op in repo.operations.values():
            op_id = op.id
            status = op.status.value
            op_type = op.op_type.value
            
            # Encontrar ciclo
            cycle_name = "?"
            for cid, cname in self.cycles.cycle_names.items():
                if cid in op_id or op_id.startswith(cid[:20]):
                    cycle_name = cname
                    break
            # Para recovery
            if "REC_" in op_id:
                for cid, cname in self.cycles.cycle_names.items():
                    if cname.startswith("R"):
                        cycle_name = cname
                        break
            
            if op_id not in self.last_ops:
                # Nueva operación - generar nombre con número
                op_name = self.get_op_short_name(op_id, op_type, cycle_name, is_new=True)
                entry = float(op.entry_price)
                tp = float(op.tp_price) if op.tp_price else 0
                self.last_ops[op_id] = {"status": status, "cycle": cycle_name, "type": op_type, "name": op_name}
                
                if status == "pending":
                    self.log(f"   ➕ {op_name} creada PENDING | entry={entry:.5f} tp={tp:.5f}")
                    self.cycles.add_op(cycle_name, op_name)
                    
            else:
                old_status = self.last_ops[op_id]["status"]
                op_name = self.last_ops[op_id]["name"]
                
                if old_status != status:
                    if old_status == "pending" and status == "active":
                        self.log(f"   ▶️  {op_name} ACTIVADA")
                        
                    elif status == "tp_hit":
                        pips = float(op.profit_pips) if op.profit_pips else 0
                        self.total_pips += pips
                        self.cycles.add_pnl(cycle_name, pips)
                        eur = pips * 0.1  # 0.01 lot
                        self.log(f"   ✅ {op_name} TP_HIT | +{pips:.1f} pips (+{eur:.2f} EUR) | Total: +{self.total_pips:.1f} pips")
                        
                    elif status == "cancelled":
                        self.log(f"   ❌ {op_name} CANCELADA (contra-orden)")
                        
                    elif status == "neutralized":
                        self.log(f"   🔒 {op_name} NEUTRALIZADA (hedged)")
                    
                    self.last_ops[op_id]["status"] = status
        
        # Detectar cambio balance
        if balance > self.last_balance + 0.01:
            diff = balance - self.last_balance
            self.log(f"💰 BALANCE: {self.last_balance:.2f} → {balance:.2f} (+{diff:.2f} EUR)")
            self.last_balance = balance
    
    def print_report(self, final_balance: float, final_equity: float, open_positions: int):
        print("\n" + "="*80)
        print("📋 REPORTE DE TRAZABILIDAD DETALLADA")
        print("="*80)
        
        # Timeline
        print("\n📜 TIMELINE DE EVENTOS:")
        print("-"*80)
        for event in self.events:
            print(event)
        
        # P&L por ciclo
        print("\n" + "-"*80)
        print("📊 P&L POR CICLO:")
        print("-"*80)
        for name, pnl in self.cycles.cycle_pnl.items():
            ops_list = ", ".join(self.cycles.cycle_ops.get(name, []))
            eur = pnl * 0.1
            status = "ABIERTO" if pnl == 0 else f"+{pnl:.1f} pips (+{eur:.2f} EUR)"
            print(f"   {name}: {status}")
            if ops_list:
                print(f"      Operaciones: {ops_list}")
        
        # Resumen final
        print("\n" + "="*80)
        print("📊 RESULTADO FINAL")
        print("="*80)
        print(f"   Balance Inicial:    10,000.00 EUR")
        print(f"   Balance Final:      {final_balance:,.2f} EUR")
        print(f"   P&L Realizado:      {final_balance - 10000:+.2f} EUR ({self.total_pips:+.1f} pips)")
        print(f"   Equity Final:       {final_equity:,.2f} EUR")
        print(f"   Flotante:           {final_equity - final_balance:+.2f} EUR")
        print(f"   Posiciones Abiertas: {open_positions}")
        print("="*80)


async def run_detailed_trace(max_bars: int = 500):
    """Ejecuta backtest con trazabilidad detallada."""
    import logging
    logging.disable(logging.CRITICAL)
    
    print(f"\n🚀 Backtest con trazabilidad detallada ({max_bars} barras)...")
    
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
    
    tracer = DetailedTracer()
    tick_count = 0
    total_ticks = len(broker.ticks)
    
    print(f"   Total ticks: {total_ticks}")
    
    while True:
        tick = await broker.advance_tick()
        if not tick:
            break
        
        await orchestrator.process_tick(tick)
        tick_count += 1
        
        acc = await broker.get_account_info()
        balance = float(acc.value["balance"])
        tracer.check(tick_count, repo, broker, balance)
    
    acc = await broker.get_account_info()
    final_balance = float(acc.value["balance"])
    final_equity = float(acc.value["equity"])
    
    tracer.print_report(final_balance, final_equity, len(broker.open_positions))


if __name__ == "__main__":
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    asyncio.run(run_detailed_trace(bars))
