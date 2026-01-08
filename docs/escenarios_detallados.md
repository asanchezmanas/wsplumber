# Escenarios Detallados de Auditoría (E1-E10)

## ¿Por qué solo 10 escenarios detallados?

De los **62 escenarios totales**, solo **10 requieren documentación completa**. Los otros **52 son variaciones**:

| Tipo | Cantidad | Ejemplo |
|------|----------|---------|
| Espejos (BUY↔SELL) | 20 | c01_sell = espejo de c01_buy |
| Subsets de E1-E10 | 18 | cy04 = parte de E1 |
| Tests unitarios | 14 | mm06 = cálculo puro |

---

## Matriz de Cobertura

| Escenario | Core | Hedge | Recovery | FIFO | Gap | JPY | Multi |
|-----------|:----:|:-----:|:--------:|:----:|:---:|:---:|:-----:|
| **E1:** Ciclo Simple | ✅ TP, FIX-001 | - | - | - | - | - | - |
| **E2:** Hedge | - | ✅ HEDGED, FIX-002 | - | ✅ 20 pips | - | - | - |
| **E3:** Recovery N1 | - | - | ✅ Desde TP | ✅ Atómico, FIX-003 | - | - | - |
| **E4:** Multinivel | - | - | ✅ N1→N2→N3 | ✅ Costo 40 | - | - | - |
| **E5:** Gap TP | ✅ Slippage | - | - | - | ✅ | - | - |
| **E6:** Gap Hedge | - | ✅ Simultáneo | - | - | ✅ | - | - |
| **E7:** Recovery Falla | - | - | ✅ N1 no TP→N2 | - | - | - | - |
| **E8:** 10 TPs | ✅ Consistencia | - | - | - | - | - | - |
| **E9:** USDJPY | ✅ | ✅ | ✅ | ✅ | - | ✅ ×100 | - |
| **E10:** Multi-Pair | - | - | - | - | - | - | ✅ Exposición |

---

## Qué cubre cada escenario detallado

| E# | ¿Por qué es único? | Qué NO cubren los anteriores |
|----|-------------------|------------------------------|
| E5 | Gaps + slippage | E1 asume TP exacto |
| E6 | Gap + HEDGED simultáneo | E2 asume activación secuencial |
| E7 | Recovery que FALLA | E3/E4 asumen éxito |
| E8 | 10 TPs sin HEDGED | E1 solo muestra 1 TP |
| E9 | Par JPY (×100) | E1-E4 usan EURUSD (×10000) |
| E10 | Multi-pair + exposición | E1-E4 son single-pair |

---

## Los 52 restantes (en Matriz Compacta)

Ver [matriz_validacion.md](matriz_validacion.md) - cada uno referencia su escenario base E1-E10.

---

> [!NOTE]
> Los escenarios E1-E4 están documentados en [expted_behavior_specification_fixed.md](expted_behavior_specification_fixed.md).
> Este documento contiene los 6 escenarios adicionales (E5-E10).

---

## E5: Gap Atraviesa TP

### Referencia
- Documento madre: Líneas 301-315 (Manejo de gaps y slippage)

### Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  
market:
  pair: EURUSD
  friday_close: 1.10050
  monday_open: 1.10150  # Gap de +100 pips
  
cycle:
  status: ACTIVE
  
operations:
  - id: OP_BUY_001
    type: MAIN_BUY
    status: ACTIVE
    entry_price: 1.10020
    tp_price: 1.10120  # TP en medio del gap
```

### Secuencia de Pasos

**PASO 1:** Operación BUY activa (Viernes)
```
[14:00:00] OP_BUY_001 activated @ 1.10020, TP @ 1.10120
```

**PASO 2:** Mercado cierra (Viernes 22:00)
```
Last price: 1.10050 (50 pips por debajo del TP)
```

**PASO 3:** Gap en apertura (Lunes 00:01)
```
[00:01:00] GAP DETECTED: 1.10050 → 1.10150 (+100 pips)
           TP @ 1.10120 atravesado por gap
```

**PASO 4:** Broker ejecuta con slippage
```
Expected TP: 1.10120
Actual close: 1.10150
Slippage: +30 pips (favorable)
```

**PASO 5:** Calcular profit con slippage
```
Entry: 1.10020, Close: 1.10150
Profit: 13.0 pips (no 10.0)
```

**PASO 6:** Renovar desde precio post-gap
```
New BUY: entry=1.10170, tp=1.10270
New SELL: entry=1.10150, tp=1.10050
```

### Estado Final
```yaml
operations:
  - id: OP_BUY_001
    status: TP_HIT
    actual_close_price: 1.10150
    profit_pips: 13.0
    metadata:
      gap_execution: true
      slippage_pips: 3.0
      
  - id: OP_BUY_002
    status: PENDING
    entry_price: 1.10170  # Post-gap
```

### Checks Críticos
- [ ] `tick.metadata['gap_detected'] == True`
- [ ] `op_buy.slippage_pips == 3.0` (favorable)
- [ ] `op_buy.profit_pips == 13.0` (no 10.0)
- [ ] Nuevas operaciones desde precio post-gap

---

## E6: Gap Simultáneo Activa Ambas Mains (HEDGED con Gap)

### Referencia
- Documento madre: Líneas 124-133 (Cobertura), 301-315 (Gaps)

### Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  
market:
  pair: EURUSD
  friday_close: 1.10000
  monday_open: 1.10050  # Gap +50 pips
  
operations:
  - id: OP_BUY_001
    status: PENDING
    entry_price: 1.10020  # Cruzado por gap
    
  - id: OP_SELL_001
    status: PENDING
    entry_price: 1.09980  # También cruzado
```

### Secuencia de Pasos

**PASO 1:** Gap atraviesa ambas entries
```
Gap 1.10000 → 1.10050
BUY entry @ 1.10020: CROSSED (+30 pips above)
SELL entry @ 1.09980: CROSSED (+70 pips above)
```

**PASO 2:** Ambas ejecutadas simultáneamente
```
BUY filled @ 1.10050 (slippage +30 pips)
SELL filled @ 1.10050 (slippage +70 pips)
Timestamps IGUALES
```

**PASO 3:** Sistema detecta → HEDGED
```
BOTH MAINS ACTIVE → HEDGE
Simultaneous activation: true
```

**PASO 4:** Calcular pips locked con gap adjustment
```
Base cost: 20 pips (separation + TP + margin)
Gap adjustment: +100 pips (slippages)
TOTAL: 120 pips locked
```

### Estado Final
```yaml
cycle:
  status: HEDGED
  pips_locked: 120.0  # 20 base + 100 gap
  
operations:
  - id: OP_BUY_001
    status: NEUTRALIZED
    actual_entry_price: 1.10050
    slippage_pips: 30.0
    
  - id: OP_SELL_001
    status: NEUTRALIZED
    actual_entry_price: 1.10050
    slippage_pips: 70.0
    activated_at: SAME_TIMESTAMP
```

### Checks Críticos
- [ ] `op_buy.activated_at == op_sell.activated_at`
- [ ] `cycle.accounting.pips_locked == 120.0`
- [ ] `metadata['gap_adjustment'] == 100.0`
- [ ] Alerta CRITICAL creada

---

## E7: Recovery Falla N1 → Activa N2

### Referencia
- Documento madre: Líneas 156-166 (FIFO), 178-189 (Cascada)

### Condiciones Iniciales
```yaml
parent_cycle:
  status: IN_RECOVERY
  pips_locked: 20.0
  recovery_level: 1
  recovery_queue: ["MAIN_SELL_debt_unit"]
  
operations:
  - id: REC_N1_BUY
    status: ACTIVE
    entry_price: 1.10140
    tp_price: 1.10220  # +80 pips
```

### Secuencia de Pasos

**PASO 1:** N1 activo, precio sube pero no alcanza TP
```
N1 @ 1.10140, TP @ 1.10220
Precio actual: 1.10170 (+30 pips floating)
Distance to TP: 50 pips (insuficiente)
```

**PASO 2:** Precio continúa adverso, 40 pips desde N1
```
Price @ 1.10180 (40 pips desde N1 entry)
THRESHOLD MET: Activate N2
```

**PASO 3:** Crear Recovery N2
```
N2 BUY: entry=1.10180 (N1 + 40 pips)
N2 SELL: entry=1.10100 (N1 - 40 pips)
N2 TP: +80 pips desde entry
```

**PASO 4:** Actualizar queue
```
Queue before: [Main+Hedge debt]
Queue after: [Main+Hedge debt, N1 debt]
Total debt: 60 pips (20 + 40)
```

**PASO 5:** N2 activa
```
N1 BUY: ACTIVE @ 1.10140
N2 BUY: ACTIVE @ 1.10180
2 recovery levels active simultaneously
```

### Estado Final
```yaml
parent_cycle:
  recovery_level: 2
  
  accounting:
    recovery_queue:
      - "MAIN_SELL_debt_unit"  # 20 pips
      - "REC_N1_debt_unit"      # 40 pips
    total_debt_cost: 60.0
    
operations:
  - id: REC_N1_BUY
    status: ACTIVE
    metadata:
      failed_to_reach_tp: true
      triggered_next_level: true
      
  - id: REC_N2_BUY
    status: ACTIVE
    entry_price: 1.10180
```

### Checks Críticos
- [ ] `rec_n1.metadata['failed_to_reach_tp'] == True`
- [ ] `parent_cycle.recovery_level == 2`
- [ ] `len(recovery_queue) == 2`
- [ ] Total debt: 60 pips (20 + 40)
- [ ] N2 TP (80) > Total debt (60) ✓

---

## E8: Ciclo Completa 10 TPs Sin Hedge

### Referencia
- Documento madre: Líneas 45-52 (Main TP), 115 (Renovación)

### Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  
cycle:
  id: CYC_MARATHON_001
  status: PENDING
  total_tps: 0
```

### Secuencia de Pasos

**Iteraciones 1-10:** (patrón alternado BUY/SELL)

| # | Dirección | Pips | Balance Δ | Commissions |
|---|-----------|------|-----------|-------------|
| 1 | BUY | +10 | -13 EUR | 14 EUR |
| 2 | SELL | +10 | -13 EUR | 14 EUR |
| 3 | BUY | +10 | -13 EUR | 14 EUR |
| 4 | SELL | +10 | -13 EUR | 14 EUR |
| 5 | BUY | +10 | -13 EUR | 14 EUR |
| 6 | SELL | +10 | -13 EUR | 14 EUR |
| 7 | BUY | +10 | -13 EUR | 14 EUR |
| 8 | SELL | +10 | -13 EUR | 14 EUR |
| 9 | BUY | +10 | -13 EUR | 14 EUR |
| 10 | SELL | +10 | -13 EUR | 14 EUR |

**Cada iteración:** TP → Cancelar counter → Renovar BUY+SELL (FIX-001)

### Estado Final
```yaml
cycle:
  status: ACTIVE  # Nunca entró en HEDGED
  
  accounting:
    total_main_tps: 10
    total_pips_won: 100.0
    pips_locked: 0.0
    total_commissions: 140.00 EUR
    net_profit: -130.00 EUR
    
  metadata:
    never_hedged: true
    never_recovery: true
    fix_001_compliance: "100%"
    
account:
  balance: 9870.00  # 10000 - 130
```

### Checks Críticos
- [ ] `cycle.status == ACTIVE` (nunca HEDGED)
- [ ] `total_main_tps == 10`
- [ ] `pips_locked == 0.0`
- [ ] Cada TP: 2 nuevas ops (BUY+SELL) - FIX-001
- [ ] Balance: 9870.00 EUR

---

## E9: USDJPY - Par JPY Flujo Completo

### Referencia
- Documento madre: Líneas 265-280 (Pares JPY, multiplicador ×100)

### Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  
market:
  pair: USDJPY
  start_price: 110.00  # 2 decimales
  
notes:
  - "JPY: 2 decimales (110.00)"
  - "Multiplicador: ×100 (no ×10000)"
  - "1 pip = 0.01"
  - "TP 10 pips = 0.10 en precio"
```

### Secuencia de Pasos

**PASO 1:** Apertura ciclo USDJPY
```
BUY entry: 110.05, TP: 110.15 (+0.10 = 10 pips)
SELL entry: 109.95, TP: 109.85 (-0.10 = 10 pips)
```

**PASO 2:** Ambas activan → HEDGED
```
BUY @ 110.05, SELL @ 109.95
Separation: 0.10 × 100 = 10 pips ✓
```

**PASO 3:** Pips locked (JPY)
```
Separation: (110.05 - 109.95) × 100 = 10 pips
Total: 20 pips locked (igual que EURUSD)
```

**PASO 4:** BUY TP
```
Close: 110.15
Profit: (110.15 - 110.05) × 100 = 10 pips ✓
(NO: 0.10 × 10000 = 1000 pips ✗)
```

**PASO 5:** Recovery (JPY)
```
Distance: 20 pips = 0.20 en precio
Recovery BUY: 110.15 + 0.20 = 110.35
Recovery TP: 110.35 + 0.80 = 111.15 (+80 pips)
```

### Estado Final
```yaml
cycle:
  pair: USDJPY
  status: ACTIVE
  
  accounting:
    pips_locked: 20.0  # Mismo cálculo, diferente mult.
    
recovery:
  entry_price: 110.35
  tp_price: 111.15
  profit_pips: 80.0  # (111.15-110.35) × 100
```

### Checks Críticos
- [ ] Multiplicador: ×100 (no ×10000)
- [ ] `pips_locked == 20.0` (correcto)
- [ ] TP profit: 10 pips (no 1000)
- [ ] Recovery profit: 80 pips (no 8000)

---

## E10: Múltiples Pares Simultáneos + Exposición Total

### Referencia
- Documento madre: Multi-pair, cálculo de exposición agregada

### Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  equity: 10000.0
  
cycles:
  - pair: EURUSD
    operations: 3 × 0.01 lotes
    
  - pair: GBPUSD
    operations: 2 × 0.01 lotes
    
  - pair: USDJPY
    operations: 1 × 0.01 lotes
```

### Secuencia de Pasos

**PASO 1:** Calcular exposición por par
```
EURUSD: 0.03 lotes → 300 EUR margin
GBPUSD: 0.02 lotes → 200 EUR margin
USDJPY: 0.01 lotes → 100 EUR margin
```

**PASO 2:** Exposición total
```
Total lots: 0.06
Total margin: 600 EUR
Exposure: 600/10000 = 6%
```

**PASO 3:** Verificar independencia
```
EURUSD TP → No afecta GBPUSD
GBPUSD HEDGED → No afecta USDJPY
Sin cross-contamination
```

### Estado Final
```yaml
total_exposure:
  lots: 0.06
  margin: 600.0
  percentage: 6.0%
  
cycles:
  - pair: EURUSD
    status: ACTIVE
    ops: 3
    
  - pair: GBPUSD
    status: HEDGED
    ops: 4
    
  - pair: USDJPY
    status: ACTIVE
    ops: 1
```

### Checks Críticos
- [ ] `total_lots == 0.06`
- [ ] `exposure_pct == 6.0`
- [ ] `exposure_pct < 30.0` (límite)
- [ ] Ciclos aislados (sin interferencia)
- [ ] Balance compartido correctamente

---

## Matriz de Cobertura

| Escenario | Core | Hedge | Recovery | FIFO | Gap | JPY | Multi |
|-----------|------|-------|----------|------|-----|-----|-------|
| E1 | ✅ | - | - | - | - | - | - |
| E2 | - | ✅ | - | - | - | - | - |
| E3 | - | ✅ | ✅ | ✅ | - | - | - |
| E4 | - | - | ✅ | ✅ | - | - | - |
| **E5** | ✅ | - | - | - | ✅ | - | - |
| **E6** | - | ✅ | - | - | ✅ | - | - |
| **E7** | - | - | ✅ | - | - | - | - |
| **E8** | ✅ | - | - | - | - | - | - |
| **E9** | ✅ | ✅ | ✅ | ✅ | - | ✅ | - |
| **E10** | - | - | - | - | - | - | ✅ |

---

*Extraído de: conversation.md (2026-01-08)*
