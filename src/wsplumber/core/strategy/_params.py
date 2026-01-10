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

# Filtro de Volatilidad Sistema Inmune (Layer 2)
MIN_ATR_PIPS = 20.0      # Mínima volatilidad (ATR de 4H) para abrir nuevos ciclos
ATR_WINDOW_SIZE = 4      # Número de velas de 1 hora para el cálculo del ATR

# =========================================
# PHASE 5: DYNAMIC DEBT FEATURE FLAGS
# =========================================

# When True, uses dynamic debt calculation based on real execution prices
# When False (default), uses hardcoded 20/40/80 pip values
USE_DYNAMIC_DEBT = False  # Set to True to enable dynamic mode

# When True, logs comparison between hardcoded and dynamic systems
# Useful for validation before switching to dynamic mode
LOG_DEBT_COMPARISON = True
