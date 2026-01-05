# src/wsplumber/core/strategy/_params.py
"""
Parámetros del Core Secreto - El Fontanero.

Contiene las constantes y configuraciones que rigen la lógica 
de la estrategia. Estos valores son críticos para el balance matemático.
"""

from typing import Dict, Any

# Configuración del Ciclo Principal (Income Motor)
MAIN_TP_PIPS = 10.0      # Objetivo de beneficio constante
MAIN_HEDGE_DISTANCE = 0.0 # La cobertura suele ser inmediata o por señal opuesta

# Configuración del Sistema Recovery (Debt Management)
RECOVERY_TP_PIPS = 80.0  # Objetivo para neutralizar deudas
RECOVERY_DISTANCE_PIPS = 20.0 # Distancia desde el precio actual
RECOVERY_LEVEL_STEP = 40.0    # Separación mínima entre niveles de recovery

# Ratio de Neutralización FIFO
# 1 Recovery (80 pips) = 2 niveles de pérdida (40 pips + 40 pips) o equivalentes
NEUTRALIZATION_RATIO = 2.0 

# Límites de Seguridad Operativa
MAX_RECOVERY_LEVELS = 10 # Máximo niveles por par antes de pausa total

# Configuración de Spreads
MAX_SPREAD_PIPS = 3.0    # No operar si el spread es superior
