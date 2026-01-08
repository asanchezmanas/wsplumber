# Matriz de Validación - 62 Escenarios de Auditoría

> **Total:** 62 escenarios | **Críticos:** 25 | **Alta:** 32 | **Media:** 4 | **Baja:** 1

## Leyenda de Prioridades
- 🔴 **CRÍTICA**: Debe pasar siempre
- 🟡 **ALTA**: Comportamiento importante
- 🟢 **MEDIA**: Edge case, no bloqueante
- ⚪ **BAJA**: Nice-to-have

---

## CORE (5 escenarios)

### c01_tp_simple_buy 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY @ 1.10020, TP @ 1.10120, precio sube |
| **Output** | status=TP_HIT, profit=10 pips |
| **Checks** | ✓ `op.status == TP_HIT` ✓ `op.profit_pips == 10.0` |

### c01_tp_simple_sell 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | SELL @ 1.09980, TP @ 1.09880, precio baja |
| **Output** | status=TP_HIT, profit=10 pips |
| **Checks** | ✓ `op.status == TP_HIT` ✓ `op.profit_pips == 10.0` |

### c03_activation_no_tp 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY activa, precio oscila pero no alcanza TP |
| **Output** | status=ACTIVE, floating < 10 pips |
| **Checks** | ✓ `op.status == ACTIVE` ✓ TP no alcanzado |

### c04_no_activation 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Precio en rango 1.09990-1.10010, no cruza entries |
| **Output** | Ambas PENDING, balance sin cambios |
| **Checks** | ✓ `buy.status == PENDING` ✓ `sell.status == PENDING` ✓ `len(broker.order_history) == 0` |

### c05_gap_tp 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Gap 1.10050 → 1.10150 (salta TP @ 1.10120) |
| **Output** | Cierre @ 1.10150, profit ≥ 10 pips |
| **Checks** | ✓ `op.actual_close_price > op.tp_price` ✓ `metadata['gap_detected'] == True` |

---

## CYCLES (6 escenarios)

### cy01_new_cycle 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Crear ciclo nuevo |
| **Output** | 2 operaciones: BUY + SELL pendientes |
| **Checks** | ✓ `len(cycle.operations) == 2` ✓ Ambas PENDING |

### cy02_tp_in_cycle 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | TP hit en ciclo activo |
| **Output** | Ciclo continúa, contadores actualizados |
| **Checks** | ✓ `cycle.status == ACTIVE` ✓ `total_tps >= 1` |

### cy03_tp_renews_operations 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY TP hit |
| **Output** | 2 nuevas mains creadas (FIX-001) |
| **Checks** | ✓ Nuevas BUY + SELL PENDING ✓ Desde precio actual |

### cy04_cancel_counter_main 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY TP, SELL pendiente |
| **Output** | SELL CANCELLED |
| **Checks** | ✓ `sell.status == CANCELLED` ✓ `metadata['cancel_reason'] == "counterpart_tp_hit"` |

### cy05_complete_10_tps 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | 10 TPs alternados (5 BUY + 5 SELL) |
| **Output** | total_tps=10, total_pips=100 |
| **Checks** | ✓ `total_main_tps == 10` ✓ Nunca HEDGED |

### cy06_multiple_cycles 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | EURUSD + GBPUSD simultáneos |
| **Output** | 2 ciclos independientes |
| **Checks** | ✓ `len(cycles) == 2` ✓ Sin cross-contamination |

---

## HEDGED (8 escenarios)

### h01_both_active_hedged 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY @ 1.10020 activa, SELL @ 1.09980 activa |
| **Output** | status=HEDGED |
| **Checks** | ✓ `cycle.status == HEDGED` |

### h02_create_hedge_operations 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Estado HEDGED alcanzado |
| **Output** | HEDGE_BUY + HEDGE_SELL creados |
| **Checks** | ✓ 2 hedges PENDING ✓ Linked to mains |

### h03_neutralize_mains 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Hedges creados |
| **Output** | Mains = NEUTRALIZED |
| **Checks** | ✓ `main_buy.status == NEUTRALIZED` ✓ `main_sell.status == NEUTRALIZED` |

### h04_lock_20_pips 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Separation 4 + TP 10 + margin 6 |
| **Output** | pips_locked = 20 |
| **Checks** | ✓ `pips_locked == 20.0` |

### h05_sequential_activation 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY activa T1, SELL activa T2 (10s después) |
| **Output** | HEDGED, timestamps diferentes |
| **Checks** | ✓ `buy.activated_at < sell.activated_at` |

### h06_simultaneous_gap 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Gap 1.10000 → 1.10050 cruza ambas entries |
| **Output** | HEDGED inmediato, mismo timestamp |
| **Checks** | ✓ `buy.activated_at == sell.activated_at` ✓ `gap_detected == True` |

### h07_buy_tp_hedge_sell 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Main BUY TP en HEDGED |
| **Output** | HEDGE_SELL cancelled (FIX-002) |
| **Checks** | ✓ `hedge_sell.status == CANCELLED` ✓ `cancel_reason == "counterpart_main_tp_hit"` |

### h08_sell_tp_hedge_buy 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Main SELL TP en HEDGED |
| **Output** | HEDGE_BUY cancelled |
| **Checks** | ✓ `hedge_buy.status == CANCELLED` |

---

## RECOVERY (10 escenarios)

### r01_open_from_tp 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Main TP @ 1.10120 |
| **Output** | Recovery abre desde TP price |
| **Checks** | ✓ `metadata['reference_price'] == 1.10120` |

### r02_recovery_distance_20 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Main TP @ 1.10120 |
| **Output** | Recovery entry = TP ± 20 pips |
| **Checks** | ✓ `recovery_buy.entry == 1.10140` ✓ `recovery_sell.entry == 1.10100` |

### r03_recovery_n1_tp_buy 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Recovery N1 BUY @ 1.10140, TP @ 1.10220 |
| **Output** | TP_HIT, 80 pips, FIFO ejecutado |
| **Checks** | ✓ `profit_pips == 80.0` ✓ `pips_recovered == 20.0` |

### r04_recovery_n1_tp_sell 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Recovery N1 SELL @ 1.10100, TP @ 1.10020 |
| **Output** | TP_HIT, 80 pips |
| **Checks** | ✓ `profit_pips == 80.0` |

### r05_recovery_n1_fails_n2 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | N1 activo, precio +40 pips desde N1 |
| **Output** | N2 creado @ N1 + 40 pips |
| **Checks** | ✓ `recovery_level == 2` ✓ `len(queue) == 2` |

### r06_recovery_n2_success 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | N2 TP = 80 pips |
| **Output** | FIFO cierra N1 (40) + Main+Hedge (20) |
| **Checks** | ✓ `pips_recovered == 60.0` ✓ Net profit = 20 pips |

### r07_cascade_n1_n2_n3 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | N1 @ 1.10140, N2 @ 1.10180, N3 @ 1.10220, N3 TP |
| **Output** | FIFO cierra N2 + N1 |
| **Checks** | ✓ `pips_recovered == 80.0` |

### r08_recovery_max_n6 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | N1-N5 activos, distancia para N6 |
| **Output** | N6 creado, alerta WARNING |
| **Checks** | ✓ `recovery_level == 6` ✓ Alert created |

### r09_cancel_recovery_counter 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Recovery BUY TP |
| **Output** | Recovery SELL cancelled |
| **Checks** | ✓ `recovery_sell.status == CANCELLED` |

### r10_multiple_recovery_pairs 🟢
| Aspecto | Detalle |
|---------|---------|
| **Input** | EURUSD N1+N2, GBPUSD N1 |
| **Output** | Queues separadas |
| **Checks** | ✓ `eurusd.recovery_level == 2` ✓ `gbpusd.recovery_level == 1` |

---

## FIFO (4 escenarios)

### f01_fifo_first_costs_20 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Primer recovery TP |
| **Output** | Costo = 20 pips (Main + Hedge) |
| **Checks** | ✓ `get_recovery_cost() == 20.0` |

### f02_fifo_subsequent_40 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Segundo+ recovery TP |
| **Output** | Costo = 40 pips |
| **Checks** | ✓ `recoveries_closed_count >= 1` → `cost == 40.0` |

### f03_fifo_atomic_close 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Recovery TP disponible |
| **Output** | Main + Hedge cerrados atómicamente |
| **Checks** | ✓ `main.closed_at == hedge.closed_at` (±1ms) ✓ `debt_unit_id` compartido |

### f04_fifo_multiple_close 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Queue [20, 40], Recovery TP = 80 pips |
| **Output** | Ambas cerradas, profit = 20 |
| **Checks** | ✓ `pips_recovered == 60.0` ✓ `queue == []` |

---

## RISK MANAGEMENT (5 escenarios)

### rm01_exposure_limit 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Exposure >= 30% |
| **Output** | Nueva operación rechazada |
| **Checks** | ✓ `can_open == False` ✓ `error == "RISK_EXPOSURE_LIMIT"` |

### rm02_drawdown_limit 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Drawdown > 20% |
| **Output** | Sistema PAUSED |
| **Checks** | ✓ `system.status == PAUSED` ✓ Alert CRITICAL |

### rm03_daily_loss_limit 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Pérdida diaria >= 100 pips |
| **Output** | Pausa hasta mañana |
| **Checks** | ✓ `pause_reason == "daily_loss_limit"` |

### rm04_margin_insufficient 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Free margin < requerido |
| **Output** | Operación rechazada pre-broker |
| **Checks** | ✓ `error == "INSUFFICIENT_MARGIN"` |

### rm05_recovery_exposure 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Mains + recoveries activos |
| **Output** | Exposición incluye todos |
| **Checks** | ✓ `total_lots` incluye recoveries |

---

## MONEY MANAGEMENT (8 escenarios)

### mm01_balance_read 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Broker: balance=10000 |
| **Output** | Sistema inicializado correctamente |
| **Checks** | ✓ `account.balance == 10000.0` |

### mm02_pnl_tp 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | TP +10 pips, 0.01 lotes |
| **Output** | Gross +1.0 EUR, Net -13.0 EUR (comisiones) |
| **Checks** | ✓ `profit_pips == 10.0` ✓ `net_profit == -13.0` |

### mm03_pnl_hedged 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Estado HEDGED |
| **Output** | Floating neutralizado |
| **Checks** | ✓ `hedge + main ≈ 0` |

### mm04_balance_update_tp 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | TP + comisiones |
| **Output** | Balance = 9987.0 |
| **Checks** | ✓ `balance == 10000 - 13` |

### mm05_equity_calculation 🔴
| Aspecto | Detalle |
|---------|---------|
| **Input** | Balance + floating |
| **Output** | Equity = Balance + Floating |
| **Checks** | ✓ `equity == balance + floating_pnl` |

### mm06_margin_calculation 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | 0.01 lotes, leverage 1:100 |
| **Output** | Margin = 10 EUR |
| **Checks** | ✓ `margin == (lot × 100000) / 100` |

### mm07_free_margin 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Equity - Margin usado |
| **Output** | Free margin calculado |
| **Checks** | ✓ `free_margin == equity - margin` |

### mm08_recovery_pnl_accumulation 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | N1 TP (80-20=60), N2 TP (80-40=40) |
| **Output** | Total profit = 100 pips |
| **Checks** | ✓ FIFO aplicado correctamente |

---

## EDGE CASES (8 escenarios)

### e01_spread_rejection 🟢
| Aspecto | Detalle |
|---------|---------|
| **Input** | Spread > 3 pips |
| **Output** | Signal → NO_ACTION |
| **Checks** | ✓ `reason == "high_spread"` |

### e02_high_spread_rejection 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Spread > 5 pips (10 ticks) |
| **Output** | Trading pausado, se recupera |
| **Checks** | ✓ Durante: `can_trade == False` ✓ Después: `can_trade == True` |

### e03_weekend_gap 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Gap +200 pips fin de semana |
| **Output** | Detección, slippage registrado |
| **Checks** | ✓ `gap_size == 200.0` ✓ Activaciones en precio post-gap |

### e04_mega_move 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | +200 pips en 100 ticks |
| **Output** | Múltiples TPs, sistema estable |
| **Checks** | ✓ No crash ✓ `processing_time < 5s` |

### e05_return_to_origin 🟢
| Aspecto | Detalle |
|---------|---------|
| **Input** | 1.10000 → 1.10150 → 1.10000 |
| **Output** | TPs en ambas direcciones |
| **Checks** | ✓ `balance > initial_balance` |

### e06_lateral_market 🟢
| Aspecto | Detalle |
|---------|---------|
| **Input** | Rango 14 pips, 50 oscilaciones |
| **Output** | 20+ TPs, nunca HEDGED |
| **Checks** | ✓ `total_tps >= 20` ✓ `recovery_level == 0` |

### e07_connection_lost 🟢
| Aspecto | Detalle |
|---------|---------|
| **Input** | Desconexión 10s, TP durante |
| **Output** | Sync detecta TP |
| **Checks** | ✓ `sync_result.success == True` |

### e08_rollover_swap ⚪
| Aspecto | Detalle |
|---------|---------|
| **Input** | Posición abierta overnight |
| **Output** | Swap aplicado |
| **Checks** | ✓ `swap_total` incluido en P&L |

---

## MULTI-PAIR (4 escenarios)

### mp01_dual_pair 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | EURUSD + GBPUSD |
| **Output** | 2 ciclos, +20 EUR total |
| **Checks** | ✓ Sin cross-contamination |

### mp02_correlation_hedged 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Ambos pares HEDGED |
| **Output** | 40 pips locked total |
| **Checks** | ✓ Queues separadas |

### mp03_jpy_calculation 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | USDJPY, multiplicador ×100 |
| **Output** | Pips correctos |
| **Checks** | ✓ `(110.10 - 110.00) × 100 == 10` |

### mp04_total_exposure 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | 3 pares activos |
| **Output** | Exposición agregada |
| **Checks** | ✓ `total_lots == sum(all_pairs)` |

---

## JPY PAIRS (4 escenarios)

### j01_usdjpy_tp 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | USDJPY 110.00 → 110.10 |
| **Output** | profit = 10 pips |
| **Checks** | ✓ `profit_pips == 10.0` (no 1000) |

### j02_usdjpy_hedged 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | BUY @ 110.05, SELL @ 109.95 |
| **Output** | pips_locked = 20 |
| **Checks** | ✓ Multiplicador ×100 correcto |

### j03_usdjpy_recovery 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | Main TP @ 110.10 |
| **Output** | Recovery @ 110.30 (TP + 0.20) |
| **Checks** | ✓ `tp_price == 111.10` |

### j04_usdjpy_pips_calculation 🟡
| Aspecto | Detalle |
|---------|---------|
| **Input** | 110.00 → 110.50 |
| **Output** | 50 pips |
| **Checks** | ✓ `0.50 × 100 == 50` (no 5000) |

---

## Comandos de Ejecución

```bash
# Todos los tests
pytest tests/test_scenarios/ -v

# Por categoría
pytest tests/test_scenarios/ -k "CORE"
pytest tests/test_scenarios/ -k "RECOVERY"

# Por prioridad
pytest tests/test_scenarios/ -m critical
pytest tests/test_scenarios/ -m high

# Con cobertura
pytest tests/test_scenarios/ --cov=wsplumber
```

---

*Extraído de: conversation_scenarios_raw.md (2026-01-08)*
