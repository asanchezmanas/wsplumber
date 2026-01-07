# Índice Completo de Escenarios de Auditoría WSPlumber

**Total: 58 escenarios**

## Resumen por Categoría

| Categoría | Cantidad | Críticos | Alta | Media | Baja |
|-----------|----------|----------|------|-------|------|
| Core | 7 | 3 | 4 | 0 | 0 |
| Cycles | 5 | 3 | 2 | 0 | 0 |
| Edge | 10 | 0 | 4 | 5 | 1 |
| FIFO | 2 | 1 | 1 | 0 | 0 |
| Hedged | 5 | 3 | 2 | 0 | 0 |
| JPY | 2 | 0 | 2 | 0 | 0 |
| Money Management | 10 | 6 | 4 | 0 | 0 |
| Multi-Pair | 4 | 0 | 4 | 0 | 0 |
| Recovery | 8 | 2 | 5 | 1 | 0 |
| Risk Management | 5 | 2 | 3 | 0 | 0 |
| **TOTAL** | **58** | **20** | **31** | **6** | **1** |

---

## CORE (7 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| 1.1_tp_simple_buy | TP Simple BUY | 🔴 CRÍTICA | BUY toca TP +10 pips |
| 1.2_tp_simple_sell | TP Simple SELL | 🔴 CRÍTICA | SELL toca TP +10 pips |
| 1.3_activation_no_tp | Activación sin TP | 🟡 ALTA | Operación activa, no alcanza TP |
| 1.4_no_activation | Sin activación | 🟡 ALTA | Precio no activa operación |
| c02_sl_hit | SL Hit (-50 pips) | 🔴 CRÍTICA | SL ejecutado con pérdida |
| c04_gap_tp | Gap atraviesa TP | 🟡 ALTA | Gap salta sobre TP |
| c05_gap_sl | Gap atraviesa SL | 🟡 ALTA | Gap salta bajo SL |

---

## CYCLES (5 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| cy01_new_cycle | Nuevo ciclo | 🔴 CRÍTICA | Crear ciclo con BUY+SELL |
| cy02_tp_in_cycle | TP en ciclo | 🔴 CRÍTICA | TP hit, ciclo continúa |
| cy03_sl_triggers_recovery | SL activa Recovery | 🔴 CRÍTICA | SL cambia a RECOVERY |
| cy04_complete_10_tps | Completar 10 TPs | 🟡 ALTA | Ciclo exitoso completo |
| cy05_multiple_cycles | Múltiples ciclos | 🟡 ALTA | Pares independientes |

---

## HEDGED (5 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| 2.1_both_active_hedged | Ambas activas → HEDGED | 🔴 CRÍTICA | BUY y SELL activan |
| 2.2_sequential_activation | Activación secuencial | 🟡 ALTA | Una después de otra |
| 2.3_simultaneous_gap | Gap simultáneo | 🟡 ALTA | Gap activa ambas |
| 3.1_buy_tp_hedge_sell | BUY TP en HEDGED | 🔴 CRÍTICA | SELL se neutraliza |
| 3.2_sell_tp_hedge_buy | SELL TP en HEDGED | 🔴 CRÍTICA | BUY se neutraliza |

---

## RECOVERY (8 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| 5.1_recovery_n1_tp | Recovery N1 TP (BUY) | 🔴 CRÍTICA | N1 recupera pips |
| 5.2_recovery_n1_sell_tp | Recovery N1 TP (SELL) | 🟡 ALTA | N1 SELL recupera |
| 6.1_recovery_n1_fails | N1 falla → N2 | 🔴 CRÍTICA | Cascada de recovery |
| 6.2_recovery_n2_success | N2 éxito | 🟡 ALTA | N2 recupera todo |
| 7.1_cascade_n1_n2_n3 | Cascada N1→N2→N3 | 🟡 ALTA | Múltiples niveles |
| r05_recovery_max_n6 | N6 máximo | 🟡 ALTA | Nivel máximo alcanzado |
| r06_recovery_n6_fails | N6 falla → BLOCKED | 🟡 ALTA | Ciclo bloqueado |
| r07_multiple_recovery | Múltiples recovery | 🟢 MEDIA | Pares en recovery |

---

## FIFO (2 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| 8.1_fifo_multiple_close | FIFO múltiple cierre | 🔴 CRÍTICA | Cierra varias recovery |
| 8.2_fifo_partial | FIFO parcial | 🟡 ALTA | Cierre parcial |

---

## RISK MANAGEMENT (5 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| rm01_exposure_limit | Límite exposición | 🔴 CRÍTICA | Máx 5 ciclos |
| rm02_drawdown_limit | Límite drawdown | 🔴 CRÍTICA | Pausa > 20% |
| rm03_daily_loss_limit | Pérdida diaria | 🟡 ALTA | Pausa hasta mañana |
| rm04_margin_insufficient | Margen insuficiente | 🟡 ALTA | Operación rechazada |
| rm05_recovery_exposure | Exposición recovery | 🟡 ALTA | Incluye recovery |

---

## MONEY MANAGEMENT (10 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| mm01_balance_read | Balance inicial | 🔴 CRÍTICA | Lee balance broker |
| mm02_pnl_tp | P&L en TP | 🔴 CRÍTICA | +10 pips = $10 |
| mm03_pnl_loss | P&L bloqueado | 🔴 CRÍTICA | Pips en HEDGED |
| mm04_balance_update_tp | Balance tras TP | 🔴 CRÍTICA | balance += P&L |
| mm05_balance_update_sl | Balance tras SL | 🔴 CRÍTICA | balance -= P&L |
| mm06_equity_calculation | Cálculo equity | 🔴 CRÍTICA | Balance + Floating |
| mm07_margin_calculation | Cálculo margen | 🟡 ALTA | lot × contract / leverage |
| mm08_free_margin | Margen libre | 🟡 ALTA | equity - margin_used |
| mm09_lot_sizing | Lot sizing | 🟡 ALTA | % riesgo → lot |
| mm10_recovery_pnl_accumulation | P&L recovery | 🟡 ALTA | Suma total |

---

## EDGE CASES (10 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| 1.5_spread_rejection | Spread alto rechaza | 🟢 MEDIA | No abre con spread |
| 10.1_high_spread_rejection | Spread muy alto | 🟡 ALTA | Operaciones pausadas |
| 10.2_weekend_gap | Gap fin de semana | 🟡 ALTA | Manejo de gap |
| 10.3_mega_move | Movimiento extremo | 🟡 ALTA | >200 pips |
| 10.4_return_to_origin | Retorno al origen | 🟢 MEDIA | Precio vuelve |
| e01_lateral_market | Mercado lateral | 🟢 MEDIA | Múltiples TPs |
| e02_strong_trend | Tendencia fuerte | 🟢 MEDIA | Recovery cascada |
| e04_connection_lost | Conexión perdida | 🟢 MEDIA | Reconexión |
| e05_external_modification | Modificación externa | 🟢 MEDIA | Cierre manual |
| e06_rollover_swap | Rollover/Swap | ⚪ BAJA | Swap aplicado |

---

## MULTI-PAIR (4 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| mp01_dual_pair | Dual pair | 🟡 ALTA | EURUSD + GBPUSD |
| mp02_correlation_hedged | Correlación | 🟡 ALTA | Ambos en HEDGED |
| mp03_jpy_calculation | Cálculo JPY | 🟡 ALTA | 2 decimales |
| mp04_total_exposure | Exposición total | 🟡 ALTA | Suma de pares |

---

## JPY PAIRS (2 escenarios)

| ID | Nombre | Prioridad | Descripción |
|----|--------|-----------|-------------|
| 11.1_usdjpy_tp | USDJPY TP | 🟡 ALTA | Cálculo 2 decimales |
| 11.2_usdjpy_recovery | USDJPY Recovery | 🟡 ALTA | Recovery en JPY |

---

## Cobertura según testing.md

| Nivel | Requeridos | Implementados | Estado |
|-------|------------|---------------|--------|
| Core (C01-C05) | 5 | 7 | ✅ +2 |
| Ciclos (CY01-CY05) | 5 | 5 | ✅ |
| Recovery (R01-R07) | 7 | 8 | ✅ +1 |
| Risk (RM01-RM05) | 5 | 5 | ✅ |
| Edge (E01-E06) | 6 | 10 | ✅ +4 |
| Multi-Par (MP01-MP04) | 4 | 4 | ✅ |
| Money (MM01-MM10) | 10 | 10 | ✅ |
| **Extras** | - | 4 | HEDGED, FIFO, JPY |
| **TOTAL** | 42 | 58 | ✅ 138% |

---

## Estructura de Archivos

```
test_scenarios/
├── core/                    (7 archivos)
├── cycles/                  (5 archivos)
├── edge/                    (10 archivos)
├── fifo/                    (2 archivos)
├── hedged/                  (5 archivos)
├── jpy/                     (2 archivos)
├── money_management/        (10 archivos)
├── multi_pair/              (4 archivos)
├── recovery/                (8 archivos)
├── risk_management/         (5 archivos)
└── COMPLETE_INDEX.md        (este archivo)
```

---

## Uso

```bash
# Ejecutar todos los escenarios
cd wsplumber_audit
python3 unified_runner.py

# Ejecutar categoría específica
python3 -c "from unified_runner import run_category; run_category('core')"
```

---

*Generado: 2026-01-06*
*Versión: 2.0 (58 escenarios)*
