# 🔧 WSPlumber - Referencia Rápida de Debugging

> **Propósito**: Documento conciso para consultar durante tests, revisión de logs y verificación de flujos.
> **Última actualización**: 2026-01-09

---

## 📐 Parámetros Críticos (Hardcoded)

| Parámetro | Valor | Uso |
|-----------|-------|-----|
| `MAIN_DISTANCE_PIPS` | **5** | Distancia de entrada de mains (BUY_STOP/SELL_STOP) |
| `MAIN_TP_PIPS` | **10** | Take Profit de operaciones principales |
| `RECOVERY_DISTANCE_PIPS` | **20** | Distancia de entrada del recovery |
| `RECOVERY_TP_PIPS` | **80** | Take Profit de operaciones recovery |
| `RECOVERY_LEVEL_STEP` | **40** | Separación entre niveles de recovery |
| `HEDGE_LOCK_PIPS` | **20** | Deuda bloqueada: 10 (distancia entre mains) + 10 (prolongación al TP) |

---

## 🔄 Máquina de Estados del Ciclo

```
PENDING ──► ACTIVE ──► HEDGED ──► IN_RECOVERY ──► CLOSED
   │           │          │            │
   │           ▼          │            │
   │      (TP simple)     │            │
   │           │          │            │
   └───────────┴──────────┴────────────┴──► CLOSED
```

### Estados y Transiciones

| Estado | Condición de Entrada | Qué Debe Pasar |
|--------|---------------------|----------------|
| `PENDING` | Ciclo recién creado | Órdenes pendientes en broker |
| `ACTIVE` | Al menos 1 orden ejecutada | Órdenes activas, monitoreando TP |
| `HEDGED` | Ambas mains activadas | Cobertura abierta, deuda = 20 pips |
| `IN_RECOVERY` | Main toca TP + hedge activo | Recovery abierto a ±20 pips |
| `CLOSED` | Todo resuelto (TP o FIFO) | Sin operaciones abiertas |

---

## 🎯 Flujos de Operación

### Flujo 1: Resolución Simple (Happy Path)
```
1. Abrir ciclo dual (BUY_STOP + SELL_STOP a ±5 pips)
2. UNA operación se activa
3. Esa operación toca TP (+10 pips de profit, a +15 pips del precio inicial)
4. Cancelar la orden pendiente opuesta
5. Ciclo → CLOSED
6. Abrir nuevo ciclo (renovación)
```
**Log esperado**: `[MAIN_TP_HIT] cycle_id=XXX profit_pips=10`

### Flujo 2: Ambas Activadas → Cobertura
```
1. Precio oscila, ambas mains se activan
2. Ciclo → HEDGED
3. Abrir órdenes HEDGE_BUY y HEDGE_SELL al nivel del TP opuesto
4. Registrar deuda: pips_locked = 20
5. Cuando UNA main toca TP:
   - La hedge correspondiente se activa (neutraliza)
   - Abrir ciclo RECOVERY a ±20 pips del precio actual
   - Ciclo → IN_RECOVERY
```
**Log esperado**: `[HEDGE_ACTIVATED] debt_locked=20 pips`

### Flujo 3: Recovery Exitoso
```
1. Recovery abierto (BUY_STOP + SELL_STOP a ±20 pips, TP=80)
2. Precio se mueve, recovery toca TP (+80 pips)
3. Sistema FIFO por UNIDADES:
   - Unidad Main+Hedge: 20 pips
   - Unidades Recovery Fallido: 40 pips cada una
4. Condición de cierre:
   - Deuda total == 0 AND Excedente >= 20 pips
5. Si OK: Cerrar ciclo completo
6. Si NO: Abrir nuevo recovery a ±20 pips del TP alcanzado
```
**Log esperado**: `[RECOVERY_TP_HIT] profit=80 debt_remaining=X`

### Flujo 4: Recovery en Cascada (Fallo)
```
1. Recovery N1 activado, precio se gira.
2. Segundo recovery de N1 se activa → Fallo bloqueado a 40 pips.
3. Deuda acumulada: 20 (Main+Hedge) + 40 (R1) = 60 pips.
4. Nuevo Recovery (N2) a ±20 pips del ENTRY de la orden que bloqueó.
5. Repetir (R3, R4...) hasta que un Recovery alcance TP.
```
**Log esperado**: `[RECOVERY_CASCADE] level=N debt_total=X`

---

## 📊 Contabilidad FIFO (First In, First Out)

### Costos por Tipo de Deuda

| Tipo | Costo | Cuándo |
|------|-------|--------|
| **Unidad Main+Hedge** | 20 pips | Al activar la primera cobertura |
| **Unidad Recovery** | 40 pips | Al activarse la orden opuesta del ciclo recovery |
| **Cierre Ciclo** | Surplus ≥ 20 | Solo si deuda es 0 y sobran pips |

### Ejemplo de Resolución

```
Estado: 4 recoveries neutralizados
Deuda total: 20 + 40 + 40 + 40 = 140 pips

Recovery 5 toca TP (+80 pips):
  - Cierra R1 (20 pips) → quedan 60 pips
  - Cierra R2 (40 pips) → quedan 20 pips
  - NO puede cerrar R3 (necesita 40)
  
Resultado: R3 y R4 siguen abiertos, deuda = 80 pips
Nuevo recovery se abre automáticamente.
```

---

## ⚠️ Límites de Emergencia

```python
EMERGENCY_LIMITS = {
    'max_daily_loss_pips': 100,      # Pausa automática
    'max_weekly_loss_pips': 300,     # Revisión obligatoria
    'max_concurrent_recovery': 20,   # No abrir más cycles
    'max_exposure_percent': 30       # Pausa nuevos mains
}
```

### Modos de Operación

| Modo | Margen Libre | Comportamiento |
|------|--------------|----------------|
| **NORMAL** | > 60% | Todo opera normalmente |
| **ALERTA** | 40-60% | Recoveries en cola, impuesto 10% |
| **SUPERVIVENCIA** | < 40% | Solo Mains, sin nuevos Recoveries |

---

## 🔍 Checklist de Debugging

### Al Abrir un Ciclo
- [ ] ¿Se crearon 2 operaciones (BUY_STOP + SELL_STOP)?
- [ ] ¿Los precios de entrada son ±5 pips del precio actual?
- [ ] ¿Los TP están a ±10 pips del ENTRY? (Resultando en ±15 pips desde el precio actual)
- [ ] ¿El estado del ciclo es `PENDING` → `ACTIVE`?
- [ ] ¿Los `broker_ticket` se guardaron en BD?

### Al Activar Cobertura
- [ ] ¿Ambas mains tienen `status = ACTIVE`?
- [ ] ¿Se crearon HEDGE_BUY y HEDGE_SELL?
- [ ] ¿El `pips_locked` del ciclo = 20?
- [ ] ¿El estado del ciclo cambió a `HEDGED`?

### Al Abrir Recovery
- [ ] ¿El recovery se abre a ±20 pips del precio actual?
- [ ] ¿El TP del recovery está a ±80 pips del ENTRY? (Resultando en ±100 pips desde el precio actual)
- [ ] ¿El `recovery_level` se incrementó?
- [ ] ¿La operación tiene `parent_cycle_id` correcto?

### Al Cerrar por TP
- [ ] ¿El `profit_pips` se registró correctamente?
- [ ] ¿Se ejecutó lógica FIFO para cerrar deudas?
- [ ] ¿Las operaciones cerradas tienen `closed_at`?
- [ ] ¿Se emitió señal de renovación (`OPEN_CYCLE`)?

---

## 📝 Logs Esperados por Evento

### Apertura de Ciclo (Ejemplo: Mid = 1.0850)
```
[INFO] Cycle created: cycle_id=EURUSD_001, type=MAIN
[INFO] Operation placed: op_id=EURUSD_001_BUY, entry=1.0855 (+5), tp=1.0865 (+15 from mid, +10 from entry)
[INFO] Operation placed: op_id=EURUSD_001_SELL, entry=1.0845 (-5), tp=1.0835 (-15 from mid, -10 from entry)
```

### Activación de Main
```
[INFO] Order filled: op_id=EURUSD_001_BUY, fill_price=1.0856, slippage=0.1 pips
[INFO] Cycle state: PENDING → ACTIVE
```

### Cobertura Activada
```
[WARNING] Both mains active, entering HEDGED state
[INFO] Hedge created: HEDGE_SELL at 1.0835 (TP of main_buy)
[INFO] Debt locked: 20 pips
```

### Recovery Abierto
```
[INFO] Main TP hit: +10 pips, opening recovery
[INFO] Recovery cycle created: REC_EURUSD_001_001, level=1
[INFO] Recovery operations: entry ±20 pips, TP=80 pips
```

### Recovery Exitoso
```
[INFO] Recovery TP hit: +80 pips
[INFO] FIFO processing: closing debt_id=EURUSD_001 (20 pips)
[INFO] Remaining pips: 60, debt remaining: 40
[INFO] FIFO processing: closing debt_id=REC_001 (40 pips)
[INFO] Remaining pips: 20 → PROFIT
[INFO] Cycle CLOSED with net profit: 20 pips
```

---

## 🧮 Fórmulas Rápidas

### Cálculo de Precio de Entrada
```python
# Main BUY
entry_buy = mid_price + (MAIN_DISTANCE_PIPS * pip_value)
tp_buy = entry_buy + (MAIN_TP_PIPS * pip_value)

# Main SELL
entry_sell = mid_price - (MAIN_DISTANCE_PIPS * pip_value)
tp_sell = entry_sell - (MAIN_TP_PIPS * pip_value)

# Valor de pip (estándar)
pip_value = 0.0001  # EURUSD, GBPUSD, etc.
pip_value = 0.01    # USDJPY, pares JPY
```

### Deuda Acumulada
```python
deuda_total = 20 + (40 * (num_recoveries - 1))
# Con 3 recoveries: 20 + 40 + 40 = 100 pips
```

### Tasa de Éxito Mínima
```python
breakeven_rate = 1/3  # 33.3%
# Por cada 2 recoveries fallidos, 1 exitoso compensa
```

---

## 🚨 Errores Comunes

| Síntoma | Causa Probable | Verificar |
|---------|---------------|-----------|
| Ciclo no pasa de PENDING | Órdenes no confirmadas por broker | `broker_ticket` en BD |
| Hedge no se activa | Una main no se activó | Status de ambas mains |
| Recovery no se abre | Main no tocó TP | `profit_pips` de la main |
| FIFO no cierra deudas | Pips insuficientes | Cálculo de deuda total |
| Renovación no ocurre | Señal OPEN_CYCLE no emitida | Logs del engine |

---

## 🔗 Archivos Clave para Debug

| Archivo | Propósito |
|---------|-----------|
| `src/wsplumber/core/strategy/_engine.py` | Lógica de decisión |
| `src/wsplumber/domain/entities/cycle.py` | Estados y transiciones |
| `src/wsplumber/domain/services/cycle_accounting.py` | Contabilidad FIFO |
| `src/wsplumber/application/services/trading_service.py` | Orquestación |
| `src/wsplumber/infrastructure/persistence/supabase_repo.py` | Persistencia |

---

## 📋 Queries SQL Útiles

### Ver ciclos activos
```sql
SELECT id, external_id, status, pips_locked, recovery_level 
FROM cycles 
WHERE status NOT IN ('closed') 
ORDER BY created_at DESC;
```

### Ver operaciones de un ciclo
```sql
SELECT op.external_id, op.op_type, op.status, op.entry_price, op.tp_price, op.profit_pips
FROM operations op
JOIN cycles c ON op.cycle_id = c.id
WHERE c.external_id = 'EURUSD_001'
ORDER BY op.created_at;
```

### Ver deuda total pendiente
```sql
SELECT pair, SUM(pips_locked) as total_debt
FROM cycles
WHERE status = 'in_recovery'
GROUP BY pair;
```

### Ver últimos errores
```sql
SELECT created_at, severity, component, error_message
FROM error_log
WHERE resolved = FALSE
ORDER BY created_at DESC
LIMIT 10;
```

---

---

## 🧪 Catálogo de Escenarios de Test

Los escenarios están organizados por categoría en `tests/scenarios/`:

### Core (C01-C05) - Operaciones Individuales
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `c01_tp_simple_buy.csv` | BUY alcanza TP | Entry → TP → CLOSED |
| `c01_tp_simple_sell.csv` | SELL alcanza TP | Entry → TP → CLOSED |
| `c03_activation_no_tp.csv` | Activación sin TP | PENDING → ACTIVE |
| `c04_no_activation.csv` | Precio no alcanza entry | Queda PENDING |
| `c05_gap_tp.csv` | Gap salta el TP | Cierre a mejor precio |

### Cycles (CY01-CY06) - Gestión de Ciclos
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `cy01_new_cycle.csv` | Crear ciclo | 2 ops creadas |
| `cy02_tp_in_cycle.csv` | TP dentro de ciclo | Una op cierra |
| `cy03_tp_renews_operations.csv` | Renovación tras TP | Nuevo ciclo se abre |
| `cy04_cancel_counter_main.csv` | Cancelar op contraria | SELL cancelada al TP del BUY |
| `cy05_complete_10_tps.csv` | 10 TPs consecutivos | Balance acumulado |

### Hedge (H01-H08) - Cobertura
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `h01_both_active_hedged.csv` | Ambas activadas | Estado → HEDGED |
| `h02_create_hedge_operations.csv` | Crear hedges | HEDGE_BUY/SELL creados |
| `h03_neutralize_mains.csv` | Neutralización | pips_locked = 20 |
| `h05_sequential_activation.csv` | Activación secuencial | BUY activa, luego SELL |
| `h07_buy_tp_hedge_sell.csv` | TP BUY activa hedge | Recovery se abre |

### Recovery (R01-R10) - Recuperación
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `r01_open_from_tp.csv` | Recovery tras TP | Recovery creado |
| `r02_recovery_distance_20.csv` | Distancia 20 pips | Entry correcto |
| `r03_recovery_n1_tp_buy.csv` | Recovery N1 TP | +80 pips |
| `r05_recovery_n1_fails_n2.csv` | Cascada N1→N2 | Level incrementa |
| `r07_cascade_n1_n2_n3.csv` | Triple cascada | 3 niveles |

### FIFO (F01-F04) - Contabilidad
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `f01_fifo_first_costs_20.csv` | Primer costo 20 | Cálculo correcto |
| `f02_fifo_subsequent_40.csv` | Siguientes 40 | Acumulación |
| `f03_fifo_atomic_close.csv` | Cierre atómico | Transacción completa |

### Risk Management (RM01-RM05)
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `rm01_exposure_limit.csv` | Límite exposición | Pausa nuevos ciclos |
| `rm02_drawdown_limit.csv` | Límite drawdown | Alerta activada |
| `rm03_daily_loss_limit.csv` | Pérdida diaria | Pausa automática |

### JPY Pairs (J01-J04)
| Archivo | Propósito | Qué Valida |
|---------|-----------|------------|
| `j01_usdjpy_tp.csv` | TP en par JPY | Cálculo pips (÷100) |
| `j04_usdjpy_pips_calculation.csv` | Fórmula JPY | pip_value = 0.01 |

---

## 🔬 Ejecutar Tests

```powershell
# Test mínimo
python tests/test_minimal_flow.py

# Todos los escenarios
python -m pytest tests/test_all_scenarios.py -v

# Escenario específico
python -m pytest tests/test_all_scenarios.py -k "c01_tp_simple_buy" -v

# Con logs detallados
python -m pytest tests/test_minimal_flow.py -v --tb=long -s
```

---

## 🔎 Interpretar Resultados de Test

### Output Exitoso
```
=== DESPUÉS DE TICK 1 ===
Cycles: 1              ✓ Ciclo creado
Operations: 2          ✓ BUY + SELL
Pending orders: 2      ✓ En broker

=== DESPUÉS DE TICK 2 ===
Balance: 1001.3        ✓ +10 pips (0.01 lot × $10 = $1)
History: 1             ✓ 1 op cerrada
BUY: status=TP_HIT     ✓ Target alcanzado
SELL: status=CANCELLED ✓ Contraria cancelada
```

### Señales de Problema
```
Cycles: 0              ✗ No se creó ciclo → revisar strategy
Operations: 0          ✗ No hay ops → revisar broker.place_order
Balance: 1000          ✗ Sin cambio → TP no procesado
History: 0             ✗ Nada cerrado → close_position no llamado
```

---

*Documento generado para debugging rápido. Para documentación completa ver `ws_plumber_system.md`*
