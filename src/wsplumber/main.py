# src/wsplumber/main.py
"""
Punto de entrada principal del sistema wsplumber.

Instancia los adaptadores de infraestructura, el core de riesgo y estrategia,
y arranca el orquestador de ciclos.
"""

import asyncio
import os
import sys
from datetime import datetime

from wsplumber.config.settings import get_settings
from wsplumber.application.services.trading_service import TradingService
from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.infrastructure.brokers.mt5_broker import MT5Broker
from wsplumber.infrastructure.persistence.supabase_repo import SupabaseRepository
from wsplumber.infrastructure.logging.safe_logger import setup_logging, get_logger

# Importar componentes del core
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.core.strategy.strategy_mock import StrategyMock # Usando mock para demo

logger = get_logger("wsplumber.main")


async def main():
    """Arranque del sistema."""
    # 1. Configuración y Logging
    settings = get_settings()
    setup_logging(
        level=settings.logging.level,
        environment=settings.environment.environment
    )
    
    logger.info("🔧 Starting El Fontanero de Wall Street 🔧", version="2.0")

    # 2. Instanciar Infraestructura
    # Repositorio (Supabase)
    repository = SupabaseRepository()
    
    # Broker (MT5)
    broker = MT5Broker(
        login=settings.mt5.login,
        password=settings.mt5.password,
        server=settings.mt5.server,
        path=settings.mt5.path
    )

    # 3. Instanciar Core
    risk_manager = RiskManager()
    strategy = StrategyMock() # Aquí se inyectarían los motores secretos en producción

    # 4. Instanciar Servicios de Aplicación
    trading_service = TradingService(broker, repository)
    
    orchestrator = CycleOrchestrator(
        trading_service=trading_service,
        strategy=strategy,
        risk_manager=risk_manager,
        repository=repository
    )

    # 5. Ejecutar
    try:
        # Nota: connect() fallará si no hay credenciales reales en .env
        conn_res = await broker.connect()
        if not conn_res.success:
            logger.error("Could not connect to broker. System will continue in observation mode (if applicable).", 
                         error=conn_res.error)
            # En modo observación podríamos seguir, pero para este demo salimos
            # return

        # Arrancar orquestación para los pares configurados
        pairs = settings.trading.pairs
        await orchestrator.start(pairs)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical("Unexpected system failure", exception=e)
    finally:
        await orchestrator.stop()
        await broker.disconnect()
        logger.info("System shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
