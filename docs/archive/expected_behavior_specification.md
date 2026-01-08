# Especificación de Comportamiento Esperado

## Propósito

Este documento define **QUÉ DEBERÍA PASAR** según la teoría del documento madre.
Cada escenario incluye:
- **PASOS EXACTOS** que debe ejecutar el sistema
- **LOGS** que deben aparecer
- **CHECKS** que deben validarse
- **ESTADO FINAL** esperado

Esto permite verificar si la implementación coincide con la teoría.

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

# ESCENARIO 1: Ciclo Simple Exitoso (Happy Path)

## Referencia Documento Madre
- Líneas 45-52: Operación Main con TP 10 pips
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

### PASO 1: Crear Ciclo
**Trigger:** Sistema detecta oportunidad de entrada

```
[10:00:00.000] [INFO] [CycleOrchestrator] Iniciando nuevo ciclo para EURUSD
[10:00:00.001] [DEBUG] [RiskManager] Validando exposición: 0/500 pips OK
[10:00:00.002] [DEBUG] [RiskManager] Validando margen: 10000/10000 OK
[10:00:00.003] [INFO] [CycleOrchestrator] Ciclo CYC_001 creado en estado PENDING
```

**Checks:**
- [ ] `risk_manager.can_open_cycle() == True`
- [ ] `cycle.status == CycleStatus.PENDING`
- [ ] `cycle.pair == "EURUSD"`

**DB Insert:**
```sql
INSERT INTO cycles (id, pair, status, created_at)
VALUES ('CYC_001', 'EURUSD', 'PENDING', '2025-01-05 10:00:00');
```

---

### PASO 2: Crear Operaciones Main (BUY y SELL pendientes)
**Trigger:** Ciclo creado

```
[10:00:00.010] [INFO] [CycleOrchestrator] Creando operaciones main para CYC_001
[10:00:00.011] [DEBUG] [LotCalculator] Calculando lote: balance=10000, risk=1%, SL=50 pips
[10:00:00.012] [DEBUG] [LotCalculator] Lote calculado: 0.02
[10:00:00.015] [INFO] [BrokerAdapter] Enviando SELL_STOP: entry=1.09980, tp=1.09880, sl=1.10480
[10:00:00.016] [INFO] [BrokerAdapter] Enviando BUY_STOP: entry=1.10020, tp=1.10120, sl=1.09520
[10:00:00.100] [INFO] [BrokerAdapter] SELL_STOP confirmado: ticket=12345
[10:00:00.101] [INFO] [BrokerAdapter] BUY_STOP confirmado: ticket=12346
[10:00:00.102] [INFO] [CycleOrchestrator] Operaciones main creadas: MAIN_SELL=OP_001, MAIN_BUY=OP_002
```

**Checks:**
- [ ] `len(cycle.main_operations) == 2`
- [ ] `main_buy.entry_price == ask` (1.10020)
- [ ] `main_sell.entry_price == bid - spread` (1.09980)
- [ ] `main_buy.tp_price == entry + 10 pips` (1.10120)
- [ ] `main_sell.tp_price == entry - 10 pips` (1.09880)
- [ ] `main_buy.status == OperationStatus.PENDING`
- [ ] `main_sell.status == OperationStatus.PENDING`
- [ ] `main_buy.broker_ticket == "12346"`
- [ ] `main_sell.broker_ticket == "12345"`

**DB Inserts:**
```sql
INSERT INTO operations (id, cycle_id, type, direction, status, entry_price, tp_price, broker_ticket)
VALUES 
  ('OP_001', 'CYC_001', 'MAIN', 'SELL', 'PENDING', 1.09980, 1.09880, '12345'),
  ('OP_002', 'CYC_001', 'MAIN', 'BUY', 'PENDING', 1.10020, 1.10120, '12346');
```

---

### PASO 3: Activar Ciclo
**Trigger:** Ambas órdenes pendientes confirmadas

```
[10:00:00.110] [INFO] [CycleOrchestrator] Ciclo CYC_001 activado
[10:00:00.111] [DEBUG] [CycleOrchestrator] Estado: PENDING → ACTIVE
```

**Checks:**
- [ ] `cycle.status == CycleStatus.ACTIVE`
- [ ] `cycle.activated_at != None`

**DB Update:**
```sql
UPDATE cycles SET status = 'ACTIVE', activated_at = '2025-01-05 10:00:00.110'
WHERE id = 'CYC_001';
```

---

### PASO 4: Precio Sube y Activa BUY_STOP
**Trigger:** `ask >= 1.10020` (entry del BUY_STOP)

```
[10:00:05.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10018, ask=1.10038
[10:00:05.001] [INFO] [BrokerAdapter] BUY_STOP activado: ticket=12346, fill_price=1.10020
[10:00:05.002] [INFO] [CycleOrchestrator] Operación OP_002 activada a 1.10020
[10:00:05.003] [DEBUG] [CycleOrchestrator] OP_002: PENDING → ACTIVE
```

**Checks:**
- [ ] `main_buy.status == OperationStatus.ACTIVE`
- [ ] `main_buy.activated_at != None`
- [ ] `main_buy.fill_price == 1.10020`
- [ ] `main_sell.status == OperationStatus.PENDING` (sin cambio)

**DB Update:**
```sql
UPDATE operations 
SET status = 'ACTIVE', activated_at = '2025-01-05 10:00:05.001', fill_price = 1.10020
WHERE id = 'OP_002';
```

---

### PASO 5: Precio Sube y Alcanza TP del BUY
**Trigger:** `bid >= 1.10120` (TP del BUY)

```
[10:00:30.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10120, ask=1.10140
[10:00:30.001] [INFO] [BrokerAdapter] TP alcanzado: ticket=12346, close_price=1.10120
[10:00:30.002] [INFO] [CycleOrchestrator] Operación OP_002 cerrada con TP
[10:00:30.003] [DEBUG] [PnLCalculator] Calculando P&L: entry=1.10020, exit=1.10120, pips=+10
[10:00:30.004] [DEBUG] [PnLCalculator] P&L monetario: 10 pips × 0.02 lot × $10 = $2.00
[10:00:30.005] [INFO] [CycleOrchestrator] OP_002: profit=+10 pips (+$2.00)
[10:00:30.006] [DEBUG] [CycleOrchestrator] OP_002: ACTIVE → TP_HIT
```

**Checks:**
- [ ] `main_buy.status == OperationStatus.TP_HIT`
- [ ] `main_buy.close_price == 1.10120`
- [ ] `main_buy.profit_pips == 10.0`
- [ ] `main_buy.profit_money == 2.00`
- [ ] `main_buy.closed_at != None`

**Cálculo Matemático (verificar):**
```
pips = (1.10120 - 1.10020) / 0.0001 = 10 pips
money = 10 × 0.02 × 10 = $2.00
```

**DB Update:**
```sql
UPDATE operations 
SET status = 'TP_HIT', 
    close_price = 1.10120, 
    closed_at = '2025-01-05 10:00:30.001',
    profit_pips = 10.0,
    profit_money = 2.00
WHERE id = 'OP_002';
```

---

### PASO 6: Cancelar SELL_STOP Pendiente
**Trigger:** BUY cerró con TP → SELL pendiente ya no es necesaria

```
[10:00:30.010] [INFO] [CycleOrchestrator] Cancelando operación pendiente contraria
[10:00:30.011] [INFO] [BrokerAdapter] Cancelando orden: ticket=12345
[10:00:30.050] [INFO] [BrokerAdapter] Orden cancelada: ticket=12345
[10:00:30.051] [INFO] [CycleOrchestrator] OP_001 cancelada
[10:00:30.052] [DEBUG] [CycleOrchestrator] OP_001: PENDING → CANCELLED
```

**Checks:**
- [ ] `main_sell.status == OperationStatus.CANCELLED`
- [ ] `main_sell.cancelled_at != None`
- [ ] Orden 12345 NO existe en broker

**DB Update:**
```sql
UPDATE operations 
SET status = 'CANCELLED', cancelled_at = '2025-01-05 10:00:30.050'
WHERE id = 'OP_001';
```

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

# ESCENARIO 2: Ambas Mains Se Activan (Hedge)

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

### PASO 1: Precio Sube → BUY Se Activa
**Trigger:** `ask >= 1.10020`

```
[10:00:05.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10018, ask=1.10038
[10:00:05.001] [INFO] [BrokerAdapter] BUY_STOP activado: ticket=20001
[10:00:05.002] [INFO] [CycleOrchestrator] OP_010 (MAIN_BUY) activada
```

**Checks:**
- [ ] `main_buy.status == ACTIVE`
- [ ] `main_sell.status == PENDING`

---

### PASO 2: Precio Baja → SELL También Se Activa
**Trigger:** `bid <= 1.09980`

```
[10:01:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.09970, ask=1.09990
[10:01:00.001] [INFO] [BrokerAdapter] SELL_STOP activado: ticket=20002
[10:01:00.002] [INFO] [CycleOrchestrator] OP_011 (MAIN_SELL) activada
[10:01:00.003] [WARN] [CycleOrchestrator] ⚠️ AMBAS MAINS ACTIVAS - Iniciando cobertura
```

**Checks:**
- [ ] `main_buy.status == ACTIVE`
- [ ] `main_sell.status == ACTIVE`

---

### PASO 3: Crear Operaciones de Cobertura (Hedge)
**Trigger:** Ambas mains activas

```
[10:01:00.010] [INFO] [CycleOrchestrator] Creando coberturas para ciclo CYC_002
[10:01:00.011] [DEBUG] [HedgeCalculator] BUY activo a 1.10020, SELL activo a 1.09980
[10:01:00.012] [DEBUG] [HedgeCalculator] Separación actual: 4 pips
[10:01:00.015] [INFO] [BrokerAdapter] Enviando HEDGE_BUY_STOP: entry=1.10020, tp=1.10120
[10:01:00.016] [INFO] [BrokerAdapter] Enviando HEDGE_SELL_STOP: entry=1.09980, tp=1.09880
[10:01:00.100] [INFO] [BrokerAdapter] HEDGE_BUY confirmado: ticket=20003
[10:01:00.101] [INFO] [BrokerAdapter] HEDGE_SELL confirmado: ticket=20004
[10:01:00.102] [INFO] [CycleOrchestrator] Ciclo CYC_002: ACTIVE → HEDGED
```

**Checks:**
- [ ] `len(cycle.hedge_operations) == 2`
- [ ] `cycle.status == CycleStatus.HEDGED`
- [ ] `hedge_buy.entry_price == main_buy.entry_price`
- [ ] `hedge_sell.entry_price == main_sell.entry_price`

**DB Inserts:**
```sql
INSERT INTO operations (id, cycle_id, type, direction, status, entry_price, tp_price)
VALUES 
  ('OP_012', 'CYC_002', 'HEDGE', 'BUY', 'PENDING', 1.10020, 1.10120),
  ('OP_013', 'CYC_002', 'HEDGE', 'SELL', 'PENDING', 1.09980, 1.09880);

UPDATE cycles SET status = 'HEDGED' WHERE id = 'CYC_002';
```

---

### PASO 4: BUY Main Alcanza TP
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

# ESCENARIO 3: Recovery Nivel 1 Exitoso

## Referencia Documento Madre
- Líneas 86-104: Sistema FIFO, costo de 20 pips primer recovery
- Sección "Recovery exitoso"

## Condiciones Iniciales
```yaml
cycle:
  id: CYC_003
  status: IN_RECOVERY
  pips_locked: 20  # De las mains neutralizadas
  recovery_queue: ["OP_020"]  # Main neutralizada
  
account:
  balance: 10000.0
```

## Secuencia de Pasos

### PASO 1: Crear Recovery Nivel 1
**Trigger:** Ciclo en IN_RECOVERY necesita abrir recovery

```
[10:00:00.000] [INFO] [CycleOrchestrator] Iniciando Recovery N1 para CYC_003
[10:00:00.001] [DEBUG] [RecoveryCalculator] Pips bloqueados: 20
[10:00:00.002] [DEBUG] [RecoveryCalculator] Recovery N1: separación=20 pips, TP=80 pips
[10:00:00.003] [DEBUG] [LotCalculator] Lote recovery: debe cubrir 20 pips con 80 pips TP
[10:00:00.010] [INFO] [BrokerAdapter] Enviando RECOVERY_BUY_STOP: entry=+20 pips, tp=+100 pips
[10:00:00.011] [INFO] [BrokerAdapter] Enviando RECOVERY_SELL_STOP: entry=-20 pips, tp=-100 pips
[10:00:00.100] [INFO] [CycleOrchestrator] Recovery N1 creado: OP_021 (BUY), OP_022 (SELL)
```

**Checks:**
- [ ] `recovery_buy.entry_price == current_price + 20 pips`
- [ ] `recovery_sell.entry_price == current_price - 20 pips`
- [ ] `recovery_buy.tp_price == entry + 80 pips`
- [ ] `recovery_sell.tp_price == entry - 80 pips`
- [ ] `cycle.recovery_level == 1`

---

### PASO 2: Recovery BUY Se Activa
**Trigger:** Precio sube 20 pips desde apertura

```
[10:05:00.000] [INFO] [PriceMonitor] Tick: precio subió 20 pips
[10:05:00.001] [INFO] [BrokerAdapter] RECOVERY_BUY activado: ticket=30001
[10:05:00.002] [INFO] [CycleOrchestrator] OP_021 (RECOVERY_BUY) activada
```

---

### PASO 3: Recovery BUY Alcanza TP (+80 pips)
**Trigger:** `bid >= recovery_buy.tp_price`

```
[10:30:00.000] [INFO] [PriceMonitor] Tick: precio subió 80 pips desde entry
[10:30:00.001] [INFO] [BrokerAdapter] TP alcanzado: ticket=30001
[10:30:00.002] [INFO] [CycleOrchestrator] OP_021 (RECOVERY_BUY) cerrada con TP: +80 pips
[10:30:00.003] [DEBUG] [PnLCalculator] Profit: 80 pips × lot = $X
```

**Checks:**
- [ ] `recovery_buy.status == TP_HIT`
- [ ] `recovery_buy.profit_pips == 80`

---

### PASO 4: Procesar Cierre FIFO
**Trigger:** Recovery TP alcanzado → cerrar según FIFO

```
[10:30:00.010] [INFO] [FIFOProcessor] Procesando TP de 80 pips según FIFO
[10:30:00.011] [DEBUG] [FIFOProcessor] Recovery queue: ["OP_020"]
[10:30:00.012] [DEBUG] [FIFOProcessor] Costo primer recovery: 20 pips (incluye mains)
[10:30:00.013] [DEBUG] [FIFOProcessor] 80 pips disponibles - 20 pips costo = 60 pips excedente
[10:30:00.014] [INFO] [FIFOProcessor] Cerrando OP_020 de la queue (coste: 20 pips)
[10:30:00.015] [INFO] [AccountingService] pips_locked: 20 → 0
[10:30:00.016] [INFO] [AccountingService] pips_recovered: 0 → 20
[10:30:00.017] [INFO] [CycleOrchestrator] Recovery FIFO completada - Ciclo recuperado
```

**Checks:**
- [ ] `cycle.accounting.pips_locked == 0`
- [ ] `cycle.accounting.pips_recovered == 20`
- [ ] `cycle.recovery_queue == []` (vacía)
- [ ] `cycle.accounting.is_fully_recovered == True`

**Cálculo FIFO (verificar):**
```
TP obtenido: 80 pips
Costo primer recovery: 20 pips (incluye las 2 mains + primera recovery)
Excedente: 80 - 20 = 60 pips de beneficio neto
Pips desbloqueados: 20
```

---

### PASO 5: Cancelar Recovery SELL Pendiente
**Trigger:** Recovery completada

```
[10:30:00.020] [INFO] [CycleOrchestrator] Cancelando recovery pendiente contraria
[10:30:00.021] [INFO] [BrokerAdapter] Cancelando: ticket=30002
[10:30:00.050] [INFO] [CycleOrchestrator] OP_022 cancelada
```

---

### PASO 6: Ciclo Vuelve a ACTIVE
**Trigger:** Fully recovered

```
[10:30:00.060] [INFO] [CycleOrchestrator] Ciclo CYC_003: IN_RECOVERY → ACTIVE
[10:30:00.061] [INFO] [CycleOrchestrator] Creando nuevas operaciones main para continuar
```

**Checks:**
- [ ] `cycle.status == CycleStatus.ACTIVE`
- [ ] `cycle.recovery_level == 0` (reset)

---

### ESTADO FINAL ESPERADO

```yaml
cycle:
  id: CYC_003
  status: ACTIVE
  pips_locked: 0
  pips_recovered: 20
  recovery_level: 0
  recovery_queue: []
  
operations:
  - id: OP_020
    type: MAIN
    status: CLOSED  # Cerrada por FIFO
    
  - id: OP_021
    type: RECOVERY
    level: 1
    direction: BUY
    status: TP_HIT
    profit_pips: 80
    
  - id: OP_022
    type: RECOVERY
    level: 1
    direction: SELL
    status: CANCELLED
    
account:
  balance: anterior + profit_neto
  pips_locked_total: 0
```

---

# ESCENARIO 4: Recovery Multinivel (Racha de Fallos)

## Referencia Documento Madre
- Líneas 86-104: FIFO con múltiples recoveries
- "Primer recovery: 20 pips, siguientes: 40 pips cada uno"

## Condiciones Iniciales
```yaml
cycle:
  id: CYC_004
  status: IN_RECOVERY
  pips_locked: 20
  recovery_queue: ["OP_030"]
```

## Secuencia de Pasos

### PASO 1-3: Recovery N1 Falla (Ambas se activan)

```
[10:00:00] Recovery N1 BUY y SELL creados
[10:05:00] Recovery N1 BUY se activa
[10:10:00] Precio revierte, Recovery N1 SELL también se activa
[10:10:01] [WARN] ⚠️ AMBAS RECOVERY N1 ACTIVAS - Neutralizando
[10:10:02] [INFO] pips_locked: 20 → 60 (+40 de esta recovery)
```

**Checks:**
- [ ] `cycle.pips_locked == 60` (20 original + 40 de R1)
- [ ] `cycle.recovery_queue == ["OP_030", "OP_031"]`
- [ ] `cycle.recovery_level == 1`

---

### PASO 4-6: Recovery N2 Falla

```
[10:15:00] Recovery N2 creado (separación 60 pips del N1)
[10:20:00] Ambas N2 se activan
[10:20:01] [INFO] pips_locked: 60 → 100 (+40 de R2)
```

**Checks:**
- [ ] `cycle.pips_locked == 100`
- [ ] `cycle.recovery_queue == ["OP_030", "OP_031", "OP_032"]`
- [ ] `cycle.recovery_level == 2`

---

### PASO 7-9: Recovery N3 Falla

```
[10:30:00] pips_locked: 100 → 140 (+40 de R3)
```

**Checks:**
- [ ] `cycle.pips_locked == 140`
- [ ] `len(cycle.recovery_queue) == 4`
- [ ] `cycle.recovery_level == 3`

---

### PASO 10: Recovery N4 Toca TP (+80 pips)

```
[10:45:00] [INFO] Recovery N4 BUY alcanza TP: +80 pips
[10:45:01] [INFO] [FIFOProcessor] Procesando 80 pips según FIFO
[10:45:02] [DEBUG] Queue: ["OP_030"(20), "OP_031"(40), "OP_032"(40), "OP_033"(40)]
[10:45:03] [DEBUG] Cerrando OP_030: costo 20 pips, restante 60
[10:45:04] [DEBUG] Cerrando OP_031: costo 40 pips, restante 20
[10:45:05] [DEBUG] No alcanza para OP_032 (costo 40, disponible 20)
[10:45:06] [INFO] Cerradas 2 de 4 recoveries
[10:45:07] [INFO] pips_locked: 140 → 80
```

**Checks:**
- [ ] 80 pips de TP cierra exactamente 2 recoveries (20 + 40 = 60)
- [ ] Sobran 20 pips (beneficio parcial)
- [ ] `cycle.pips_locked == 80` (140 - 60)
- [ ] `cycle.recovery_queue == ["OP_032", "OP_033"]` (quedan 2)
- [ ] `cycle.status == IN_RECOVERY` (no fully recovered)

---

### PASO 11: Recovery N5 Toca TP (+80 pips)

```
[11:00:00] [INFO] Recovery N5 BUY alcanza TP: +80 pips
[11:00:01] [DEBUG] Queue: ["OP_032"(40), "OP_033"(40)]
[11:00:02] [DEBUG] Cerrando OP_032: costo 40 pips, restante 40
[11:00:03] [DEBUG] Cerrando OP_033: costo 40 pips, restante 0
[11:00:04] [INFO] Todas las recoveries cerradas
[11:00:05] [INFO] pips_locked: 80 → 0
[11:00:06] [INFO] Ciclo CYC_004: IN_RECOVERY → ACTIVE
```

**Checks:**
- [ ] `cycle.pips_locked == 0`
- [ ] `cycle.recovery_queue == []`
- [ ] `cycle.status == CycleStatus.ACTIVE`
- [ ] `cycle.accounting.is_fully_recovered == True`

---

### CONTABILIDAD FINAL

```
Racha de fallos:
  R0 (mains): 20 pips bloqueados
  R1: +40 pips bloqueados
  R2: +40 pips bloqueados  
  R3: +40 pips bloqueados
  TOTAL: 140 pips bloqueados

Resolución:
  TP R4: 80 pips → cierra R0(20) + R1(40) = 60 pips
  TP R5: 80 pips → cierra R2(40) + R3(40) = 80 pips
  TOTAL recuperado: 140 pips

Balance de TPs:
  2 × 80 = 160 pips ganados
  140 pips usados para cerrar
  20 pips beneficio neto
```

**Verificar ratio 2:1:**
```
4 recoveries fallidas: 4 × 40 = 160 pips bloqueados (pero el primero es 20, así que 20+40×3=140)
2 recoveries exitosas: 2 × 80 = 160 pips ganados
Resultado: +20 pips beneficio

Esto confirma: por cada 2 fallos, 1 éxito recupera todo + beneficio
```

---

# ESCENARIO 5: Límites de Risk Management

## Referencia Documento Madre
- max_pips_locked = 500
- max_concurrent_recovery = 20

## Secuencia: Límite de Pips Alcanzado

```
[Estado inicial]
system.total_pips_locked: 480

[10:00:00] [INFO] Intentando abrir nuevo ciclo EURUSD
[10:00:01] [DEBUG] [RiskManager] Validando: 480 + 40 (estimado) = 520 > 500
[10:00:02] [WARN] [RiskManager] ⚠️ Límite de pips bloqueados alcanzado
[10:00:03] [INFO] [CycleOrchestrator] Nuevo ciclo BLOQUEADO por límite de riesgo
```

**Checks:**
- [ ] `risk_manager.can_open_cycle() == False`
- [ ] `risk_manager.rejection_reason == "max_pips_locked_exceeded"`
- [ ] Nuevo ciclo NO se crea

---

## Secuencia: Emergency Stop

```
[10:00:00] [CRITICAL] [ReconciliationService] Detectada posición BROKER_ONLY
[10:00:01] [CRITICAL] [RiskManager] 🚨 EMERGENCY STOP ACTIVADO
[10:00:02] [CRITICAL] [CycleOrchestrator] Pausando TODOS los ciclos
[10:00:03] [CRITICAL] [AlertService] Enviando alerta: email, telegram, dashboard
```

**Checks:**
- [ ] `system.emergency_stop == True`
- [ ] Todos los ciclos en `PAUSED`
- [ ] No se procesan nuevas órdenes
- [ ] Alertas enviadas

---

# MATRIZ DE CHECKS POR ESCENARIO

## Escenario 1: Ciclo Simple

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E1-C01 | Ciclo creado en PENDING | `cycle.status == PENDING` |
| E1-C02 | 2 operaciones main creadas | `len(cycle.main_operations) == 2` |
| E1-C03 | BUY entry = ask | `main_buy.entry == ask` |
| E1-C04 | SELL entry = bid - spread | `main_sell.entry == bid - spread` |
| E1-C05 | TP = entry ± 10 pips | `op.tp == op.entry ± 0.0010` |
| E1-C06 | Activación cambia estado | `op.status == ACTIVE after fill` |
| E1-C07 | TP hit calcula profit correcto | `op.profit_pips == 10` |
| E1-C08 | Pendiente contraria cancelada | `other_op.status == CANCELLED` |
| E1-C09 | Balance actualizado | `account.balance += profit` |

## Escenario 2: Hedge

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E2-C01 | Ambas mains activas detectadas | `both_active == True` |
| E2-C02 | Hedges creados | `len(cycle.hedge_operations) == 2` |
| E2-C03 | Ciclo pasa a HEDGED | `cycle.status == HEDGED` |
| E2-C04 | TP main neutraliza contraria | `other_main.status == NEUTRALIZED` |
| E2-C05 | Pips locked = 20 | `cycle.pips_locked == 20` |
| E2-C06 | Ciclo pasa a IN_RECOVERY | `cycle.status == IN_RECOVERY` |
| E2-C07 | Queue FIFO poblada | `len(cycle.recovery_queue) == 1` |

## Escenario 3: Recovery N1 Exitoso

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E3-C01 | Recovery entry = ±20 pips | `r.entry == price ± 0.0020` |
| E3-C02 | Recovery TP = ±80 pips | `r.tp == entry ± 0.0080` |
| E3-C03 | TP procesa FIFO | `fifo_processor called` |
| E3-C04 | Costo primer recovery = 20 | `first_cost == 20` |
| E3-C05 | Pips locked → 0 | `cycle.pips_locked == 0` |
| E3-C06 | Queue vacía | `cycle.recovery_queue == []` |
| E3-C07 | Ciclo vuelve a ACTIVE | `cycle.status == ACTIVE` |

## Escenario 4: Recovery Multinivel

| Check ID | Descripción | Código a Verificar |
|----------|-------------|-------------------|
| E4-C01 | Costo R1 = 20 | `costs[0] == 20` |
| E4-C02 | Costo R2+ = 40 | `costs[1:] == [40, 40, ...]` |
| E4-C03 | 80 pips cierra exactamente 2 (20+40) | `closed_count == 2` |
| E4-C04 | Queue actualizada correctamente | `queue reduced by 2` |
| E4-C05 | Ratio 2:1 funciona | `2 éxitos recuperan 4 fallos` |

---

# LOGS ESPERADOS POR COMPONENTE

## CycleOrchestrator

```python
# Formato esperado
LOG_PATTERNS = {
    "cycle_create": "[INFO] [CycleOrchestrator] Ciclo {id} creado en estado {status}",
    "cycle_activate": "[INFO] [CycleOrchestrator] Ciclo {id} activado",
    "cycle_transition": "[DEBUG] [CycleOrchestrator] Ciclo {id}: {old_status} → {new_status}",
    "op_create": "[INFO] [CycleOrchestrator] Operación {id} creada: {type} {direction}",
    "op_activate": "[INFO] [CycleOrchestrator] Operación {id} activada a {price}",
    "op_close_tp": "[INFO] [CycleOrchestrator] Operación {id} cerrada con TP: +{pips} pips",
    "op_neutralize": "[INFO] [CycleOrchestrator] Neutralizando {id}",
    "recovery_start": "[INFO] [CycleOrchestrator] Iniciando Recovery N{level} para {cycle_id}",
    "both_active_warn": "[WARN] [CycleOrchestrator] ⚠️ AMBAS {type} ACTIVAS - Iniciando cobertura",
}
```

## RiskManager

```python
LOG_PATTERNS = {
    "validation_ok": "[DEBUG] [RiskManager] Validando {check}: {value}/{limit} OK",
    "validation_fail": "[WARN] [RiskManager] ⚠️ Límite {check} alcanzado: {value}/{limit}",
    "blocked": "[INFO] [RiskManager] Operación BLOQUEADA: {reason}",
    "emergency": "[CRITICAL] [RiskManager] 🚨 EMERGENCY STOP: {reason}",
}
```

## FIFOProcessor

```python
LOG_PATTERNS = {
    "process_start": "[INFO] [FIFOProcessor] Procesando {pips} pips según FIFO",
    "queue_state": "[DEBUG] [FIFOProcessor] Queue: {queue}",
    "closing": "[DEBUG] [FIFOProcessor] Cerrando {id}: costo {cost}, restante {remaining}",
    "complete": "[INFO] [FIFOProcessor] Cerradas {count} de {total} recoveries",
}
```

## BrokerAdapter

```python
LOG_PATTERNS = {
    "send_order": "[INFO] [BrokerAdapter] Enviando {type}: entry={entry}, tp={tp}",
    "order_confirmed": "[INFO] [BrokerAdapter] {type} confirmado: ticket={ticket}",
    "order_activated": "[INFO] [BrokerAdapter] {type} activado: ticket={ticket}, fill={price}",
    "tp_hit": "[INFO] [BrokerAdapter] TP alcanzado: ticket={ticket}, close={price}",
    "cancel": "[INFO] [BrokerAdapter] Cancelando orden: ticket={ticket}",
}
```

---

# VERIFICACIÓN DE IMPLEMENTACIÓN

## Checklist Pre-Test

Antes de ejecutar cada escenario, verificar:

- [ ] Logger configurado con formato correcto
- [ ] Todos los componentes inyectan logger
- [ ] Transiciones de estado loggean old → new
- [ ] Cálculos matemáticos loggean inputs y outputs
- [ ] Errores loggean stack trace completo
- [ ] Timestamps en formato ISO

## Checklist Post-Test

Después de ejecutar cada escenario:

- [ ] Comparar logs reales vs logs esperados
- [ ] Verificar cada check de la matriz
- [ ] Confirmar estados finales en DB
- [ ] Validar contabilidad matemática
- [ ] Revisar alertas enviadas (si aplica)

---

*Documento generado: 2026-01-05*
*Versión: 1.0*
*Complementa: testing.md*
