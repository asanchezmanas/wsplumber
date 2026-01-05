# src/wsplumber/core/risk/risk_manager.py
"""
Gestor de Riesgo (Core).

Implementa IRiskManager. Controla la exposición, límites diarios
y paradas de emergencia. Este componente es parte del "Core" y
contiene reglas de negocio críticas.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from decimal import Decimal

from wsplumber.domain.interfaces.ports import IRiskManager
from wsplumber.domain.types import (
    CurrencyPair,
    LotSize,
    Result,
)
from wsplumber.config.settings import get_settings
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)

# Límites de emergencia extraídos del documento madre (pág. 7219)
EMERGENCY_LIMITS = {
    'max_daily_loss_pips': 100,      # Pausa automática
    'max_weekly_loss_pips': 300,     # Revisión obligatoria
    'max_monthly_loss_pips': 500,    # Stop total del sistema
    'max_concurrent_recovery': 20,   # Pausa nuevos ciclos
    'max_exposure_percent': 30       # No abrir más operaciones
}


class RiskManager(IRiskManager):
    """
    Implementación del gestor de riesgos.
    """

    def __init__(self):
        self.settings = get_settings()

    def can_open_position(
        self,
        pair: CurrencyPair,
        current_exposure: float,
    ) -> Result[bool]:
        """
        Verifica si se permite abrir una nueva posición.
        """
        # 1. Verificar exposición total
        max_exp = EMERGENCY_LIMITS['max_exposure_percent']
        if current_exposure >= max_exp:
            msg = f"Max exposure reached: {current_exposure:.2f}% >= {max_exp}%"
            logger.warning(msg, pair=pair)
            return Result.fail(msg, "RISK_EXPOSURE_LIMIT")

        # 2. Verificar límites de drawdown (esto debería venir de métricas en tiempo real)
        # Por ahora es una implementación básica
        if self.check_emergency_stop():
            return Result.fail("Emergency stop active", "RISK_EMERGENCY_STOP")

        return Result.ok(True)

    def calculate_lot_size(
        self,
        pair: CurrencyPair,
        account_balance: float,
    ) -> LotSize:
        """
        Calcula el tamaño del lote basado en el balance y configuración.
        """
        # Implementación simple por ahora: lote fijo desde settings
        base_lot = self.settings.trading.default_lot_size
        
        # TODO: Implementar escalado basado en balance o riesgo por trade
        lot = base_lot
        
        # Limitar al máximo configurado
        max_lot = self.settings.trading.max_lot_size
        lot = min(lot, max_lot)
        
        logger.debug("Calculated lot size", pair=pair, lot=lot, balance=account_balance)
        return LotSize(lot)

    def check_daily_limits(self) -> Result[bool]:
        """
        Verifica si se han alcanzado los límites de pérdida diarios.
        """
        # Requiere acceso a métricas diarias. 
        # Esta implementación es un placeholder que asume todo OK.
        return Result.ok(True)

    def check_emergency_stop(self) -> bool:
        """
        Verifica condiciones de parada catastrófica.
        """
        # Placeholder
        return False
