# Índice Completo de Escenarios de Auditoría WSPlumber

**Total: 62 escenarios** (corregido para sistema sin SL)

## Resumen por Categoría

| Categoría | Cantidad | Críticos | Alta | Media | Baja |
|-----------|----------|----------|------|-------|------|
| Core | 5 | 3 | 2 | 0 | 0 |
| Cycles | 6 | 4 | 2 | 0 | 0 |
| Hedged | 8 | 5 | 3 | 0 | 0 |
| Recovery | 10 | 4 | 5 | 1 | 0 |
| FIFO | 4 | 2 | 2 | 0 | 0 |
| Risk Management | 5 | 2 | 3 | 0 | 0 |
| Money Management | 8 | 5 | 3 | 0 | 0 |
| Edge Cases | 8 | 0 | 4 | 3 | 1 |
| Multi-Pair | 4 | 0 | 4 | 0 | 0 |
| JPY Pairs | 4 | 0 | 4 | 0 | 0 |
| **TOTAL** | **62** | **25** | **32** | **4** | **1** |

---

## CORE (5 escenarios) ✅ Corregido

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| c01_tp_simple_buy | TP Simple BUY | 🔴 CRÍTICA | BUY toca TP +10 pips |
| c01_tp_simple_sell | TP Simple SELL | 🔴 CRÍTICA | SELL toca TP +10 pips |
| c03_activation_no_tp | Activación sin TP | 🟡 ALTA | Operación activa, no alcanza TP |
| c04_no_activation | Sin activación | 🟡 ALTA | Precio no activa operación |
| c05_gap_tp | Gap atraviesa TP | 🔴 CRÍTICA | Gap salta sobre TP |

---

## CYCLES (6 escenarios) ✅ Corregido

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| cy01_new_cycle | Nuevo ciclo | 🔴 CRÍTICA | Crear ciclo con BUY+SELL |
| cy02_tp_in_cycle | TP en ciclo | 🔴 CRÍTICA | TP hit, ciclo continúa |
| cy03_tp_renews_operations | TP renueva operaciones | 🔴 CRÍTICA | FIX-001: Crea nuevas BUY+SELL |
| cy04_cancel_counter_main | Cancela main contraria | 🔴 CRÍTICA | Cuando una toca TP |
| cy05_complete_10_tps | Completar 10 TPs | 🟡 ALTA | Ciclo exitoso completo |
| cy06_multiple_cycles | Múltiples ciclos | 🟡 ALTA | Pares independientes |

---

## HEDGED (8 escenarios) ✅ Nuevo - Refleja arquitectura real

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| h01_both_active_hedged | Ambas activas → HEDGED | 🔴 CRÍTICA | BUY y SELL activan |
| h02_create_hedge_operations | Crear hedges | 🔴 CRÍTICA | HEDGE_BUY + HEDGE_SELL |
| h03_neutralize_mains | Neutralizar mains | 🔴 CRÍTICA | Status → NEUTRALIZED |
| h04_lock_20_pips | Bloquear 20 pips | 🔴 CRÍTICA | pips_locked = 20 |
| h05_sequential_activation | Activación secuencial | 🟡 ALTA | Una después de otra |
| h06_simultaneous_gap | Gap simultáneo | 🟡 ALTA | Gap activa ambas |
| h07_buy_tp_hedge_sell | BUY TP en HEDGED | 🔴 CRÍTICA | FIX-002: Cancela HEDGE_SELL pendiente |
| h08_sell_tp_hedge_buy | SELL TP en HEDGED | 🟡 ALTA | FIX-002: Cancela HEDGE_BUY pendiente |

---

## RECOVERY (10 escenarios) ✅ Expandido

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| r01_open_from_tp | Recovery desde TP | 🔴 CRÍTICA | Abre recovery desde precio TP del main |
| r02_recovery_distance_20 | Distancia 20 pips | 🔴 CRÍTICA | Entry a ±20 pips del TP |
| r03_recovery_n1_tp_buy | Recovery N1 TP (BUY) | 🔴 CRÍTICA | N1 recupera +80 pips |
| r04_recovery_n1_tp_sell | Recovery N1 TP (SELL) | 🟡 ALTA | N1 SELL recupera |
| r05_recovery_n1_fails_n2 | N1 falla → N2 | 🔴 CRÍTICA | Cascada de recovery |
| r06_recovery_n2_success | N2 éxito | 🟡 ALTA | N2 recupera todo |
| r07_cascade_n1_n2_n3 | Cascada N1→N2→N3 | 🟡 ALTA | Múltiples niveles |
| r08_recovery_max_n6 | N6 máximo | 🟡 ALTA | Nivel máximo alcanzado |
| r09_cancel_recovery_counter | Cancela recovery contrario | 🟡 ALTA | Cuando uno toca TP |
| r10_multiple_recovery_pairs | Múltiples recovery | 🟢 MEDIA | Pares en recovery |

---

## FIFO (4 escenarios) ✅ Expandido - Crucial

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| f01_fifo_first_costs_20 | Primer recovery 20 pips | 🔴 CRÍTICA | FIX-003: Incluye main+hedge |
| f02_fifo_subsequent_40 | Siguientes 40 pips | 🔴 CRÍTICA | Recovery adicionales |
| f03_fifo_atomic_close | Cierre atómico | 🟡 ALTA | Main + Hedge juntos |
| f04_fifo_multiple_close | FIFO múltiple | 🟡 ALTA | 80 pips cierran varios |

---

## RISK MANAGEMENT (5 escenarios) ✅ Sin cambios

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| rm01_exposure_limit | Límite exposición | 🔴 CRÍTICA | Máx 5 ciclos |
| rm02_drawdown_limit | Límite drawdown | 🔴 CRÍTICA | Pausa > 20% |
| rm03_daily_loss_limit | Pérdida diaria | 🟡 ALTA | Pausa hasta mañana |
| rm04_margin_insufficient | Margen insuficiente | 🟡 ALTA | Operación rechazada |
| rm05_recovery_exposure | Exposición recovery | 🟡 ALTA | Incluye recovery |

---

## MONEY MANAGEMENT (8 escenarios) ✅ Corregido (sin SL)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| mm01_balance_read | Balance inicial | 🔴 CRÍTICA | Lee balance broker |
| mm02_pnl_tp | P&L en TP | 🔴 CRÍTICA | +10 pips = $10 |
| mm03_pnl_hedged | P&L bloqueado | 🔴 CRÍTICA | Pips en HEDGED |
| mm04_balance_update_tp | Balance tras TP | 🔴 CRÍTICA | balance += P&L |
| mm05_equity_calculation | Cálculo equity | 🔴 CRÍTICA | Balance + Floating |
| mm06_margin_calculation | Cálculo margen | 🟡 ALTA | lot × contract / leverage |
| mm07_free_margin | Margen libre | 🟡 ALTA | equity - margin_used |
| mm08_recovery_pnl_accumulation | P&L recovery | 🟡 ALTA | Suma total |

---

## EDGE CASES (8 escenarios) ✅ Sin cambios

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| e01_spread_rejection | Spread alto rechaza | 🟢 MEDIA | No abre con spread |
| e02_high_spread_rejection | Spread muy alto | 🟡 ALTA | Operaciones pausadas |
| e03_weekend_gap | Gap fin de semana | 🟡 ALTA | Manejo de gap |
| e04_mega_move | Movimiento extremo | 🟡 ALTA | >200 pips |
| e05_return_to_origin | Retorno al origen | 🟢 MEDIA | Precio vuelve |
| e06_lateral_market | Mercado lateral | 🟢 MEDIA | Múltiples TPs |
| e07_connection_lost | Conexión perdida | 🟢 MEDIA | Reconexión |
| e08_rollover_swap | Rollover/Swap | ⚪ BAJA | Swap aplicado |

---

## MULTI-PAIR (4 escenarios) ✅ Sin cambios

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| mp01_dual_pair | Dual pair | 🟡 ALTA | EURUSD + GBPUSD |
| mp02_correlation_hedged | Correlación | 🟡 ALTA | Ambos en HEDGED |
| mp03_jpy_calculation | Cálculo JPY | 🟡 ALTA | 2 decimales |
| mp04_total_exposure | Exposición total | 🟡 ALTA | Suma de pares |

---

## JPY PAIRS (4 escenarios) ✅ Expandido

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| j01_usdjpy_tp | USDJPY TP | 🟡 ALTA | Cálculo 2 decimales |
| j02_usdjpy_hedged | USDJPY HEDGED | 🟡 ALTA | Hedge con 2 decimales |
| j03_usdjpy_recovery | USDJPY Recovery | 🟡 ALTA | Recovery en JPY |
| j04_usdjpy_pips_calculation | Cálculo pips JPY | 🟡 ALTA | Multiplicador × 100 |

---

## Cobertura vs Especificación

| Categoría | Doc Madre | Implementado | Estado |
|-----------|-----------|--------------|--------|
| Arquitectura sin SL | ✅ | ✅ | ✅ |
| Coberturas (Hedge) | ✅ | ✅ 8 escenarios | ✅ |
| Recoveries | ✅ | ✅ 10 escenarios | ✅ |
| FIFO (FIX-003) | ✅ | ✅ 4 escenarios | ✅ |
| Renovación Main (FIX-001) | ✅ | ✅ en cy03 | ✅ |
| Cancelación Counter (FIX-002) | ✅ | ✅ en cy04, h07, h08 | ✅ |
| **TOTAL** | - | **62 escenarios** | ✅ |

---

## Verificación de Escenarios

Para verificar un escenario específico y generar un reporte detallado del ciclo de vida y la contabilidad FIFO:

```bash
# Uso del Auditor de Escenarios
python scripts/audit_scenario.py tests/scenarios/r07_cascade_n1_n2_n3.csv
```

Este comando generará un reporte "limpio" que muestra:
1. **Contabilidad FIFO**: Unidades de deuda `[20, 40]` y su liquidación.
2. **Timeline de Eventos**: Activaciones, neutralizaciones y cierres atómicos.
3. **P&L Acumulado**: Beneficio neto pips tras recuperar deudas.

## Estructura de Archivos (Tests)

Los archivos CSV de los escenarios se encuentran en:
- `tests/scenarios/`: Escenarios oficiales por ID (r01, f01, etc.)
- `tests/test_scenarios/`: Escenarios de integración y casos de borde.

---
*Actualizado: 2026-01-09*
*Versión: 3.1 (Con Cierre Atómico FIFO verificado)*

---

## Archivos CSV Corregidos
```bash
# ❌ ELIMINAR (usan SL inexistente)
tests/test_scenarios/core/c02_sl_hit.csv
tests/test_scenarios/core/c05_gap_sl.csv
tests/test_scenarios/cycles/cy03_sl_triggers_recovery.csv
tests/test_scenarios/money_management/mm05_balance_update_sl.csv

# ✅ CREAR NUEVOS (reflejan arquitectura real)
tests/test_scenarios/hedged/h02_create_hedge_operations.csv
tests/test_scenarios/hedged/h03_neutralize_mains.csv
tests/test_scenarios/hedged/h04_lock_20_pips.csv
tests/test_scenarios/hedged/h07_buy_tp_hedge_sell.csv
tests/test_scenarios/hedged/h08_sell_tp_hedge_buy.csv

tests/test_scenarios/recovery/r01_open_from_tp.csv
tests/test_scenarios/recovery/r02_recovery_distance_20.csv
tests/test_scenarios/recovery/r09_cancel_recovery_counter.csv

tests/test_scenarios/fifo/f01_fifo_first_costs_20.csv
tests/test_scenarios/fifo/f02_fifo_subsequent_40.csv
tests/test_scenarios/fifo/f03_fifo_atomic_close.csv

tests/test_scenarios/cycles/cy03_tp_renews_operations.csv
tests/test_scenarios/cycles/cy04_cancel_counter_main.csv

tests/test_scenarios/jpy/j02_usdjpy_hedged.csv
tests/test_scenarios/jpy/j04_usdjpy_pips_calculation.csv

tests/test_scenarios/money_management/mm03_pnl_hedged.csv (renombrado desde mm03_pnl_loss)
```