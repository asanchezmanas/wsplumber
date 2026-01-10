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
    'max_concurrent_recovery': 999999, # Límite prácticamente eliminado por petición
    'max_exposure_percent': 999999.0   # Límite prácticamente eliminado por petición
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
        num_recoveries: int = 0,
        free_margin_percent: float = 100.0,
        is_recovery: bool = False
    ) -> Result[bool]:
        """
        Verifica si se permite abrir una nueva posición basándose en exposición,
        recoveries y salud del margen (Sistema Inmune Layer 3).
        """
        # --- IMMUNE SYSTEM: Layer 3 - Margin Operating Modes ---
        # 1. Modo SUPERVIVENCIA (< 40%) - Bloqueo TOTAL de nuevas operaciones
        if free_margin_percent < 40.0:
            msg = f"SURVIVAL MODE: Margin too low ({free_margin_percent:.1f}%). Blocked all operations."
            logger.error(msg, pair=pair)
            return Result.fail(msg, "RISK_MARGIN_SURVIVAL")

        # 2. Modo ALERTA (40% - 60%) - Bloquea nuevos ciclos, solo permite gestionar los existentes
        if free_margin_percent <= 60.0 and not is_recovery:
            msg = f"ALERT MODE: Margin at {free_margin_percent:.1f}%. Only RECOVERY allowed."
            logger.warning(msg, pair=pair)
            return Result.fail(msg, "RISK_MARGIN_ALERT")
        # --- END IMMUNE SYSTEM ---

        # 3. Verificar exposición total (Límite dinámico si fuera necesario)
        max_exp = EMERGENCY_LIMITS['max_exposure_percent']
        if current_exposure >= max_exp:
            msg = f"Max exposure reached: {current_exposure:.2f}% >= {max_exp}%"
            logger.warning(msg, pair=pair)
            return Result.fail(msg, "RISK_EXPOSURE_LIMIT")

        # 4. Verificar número de recoveries simultáneos
        max_rec = EMERGENCY_LIMITS['max_concurrent_recovery']
        if num_recoveries >= max_rec:
            msg = f"Max concurrent recoveries reached for {pair}: {num_recoveries} >= {max_rec}"
            logger.warning(msg, pair=pair)
            return Result.fail(msg, "RISK_RECOVERY_LIMIT")

        # 5. Verificar límites de drawdown (Placeholder)
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
