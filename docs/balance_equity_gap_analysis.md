# Balance vs Equity Gap Analysis

**Fecha:** 2026-01-13
**Estado:** 🔴 PROBLEMA CRÍTICO - Equity Drain Persiste
**Impacto:** Crítico - Balance y Equity fuertemente desincronizados

---

## 1. Resumen Ejecutivo

A pesar de que TODOS los fixes están aplicados correctamente:
- ✅ SimulatedBroker cierra posiciones automáticamente en TP
- ✅ Recovery cycles cierran sus operaciones cuando el ciclo cierra
- ✅ No hay posiciones con status="tp_hit" acumuladas

**El equity drain PERSISTE** con magnitud CRÍTICA:

### Test 1 (last_positions.json - 21:33:31):
- **344 posiciones abiertas**
- **-9,471.9 pips de P&L flotante**
- Esto representa aproximadamente **-947 EUR** de equity drain (asumiendo 0.10 EUR/pip)

### Test 2 (temp_positions.json - 21:59:26):
- **207 posiciones abiertas**
- **-51,497.3 pips de P&L flotante** ← 🚨 EXTREMADAMENTE GRAVE
- Esto representa aproximadamente **-5,150 EUR** de equity drain
- **91 posiciones con >500 pips** de P&L flotante (absoluto)

---

## 2. Distribución del P&L Flotante

### Test 1 (344 posiciones):
```
Positive P&L: 105 positions (+1,950.3 pips)
Negative P&L: 239 positions (-11,422.2 pips)
────────────────────────────────────────────
Net Floating:              -9,471.9 pips

Ratio: 2.27 posiciones negativas por cada positiva
Average negative: -47.8 pips por posición
```

### Test 2 (207 posiciones):
```
Positive P&L:  37 positions (+11,592.5 pips)
Negative P&L: 170 positions (-63,089.8 pips)
────────────────────────────────────────────
Net Floating:              -51,497.3 pips

Ratio: 4.59 posiciones negativas por cada positiva ← PEOR
Average positive: +313.3 pips por posición
Average negative: -371.1 pips por posición
```

---

## 3. Tipo de Posiciones Zombie

### Main Cycle Operations:
```
Ticket 1036: CYC_EURUSD_20260112221716_792_B (-562.7 pips)
Ticket 1044: CYC_EURUSD_20260112221716_285_B (-584.1 pips)
Ticket 1052: CYC_EURUSD_20260112221716_431_B (-549.5 pips)
```
**Problema:** Operaciones MAIN que nunca tocaron TP y nunca se cerraron.

### Recovery Operations:
```
Ticket 1022: REC_EURUSD_1_221715_B (-551.7 pips)
Ticket 1074: REC_EURUSD_1_221719_B (-569.5 pips)
```
**Problema:** Operaciones de recovery que quedaron abiertas cuando el recovery cycle cerró.

### Posiciones Más Extremas (Test 2):
```
Peores Pérdidas:
  Ticket 2162: -623.1 pips
  Ticket 2160: -622.4 pips
  Ticket 2158: -622.0 pips
  Ticket 2164: -617.0 pips
  Ticket 2178: -611.2 pips

Mayores Ganancias:
  Ticket 2167: +588.0 pips (neutralized)
  Ticket 1039: +533.7 pips (neutralized)
  Ticket 1033: +514.6 pips (neutralized)
```

---

## 4. Root Causes Identificados

### 4.1 Recovery Operations No Se Cierran
**Evidencia:** Tickets 1022, 1074 con -550 pips, son `REC_*` (recoveries)

**Causa:** El código en `cycle_orchestrator.py:838-852` intenta cerrar las operaciones del recovery, PERO:
1. El código se ejecuta DESPUÉS de que una operación del recovery toca TP
2. Las operaciones que YA tocaron TP se cierran correctamente (por el SimulatedBroker fix)
3. Las operaciones que AÚN NO tocaron TP tienen `status=ACTIVE`
4. El código DEBERÍA cerrarlas pero NO lo hace

**Hipótesis:** El código `lines 838-852` NO se está ejecutando, o `get_operations_by_cycle()` devuelve lista vacía.

### 4.2 Main Cycle Operations Nunca Cierran
**Evidencia:** Tickets 1036, 1044, 1052 con -550 a -580 pips, son `CYC_*` (main cycles)

**Causa:** Ciclos main que:
1. Entraron en estado IN_RECOVERY (porque alguna operación perdió)
2. Los recoveries tocaron TP y cerraron
3. El ciclo main sigue IN_RECOVERY o se marcó CLOSED
4. PERO las operaciones main (BUY/SELL) NUNCA se cerraron en el broker

**Problema:** No hay código que cierre las operaciones main cuando el recovery paga la deuda.

### 4.3 Posiciones con TP Inalcanzable
**Evidencia:** Posiciones con -600 pips cuando TP está a +80 pips

Las operaciones tienen TP establecidos (ejemplo: `1.25507` para una posición en `1.24707`), pero el precio se movió en dirección contraria por 600+ pips. Estas posiciones:
1. Nunca tocarán TP naturalmente
2. Deberían cerrarse manualmente cuando el recovery paga la deuda
3. NO se están cerrando

---

## 5. Impacto en Balance vs Equity

### Ejemplo Hipotético:
```
Balance: 11,000 EUR (ganancias realizadas)
Floating P&L: -5,150 EUR (posiciones zombie)
────────────────────────────────────────────
Equity: 5,850 EUR

Drawdown: (11,000 - 5,850) / 11,000 = 46.8% DD
```

Este DD es ARTIFICIAL - causado por posiciones que debieron cerrarse hace tiempo.

---

## 6. Verificación de Fixes Aplicados

### Fix 1: SimulatedBroker Auto-Close en TP ✅
**Archivo:** `tests/fixtures/simulated_broker.py:489-538`
```python
if tp_hit:
    tp_closures.append({...})

for closure in tp_closures:
    self.balance += Decimal(str(closure["pnl_money"]))
    self.history.append({...})
    del self.open_positions[ticket]  # ← CERRADO
```
**Status:** ✅ Funcionando - No hay posiciones con status="tp_hit"

### Fix 2: Recovery Cycle Operation Closure ⚠️
**Archivo:** `src/wsplumber/application/use_cases/cycle_orchestrator.py:838-852`
```python
recovery_ops_result = await self.repository.get_operations_by_cycle(recovery_cycle.id)
if recovery_ops_result.success:
    for op in recovery_ops_result.value:
        if op.broker_ticket and op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
            close_result = await self.trading_service.close_operation(op)
```
**Status:** ⚠️ Código existe pero NO ejecuta - 0 log entries "Closing recovery operation in broker"

**Hipótesis de por qué no ejecuta:**
- Las operaciones tienen `status=TP_HIT` cuando el código ejecuta (ya filtradas)
- O `get_operations_by_cycle()` falla/devuelve vacío
- O el código nunca se alcanza

---

## 7. Plan de Acción

### Prioridad 1: Verificar Por Qué Recovery Closure No Ejecuta
```bash
# Verificar si _handle_recovery_tp se llama
grep -c "Recovery TP hit, applying FIFO logic" audit_logs_*.log

# Verificar si el código de closure se alcanza
grep -c "CRÍTICO: Cerrar todas" audit_logs_*.log  # Esto es un comentario, no log

# Verificar cuántos recovery cycles cierran
grep -c "Recovery cycle closed after TP hit" audit_logs_*.log
```

### Prioridad 2: Implementar Cierre de Main Operations
Cuando un recovery paga la deuda de un ciclo main, las operaciones main deben cerrarse.

**Ubicación sugerida:** `cycle_orchestrator.py`, método `_handle_recovery_tp`, después de aplicar el FIFO:

```python
# Después de línea 792 (FIFO processing results)
# Si la deuda se pagó completamente, cerrar las operaciones main
if parent_cycle.accounting.pips_remaining == 0:
    logger.info("Debt fully paid, closing parent cycle main operations")
    parent_ops = await self.repository.get_operations_by_cycle(parent_cycle.id)
    if parent_ops.success:
        for op in parent_ops.value:
            if not op.is_recovery and op.broker_ticket:
                if op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                    await self.trading_service.close_operation(op)
```

### Prioridad 3: Agregar Logging Explícito
Modificar línea 844 para asegurar que el log se genera:
```python
logger.info("Closing recovery operation in broker",
           op_id=op.id,
           ticket=op.broker_ticket,
           status=op.status.value,
           cycle_id=recovery_cycle.id)  # ← Agregar cycle_id para tracking
```

---

## 8. Métricas de Validación

Después de implementar fixes, verificar:

### ✅ Success Criteria:
1. **Open Positions < 100** en test de 500k ticks
2. **Floating P&L < -1000 pips** (< -100 EUR)
3. **No posiciones con >200 pips** flotante (abs)
4. **Equity Gap < 5% del Balance**
5. **Log entries de "Closing recovery operation"** > 0

### 📊 Monitoreo:
```bash
# Posiciones totales
grep '"count":' audit_logs_*.log | tail -10

# P&L flotante total
python analyze_positions.py --show-summary

# Posiciones extremas
python analyze_positions.py --show-extremes --threshold=200
```

---

## 9. Conclusión

**Problema Principal:** Las posiciones NO se están cerrando cuando deberían:
1. Recovery operations quedan abiertas cuando el recovery cycle cierra
2. Main operations quedan abiertas cuando el recovery paga la deuda
3. Código de cierre existe pero no ejecuta correctamente

**Impacto:** Equity drain de -5,150 EUR en test de ~200 posiciones, haciendo que el sistema parezca no rentable cuando en realidad el Balance es positivo.

**Siguiente Paso:** Debugging profundo del flujo de cierre de recovery operations para entender por qué el código en líneas 838-852 no ejecuta.

---

**Autor:** Claude Code
**Revisado:** 2026-01-13
**Versión:** 1.0
