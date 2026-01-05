import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from wsplumber.domain.types import CurrencyPair

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Motor de ejecución para backtesting masivo.
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.repository = InMemoryRepository()
        self.broker = SimulatedBroker(initial_balance=initial_balance)
        self.trading_service = TradingService(self.broker, self.repository)
        self.risk_manager = RiskManager()
        self.strategy = WallStreetPlumberStrategy()
        
        self.orchestrator = CycleOrchestrator(
            self.trading_service,
            self.strategy,
            self.risk_manager,
            self.repository
        )

    def setup_logging(self, audit_file: str):
        """Configura el logging para exportar a un archivo de auditoría."""
        # Limpiar handlers previos si los hay
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Handler para archivo de auditoría
        file_handler = logging.FileHandler(audit_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
        file_handler.setFormatter(file_formatter)
        
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        logger.info(f"Logging de auditoría configurado en: {audit_file}")

    async def run(self, csv_path: str, pair: str = "EURUSD", audit_file: str = "docs/audit_backtest_output.md", max_bars: int = None):
        """Ejecuta el backtest completo para un par."""
        self.setup_logging(audit_file)
        start_time = time.time()
        
        # 1. Cargar datos
        logger.info(f"Cargando datos M1 para {pair} desde {csv_path} (max_bars={max_bars})...")
        self.broker.load_m1_csv(csv_path, CurrencyPair(pair), max_bars=max_bars)
        total_ticks = len(self.broker.ticks)
        
        if total_ticks == 0:
            logger.error("No se cargaron ticks. Abortando.")
            return

        logger.info(f"Iniciando simulación de {total_ticks} ticks...")
        
        # 2. Loop de simulación
        tick_count = 0
        last_report_pct = 0
        
        while True:
            tick = await self.broker.advance_tick()
            if not tick:
                break
            
            await self.orchestrator.process_tick(tick)
            
            tick_count += 1
            # Reportar progreso cada 10%
            pct = int((tick_count / total_ticks) * 100)
            if pct >= last_report_pct + 10:
                logger.info(f"Progreso: {pct}% ({tick_count}/{total_ticks} ticks)")
                last_report_pct = pct

        end_time = time.time()
        duration = end_time - start_time
        
        # 3. Reporte de resultados
        await self.report_results(duration, total_ticks)

    async def report_results(self, duration: float, total_ticks: int):
        """Genera un reporte final con estadísticas detalladas del backtest."""
        acc_info_res = await self.broker.get_account_info()
        acc_info = acc_info_res.unwrap()
        
        cycles = await self.repository.get_all_cycles()
        ops = await self.repository.get_all_operations()
        
        # Categorización de ciclos
        active_cycles = [c for c in cycles if c.status.name not in ["CLOSED", "PAUSED"]]
        closed_cycles = [c for c in cycles if c.status.name == "CLOSED"]
        
        # Categorización de operaciones
        active_ops = [op for op in ops if op.status.name == "ACTIVE"]
        pending_ops = [op for op in ops if op.status.name == "PENDING"]
        tp_ops = [op for op in ops if op.status.name == "TP_HIT"]
        
        # Cálculo de flotante
        floating_pips = sum(op.current_pips or 0.0 for op in active_ops)
        
        print("\n" + "="*60)
        print("📊 REPORTE DETALLADO DE BACKTEST")
        print("="*60)
        print(f"⏱️  Duración Simulación: {duration:.2f} segundos")
        print(f"📈 Ticks procesados:    {total_ticks}")
        print(f"🚀 Velocidad:          {total_ticks/duration:.0f} ticks/seg")
        print("-" * 60)
        print(f"💰 Balance Inicial:     10000.00 EUR")
        print(f"💰 Balance Final:       {acc_info['balance']:.2f} EUR")
        print(f"📉 Equity Final:        {acc_info['equity']:.2f} EUR")
        print(f"📊 Profit/Loss Realizado:{acc_info['balance'] - 10000.0:.2f} EUR")
        print(f"🌊 Flotante (Pips):     {floating_pips:+.2f} pips")
        print("-" * 60)
        print(f"🔄 Ciclos Totales:      {len(cycles)}")
        print(f"   └─ ✅ Cerrados:      {len(closed_cycles)}")
        print(f"   └─ 🕒 Activos:       {len(active_cycles)}")
        print(f"🏗️  Operaciones Totales: {len(ops)}")
        print(f"   └─ 🎯 Take Profits:  {len(tp_ops)}")
        print(f"   └─ 🔥 Activas:       {len(active_ops)}")
        print(f"   └─ ⏳ Pendientes:    {len(pending_ops)}")
        
        if active_cycles:
            print("-" * 60)
            print("📜 ESTADO DE CICLOS ACTIVOS:")
            for c in active_cycles:
                rec_count = len(c.accounting.recovery_queue) if hasattr(c, 'accounting') else 0
                print(f"   • {c.id:35} | Status: {c.status.name:12} | Recov: {rec_count}")
        
        print("="*60 + "\n")

if __name__ == "__main__":
    # Script rápido para lanzar desde consola
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Uso: python backtest_engine.py <csv_path> [pair]")
        sys.exit(1)
        
    path = sys.argv[1]
    pair = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    
    engine = BacktestEngine()
    # Por defecto para auditoría usamos 50,000 barras si no se especifica lo contrario
    asyncio.run(engine.run(path, pair, max_bars=50000))
