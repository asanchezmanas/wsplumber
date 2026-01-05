# src/wsplumber/application/services/history_service.py
"""
Servicio de Ingesta de Datos Históricos.

Orquesta la descarga de datos desde el broker y su persistencia en el repositorio.
"""

from datetime import datetime
from typing import List, Optional

from wsplumber.domain.interfaces.ports import IBroker, IRepository
from wsplumber.domain.types import CurrencyPair, Result
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)

class HistoryService:
    """Servicio para gestionar la ingesta de datos históricos."""

    def __init__(self, broker: IBroker, repository: IRepository):
        self.broker = broker
        self.repository = repository

    async def ingest_ohlc(
        self,
        pair: CurrencyPair,
        timeframe: str,
        count: int,
        from_date: Optional[datetime] = None
    ) -> Result[int]:
        """
        Descarga velas de MT5 y las guarda en Supabase.
        """
        logger.info(f"💾 Starting OHLC ingestion for {pair} {timeframe} (count: {count})")
        
        # 1. Obtener del broker
        rates_res = await self.broker.get_historical_rates(pair, timeframe, count, from_date)
        if not rates_res.success:
            return Result.fail(f"Failed to get rates: {rates_res.error}")

        rates = rates_res.value
        
        # 2. Guardar en repositorio
        save_res = await self.repository.save_historical_rates(pair, timeframe, rates)
        if not save_res.success:
            return Result.fail(f"Failed to save rates: {save_res.error}")

        logger.info(f"✅ Ingested {save_res.value} candles for {pair}")
        return Result.ok(save_res.value)

    async def ingest_ticks(
        self,
        pair: CurrencyPair,
        count: int,
        from_date: Optional[datetime] = None
    ) -> Result[int]:
        """
        Descarga ticks de MT5 y los guarda en Supabase.
        """
        logger.info(f"💾 Starting Ticks ingestion for {pair} (count: {count})")
        
        # 1. Obtener del broker
        ticks_res = await self.broker.get_historical_ticks(pair, count, from_date)
        if not ticks_res.success:
            return Result.fail(f"Failed to get ticks: {ticks_res.error}")

        ticks = ticks_res.value
        
        # 2. Guardar en repositorio
        save_res = await self.repository.save_historical_ticks(pair, ticks)
        if not save_res.success:
            return Result.fail(f"Failed to save ticks: {save_res.error}")

        logger.info(f"✅ Ingested {save_res.value} ticks for {pair}")
        return Result.ok(save_res.value)
