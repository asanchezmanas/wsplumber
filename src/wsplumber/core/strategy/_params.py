# src/wsplumber/core/strategy/_params.py
"""
Parámetros del Core Secreto - El Fontanero.

Contiene las constantes y configuraciones que rigen la lógica 
de la estrategia. Estos valores son críticos para el balance matemático.
"""

from typing import Dict, Any

# Configuración del Ciclo Principal (Income Motor)
MAIN_TP_PIPS = 10.0       # Objetivo de beneficio constante (TP)
MAIN_DISTANCE_PIPS = 5.0  # Distancia de entrada desde precio actual (BUY_STOP/SELL_STOP)
MAIN_HEDGE_DISTANCE = 0.0 # La cobertura suele ser inmediata o por señal opuesta

# Configuración del Sistema Recovery (Debt Management)
RECOVERY_TP_PIPS = 80.0  # Objetivo para neutralizar deudas
RECOVERY_DISTANCE_PIPS = 20.0 # Distancia desde el precio actual
RECOVERY_LEVEL_STEP = 40.0    # Separación mínima entre niveles de recovery

# Ratio de Neutralización FIFO
# 1 Recovery (80 pips) = 2 niveles de pérdida (40 pips + 40 pips) o equivalentes
NEUTRALIZATION_RATIO = 2.0 

# Límites de Seguridad Operativa
MAX_RECOVERY_LEVELS = 999999 # Límite eliminado por petición

# Configuración de Spreads
MAX_SPREAD_PIPS = 3.0    # No operar si el spread es superior

# =========================================
# PHASE 5: DYNAMIC DEBT FEATURE FLAGS
# =========================================

# When True, uses dynamic debt calculation based on real execution prices
USE_DYNAMIC_DEBT = True
LOG_DEBT_COMPARISON = True
PRODUCE_AUDIT_LOGS = True

# =========================================
# IMMUNE SYSTEM: LAYER 1 - ADAPTIVE TRAILING
# =========================================

# Layer 1 Mode: "OFF" | "BREAKEVEN" | "ADAPTIVE_TRAILING"
# OFF = No trailing (baseline), ADAPTIVE_TRAILING = Progressive trailing
LAYER1_MODE = "OFF"  # Change to "ADAPTIVE_TRAILING" to enable

# Trailing Levels: (threshold_pips, lock_pips)
# When recovery reaches threshold, lock at lock_pips
# Example: At +30 pips reached, trail at +10 pips (33% captured)
TRAILING_LEVELS = [
    (30, 10),   # Level 1: +30 pips → Lock +10 pips (33%)
    (50, 25),   # Level 2: +50 pips → Lock +25 pips (50%)
    (70, 50),   # Level 3: +70 pips → Lock +50 pips (71%)
]

# Re-positioning: When trailing stop is hit, open new recovery from current price
TRAILING_REPOSITION = True

# Minimum profit to consider trailing hit (avoids noise)
TRAILING_MIN_LOCK = 5.0

