# Especificación de Comportamiento Esperado - VERSIÓN CORREGIDA

## Propósito

Este documento define **QUÉ DEBERÍA PASAR** según la teoría del documento madre.
Cada escenario incluye:
- **PASOS EXACTOS** que debe ejecutar el sistema
- **LOGS** que deben aparecer
- **CHECKS** que deben validarse
- **ESTADO FINAL** esperado

**VERSIÓN**: 2.0 - Corregida según bugs identificados

---

## Convenciones de Logs

```
[TIMESTAMP] [NIVEL] [COMPONENTE] Mensaje
```

Niveles:
- `INFO`: Operación normal
- `DEBUG`: Detalle para desarrollo
- `WARN`: Algo inusual pero manejable
- `ERROR`: Problema que requiere atención
- `CRITICAL`: Requiere acción inmediata

---

# ESCENARIO 1: Ciclo Simple Exitoso (Happy Path) - CORREGIDO

## Referencia Documento Madre
- Líneas 45-52: Operación Main con TP 10 pips
- Línea 115: "Cuando un ciclo principal toca TP, inmediatamente se abre otro nuevo"
- Sección "Resolución Simple"

## Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  equity: 10000.0
  margin_free: 10000.0
  
market:
  pair: EURUSD
  bid: 1.10000
  ask: 1.10020
  spread: 2 pips
  
system:
  active_cycles: 0
  pips_locked: 0
  recovery_active: 0
```

## Secuencia de Pasos

### PASO 1-6: Sin cambios (igual que versión anterior)
[Ver pasos 1-6 del documento original]

---

### PASO 7: Actualizar Contabilidad y Renovar Operaciones Main (FIX-001) ✅
**Trigger:** TP alcanzado, ciclo continúa

**⚠️ CAMBIO CRÍTICO:** Se crean **DOS nuevas operaciones** (BUY + SELL), no solo una.

```
[10:00:30.060] [INFO] [AccountingService] Balance actualizado: 10000 → 10002
[10:00:30.061] [DEBUG] [CycleOrchestrator] Ciclo CYC_001: TPs=1, pips_ganados=10
[10:00:30.062] [INFO] [CycleOrchestrator] *** RENOVANDO OPERACIONES MAIN (BUY + SELL) ***
[10:00:30.063] [DEBUG] [CycleOrchestrator] Precio actual: bid=1.10120, ask=1.10140
[10:00:30.064] [DEBUG] [LotCalculator] Manteniendo lote: 0.02
[10:00:30.065] [INFO] [BrokerAdapter] Enviando BUY_STOP: entry=1.10140, tp=1.10240, sl=1.09640
[10:00:30.066] [INFO] [BrokerAdapter] Enviando SELL_STOP: entry=1.10120, tp=1.10020, sl=1.10620
[10:00:30.150] [INFO] [BrokerAdapter] BUY_STOP confirmado: ticket=12347
[10:00:30.151] [INFO] [BrokerAdapter] SELL_STOP confirmado: ticket=12348
[10:00:30.152] [INFO] [CycleOrchestrator] Operaciones main renovadas exitosamente
[10:00:30.153] [DEBUG] [CycleOrchestrator] Nueva BUY: OP_003, Nueva SELL: OP_004
```

**Checks:**
- [ ] `account.balance == 10002.00`
- [ ] `cycle.accounting.total_tp_count == 1`
- [ ] `cycle.accounting.total_pips_won == 10.0`
- [ ] `len([op for op in cycle.operations if op.is_main and op.status == PENDING]) == 2`
- [ ] Nueva operación BUY: `id=OP_003, entry=1.10140, tp=1.10240, status=PENDING`
- [ ] Nueva operación SELL: `id=OP_004, entry=1.10120, tp=1.10020, status=PENDING`
- [ ] `cycle.status == CycleStatus.ACTIVE` (sin cambio)

**DB Inserts:**
```sql
INSERT INTO operations (id, cycle_id, type, direction, status, entry_price, tp_price, broker_ticket)
VALUES 
  ('OP_003', 'CYC_001', 'MAIN', 'BUY', 'PENDING', 1.10140, 1.10240, '12347'),
  ('OP_004', 'CYC_001', 'MAIN', 'SELL', 'PENDING', 1.10120, 1.10020, '12348');
```

**Justificación:**
El documento madre establece que el ciclo opera indefinidamente con cobertura 
bidireccional. Al cerrar un main con TP, se renuevan AMBAS operaciones (BUY+SELL)
para mantener la estrategia activa.

---

### ESTADO FINAL ESPERADO (CORREGIDO)

```yaml
cycle:
  id: CYC_001
  status: ACTIVE  # Continúa operando
  total_tps: 1
  pips_won: 10
  operations_count: 4  # 2 cerradas/canceladas + 2 nuevas pendientes
  
operations:
  # === ITERACIÓN 1 (Cerrada) ===
  - id: OP_001
    type: MAIN
    direction: SELL
    status: CANCELLED
    profit_pips: 0
    cancel_reason: "counterpart_tp_hit"
    
  - id: OP_002
    type: MAIN
    direction: BUY
    status: TP_HIT
    profit_pips: 10
    profit_money: 2.00
    
  # === ITERACIÓN 2 (Activa) ===
  - id: OP_003  # ✅ Nueva BUY
    type: MAIN
    direction: BUY
    status: PENDING
    entry_price: 1.10140
    tp_price: 1.10240
    
  - id: OP_004  # ✅ Nueva SELL
    type: MAIN
    direction: SELL  
    status: PENDING
    entry_price: 1.10120
    tp_price: 1.10020
    
account:
  balance: 10002.00  # +2 EUR del TP
  equity: 10002.00
  
system:
  pips_locked: 0
  recovery_active: 0
  cycles_active: 1
```

---

# ESCENARIO 2: Ambas Mains Se Activan (Hedge) - CORREGIDO

## Referencia Documento Madre
- Líneas 124-133: Cobertura cuando ambas se activan
- Sección "Ambas operaciones se activan"

## Condiciones Iniciales
```yaml
account:
  balance: 10000.0
  
market:
  pair: EURUSD
  initial_bid: 1.10000
  initial_ask: 1.10020
  
cycle:
  id: CYC_002
  status: ACTIVE
  main_buy:
    id: OP_010
    entry: 1.10020
    tp: 1.10120
    status: PENDING
  main_sell:
    id: OP_011
    entry: 1.09980
    tp: 1.09880
    status: PENDING
```

## Secuencia de Pasos

### PASO 1-4: Sin cambios
[Ver pasos 1-4 del documento original]

---

### PASO 5: BUY Main Alcanza TP
**Trigger:** `bid >= 1.10120`

```
[10:05:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10125, ask=1.10145
[10:05:00.001] [INFO] [BrokerAdapter] TP alcanzado: ticket=20001
[10:05:00.002] [INFO] [CycleOrchestrator] OP_010 (MAIN_BUY) cerrada con TP: +10 pips
[10:05:00.003] [DEBUG] [CycleOrchestrator] OP_010: ACTIVE → TP_HIT
```

**Checks:**
- [ ] `main_buy.status == TP_HIT`
- [ ] `main_buy.profit_pips == 10`

---

### PASO 5.5: Cancelar Hedge Pendiente Contrario (FIX-002) ⚠️ NUEVO PASO
**Trigger:** Main cerró con TP → cancelar hedge pendiente opuesto

```
[10:05:00.010] [INFO] [CycleOrchestrator] Main TP detectado, verificando hedges pendientes
[10:05:00.011] [DEBUG] [CycleOrchestrator] Buscando hedge pendiente contrario a OP_010 (BUY)...
[10:05:00.012] [INFO] [CycleOrchestrator] Encontrado: OP_013 (HEDGE_SELL) - PENDING
[10:05:00.013] [INFO] [BrokerAdapter] Cancelando orden: ticket=20004
[10:05:00.050] [INFO] [BrokerAdapter] Orden cancelada exitosamente: ticket=20004
[10:05:00.051] [INFO] [CycleOrchestrator] OP_013 cancelado
[10:05:00.052] [DEBUG] [CycleOrchestrator] OP_013: PENDING → CANCELLED
[10:05:00.053] [DEBUG] [CycleOrchestrator] Metadata: cancel_reason="counterpart_main_tp_hit"
```

**Checks:**
- [ ] `hedge_sell.status == OperationStatus.CANCELLED`
- [ ] `hedge_sell.cancelled_at != None`
- [ ] Orden 20004 NO existe en broker
- [ ] `hedge_sell.metadata["cancel_reason"] == "counterpart_main_tp_hit"`

**DB Update:**
```sql
UPDATE operations 
SET status = 'CANCELLED', 
    cancelled_at = '2025-01-05 10:05:00.050',
    metadata = jsonb_set(metadata, '{cancel_reason}', '"counterpart_main_tp_hit"')
WHERE id = 'OP_013';
```

**Justificación:**
Sin este paso, el HEDGE_SELL pendiente podría activarse después del cierre del 
MAIN_BUY, creando posiciones huérfanas sin propósito.

---

### PASO 6: Neutralizar SELL Main + Activar HEDGE_BUY
**Trigger:** Main contraria (SELL) debe neutralizarse

```
[10:05:00.060] [INFO] [CycleOrchestrator] Neutralizando MAIN_SELL (OP_011)
[10:05:00.061] [DEBUG] [CycleOrchestrator] SELL entry=1.09980, precio_actual=1.10125
[10:05:00.062] [DEBUG] [PnLCalculator] Pérdida flotante SELL: (1.09980-1.10125)/0.0001 = -14.5 pips
[10:05:00.063] [INFO] [CycleOrchestrator] OP_011: ACTIVE → NEUTRALIZED
[10:05:00.064] [INFO] [CycleOrchestrator] Activando HEDGE_BUY (OP_012) para cubrir pérdida
```

**Checks:**
- [ ] `main_sell.status == NEUTRALIZED`
- [ ] `main_sell.neutralized_at != None`
- [ ] `main_sell.neutralized_by == "OP_012"`
- [ ] `main_sell.floating_pips < 0` (en pérdida)
- [ ] `hedge_buy.status == PENDING` (esperando activación)

---

### PASO 7: Actualizar Contabilidad y Preparar Recoveries (ACTUALIZADO)
**Trigger:** Neutralización completada

```
[10:05:00.070] [INFO] [AccountingService] Calculando deuda total del ciclo
[10:05:00.071] [DEBUG] [AccountingService] === COMPOSICIÓN DE LA DEUDA ===
[10:05:00.072] [DEBUG] [AccountingService] Main SELL: entry=1.09980
[10:05:00.073] [DEBUG] [AccountingService] Main BUY: entry=1.10020
[10:05:00.074] [DEBUG] [AccountingService] Separación inicial: 4 pips
[10:05:00.075] [DEBUG] [AccountingService] TP alcanzado por BUY: 10 pips (hasta 1.10120)
[10:05:00.076] [DEBUG] [AccountingService] Margen de seguridad: 6 pips
[10:05:00.077] [DEBUG] [AccountingService] TOTAL: 4 + 10 + 6 = 20 pips
[10:05:00.078] [INFO] [AccountingService] Ciclo CYC_002: pips_locked = 20
[10:05:00.079] [INFO] [CycleOrchestrator] Ciclo CYC_002: HEDGED → IN_RECOVERY
[10:05:00.080] [INFO] [CycleOrchestrator] Preparando recoveries desde precio TP: 1.10120
[10:05:00.081] [DEBUG] [CycleOrchestrator] Recovery BUY entry: 1.10140 (TP + 20 pips)
[10:05:00.082] [DEBUG] [CycleOrchestrator] Recovery SELL entry: 1.10100 (TP - 20 pips)
```

**Checks:**
- [ ] `cycle.accounting.pips_locked == 20`
- [ ] `cycle.status == CycleStatus.IN_RECOVERY`
- [ ] `cycle.recovery_queue == ["OP_011_debt_unit"]`
- [ ] Recoveries colocados **desde TP del Main**, no desde precio actual
- [ ] Metadata incluye `debt_composition`

**Debt Unit Structure:**
```json
{
  "id": "OP_011_debt_unit",
  "main_id": "OP_011",
  "hedge_id": "OP_012",
  "cost_pips": 20,
  "components": {
    "separation": 4,
    "tp_distance": 10,
    "margin": 6
  }
}
```

---

### ESTADO FINAL ESPERADO (CORREGIDO)

```yaml
cycle:
  id: CYC_002
  status: IN_RECOVERY
  pips_locked: 20
  recovery_queue: ["OP_011_debt_unit"]  # Unidad: Main + Hedge
  
operations:
  # === MAIN OPERATIONS ===
  - id: OP_010
    type: MAIN
    direction: BUY
    status: TP_HIT
    profit_pips: 10
    
  - id: OP_011
    type: MAIN
    direction: SELL
    status: NEUTRALIZED
    neutralized_by: OP_012
    entry_price: 1.09980
    neutralized_at_price: 1.10120
    debt_pips: 14  # Flotante cuando se neutralizó
    
  # === HEDGE OPERATIONS ===
  - id: OP_012
    type: HEDGE
    direction: BUY
    status: ACTIVE  # ✅ Cubriendo OP_011
    entry_price: 1.10020
    tp_price: 1.10120
    covering_operation: OP_011
    
  - id: OP_013
    type: HEDGE
    direction: SELL
    status: CANCELLED  # ✅ FIX-002: Cancelado cuando Main BUY tocó TP
    cancel_reason: "counterpart_main_tp_hit"
    cancelled_at: "2025-01-05 10:05:00.050"
    
  # === RECOVERY OPERATIONS (Desde TP = 1.10120) ===
  - id: OP_014
    type: RECOVERY
    level: 1
    direction: BUY
    status: PENDING
    entry_price: 1.10140  # ✅ TP + 20 pips
    tp_price: 1.10220     # entry + 80 pips
    
  - id: OP_015
    type: RECOVERY
    level: 1
    direction: SELL
    status: PENDING
    entry_price: 1.10100  # ✅ TP - 20 pips
    tp_price: 1.10020     # entry - 80 pips
    
account:
  balance: 10002.00  # +2 del TP del BUY
  pips_locked_total: 20
  
metadata:
  debt_composition:
    main_separation: 4      # Separación inicial entre mains
    tp_distance: 10          # TP alcanzado
    margin: 6                # Margen de seguridad
    total: 20
  recovery_placement:
    reference_price: 1.10120  # TP del Main BUY
    distance: 20              # Pips desde referencia
```

---

# ESCENARIO 3: Recovery Nivel 1 Exitoso - CORREGIDO

## Referencia Documento Madre
- Líneas 86-104: Sistema FIFO, costo de 20 pips primer recovery
- Sección "Recovery exitoso"

## Condiciones Iniciales
```yaml
cycle:
  id: CYC_003
  status: IN_RECOVERY
  pips_locked: 20
  recovery_queue: ["OP_020_debt_unit"]  # Incluye Main + Hedge
  
account:
  balance: 10000.0
  
operations_existing:
  - OP_020: Main SELL neutralizada
  - OP_021: Hedge BUY cubriendo OP_020
```

## Secuencia de Pasos

### PASO 1-3: Sin cambios
[Ver pasos 1-3 del documento original]

---

### PASO 4: Procesar Cierre FIFO (FIX-003 - VERSIÓN DETALLADA) ✅
**Trigger:** Recovery TP alcanzado → cerrar según FIFO

```
[10:30:00.010] [INFO] [FIFOProcessor] Procesando TP de 80 pips según FIFO
[10:30:00.011] [DEBUG] [FIFOProcessor] ═══════════════════════════════════════
[10:30:00.012] [DEBUG] [FIFOProcessor] ESTADO DE LA COLA FIFO
[10:30:00.013] [DEBUG] [FIFOProcessor] ═══════════════════════════════════════
[10:30:00.014] [DEBUG] [FIFOProcessor] Queue: ["OP_020_debt_unit"]
[10:30:00.015] [DEBUG] [FIFOProcessor] 
[10:30:00.016] [DEBUG] [FIFOProcessor] === UNIDAD DE DEUDA: OP_020_debt_unit ===
[10:30:00.017] [DEBUG] [FIFOProcessor] Composición:
[10:30:00.018] [DEBUG] [FIFOProcessor]   • Main SELL neutralizada (OP_020)
[10:30:00.019] [DEBUG] [FIFOProcessor]     - Entry: 1.09980
[10:30:00.020] [DEBUG] [FIFOProcessor]     - Status: NEUTRALIZED
[10:30:00.021] [DEBUG] [FIFOProcessor]   • Hedge BUY cubriendo (OP_021)
[10:30:00.022] [DEBUG] [FIFOProcessor]     - Entry: 1.10020
[10:30:00.023] [DEBUG] [FIFOProcessor]     - Status: ACTIVE
[10:30:00.024] [DEBUG] [FIFOProcessor]   • Componentes de costo:
[10:30:00.025] [DEBUG] [FIFOProcessor]     - Separación inicial: 4 pips
[10:30:00.026] [DEBUG] [FIFOProcessor]     - TP alcanzado: 10 pips
[10:30:00.027] [DEBUG] [FIFOProcessor]     - Margen: 6 pips
[10:30:00.028] [DEBUG] [FIFOProcessor]   COSTO TOTAL: 20 pips (primer recovery)
[10:30:00.029] [DEBUG] [FIFOProcessor] 
[10:30:00.030] [INFO] [FIFOProcessor] Calculando distribución de pips...
[10:30:00.031] [DEBUG] [FIFOProcessor] 80 pips disponibles - 20 pips costo = 60 pips excedente
[10:30:00.032] [INFO] [FIFOProcessor] 
[10:30:00.033] [INFO] [FIFOProcessor] ╔═══════════════════════════════════════╗
[10:30:00.034] [INFO] [FIFOProcessor] ║ CERRANDO UNIDAD DE DEUDA (ATÓMICA)   ║
[10:30:00.035] [INFO] [FIFOProcessor] ╚═══════════════════════════════════════╝
[10:30:00.036] [INFO] [FIFOProcessor] 
[10:30:00.037] [INFO] [BrokerAdapter] Cerrando OP_020 (MAIN_SELL neutralizada)
[10:30:00.050] [INFO] [BrokerAdapter] Posición OP_020 cerrada exitosamente
[10:30:00.051] [INFO] [BrokerAdapter] Cerrando OP_021 (HEDGE_BUY que cubría OP_020)
[10:30:00.075] [INFO] [BrokerAdapter] Posición OP_021 cerrada exitosamente
[10:30:00.076] [INFO] [FIFOProcessor] ✓ Unidad de deuda cerrada completamente
[10:30:00.077] [INFO] [FIFOProcessor] 
[10:30:00.078] [INFO] [AccountingService] Actualizando contabilidad...
[10:30:00.079] [DEBUG] [AccountingService] pips_locked: 20 → 0
[10:30:00.080] [DEBUG] [AccountingService] pips_recovered: 0 → 20
[10:30:00.081] [DEBUG] [AccountingService] pips_profit_net: 60 (80 - 20)
[10:30:00.082] [INFO] [AccountingService] recovery_queue: ["OP_020_debt_unit"] → []
[10:30:00.083] [INFO] [CycleOrchestrator] Recovery FIFO completada - Ciclo FULLY RECOVERED
```

**Checks:**
- [ ] `cycle.accounting.pips_locked == 0`
- [ ] `cycle.accounting.pips_recovered == 20`
- [ ] `cycle.recovery_queue == []` (vacía)
- [ ] `cycle.accounting.is_fully_recovered == True`
- [ ] Main neutralizada (OP_020) cerrada en broker: `status == CLOSED`
- [ ] Hedge que cubría (OP_021) cerrada en broker: `status == CLOSED`
- [ ] Ambas operaciones cerradas en la misma transacción FIFO

**Orden de Cierre FIFO (CRÍTICO):**
1. ✅ **PRIMERO**: Main + Hedge como **unidad atómica**
2. ✅ **DESPUÉS**: Recoveries subsecuentes (si los hubiera)

**Justificación:**
- Main + Hedge forman la **primera unidad de deuda** (20 pips)
- Cerrarlos juntos:
  - ✓ Minimiza comisiones acumuladas
  - ✓ Cierre atómico (todo o nada)
  - ✓ Evita estados inconsistentes
- La queue FIFO almacena **unidades**, no operaciones individuales

**Cálculo FIFO Verificado:**
```
TP Recovery obtenido: 80 pips
├─ UNIDAD 1 (Main + Hedge): 20 pips
│  ├─ Separación: 4 pips
│  ├─ TP distancia: 10 pips
│  └─ Margen: 6 pips
├─ Pips recuperados: 20
└─ Beneficio neto: 60 pips
```

---

### PASO 5-6: Sin cambios
[Ver pasos 5-6 del documento original]

---

### ESTADO FINAL ESPERADO (CORREGIDO - EXPLÍCITO)

```yaml
cycle:
  id: CYC_003
  status: ACTIVE  # Vuelve a ACTIVE tras full recovery
  pips_locked: 0
  pips_recovered: 20
  recovery_level: 0
  recovery_queue: []
  
operations:
  # ═══════════════════════════════════════════════════════
  # UNIDAD DE DEUDA 1: MAIN + HEDGE (Cerrada por FIFO)
  # ═══════════════════════════════════════════════════════
  - id: OP_020
    type: MAIN
    direction: SELL
    status: CLOSED  # ✅ Cerrada por FIFO
    neutralized_by: OP_021
    close_reason: "fifo_recovery_tp"
    close_method: "atomic_with_hedge"
    debt_unit_id: "OP_020_debt_unit"
    debt_cost_pips: 20
    closed_at: "2025-01-05 10:30:00.050"
    
  - id: OP_021
    type: HEDGE
    direction: BUY
    status: CLOSED  # ✅ Cerrada junto con OP_020
    covering_operation: OP_020
    close_reason: "fifo_recovery_tp"
    close_method: "atomic_with_main"
    debt_unit_id: "OP_020_debt_unit"
    closed_at: "2025-01-05 10:30:00.075"
    
  # ═══════════════════════════════════════════════════════
  # RECOVERY QUE RECUPERÓ LA DEUDA
  # ═══════════════════════════════════════════════════════
  - id: OP_022
    type: RECOVERY
    level: 1
    direction: BUY
    status: TP_HIT
    profit_pips: 80
    recovered_pips: 20  # Usados para cerrar OP_020 + OP_021
    net_profit_pips: 60  # Profit después de FIFO
    closed_debt_units: ["OP_020_debt_unit"]
    
  - id: OP_023
    type: RECOVERY
    level: 1
    direction: SELL
    status: CANCELLED
    cancel_reason: "counterpart_tp_hit"
    
account:
  balance: 10002.00 + (60 * pip_value)  # +Profit neto recovery
  pips_locked_total: 0
  
fifo_summary:
  debt_units_closed: 1
  total_pips_recovered: 20
  recovery_tps_used: 1
  net_profit_pips: 60
  operations_closed:
    - OP_020  # Main
    - OP_021  # Hedge
  close_method: "atomic"
  
metadata:
  debt_unit_composition:
    unit_id: "OP_020_debt_unit"
    main: "OP_020"
    hedge: "OP_021"
    components:
      separation: 4
      tp_distance: 10
      margin: 6
    total_cost: 20
```

---

# ESCENARIO 4: Recovery Multinivel (Sin cambios mayores)

[El escenario 4 permanece igual, solo se actualiza para usar debt_units]

**Nota:** Los debt_units de recoveries subsecuentes cuestan 40 pips cada uno 
(no incluyen main+hedge, solo recovery vs recovery).

---

# MATRIZ DE CHECKS ACTUALIZADA

## Escenario 1: Ciclo Simple ✅

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E1-C01-NEW | Renovación dual de mains | `len([op for op in cycle.operations if op.is_main and op.status == PENDING]) == 2` |
| E1-C02-NEW | BUY renovado existe | `new_buy.entry == current_ask` |
| E1-C03-NEW | SELL renovado existe | `new_sell.entry == current_bid` |

## Escenario 2: Hedge ✅

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E2-C01-NEW | Hedge pendiente cancelado | `hedge_sell.status == CANCELLED` |
| E2-C02-NEW | Cancel reason correcto | `hedge_sell.metadata["cancel_reason"] == "counterpart_main_tp_hit"` |
| E2-C03-NEW | Recoveries desde TP | `recovery_buy.entry == main_tp + 20pips` |

## Escenario 3: Recovery FIFO ✅

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E3-C01-NEW | Main cerrada por FIFO | `main.status == CLOSED && main.close_reason == "fifo_recovery_tp"` |
| E3-C02-NEW | Hedge cerrada con main | `hedge.status == CLOSED && hedge.close_method == "atomic_with_main"` |
| E3-C03-NEW | Cierre atómico | `main.closed_at == hedge.closed_at (±1ms)` |
| E3-C04-NEW | Debt unit registrado | `main.debt_unit_id == hedge.debt_unit_id` |

---

## RESUMEN DE CAMBIOS

### ✅ FIX-001: Renovación de Mains (Escenario 1)

Problema: Solo se creaba una operación al renovar
Solución: Ahora se crean DOS operaciones (BUY + SELL) simultáneamente
Impacto: Mantiene la cobertura bidireccional constante

### ✅ FIX-002: Cancelación de Hedge Pendiente (Escenario 2)

Problema: Hedge pendiente contrario quedaba huérfano cuando main tocaba TP
Solución: Nuevo PASO 5.5 que cancela automáticamente el hedge pendiente opuesto
Impacto: Previene activaciones no deseadas y posiciones huérfanas

### ✅ FIX-003: FIFO y Composición de Deuda (Escenario 3)

Problema: No se mencionaba el hedge en el cierre, ambigüedad en orden de cierre
Solución:

Main + Hedge se cierran como unidad atómica
Logs detallan composición (4 + 10 + 6 = 20 pips)
Queue FIFO almacena "debt_units", no operaciones sueltas


Impacto: Minimiza comisiones, cierre consistente

📊 Debt Unit Structure
Ahora la queue FIFO usa:
json{
  "id": "OP_020_debt_unit",
  "main_id": "OP_020",
  "hedge_id": "OP_021",
  "cost_pips": 20,
  "components": {
    "separation": 4,
    "tp_distance": 10,
    "margin": 6
  }
}


---

# APÉNDICE: MATRIZ DE VALIDACIÓN RÁPIDA

## Propósito

Esta matriz complementa los 4 escenarios detallados anteriores, proporcionando especificaciones compactas para los 58 escenarios restantes. Cada fila define:

- **Input**: Condiciones iniciales y secuencia de precios
- **Output**: Estado final esperado del sistema
- **Checks Críticos**: 2-4 assertions que DEBEN pasar

**Leyenda de Prioridades:**
- 🔴 **CRÍTICA**: Funcionalidad core, debe pasar siempre
- 🟡 **ALTA**: Comportamiento importante, alta prioridad
- 🟢 **MEDIA**: Caso edge, importante pero no bloqueante
- ⚪ **BAJA**: Nice-to-have, puede diferirse

---

## CORE (1 escenario restante)

### c04_no_activation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Precio se mantiene en rango, no activa ninguna operación |
| **Input** | • Balance: 10000 EUR<br>• Precio inicial: 1.10000<br>• Órdenes: BUY@1.10020, SELL@1.09980<br>• Movimiento: ±5 pips (no alcanza entry) |
| **Output** | • Ambas operaciones: `PENDING`<br>• Balance: 10000 (sin cambios)<br>• Broker calls: 0 |
| **Checks** | ✓ `buy_op.status == PENDING`<br>✓ `sell_op.status == PENDING`<br>✓ `len(broker.order_history) == 0`<br>✓ `account.balance == 10000.0` |
| **CSV** | Rango: 1.09990 - 1.10010 (20 ticks, sin cruces) |

---

## CYCLES (2 escenarios restantes)

### cy04_cancel_counter_main

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Cuando un main toca TP, la main contraria pendiente se cancela |
| **Input** | • BUY activada: entry=1.10020<br>• SELL pendiente: entry=1.09980<br>• Precio sube: 1.10020 → 1.10120 (TP) |
| **Output** | • BUY: `TP_HIT`, profit=10 pips<br>• SELL: `CANCELLED`<br>• 2 nuevas mains creadas (renovación) |
| **Checks** | ✓ `buy.status == TP_HIT`<br>✓ `sell.status == CANCELLED`<br>✓ `sell.metadata['cancel_reason'] == "counterpart_tp_hit"`<br>✓ Nuevas ops: `len([op for op in cycle.operations if op.is_main and op.status == PENDING]) == 2` |
| **CSV** | 1.10000 → 1.10020 (activa BUY) → 1.10120 (TP) |

### cy06_multiple_cycles

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Múltiples pares operan independientemente sin interferencia |
| **Input** | • Par 1: EURUSD @ 1.10000<br>• Par 2: GBPUSD @ 1.25000<br>• Ambos con ciclos activos |
| **Output** | • 2 ciclos independientes<br>• EURUSD: 1 TP<br>• GBPUSD: 1 TP<br>• Sin cross-contamination |
| **Checks** | ✓ `len(active_cycles) == 2`<br>✓ `eurusd_cycle.pair == "EURUSD"`<br>✓ `gbpusd_cycle.pair == "GBPUSD"`<br>✓ `eurusd_cycle.accounting.total_tp_count == 1`<br>✓ `gbpusd_cycle.accounting.total_tp_count == 1` |
| **CSV** | 2 archivos: `cy06_eurusd.csv` + `cy06_gbpusd.csv` |

---

## HEDGED (6 escenarios restantes)

### h05_sequential_activation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Ambas mains se activan secuencialmente (no gap simultáneo) |
| **Input** | • Start: 1.10000<br>• T1: 1.10020 (activa BUY)<br>• T2: 1.09990 (activa SELL)<br>• 10 segundos entre activaciones |
| **Output** | • Estado: `HEDGED`<br>• pips_locked: 20<br>• HEDGE_BUY + HEDGE_SELL creados |
| **Checks** | ✓ `cycle.status == HEDGED`<br>✓ `main_buy.status == NEUTRALIZED`<br>✓ `main_sell.status == NEUTRALIZED`<br>✓ `cycle.accounting.pips_locked == 20.0`<br>✓ `len([op for op in cycle.operations if op.is_hedge]) == 2` |
| **CSV** | 1.10000 → 1.10020 (10 ticks) → 1.09990 (10 ticks) |

### h06_simultaneous_gap

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Gap de fin de semana activa ambas mains en el mismo tick |
| **Input** | • Viernes 22:00: 1.10000<br>• Lunes 00:01: 1.10050 (gap +50 pips)<br>• Ambas entries cruzadas |
| **Output** | • Estado: `HEDGED` inmediato<br>• pips_locked: 20 + gap_cost<br>• Metadata: `gap_detected=true` |
| **Checks** | ✓ `cycle.status == HEDGED`<br>✓ `cycle.metadata['gap_detected'] == True`<br>✓ `cycle.accounting.pips_locked >= 20.0`<br>✓ Ambas mains: `activated_at` mismo timestamp |
| **CSV** | Tick 1: 1.10000 → Tick 2: 1.10050 (sin intermedios) |

### h07_buy_tp_hedge_sell (FIX-002)

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Main BUY toca TP en estado HEDGED → cancelar HEDGE_SELL pendiente |
| **Input** | • Estado: HEDGED<br>• Main BUY: ACTIVE<br>• Main SELL: NEUTRALIZED<br>• HEDGE_SELL: PENDING (entry=1.10100)<br>• Precio: 1.10120 (TP del BUY) |
| **Output** | • Main BUY: `TP_HIT`<br>• HEDGE_SELL: `CANCELLED`<br>• Metadata: `cancel_reason="counterpart_main_tp_hit"` |
| **Checks** | ✓ `main_buy.status == TP_HIT`<br>✓ `hedge_sell.status == CANCELLED`<br>✓ `hedge_sell.metadata['cancel_reason'] == "counterpart_main_tp_hit"`<br>✓ `hedge_sell.metadata['cancelled_by_operation'] == main_buy.id` |
| **CSV** | 1.10000 → HEDGED → 1.10120 (TP) |

### h08_sell_tp_hedge_buy

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Main SELL toca TP en HEDGED → cancelar HEDGE_BUY pendiente |
| **Input** | • Estado: HEDGED<br>• Main SELL: ACTIVE<br>• HEDGE_BUY: PENDING<br>• Precio: 1.09920 (TP del SELL) |
| **Output** | • Main SELL: `TP_HIT`<br>• HEDGE_BUY: `CANCELLED` |
| **Checks** | ✓ `main_sell.status == TP_HIT`<br>✓ `hedge_buy.status == CANCELLED`<br>✓ `hedge_buy.metadata['cancel_reason'] == "counterpart_main_tp_hit"` |
| **CSV** | 1.10000 → HEDGED → 1.09920 (TP) |

---

## RECOVERY (7 escenarios restantes)

### r04_recovery_n1_tp_sell

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Recovery N1 SELL exitoso (variante de r03) |
| **Input** | • Recovery N1 SELL entry: 1.10100<br>• TP: 1.10020 (-80 pips) |
| **Output** | • Recovery SELL: `TP_HIT`<br>• pips_recovered: 20<br>• FIFO: Main + Hedge cerrados |
| **Checks** | ✓ `recovery.status == TP_HIT`<br>✓ `recovery.profit_pips == 80.0`<br>✓ `parent_cycle.accounting.pips_recovered == 20.0`<br>✓ `len(parent_cycle.accounting.recovery_queue) == 0` |
| **CSV** | Precio baja 80 pips desde entry |

### r05_recovery_n1_fails_n2

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Recovery N1 no alcanza TP, se activa N2 por distancia |
| **Input** | • Recovery N1 @ 1.10140 (BUY)<br>• Precio: 1.10140 → 1.10120 (no TP)<br>• Distancia N2: 40 pips adicionales |
| **Output** | • N1: sigue `ACTIVE`<br>• N2 creado @ 1.10180<br>• recovery_queue: [N1, N2] |
| **Checks** | ✓ `n1.status == ACTIVE`<br>✓ `n2.status == PENDING`<br>✓ `n2.entry_price == 1.10180`<br>✓ `len(parent_cycle.accounting.recovery_queue) == 2` |
| **CSV** | 1.10140 → 1.10120 (N1 activa, no TP) → 1.10180 (N2 coloca) |

### r07_cascade_n1_n2_n3

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cascada de 3 niveles de recovery antes de resolución |
| **Input** | • N1 @ 1.10140<br>• N2 @ 1.10180<br>• N3 @ 1.10220<br>• N3 toca TP |
| **Output** | • N3: `TP_HIT` (80 pips)<br>• FIFO cierra: N1 (40) + parte N2 (40) |
| **Checks** | ✓ `n3.status == TP_HIT`<br>✓ `parent_cycle.accounting.pips_recovered == 80.0`<br>✓ `len(closed_by_fifo) == 2` |
| **CSV** | Cascada +40 pips cada nivel, luego reversa 80 pips |

### r08_recovery_max_n6

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Alcanza nivel máximo de recovery (N6) |
| **Input** | • Recoveries N1-N5 activos<br>• Distancia para N6 alcanzada |
| **Output** | • N6 creado<br>• Sistema: alerta `max_recovery_level_reached`<br>• N6 esperando resolución |
| **Checks** | ✓ `parent_cycle.recovery_level == 6`<br>✓ `len(recovery_queue) == 6`<br>✓ Alert creada: `severity=WARNING` |
| **CSV** | Cascada extrema +240 pips (40*6) |

### r09_cancel_recovery_counter

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Recovery BUY toca TP → cancelar SELL pendiente |
| **Input** | • Recovery BUY: TP hit<br>• Recovery SELL: PENDING |
| **Output** | • Recovery SELL: `CANCELLED` |
| **Checks** | ✓ `recovery_buy.status == TP_HIT`<br>✓ `recovery_sell.status == CANCELLED`<br>✓ `recovery_sell.metadata['cancel_reason'] == "counterpart_tp_hit"` |
| **CSV** | Recovery TP alcanzado unilateralmente |

### r10_multiple_recovery_pairs

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟢 MEDIA |
| **Descripción** | Múltiples pares con recoveries simultáneos |
| **Input** | • EURUSD: N1+N2 activos<br>• GBPUSD: N1 activo |
| **Output** | • 3 recoveries independientes<br>• Sin interferencia cross-pair |
| **Checks** | ✓ `eurusd_cycle.recovery_level == 2`<br>✓ `gbpusd_cycle.recovery_level == 1`<br>✓ Recovery queues separadas |
| **CSV** | 2 archivos paralelos |

---

## FIFO (2 escenarios restantes)

### f03_fifo_atomic_close

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cierre atómico de Main + Hedge como unidad |
| **Input** | • Main SELL: NEUTRALIZED<br>• Hedge BUY: ACTIVE<br>• Recovery TP: 80 pips disponibles |
| **Output** | • Ambos cerrados en mismo timestamp<br>• debt_unit_id compartido |
| **Checks** | ✓ `main.status == CLOSED`<br>✓ `hedge.status == CLOSED`<br>✓ `main.closed_at == hedge.closed_at` (±1ms)<br>✓ `main.metadata['debt_unit_id'] == hedge.metadata['debt_unit_id']`<br>✓ `main.metadata['close_method'] == "atomic_with_hedge"` |
| **CSV** | Recovery alcanza TP con deuda pendiente |

### f04_fifo_multiple_close

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Un recovery TP cierra múltiples unidades de deuda |
| **Input** | • Queue: [debt_unit_1 (20 pips), debt_unit_2 (40 pips)]<br>• Recovery TP: 80 pips |
| **Output** | • Ambas unidades cerradas<br>• Profit neto: 20 pips |
| **Checks** | ✓ `pips_recovered == 60.0` (20+40)<br>✓ `recovery_queue == []`<br>✓ `len(closed_units) == 2`<br>✓ `net_profit_pips == 20.0` |
| **CSV** | Recovery con deuda acumulada 60 pips |

---

## RISK MANAGEMENT (3 escenarios adicionales de ejemplo)

### rm03_daily_loss_limit

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Pérdida diaria excede límite → pausa hasta mañana |
| **Input** | • Pérdidas acumuladas: -100 pips en el día<br>• Límite: 100 pips |
| **Output** | • Sistema: `PAUSED`<br>• Metadata: `pause_reason="daily_loss_limit"`<br>• No nuevas operaciones |
| **Checks** | ✓ Alerta generada: `severity=CRITICAL`<br>✓ `can_open_position() == False`<br>✓ `system.status == PAUSED` |
| **CSV** | Secuencia de 10 TPs perdidos |

### rm04_margin_insufficient

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Margen insuficiente rechaza nueva operación |
| **Input** | • Free margin: 50 EUR<br>• Nueva operación requiere: 100 EUR |
| **Output** | • Operación: rechazada<br>• Log: "Insufficient margin" |
| **Checks** | ✓ `result.success == False`<br>✓ `result.error_code == "INSUFFICIENT_MARGIN"`<br>✓ `operation.status == PENDING` (sin cambios) |
| **CSV** | N/A (test unitario, no CSV) |

---

## MONEY MANAGEMENT (1 ejemplo adicional)

### mm08_recovery_pnl_accumulation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | P&L de recoveries acumula correctamente |
| **Input** | • N1 TP: +80 pips → -20 costo FIFO = +60 neto<br>• N2 TP: +80 pips → -40 costo FIFO = +40 neto |
| **Output** | • Total recovered: 60 pips<br>• Profit neto: 100 pips |
| **Checks** | ✓ `pips_recovered == 60.0`<br>✓ `net_profit_pips == 100.0`<br>✓ Balance incrementado correctamente |
| **CSV** | 2 recoveries exitosos secuenciales |

---

## EDGE CASES (3 ejemplos)

### e02_high_spread_rejection

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Spread >3 pips rechaza todas las operaciones |
| **Input** | • Spread: 5 pips<br>• Señal: OPEN_CYCLE |
| **Output** | • Operación: NO enviada<br>• Log: "Spread too high" |
| **Checks** | ✓ `signal.signal_type == NO_ACTION`<br>✓ `signal.metadata['reason'] == "high_spread"`<br>✓ `len(broker.orders) == 0` |
| **CSV** | Ticks con spread artificialmente alto |

### e03_weekend_gap

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Gap atraviesa múltiples niveles (TP + Recovery entry) |
| **Input** | • Viernes: 1.10000<br>• Lunes: 1.10200 (gap +200 pips) |
| **Output** | • Detección de gap<br>• Metadata: `gap_size=200`<br>• Manejo especial de activaciones |
| **Checks** | ✓ `cycle.metadata['gap_detected'] == True`<br>✓ `cycle.metadata['gap_size'] == 200.0`<br>✓ Operaciones activadas con precio post-gap |
| **CSV** | Salto de 200 pips sin ticks intermedios |

---

## MULTI-PAIR (2 ejemplos)

### mp01_dual_pair

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | EURUSD + GBPUSD operan simultáneamente sin conflictos |
| **Input** | • EURUSD: ciclo con 1 TP<br>• GBPUSD: ciclo con 1 TP |
| **Output** | • 2 ciclos independientes<br>• Balance: +20 EUR (+10 cada par) |
| **Checks** | ✓ `len(cycles) == 2`<br>✓ `eurusd_balance_delta == 10.0`<br>✓ `gbpusd_balance_delta == 10.0`<br>✓ Sin cross-contamination |
| **CSV** | 2 archivos: `mp01_eurusd.csv` + `mp01_gbpusd.csv` |

### mp04_total_exposure

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Exposición total calcula suma de todos los pares |
| **Input** | • EURUSD: 3 operaciones (0.03 lotes)<br>• GBPUSD: 2 operaciones (0.02 lotes) |
| **Output** | • Exposición total: 0.05 lotes<br>• Porcentaje: calculado vs equity |
| **Checks** | ✓ `total_lots == 0.05`<br>✓ `exposure_pct < 30.0` (límite) |
| **CSV** | Multi-pair con varias operaciones activas |

---

## JPY PAIRS (2 ejemplos)

### j02_usdjpy_hedged

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | USDJPY entra en hedge (2 decimales) |
| **Input** | • USDJPY @ 110.00<br>• BUY @ 110.05 activada<br>• SELL @ 109.95 activada |
| **Output** | • Estado: HEDGED<br>• pips_locked: 20 (ajustado para JPY) |
| **Checks** | ✓ `cycle.status == HEDGED`<br>✓ `pips_locked == 20.0`<br>✓ Multiplicador × 100 aplicado correctamente |
| **CSV** | USDJPY con precisión de 2 decimales |

### j04_usdjpy_pips_calculation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cálculo de pips correcto para par JPY (multiplier × 100) |
| **Input** | • Entry: 110.00<br>• Close: 110.10<br>• Diferencia: 0.10 |
| **Output** | • Profit: 10 pips (0.10 × 100) |
| **Checks** | ✓ `profit_pips == 10.0`<br>✓ Multiplicador correcto aplicado<br>✓ `_pips_between()` usa multiplier 100 |
| **CSV** | USDJPY con movimiento de 10 pips |

---

## Formato de Checks

Cada check sigue la convención:
```python
✓ assertion_expresion  # Debe ser True
```

Ejemplos:
- `✓ operation.status == OperationStatus.TP_HIT`
- `✓ len(cycle.operations) == 4`
- `✓ cycle.accounting.pips_locked == 20.0`
- `✓ "gap_detected" in cycle.metadata`

---

## Notas de Implementación

### Generación de CSVs
```python
# El generador usa esta matriz como spec:
SCENARIO_SPECS = {
    'c04_no_activation': {
        'pair': 'EURUSD',
        'start': 1.10000,
        'ticks': 20,
        'price_range': (1.09990, 1.10010),  # No cruza entries
        'expected_orders': 0
    }
}
```

### Ejecución de Tests
```bash
# Test individual
pytest tests/test_scenarios/test_all_scenarios.py::test_scenario[c04_no_activation]

# Categoría completa
pytest tests/test_scenarios/ -k "CORE"

# Todos
pytest tests/test_scenarios/ -v
```

### Estructura de Reporte
Al ejecutar los 62 tests, el reporte debe mostrar:
```
tests/test_scenarios/test_all_scenarios.py::test_scenario[c01_tp_simple_buy] PASSED
tests/test_scenarios/test_all_scenarios.py::test_scenario[c04_no_activation] PASSED
tests/test_scenarios/test_all_scenarios.py::test_scenario[cy04_cancel_counter_main] PASSED
...
===================== 62 passed in 45.23s =====================
```

---

## Siguiente Paso

Con esta matriz, puedes:
1. ✅ **Generar CSVs automáticamente** usando script
2. ✅ **Crear tests parametrizados** que lean esta spec
3. ✅ **Validar cobertura** de los 62 escenarios
4. ✅ **Documentar comportamiento esperado** de forma compacta
