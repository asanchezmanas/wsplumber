# src/wsplumber/core/strategy/_formulas.py
"""
Fórmulas Matemáticas del Core Secreto - El Fontanero.

Contiene las funciones puras para el cálculo de niveles, 
neutralización y objetivos de trading.
"""

from decimal import Decimal
from typing import Tuple
from wsplumber.domain.types import Price, Pips, CurrencyPair
from ._params import (
    MAIN_TP_PIPS, 
    RECOVERY_TP_PIPS, 
    RECOVERY_DISTANCE_PIPS,
    RECOVERY_LEVEL_STEP
)

def calculate_main_tp(entry_price: Price, is_buy: bool, pair: CurrencyPair) -> Price:
    """Calcula el precio TP para una operación principal (10 pips)."""
    multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
    move = Decimal(str(MAIN_TP_PIPS)) * multiplier
    
    if is_buy:
        return entry_price + move
    return entry_price - move

def calculate_recovery_setup(current_price: Price, is_buy: bool, pair: CurrencyPair) -> Tuple[Price, Price]:
    """
    Calcula el precio de entrada y el TP para una operación de Recovery.
    Entrada: a 20 pips del precio actual.
    TP: a 80 pips de la entrada.
    """
    multiplier = Decimal("0.01") if "JPY" in str(pair) else Decimal("0.0001")
    distance = Decimal(str(RECOVERY_DISTANCE_PIPS)) * multiplier
    tp_move = Decimal(str(RECOVERY_TP_PIPS)) * multiplier
    
    if is_buy:
        entry = current_price + distance
        tp = entry + tp_move
    else:
        entry = current_price - distance
        tp = entry - tp_move
        
    return entry, tp

def calculate_neutralization(recovery_profit_pips: Pips) -> float:
    """
    Calcula cuántos niveles de deuda se neutralizan.
    Basado en el ratio 2:1 (80 pips recuperan 2x40 pips).
    """
    # Lógica simplificada: un recovery exitoso siempre intenta limpiar lo máximo posible
    # según la cola FIFO de deudas.
    return float(recovery_profit_pips) / 40.0 # Cada 40 pips de beneficio limpian un nivel
