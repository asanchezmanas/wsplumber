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

# Umbral de Avaricia: Pips extra necesarios sobre la deuda para cerrar unidad (Experimento)
# 0.0 = Cerrar lo antes posible (Aconsejado). 10.0-20.0 = Esperar a más beneficio.
RECOVERY_MIN_SURPLUS = 0.0 

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
LAYER1_MODE = "ADAPTIVE_TRAILING"  # Change to "ADAPTIVE_TRAILING" to enable

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

# =========================================
# IMMUNE SYSTEM: LAYER 2 - EVENT GUARD
# =========================================

# Layer 2 Mode: "OFF" | "ON"
# If ON, cancels pending orders and forces BE before scheduled events
LAYER2_MODE = "ON"

# Minutes before/after event to activate protection
EVENT_PROTECTION_WINDOW_PRE = 5
EVENT_PROTECTION_WINDOW_POST = 5

# Event Calendar: List of (datetime_iso, importance, description)
# 2015 High-Impact Events for testing
EVENT_CALENDAR = [
    # NFP (Non-Farm Payroll) - First Friday of month, 13:30 UTC
    ("2015-01-02T13:30:00", "HIGH", "NFP January"),
    ("2015-02-06T13:30:00", "HIGH", "NFP February"),
    ("2015-03-06T13:30:00", "HIGH", "NFP March"),
    ("2015-04-03T13:30:00", "HIGH", "NFP April"),
    ("2015-05-01T13:30:00", "HIGH", "NFP May"),
    ("2015-06-05T13:30:00", "HIGH", "NFP June"),
    ("2015-07-02T13:30:00", "HIGH", "NFP July"),
    ("2015-08-07T13:30:00", "HIGH", "NFP August"),
    ("2015-09-04T13:30:00", "HIGH", "NFP September"),
    ("2015-10-02T13:30:00", "HIGH", "NFP October"),
    ("2015-11-06T13:30:00", "HIGH", "NFP November"),
    ("2015-12-04T13:30:00", "HIGH", "NFP December"),
    # FOMC Announcements - 19:00 UTC
    ("2015-01-28T19:00:00", "HIGH", "FOMC January"),
    ("2015-03-18T19:00:00", "HIGH", "FOMC March"),
    ("2015-04-29T19:00:00", "HIGH", "FOMC April"),
    ("2015-06-17T19:00:00", "HIGH", "FOMC June"),
    ("2015-07-29T19:00:00", "HIGH", "FOMC July"),
    ("2015-09-17T19:00:00", "HIGH", "FOMC September"),
    ("2015-10-28T19:00:00", "HIGH", "FOMC October"),
    ("2015-12-16T19:00:00", "HIGH", "FOMC December Rate Hike"),
    ("2015-01-15T09:30:00", "HIGH", "SNB Black Thursday - 1.20 Cap Removed"),
    ("2015-01-22T12:45:00", "HIGH", "ECB January QE"),
    ("2015-03-05T12:45:00", "HIGH", "ECB March"),
    ("2015-04-15T12:45:00", "HIGH", "ECB April"),
    ("2015-06-03T12:45:00", "HIGH", "ECB June"),
    ("2015-07-16T12:45:00", "HIGH", "ECB July"),
    ("2015-09-03T12:45:00", "HIGH", "ECB September"),
    ("2015-10-22T12:45:00", "HIGH", "ECB October"),
    ("2015-12-03T12:45:00", "HIGH", "ECB December"),
    # Test Event for Scenario E01
    ("2026-01-16T12:00:00", "HIGH", "Scenario Test Event"),
]

# =========================================
# IMMUNE SYSTEM: LAYER 3 - BLIND GAP GUARD
# =========================================

# Layer 3 Mode: "OFF" | "ON"
# If ON, stops everything if a sudden price jump is detected
LAYER3_MODE = "ON"

# Jump threshold in pips to trigger emergency freeze
GAP_FREEZE_THRESHOLD_PIPS = 50.0

# Freeze duration in minutes after a blind gap
GAP_FREEZE_DURATION_MINUTES = 30

# =========================================
# IMMUNE SYSTEM: LAYER 1B - TRAILING COUNTER-ORDER
# =========================================

# Layer 1B Mode: "OFF" | "ON"
# If ON, trails the pending recovery counter-order when active is in profit
LAYER1B_MODE = "ON"

# Minimum profit on active recovery before trailing starts
LAYER1B_ACTIVATION_PIPS = 10.0

# Buffer distance: how close to trail the counter-order
LAYER1B_BUFFER_PIPS = 5.0

# Minimum move: don't reposition unless it moves at least this much
LAYER1B_MIN_MOVE_PIPS = 3.0

# Threshold to detect OVERLAP (close-distance hedge vs correction fail)
LAYER1B_OVERLAP_THRESHOLD_PIPS = 10.0

# =========================================
# PHASE 11: FIDELITY & PATIENCE STRATEGY
# =========================================

# Minimum net profit (pips) required to close by overlapping.
# If profit is positive but less than this, move to BE instead of closing.
OVERLAP_MIN_PIPS = 50.0

# Buffer for Break Even protection (pips above/below entry)
BE_BUFFER_PIPS = 0.1

