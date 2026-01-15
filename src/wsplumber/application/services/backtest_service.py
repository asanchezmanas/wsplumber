# src/wsplumber/application/services/backtest_service.py
"""
BacktestService - Servicio de backtesting con soporte para streaming.

Este servicio encapsula la lógica de audit_scenario.py pero como generador
async que puede usarse desde endpoints de FastAPI con SSE.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator, Optional
from wsplumber.infrastructure.logging.safe_logger import get_logger

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker

logger = get_logger(__name__)


class BacktestProgress:
    """Estructura de progreso de backtest."""
    def __init__(
        self,
        tick: int,
        total_ticks: int,
        balance: float,
        equity: float,
        active_cycles: int = 0,
        hedged_cycles: int = 0,
        in_recovery_cycles: int = 0,
        closed_cycles: int = 0,
        main_tps: int = 0,
        recovery_tps: int = 0,
        status: str = "running",
        message: str = None
    ):
        self.tick = tick
        self.total_ticks = total_ticks
        self.progress_pct = (tick / total_ticks * 100) if total_ticks > 0 else 0
        self.balance = balance
        self.equity = equity
        self.drawdown_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
        self.active_cycles = active_cycles
        self.hedged_cycles = hedged_cycles
        self.in_recovery_cycles = in_recovery_cycles
        self.closed_cycles = closed_cycles
        self.main_tps = main_tps
        self.recovery_tps = recovery_tps
        self.status = status
        self.message = message
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "total_ticks": self.total_ticks,
            "progress_pct": round(self.progress_pct, 1),
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "active_cycles": self.active_cycles,
            "hedged_cycles": self.hedged_cycles,
            "in_recovery_cycles": self.in_recovery_cycles,
            "closed_cycles": self.closed_cycles,
            "main_tps": self.main_tps,
            "recovery_tps": self.recovery_tps,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


class BacktestService:
    """Servicio de backtesting con streaming."""
    
    def __init__(self, scenarios_dir: str = None):
        self.scenarios_dir = Path(scenarios_dir) if scenarios_dir else Path("tests/scenarios")
        self.partitions_dir = Path("data/partitions")
    
    def list_scenarios(self) -> list[dict]:
        """Lista escenarios disponibles para backtest."""
        scenarios = []
        
        # Escenarios de tests/scenarios
        if self.scenarios_dir.exists():
            for f in sorted(self.scenarios_dir.glob("*.csv")):
                scenarios.append({
                    "name": f.stem,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024*1024), 2),
                    "pair": "EURUSD"
                })
        
        # Particiones por año
        if self.partitions_dir.exists():
            for f in sorted(self.partitions_dir.glob("*.parquet")):
                parts = f.stem.split("_")
                pair = parts[0] if parts else "EURUSD"
                year = int(parts[1]) if len(parts) > 1 else None
                scenarios.append({
                    "name": f.stem,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024*1024), 2),
                    "year": year,
                    "pair": pair
                })
        
        # CSVs grandes en root
        root = Path(".")
        for f in root.glob("*.csv"):
            if f.stat().st_size > 1024*1024:  # Solo archivos > 1MB
                scenarios.append({
                    "name": f.stem,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024*1024), 2),
                    "pair": "EURUSD" if "EURUSD" in f.name.upper() else "UNKNOWN"
                })
        
        return scenarios
    
    async def run_streaming(
        self,
        csv_path: str,
        pair: str = "EURUSD",
        max_ticks: int = None,
        report_interval: int = 1000,
        initial_balance: float = 10000.0
    ) -> AsyncGenerator[BacktestProgress, None]:
        """
        Ejecuta backtest y yield progreso periódicamente.
        
        Args:
            csv_path: Ruta al archivo CSV/Parquet
            pair: Par de divisas
            max_ticks: Límite de ticks
            report_interval: Cada cuántos ticks reportar progreso
            initial_balance: Balance inicial
        
        Yields:
            BacktestProgress con el estado actual
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            yield BacktestProgress(
                tick=0, total_ticks=0, balance=0, equity=0,
                status="error", message=f"Archivo no encontrado: {csv_path}"
            )
            return
        
        start_time = time.time()
        
        # Setup
        broker = SimulatedBroker(initial_balance=initial_balance)
        
        # Cargar datos - Parquets están en formato tick (timestamp,bid,ask)
        if csv_path.endswith(".parquet"):
            # Convertir Parquet a CSV temporal para compatibilidad con broker
            import polars as pl
            import tempfile
            import os
            df = pl.read_parquet(csv_path)
            if max_ticks:
                df = df.head(max_ticks)
            temp_dir = tempfile.gettempdir()
            temp_csv = os.path.join(temp_dir, f"{csv_file.stem}_temp.csv")
            df.write_csv(temp_csv)
            broker.load_csv(temp_csv, default_pair=pair)
        else:
            # CSV directo
            broker.load_csv(csv_path, default_pair=pair)
        
        await broker.connect()
        
        total_ticks = len(broker.ticks)
        if max_ticks:
            total_ticks = min(total_ticks, max_ticks)
        
        # Yield inicial
        yield BacktestProgress(
            tick=0, total_ticks=total_ticks,
            balance=initial_balance, equity=initial_balance,
            status="running", message=f"Iniciando backtest de {total_ticks:,} ticks..."
        )
        
        # Setup orchestrator
        repo = InMemoryRepository()
        trading_service = TradingService(broker, repo)
        risk_manager = RiskManager()
        strategy = WallStreetPlumberStrategy()
        currency_pair = CurrencyPair(pair)
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        # Re-init tick generator
        broker._tick_generator = broker._create_tick_generator()
        
        tick_count = 0
        
        while True:
            tick = await broker.advance_tick()
            if not tick:
                break
            
            if max_ticks and tick_count >= max_ticks:
                break
            
            await orchestrator._process_tick_for_pair(currency_pair)
            
            # FIX-LAYER1: Call sync to process adaptive trailing stops
            await trading_service.sync_all_active_positions(pair)
            
            tick_count += 1
            
            # Reportar progreso
            if tick_count % report_interval == 0 or tick_count == 1:
                acc = await broker.get_account_info()
                balance = acc.value["balance"]
                equity = acc.value["equity"]
                
                # Stats de ciclos
                all_cycles = list(repo.cycles.values())
                main_cycles = [c for c in all_cycles if c.cycle_type.value == "main"]
                rec_cycles = [c for c in all_cycles if c.cycle_type.value == "recovery"]
                
                progress = BacktestProgress(
                    tick=tick_count,
                    total_ticks=total_ticks,
                    balance=balance,
                    equity=equity,
                    active_cycles=sum(1 for c in main_cycles if c.status.value == "active"),
                    hedged_cycles=sum(1 for c in main_cycles if c.status.value == "hedged"),
                    in_recovery_cycles=sum(1 for c in main_cycles if c.status.value == "in_recovery"),
                    closed_cycles=sum(1 for c in main_cycles if c.status.value == "closed"),
                    main_tps=sum(1 for o in repo.operations.values() 
                                if o.is_main and o.status.value == "tp_hit"),
                    recovery_tps=sum(1 for o in repo.operations.values() 
                                    if o.is_recovery and o.status.value == "tp_hit"),
                    status="running"
                )
                
                # FIX-LOG: Log progress to server logs
                if tick_count % 10000 == 0 or tick_count == 1:
                    logger.critical(f"PROGRESS|{tick_count}|{total_ticks}|{balance:.2f}|{equity:.2f}")
                
                yield progress
                
                # Small delay to not overwhelm
                await asyncio.sleep(0.01)
        
        # Final report
        duration = time.time() - start_time
        acc = await broker.get_account_info()
        final_balance = acc.value["balance"]
        final_equity = acc.value["equity"]
        
        all_cycles = list(repo.cycles.values())
        main_cycles = [c for c in all_cycles if c.cycle_type.value == "main"]
        
        progress = BacktestProgress(
            tick=tick_count,
            total_ticks=total_ticks,
            balance=final_balance,
            equity=final_equity,
            active_cycles=sum(1 for c in main_cycles if c.status.value == "active"),
            hedged_cycles=sum(1 for c in main_cycles if c.status.value == "hedged"),
            in_recovery_cycles=sum(1 for c in main_cycles if c.status.value == "in_recovery"),
            closed_cycles=sum(1 for c in main_cycles if c.status.value == "closed"),
            main_tps=sum(1 for o in repo.operations.values() if o.is_main and o.status.value == "tp_hit"),
            recovery_tps=sum(1 for o in repo.operations.values() if o.is_recovery and o.status.value == "tp_hit"),
            status="complete",
            message=f"Backtest completado en {duration:.1f}s. P/L: {final_balance - initial_balance:+.2f} EUR"
        )
        
        # FIX-LOG: Log final result
        logger.info(f"Backtest Completed! Final Balance: {final_balance:.2f} | P/L: {final_balance - initial_balance:+.2f} EUR")
        print(f"===RESULT=== Final Balance: {final_balance:.2f} | P/L: {final_balance - initial_balance:+.2f} EUR")
        
        yield progress


# Singleton para uso desde la API
backtest_service = BacktestService()
