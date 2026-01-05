# src/wsplumber/core/strategy/_engine.py
"""
Motor Principal del Core Secreto - El Fontanero.

Implementa IStrategy. Coordina la generación de señales 
principales y de recuperación basadas en las fórmulas y parámetros.
"""

from typing import List, Optional
from datetime import datetime

from wsplumber.domain.interfaces.ports import IStrategy
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.types import (
    StrategySignal, 
    SignalType, 
    TickData, 
    CurrencyPair,
    Result
)
from wsplumber.infrastructure.logging.safe_logger import get_logger

from ._params import MAX_SPREAD_PIPS
from ._formulas import calculate_main_tp, calculate_recovery_setup

logger = get_logger(__name__)

class WallStreetPlumberStrategy(IStrategy):
    """
    Estrategia "El Fontanero de Wall Street".
    
    Se basa en ciclos duales continuos y un sistema de recuperación 
    matemática FIFO.
    """

    async def generate_signals(self, tick: TickData, active_cycles: List[Cycle]) -> List[StrategySignal]:
        """
        Analiza el mercado y el estado actual para generar señales.
        """
        signals = []
        pair = tick.pair

        # 1. Validar Spread (Seguridad)
        if float(tick.spread_pips) > MAX_SPREAD_PIPS:
            logger.debug("Spread too high, skipping signal generation", pair=pair, spread=tick.spread_pips)
            return signals

        # 2. Verificar si necesitamos un nuevo ciclo principal
        # (Si no hay ciclo activo para este par)
        pair_cycles = [c for c in active_cycles if c.pair == pair]
        if not pair_cycles:
            signals.append(StrategySignal(
                pair=pair,
                signal_type=SignalType.OPEN_NEW_CYCLE,
                entry_price=tick.ask, # Se usa el tick actual como referencia
                timestamp=datetime.now(),
                metadata={"reason": "no_active_cycle"}
            ))
            return signals # Prioridad alta

        # 3. Analizar ciclos activos para detectar necesidad de Recovery
        for cycle in pair_cycles:
            # Si el ciclo tiene una operación principal 'colgada' (en pérdida considerable)
            # y aún no tiene un recovery abierto o necesita el siguiente nivel.
            # NOTA: La lógica de 'cuándo' abrir recovery viene dictada por la 
            # separación de 40 pips y el estado de la cobertura.
            
            # Buscamos la operación que necesita cobertura
            for op in cycle.operations:
                if op.status == "active" and op.is_main():
                    # Lógica de detección de cobertura (simplificada para el core)
                    # Si el precio se ha movido en contra...
                    pass

        return signals

    async def calculate_levels(self, pair: CurrencyPair, current_price: float) -> Result[dict]:
        """Calcula niveles de TP/SL para nuevas operaciones."""
        # Esta función puede ser llamada por el orquestador si necesita recalcular
        return Result.ok({})
