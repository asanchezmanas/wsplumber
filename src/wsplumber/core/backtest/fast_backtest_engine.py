# src/wsplumber/core/backtest/fast_backtest_engine.py
"""
TurboBacktestEngine - Motor de backtesting de alto rendimiento.
Usa Polars para saltar directamente a los eventos relevantes.
"""

import time
import logging
import asyncio
import polars as pl
from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any

from wsplumber.domain.types import (
    CurrencyPair, TickData, Price, Pips, Timestamp,
    OperationType, OperationStatus, OrderRequest, OrderResult
)
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation
from wsplumber.core.backtest.backtest_engine import BacktestEngine
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)

class TurboBacktestEngine(BacktestEngine):
    """
    Versión 'Turbo' que usa Discrete Event Simulation.
    Ideal para Colab y simulaciones de años.
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        super().__init__(initial_balance)
        self.df: Optional[pl.DataFrame] = None
        self.pips_mult = 10000
        
    async def run(self, csv_path: str, pair: str = "EURUSD", audit_file: str = "docs/audit_turbo_output.md", max_bars: int = None):
        """Ejecuta el backtest en modo Turbo."""
        self.setup_logging(audit_file)
        await self.broker.connect()
        
        start_time = time.time()
        
        # 1. Cargar datos con Polars
        logger.info(f"Cargando datos turbo para {pair}...")
        self.df = pl.read_csv(csv_path).head(max_bars) if max_bars else pl.read_csv(csv_path)
        
        # Pre-procesar fechas y tipos
        # (Aquí añadiríamos la lógica de M1DataLoader pero vectorizada)
        
        logger.info(f"Iniciando simulación Turbo de {len(self.df)} ticks...")
        
        # 2. Loop de Eventos (Simulado por ahora para integración)
        # TODO: Implementar el salto de ticks
        await super().run(csv_path, pair, audit_file, max_bars)
        
        end_time = time.time()
        logger.info(f"Backtest Turbo finalizado en {end_time - start_time:.2f}s")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv"
    engine = TurboBacktestEngine()
    asyncio.run(engine.run(path))
