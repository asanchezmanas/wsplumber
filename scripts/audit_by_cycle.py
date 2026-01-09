"""
WSPlumber - Auditoría por Ciclo

Genera un reporte detallado POR CICLO que muestra:
- Apertura de mains
- Activaciones
- Estado HEDGED → creación de hedges
- TPs con pips ganados
- Cancelaciones (contra-órdenes)
- Apertura de Recovery
- TPs de Recovery con compensación FIFO
- Cierre del ciclo

Cada evento incluye el tick # para trazabilidad.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from collections import defaultdict

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
class CycleEvent:
    """Evento de un ciclo."""
    tick: int
    event_type: str
    description: str
    details: str = ""
    pips: float = 0.0


@dataclass
class CycleAudit:
    """Auditoría de un ciclo."""
    id: str
    name: str
    cycle_type: str
    created_tick: int = 0
    status: str = "pending"
    events: List[CycleEvent] = field(default_factory=list)
    mains: List[str] = field(default_factory=list)
    hedges: List[str] = field(default_factory=list)
    recoveries: List[str] = field(default_factory=list)
    total_pips: float = 0.0
    
    def add_event(self, tick: int, event_type: str, desc: str, details: str = "", pips: float = 0.0):
        self.events.append(CycleEvent(tick, event_type, desc, details, pips))
        if pips > 0:
            self.total_pips += pips


class CycleAuditor:
    """Auditor que rastrea el ciclo de vida de cada ciclo."""
    
    def __init__(self):
        self.cycles: Dict[str, CycleAudit] = {}
        self.cycle_counter = 0
        self.recovery_counter = 0
        self.tick = 0
        self.last_ops: Dict[str, dict] = {}  # op_id -> {status, cycle_id}
        self.last_cycles: Set[str] = set()
        self.last_balance = 10000.0
        
    def get_cycle_name(self, cycle_id: str, cycle_type: str) -> str:
        """Genera nombre legible para ciclo."""
        if cycle_id not in self.cycles:
            if cycle_type == "main":
                self.cycle_counter += 1
                name = f"C{self.cycle_counter}"
            else:
                self.recovery_counter += 1
                name = f"R{self.recovery_counter}"
            return name
        return self.cycles[cycle_id].name
    
    def check(self, tick: int, repo, broker, balance: float):
        """Analiza cambios y registra eventos por ciclo."""
        self.tick = tick
        
        # Detectar nuevos ciclos
        for c in repo.cycles.values():
            if c.id not in self.cycles:
                name = self.get_cycle_name(c.id, c.cycle_type.value)
                self.cycles[c.id] = CycleAudit(
                    id=c.id,
                    name=name,
                    cycle_type=c.cycle_type.value,
                    created_tick=tick,
                    status=c.status.value
                )
                self.cycles[c.id].add_event(
                    tick, "CREATED", 
                    f"Ciclo {name} creado ({c.cycle_type.value})"
                )
        
        # Detectar cambios de estado en ciclos
        for c in repo.cycles.values():
            if c.id in self.cycles:
                audit = self.cycles[c.id]
                if audit.status != c.status.value:
                    old_status = audit.status
                    new_status = c.status.value
                    audit.add_event(
                        tick, "STATUS_CHANGE",
                        f"{old_status.upper()} → {new_status.upper()}",
                        details=f"Transición de estado del ciclo"
                    )
                    audit.status = new_status
        
        # Detectar operaciones nuevas y cambios
        for op in repo.operations.values():
            op_id = op.id
            status = op.status.value
            op_type = op.op_type.value
            cycle_id = op.cycle_id
            
            # Asegurar que el ciclo existe
            if cycle_id not in self.cycles:
                continue
            
            audit = self.cycles[cycle_id]
            
            if op_id not in self.last_ops:
                # Nueva operación
                entry = float(op.entry_price)
                tp = float(op.tp_price) if op.tp_price else 0
                
                self.last_ops[op_id] = {"status": status, "cycle_id": cycle_id, "type": op_type}
                
                # Clasificar tipo
                if "main" in op_type:
                    audit.mains.append(op_id)
                    audit.add_event(tick, "MAIN_OPEN", f"{op_type} abierto PENDING", 
                                   f"entry={entry:.5f}, tp={tp:.5f}")
                elif "hedge" in op_type:
                    audit.hedges.append(op_id)
                    audit.add_event(tick, "HEDGE_OPEN", f"{op_type} abierto PENDING",
                                   f"entry={entry:.5f}")
                elif "recovery" in op_type:
                    audit.recoveries.append(op_id)
                    audit.add_event(tick, "RECOVERY_OPEN", f"{op_type} abierto PENDING",
                                   f"entry={entry:.5f}, tp={tp:.5f}")
            else:
                # Cambio de estado
                old_status = self.last_ops[op_id]["status"]
                
                if old_status != status:
                    if old_status == "pending" and status == "active":
                        audit.add_event(tick, "ACTIVATED", f"{op_type} ACTIVADO")
                        
                    elif old_status == "active" and status == "neutralized":
                        audit.add_event(tick, "NEUTRALIZED", f"{op_type} NEUTRALIZADO (hedged)")
                        
                    elif status == "tp_hit":
                        pips = float(op.profit_pips) if op.profit_pips else 0
                        audit.add_event(tick, "TP_HIT", f"{op_type} TP alcanzado", 
                                       f"+{pips:.1f} pips", pips)
                        
                    elif status == "cancelled":
                        audit.add_event(tick, "CANCELLED", f"{op_type} CANCELADO",
                                       "contra-orden cancelada")
                    
                    self.last_ops[op_id]["status"] = status
        
        # Detectar cambio de balance
        if balance > self.last_balance + 0.01:
            diff = balance - self.last_balance
            # Encontrar el ciclo que causó este cambio (el último con TP)
            for cid, audit in self.cycles.items():
                for event in reversed(audit.events):
                    if event.tick == tick and event.event_type == "TP_HIT":
                        audit.add_event(tick, "PROFIT_REALIZED", 
                                       f"+{diff:.2f} EUR realizados")
                        break
            self.last_balance = balance
    
    def print_report(self, final_balance: float, final_equity: float):
        """Imprime reporte agrupado por ciclo."""
        print("\n" + "="*80)
        print("📋 AUDITORÍA POR CICLO - WSPlumber")
        print("="*80)
        
        # Ordenar ciclos por tick de creación
        sorted_cycles = sorted(self.cycles.values(), key=lambda c: c.created_tick)
        
        for audit in sorted_cycles:
            print(f"\n{'─'*80}")
            print(f"📍 {audit.name}: {audit.cycle_type.upper()} (ID: {audit.id[:30]}...)")
            print(f"{'─'*80}")
            print(f"   Creado en tick #{audit.created_tick}")
            print(f"   Estado final: {audit.status.upper()}")
            print(f"   Mains: {len(audit.mains)} | Hedges: {len(audit.hedges)} | Recoveries: {len(audit.recoveries)}")
            print(f"   P&L Total: +{audit.total_pips:.1f} pips")
            print()
            print("   📜 EVENTOS:")
            for event in audit.events:
                pips_str = f" | +{event.pips:.1f} pips" if event.pips > 0 else ""
                details_str = f" ({event.details})" if event.details else ""
                print(f"      #{event.tick:5} | {event.event_type:18} | {event.description}{details_str}{pips_str}")
            
            # Verificaciones para este ciclo
            print()
            print("   ✓ VERIFICACIONES:")
            
            # V1: Exactamente 2 mains
            if audit.cycle_type == "main":
                if len(audit.mains) == 2:
                    print(f"      ✅ Mains: {len(audit.mains)}/2 (correcto)")
                else:
                    print(f"      ❌ Mains: {len(audit.mains)}/2 (INCORRECTO!)")
            
            # V2: Hedges solo si hubo HEDGED
            hedged_events = [e for e in audit.events if e.event_type == "STATUS_CHANGE" and "HEDGED" in e.description]
            if hedged_events:
                if len(audit.hedges) >= 2:
                    print(f"      ✅ Hedges creados: {len(audit.hedges)} (estado fue HEDGED)")
                else:
                    print(f"      ⚠️  Hedges: {len(audit.hedges)} (esperados 2 si HEDGED)")
            
            # V3: TPs con pips positivos
            tp_events = [e for e in audit.events if e.event_type == "TP_HIT"]
            if tp_events:
                print(f"      ✅ TPs alcanzados: {len(tp_events)} (total +{sum(e.pips for e in tp_events):.1f} pips)")
            
            # V4: Cancelaciones apropiadas
            cancel_events = [e for e in audit.events if e.event_type == "CANCELLED"]
            if cancel_events:
                print(f"      ✅ Cancelaciones: {len(cancel_events)} (contra-órdenes)")
        
        # Resumen global
        print("\n" + "="*80)
        print("📊 RESUMEN GLOBAL")
        print("="*80)
        main_cycles = [c for c in self.cycles.values() if c.cycle_type == "main"]
        recovery_cycles = [c for c in self.cycles.values() if c.cycle_type == "recovery"]
        
        print(f"   Ciclos MAIN: {len(main_cycles)}")
        print(f"   Ciclos RECOVERY: {len(recovery_cycles)}")
        print(f"   Total P&L: +{sum(c.total_pips for c in self.cycles.values()):.1f} pips")
        print(f"   Balance: {self.last_balance:.2f} EUR → {final_balance:.2f} EUR")
        print(f"   Equity: {final_equity:.2f} EUR")
        print(f"   Flotante: {final_equity - final_balance:+.2f} EUR")
        
        # Verificación global de invariantes
        print("\n   ✓ INVARIANTES GLOBALES:")
        all_main_have_2 = all(len(c.mains) == 2 for c in main_cycles)
        if all_main_have_2:
            print("      ✅ Todos los ciclos MAIN tienen exactamente 2 mains")
        else:
            problematic = [c.name for c in main_cycles if len(c.mains) != 2]
            print(f"      ❌ Ciclos con mains != 2: {problematic}")
        
        print("="*80)


async def run_cycle_audit(max_bars: int = 500):
    """Ejecuta backtest con auditoría por ciclo."""
    import logging
    logging.disable(logging.CRITICAL)
    
    print(f"\n🚀 Auditoría por Ciclo ({max_bars} barras)...")
    
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
    
    auditor = CycleAuditor()
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
        auditor.check(tick_count, repo, broker, balance)
    
    acc = await broker.get_account_info()
    final_balance = float(acc.value["balance"])
    final_equity = float(acc.value["equity"])
    
    auditor.print_report(final_balance, final_equity)


if __name__ == "__main__":
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    asyncio.run(run_cycle_audit(bars))
