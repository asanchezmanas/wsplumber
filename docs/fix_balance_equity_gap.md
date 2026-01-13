# Fix: Balance vs Equity Gap - Zombie Positions

**Fecha:** 2026-01-13
**Estado:** ✅ IMPLEMENTADO - Pendiente Testing
**Impacto:** Crítico - Cierra posiciones zombie que causan equity drain

---

## 1. Problema Identificado

### Síntomas (Ver: balance_equity_gap_analysis.md)

- **Equity drain masivo**: -51,497 pips en 207 posiciones (test temp_positions.json)
- **Posiciones zombie**: 91 posiciones con >500 pips de P&L flotante
- **Dos tipos de zombies**:
  1. Main operations que nunca cierran (-550 a -600 pips)
  2. Recovery operations que quedan abiertas cuando el recovery cycle cierra

### Root Causes

1. **Recovery operations no se cierran**: Código existía (líneas 838-852) pero no ejecutaba o ejecutaba después de que las operaciones ya estaban cerradas por el broker
2. **Main operations nunca cierran**: No existía código para cerrar las operaciones main cuando un recovery paga la deuda completamente

---

## 2. Fixes Implementados

### Fix 1: Enhanced Logging para Recovery Closure

**Archivo:** `src/wsplumber/application/use_cases/cycle_orchestrator.py`
**Líneas:** 835-900

**Cambios:**
1. Agregado logging ANTES de intentar obtener recovery operations
2. Agregado logging del resultado de `get_operations_by_cycle()`
3. Agregado logging de cada operación (cerrada vs skipped)
4. Agregado summary con contadores (closed/skipped)

**Ejemplo de logs que ahora se generan:**
```
FIX-RECOVERY-CLOSURE: Attempting to close recovery operations
  recovery_id: REC_EURUSD_1_221715
  parent_id: CYC_EURUSD_20260112221715_812

Recovery operations fetched
  recovery_id: REC_EURUSD_1_221715
  total_ops: 4
  op_statuses: ["REC_..._B:ACTIVE", "REC_..._S:TP_HIT", "REC_..._B:ACTIVE", "REC_..._S:CLOSED"]

Closing recovery operation in broker
  op_id: REC_EURUSD_1_221715_B
  ticket: 1022
  status: active
  recovery_id: REC_EURUSD_1_221715

Recovery operation closed successfully
  op_id: REC_EURUSD_1_221715_B
  ticket: 1022

Recovery operations closure summary
  recovery_id: REC_EURUSD_1_221715
  total: 4
  closed: 2
  skipped: 2
```

**Por qué esto ayuda:**
- Permite debugging del flujo completo
- Identifica si `get_operations_by_cycle()` falla o devuelve vacío
- Muestra exactamente cuántas operaciones se cierran vs se saltan
- Identifica el status de cada operación

---

### Fix 2: Main Operations Closure After Debt Paid ⭐ CRÍTICO

**Archivo:** `src/wsplumber/application/use_cases/cycle_orchestrator.py`
**Líneas:** 794-844

**Cambios:**
Agregado código para cerrar TODAS las operaciones main cuando `pips_remaining == 0`:

```python
# FIX-MAIN-OPERATIONS-CLOSURE: Cerrar operaciones main cuando la deuda se paga completamente
if parent_cycle.accounting.pips_remaining == 0:
    logger.info("FIX-MAIN-OPERATIONS: Debt fully paid, closing parent cycle main operations")

    parent_ops_result = await self.repository.get_operations_by_cycle(parent_cycle.id)
    if parent_ops_result.success:
        for op in parent_ops_result.value:
            # Solo cerrar operaciones MAIN (no recovery) que estén activas
            if not op.is_recovery and op.broker_ticket:
                if op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
                    await self.trading_service.close_operation(op)
```

**Flujo:**
1. Recovery toca TP y paga deuda al padre
2. Se calcula `pips_remaining` después del FIFO
3. **SI** `pips_remaining == 0` → La deuda está completamente pagada
4. **ENTONCES** cerrar TODAS las operaciones main del ciclo padre
5. Esto incluye BUY y SELL que nunca tocaron TP

**Ejemplo:**
```
Ciclo Main CYC_123 con operaciones:
  - BUY ticket 1036 (TP +100 pips, actualmente -550 pips) ← Zombie
  - SELL ticket 1037 (cerrada en TP)

Recovery REC_1 paga deuda:
  - pips_remaining pasa de 140 → 0

✅ FIX-MAIN-OPERATIONS se activa:
  - Cierra ticket 1036 en -550 pips (realiza la pérdida)
  - Ticket 1037 ya cerrado, se salta

Resultado:
  - Balance baja por -55 EUR (pérdida realizada)
  - Equity SUBE porque ya no hay -550 pips flotantes
  - Gap balance-equity se reduce
```

**Por qué es crítico:**
- Las operaciones main con TP inalcanzable (-600 pips) NUNCA cerrarían naturalmente
- Causan equity drain masivo
- Con este fix, se cierran cuando el recovery paga la deuda, realizando la pérdida
- Esto es CORRECTO: el recovery ya compensó la pérdida, las main deben cerrarse

---

## 3. Lógica del Cierre de Main Operations

### Cuándo se cierra:
```
Condición: parent_cycle.accounting.pips_remaining == 0
```

Esto significa que el sistema FIFO ya aplicó todos los profits de recovery y pagó todas las deudas.

### Qué se cierra:
```python
if not op.is_recovery and op.broker_ticket:
    if op.status not in (OperationStatus.CLOSED, OperationStatus.CANCELLED):
        # Cerrar
```

Solo operaciones que:
1. ✅ Son MAIN (no recovery)
2. ✅ Tienen broker ticket (están en el broker)
3. ✅ NO están ya cerradas o canceladas

### Qué NO se cierra:
- ❌ Recovery operations (esas se cierran en líneas 835-900)
- ❌ Operaciones ya cerradas (status CLOSED)
- ❌ Operaciones canceladas (status CANCELLED)
- ❌ Operaciones sin ticket (pendientes)

---

## 4. Impacto Esperado

### Antes del Fix:
```
Test: 207 posiciones
Floating P&L: -51,497 pips (-5,150 EUR)
Zombie positions: 91 con >500 pips

Balance: 11,000 EUR
Equity: 5,850 EUR (-46.8% DD)
```

### Después del Fix:
```
Test: ~50-80 posiciones (esperado)
Floating P&L: -500 a -1,000 pips (-50 a -100 EUR)
Zombie positions: 0 con >500 pips

Balance: ~10,500 EUR (baja por pérdidas realizadas)
Equity: ~10,400 EUR
Gap: <5% (solo P&L normal flotante)
```

**Nota:** El balance BAJARÁ inicialmente porque se realizan las pérdidas de las posiciones zombie, pero el equity SUBIRÁ porque ya no hay -50k pips flotantes. El gap balance-equity se reducirá dramáticamente.

---

## 5. Logs para Verificación

### Logs de Recovery Closure:
```bash
# Verificar que recovery operations se cierran
grep "FIX-RECOVERY-CLOSURE: Attempting to close" audit_logs_*.log | wc -l
# Esperado: >0 (cada vez que un recovery cycle cierra)

# Verificar operaciones cerradas
grep "Recovery operation closed successfully" audit_logs_*.log | wc -l
# Esperado: >0

# Ver summary
grep "Recovery operations closure summary" audit_logs_*.log | tail -10
```

### Logs de Main Operations Closure:
```bash
# Verificar que main operations se cierran cuando deuda = 0
grep "FIX-MAIN-OPERATIONS: Debt fully paid" audit_logs_*.log | wc -l
# Esperado: >0 (cada vez que un recovery paga toda la deuda)

# Verificar operaciones main cerradas
grep "Main operation closed successfully after debt paid" audit_logs_*.log | wc -l
# Esperado: >0 (al menos algunas main operations zombie)

# Ver summary
grep "Main operations closure summary" audit_logs_*.log | tail -10
```

### Análisis de Posiciones:
```bash
# Verificar que no hay zombies extremos
python -c "
import json
import re

with open('last_positions.json', 'r') as f:
    content = f.read()
    match = re.search(r'\{\"timestamp.*\}', content)
    data = json.loads(match.group(0))
    positions = data['data']['positions']

extreme = [p for p in positions if abs(p['pips']) > 500]
print(f'Positions with >500 pips: {len(extreme)}')
# Esperado: 0 o muy pocos

total_pips = sum(p['pips'] for p in positions)
print(f'Total floating P&L: {total_pips:.1f} pips')
# Esperado: < -1000 pips
"
```

---

## 6. Casos Edge

### Case 1: Recovery cierra pero aún hay deuda pendiente
```
pips_remaining = 60 pips (aún hay deuda)
→ Main operations NO se cierran
→ Se abre nuevo recovery
→ CORRECTO: aún se necesita recuperar
```

### Case 2: Deuda = 0 pero surplus < 20 pips
```
pips_remaining = 0
surplus = 15 pips
→ Main operations SÍ se cierran (FIX-MAIN-OPERATIONS)
→ Se abre nuevo recovery (lógica línea 816-830)
→ CORRECTO: deuda pagada, posiciones main cerradas, se sigue recuperando
```

### Case 3: Deuda = 0 y surplus >= 20 pips
```
pips_remaining = 0
surplus = 25 pips
→ Main operations SÍ se cierran (FIX-MAIN-OPERATIONS)
→ Cycle se cierra completamente (línea 848-860)
→ CORRECTO: todo resuelto
```

---

## 7. Testing

### Test Script:
```bash
# Ejecutar test pequeño
python scripts/audit_scenario.py "tests/scenarios/2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.csv"

# Durante el test, en otra terminal:
tail -f audit_logs_*.log | grep -E "(FIX-RECOVERY|FIX-MAIN|closed successfully)"

# Al finalizar:
python analyze_positions.py --last
```

### Success Criteria:
1. ✅ Log entries de "FIX-RECOVERY-CLOSURE" > 0
2. ✅ Log entries de "FIX-MAIN-OPERATIONS" > 0
3. ✅ Open positions < 100 al final del test
4. ✅ Floating P&L < -1000 pips
5. ✅ No posiciones con >500 pips (abs)

---

## 8. Rollback Plan

Si los fixes causan problemas:

### Rollback Fix 1 (Enhanced Logging):
No necesario - solo logging, no afecta lógica

### Rollback Fix 2 (Main Operations Closure):
```bash
git diff src/wsplumber/application/use_cases/cycle_orchestrator.py

# Revertir solo las líneas 794-844
git checkout HEAD~1 -- src/wsplumber/application/use_cases/cycle_orchestrator.py
```

O comentar el bloque:
```python
# FIX-MAIN-OPERATIONS-CLOSURE: Comentado temporalmente
# if parent_cycle.accounting.pips_remaining == 0:
#     ...
```

---

## 9. Archivos Modificados

### Core Fix:
- `src/wsplumber/application/use_cases/cycle_orchestrator.py`:
  - Líneas 794-844: FIX-MAIN-OPERATIONS-CLOSURE
  - Líneas 835-900: Enhanced logging para recovery closure

### Documentación:
- `docs/balance_equity_gap_analysis.md`: Análisis del problema
- `docs/fix_balance_equity_gap.md`: Este documento (implementación)

---

## 10. Conclusión

Se han implementado dos fixes críticos:

1. **Enhanced Logging** ✅
   - Permite debugging del cierre de recovery operations
   - Identifica problemas en el flujo de cierre
   - No afecta lógica, solo observabilidad

2. **Main Operations Closure** ⭐
   - Cierra operaciones main cuando la deuda se paga
   - Elimina las posiciones zombie más graves (-600 pips)
   - Reduce dramáticamente el gap balance-equity
   - Este es el fix CRÍTICO para el equity drain

**Próximo Paso:** Ejecutar test para validar que los fixes funcionan correctamente.

---

**Autor:** Claude Code
**Revisado:** 2026-01-13
**Versión:** 1.0
