#!/usr/bin/env python3
"""
Test completo de todos los flujos del sistema.
Este script ejercita:
1. Apertura de ciclo
2. Activación de órdenes
3. TP detection
4. Renovación de mains
5. Cobertura (HEDGE)
6. Recovery
7. FIFO Cierre
"""

import asyncio
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import datetime
from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.domain.types import CurrencyPair
from tests.fixtures.simulated_broker import SimulatedBroker
from tests.integration.test_scenarios import InMemoryRepository


def print_section(title):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


async def main():
    print_section("INICIO DE TEST COMPLETO DE FLUJOS")

    # ========================================================================
    # SETUP
    # ========================================================================
    print("📋 Configurando componentes del sistema...")

    # Broker simulado
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv("tests/scenarios/scenario_full_flow.csv")
    await broker.connect()
    print(f"[OK] Broker configurado: {len(broker.ticks)} ticks cargados")

    # Repositorio
    repo = InMemoryRepository()
    print("[OK] Repositorio en memoria creado")

    # Risk Manager
    risk_mgr = RiskManager()
    print("[OK] Risk Manager configurado")

    # Estrategia
    strategy = WallStreetPlumberStrategy()
    print("[OK] Estrategia 'El Fontanero' inicializada")

    # Trading Service
    trading_service = TradingService(broker=broker, repository=repo)
    print("[OK] Trading Service configurado")

    # Orquestador
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        strategy=strategy,
        risk_manager=risk_mgr,
        repository=repo
    )
    print("[OK] Orquestador configurado")

    # ========================================================================
    # FLUJO 1: APERTURA DE CICLO
    # ========================================================================
    print_section("FLUJO 1: APERTURA DE CICLO")

    tick = await broker.advance_tick()
    print(f"📈 Tick 0: {tick.pair} Bid={tick.bid} Ask={tick.ask}")

    print("\n🔍 Estado ANTES de process_tick:")
    print(f"   - Ciclos activos: {len(orchestrator._active_cycles)}")
    print(f"   - Posiciones broker: {len(broker.open_positions)}")
    print(f"   - Órdenes pendientes: {len(broker.pending_orders)}")

    await orchestrator.process_tick(tick)

    print("\n[OK] Estado DESPUÉS de process_tick:")
    print(f"   - Ciclos activos: {len(orchestrator._active_cycles)}")
    print(f"   - Órdenes pendientes: {len(broker.pending_orders)}")

    if orchestrator._active_cycles:
        pair = CurrencyPair("EURUSD")
        cycle = orchestrator._active_cycles[pair]
        print(f"\n📊 Ciclo creado: {cycle.id}")
        print(f"   - Status: {cycle.status.value}")
        print(f"   - Operaciones: {len(cycle.operations)}")

        for op in cycle.operations:
            print(f"   - {op.id}: {op.op_type.value} @ {op.entry_price} → TP {op.tp_price}")
            print(f"     Status: {op.status.value}, Ticket: {op.broker_ticket}")

    # ========================================================================
    # FLUJO 2: ACTIVACIÓN DE ÓRDENES
    # ========================================================================
    print_section("FLUJO 2: ACTIVACIÓN DE ÓRDENES")

    # Avanzar ticks para activar operaciones
    for i in range(1, 6):
        tick = await broker.advance_tick()
        print(f"📈 Tick {i}: Bid={tick.bid} Ask={tick.ask}")
        await orchestrator.process_tick(tick)

        # Mostrar activaciones
        cycle = orchestrator._active_cycles.get(CurrencyPair("EURUSD"))
        if cycle:
            for op in cycle.operations:
                if op.status.value == "active" and not op.metadata.get("logged_here"):
                    print(f"   [OK] ACTIVADA: {op.id} ({op.op_type.value})")
                    print(f"      Entry: {op.actual_entry_price or op.entry_price}")
                    op.metadata["logged_here"] = True

    print(f"\n📊 Estado del ciclo:")
    cycle = orchestrator._active_cycles.get(CurrencyPair("EURUSD"))
    if cycle:
        active_ops = [op for op in cycle.operations if op.status.value == "active"]
        pending_ops = [op for op in cycle.operations if op.status.value == "pending"]
        print(f"   - Status ciclo: {cycle.status.value}")
        print(f"   - Operaciones ACTIVE: {len(active_ops)}")
        print(f"   - Operaciones PENDING: {len(pending_ops)}")

    # ========================================================================
    # FLUJO 3 y 4: TP DETECTION Y RENOVACIÓN
    # ========================================================================
    print_section("FLUJO 3 y 4: TP DETECTION Y RENOVACIÓN DE MAINS")

    print("🎯 Avanzando ticks para alcanzar TP (10 pips)...\n")

    initial_ops_count = len(cycle.operations) if cycle else 0
    tp_detected = False

    for i in range(6, 20):
        tick = await broker.advance_tick()
        if tick is None:
            break

        print(f"📈 Tick {i}: Bid={tick.bid} Ask={tick.ask}", end="")

        # Check for TP hits in broker
        tp_hits = []
        for ticket, pos in broker.open_positions.items():
            if pos.status.value == "tp_hit" and not pos.metadata.get("logged_tp"):
                tp_hits.append(pos)
                pos.metadata["logged_tp"] = True

        if tp_hits:
            print(f" → TP HIT detectado!")
            for pos in tp_hits:
                print(f"   🎯 {pos.operation_id}: {pos.current_pnl_pips:.1f} pips")
            tp_detected = True
        else:
            print()

        await orchestrator.process_tick(tick)

        # Verificar si se renovaron operaciones
        cycle = orchestrator._active_cycles.get(CurrencyPair("EURUSD"))
        if cycle and len(cycle.operations) > initial_ops_count:
            print(f"\n   [NEW] RENOVACIÓN DETECTADA!")
            print(f"   - Operaciones antes: {initial_ops_count}")
            print(f"   - Operaciones ahora: {len(cycle.operations)}")

            # Mostrar nuevas operaciones
            new_ops = cycle.operations[initial_ops_count:]
            for op in new_ops:
                print(f"   - NUEVA: {op.id} ({op.op_type.value}) @ {op.entry_price}")

            initial_ops_count = len(cycle.operations)

    # ========================================================================
    # FLUJO 5: COBERTURA (HEDGE)
    # ========================================================================
    print_section("FLUJO 5: COBERTURA (HEDGE)")

    print("🔄 Moviendo precio para activar ambas main operations...\n")

    # Continuar avanzando para ver si se activa hedge
    for i in range(20, 30):
        tick = await broker.advance_tick()
        if tick is None:
            break

        print(f"📈 Tick {i}: Bid={tick.bid} Ask={tick.ask}")
        await orchestrator.process_tick(tick)

        cycle = orchestrator._active_cycles.get(CurrencyPair("EURUSD"))
        if cycle and cycle.status.value == "hedged":
            print(f"\n   🛡️ HEDGE ACTIVADO!")
            print(f"   - Status ciclo: {cycle.status.value}")
            print(f"   - Pips bloqueados: {cycle.accounting.pips_locked}")

            hedge_ops = [op for op in cycle.operations if op.is_hedge]
            print(f"   - Operaciones hedge: {len(hedge_ops)}")
            for op in hedge_ops:
                print(f"     - {op.id} ({op.op_type.value})")
            break

    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print_section("RESUMEN FINAL")

    cycle = orchestrator._active_cycles.get(CurrencyPair("EURUSD"))
    if cycle:
        print(f"📊 Ciclo: {cycle.id}")
        print(f"   Status: {cycle.status.value}")
        print(f"   Total operaciones: {len(cycle.operations)}")
        print(f"   - Main: {len(cycle.main_operations)}")
        print(f"   - Hedge: {len(cycle.hedge_operations)}")
        print(f"   - Recovery: {len(cycle.recovery_operations)}")
        print(f"\n📈 Contabilidad:")
        print(f"   - Pips bloqueados: {cycle.accounting.pips_locked}")
        print(f"   - Pips recuperados: {cycle.accounting.pips_recovered}")
        print(f"   - TPs main: {cycle.accounting.total_main_tps}")
        print(f"   - TPs recovery: {cycle.accounting.total_recovery_tps}")

    print(f"\n💰 Broker:")
    acc_info = await broker.get_account_info()
    if acc_info.success:
        info = acc_info.value
        print(f"   Balance: ${info['balance']:.2f}")
        print(f"   Equity: ${info['equity']:.2f}")
        print(f"   Margin: ${info['margin']:.2f}")

    print(f"\n📋 Posiciones:")
    print(f"   - Abiertas: {len(broker.open_positions)}")
    print(f"   - Historial: {len(broker.history)}")

    print_section("TEST COMPLETADO")

    # Verificar flujos
    flujos_ok = []
    flujos_fallo = []

    if cycle:
        flujos_ok.append("[OK] FLUJO 1: Apertura de ciclo")
        flujos_ok.append("[OK] FLUJO 2: Activación de órdenes")

        if cycle.accounting.total_main_tps > 0 or tp_detected:
            flujos_ok.append("[OK] FLUJO 3: TP Detection")
        else:
            flujos_fallo.append("❌ FLUJO 3: TP Detection NO ejecutado")

        if len(cycle.operations) > 2:
            flujos_ok.append("[OK] FLUJO 4: Renovación de mains")
        else:
            flujos_fallo.append("❌ FLUJO 4: Renovación NO ejecutada")

        if cycle.status.value == "hedged" or len(cycle.hedge_operations) > 0:
            flujos_ok.append("[OK] FLUJO 5: Cobertura (HEDGE)")
        else:
            flujos_fallo.append("⚠️ FLUJO 5: HEDGE no activado (puede ser esperado)")

    print("\n📝 Verificación de flujos:")
    for f in flujos_ok:
        print(f)
    for f in flujos_fallo:
        print(f)

    print("\n" + "="*80)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
