# Archivos que Requieren Actualización - Fix Cycle Renewal

**Fecha:** 2026-01-09
**Fix:** Main TP debe crear NUEVO ciclo (C2) en vez de renovar dentro del mismo ciclo (C1)

---

## 📋 Resumen del Cambio

### Comportamiento INCORRECTO (antes del fix)
```
TICK 1: C1 creado con 2 mains (OP_001, OP_002)
TICK 2: OP_002 (BUY) toca TP
TICK 3: Se renuevan mains DENTRO DE C1
  - C1 ahora tiene 4 mains: OP_001, OP_002, OP_003, OP_004
  - Acumulación infinita en el mismo ciclo
```

### Comportamiento CORRECTO (después del fix)
```
TICK 1: C1 creado con 2 mains (OP_001, OP_002)
TICK 2: OP_002 (BUY) toca TP
TICK 3: Se crea NUEVO CICLO C2
  - C1 queda con 2 mains (OP_001, OP_002)
  - C2 se crea con 2 mains nuevos (OP_003, OP_004)
  - C1 y C2 son INDEPENDIENTES
  - C1 queda en estado HEDGED/IN_RECOVERY
  - C2 opera normalmente en PENDING/ACTIVE
```

---

## 🔴 CRÍTICO - Requieren Actualización Inmediata

### 1. **docs/archive/expected_behavior_specification.md**

**Ubicación:** Líneas 225-310 (PASO 7 y ESTADO FINAL)

**Problema:**
- Describe renovación DENTRO del mismo ciclo (CYC_001)
- OP_003 y OP_004 se añaden a CYC_001
- `operations_count: 4` en CYC_001
- Dice "ITERACIÓN 2 (Activa)" pero dentro del mismo ciclo

**Debe cambiarse a:**
```yaml
# PASO 7: Crear Nuevo Ciclo C2 (NO renovar en C1)
[10:00:30.060] [INFO] [AccountingService] Balance actualizado: 10000 → 10002
[10:00:30.061] [DEBUG] [CycleOrchestrator] Ciclo CYC_001: TPs=1, pips_ganados=10
[10:00:30.062] [INFO] [CycleOrchestrator] Main tocó TP → CREANDO NUEVO CICLO
[10:00:30.063] [INFO] [CycleOrchestrator] *** ABRIENDO CICLO C2 (independiente de C1) ***
[10:00:30.064] [DEBUG] [CycleOrchestrator] C1 queda en estado HEDGED esperando recovery
[10:00:30.065] [INFO] [CycleOrchestrator] Nuevo ciclo CYC_002 creado
[10:00:30.066] [INFO] [BrokerAdapter] Enviando BUY_STOP para C2: entry=1.10140
[10:00:30.067] [INFO] [BrokerAdapter] Enviando SELL_STOP para C2: entry=1.10120
```

**Checks deben cambiar:**
```yaml
# ANTES (INCORRECTO):
- [ ] `len([op for op in cycle.operations if op.is_main and op.status == PENDING]) == 2`
- [ ] Nueva operación BUY: `id=OP_003, entry=1.10140, status=PENDING`
- [ ] Nueva operación SELL: `id=OP_004, entry=1.10120, status=PENDING`
- [ ] `cycle.status == CycleStatus.ACTIVE` (sin cambio)

# DESPUÉS (CORRECTO):
- [ ] `len(repo.cycles.values()) == 2` (C1 + C2)
- [ ] C1 tiene exactamente 2 mains (OP_001, OP_002)
- [ ] C1 status: HEDGED o IN_RECOVERY
- [ ] C2 existe como ciclo independiente
- [ ] C2 tiene 2 mains propios (OP_003, OP_004)
- [ ] C2 status: PENDING o ACTIVE
- [ ] OP_003.cycle_id == CYC_002 (NO CYC_001)
- [ ] OP_004.cycle_id == CYC_002 (NO CYC_001)
```

**Estado final debe cambiar:**
```yaml
# ANTES (INCORRECTO):
cycle:
  id: CYC_001
  status: ACTIVE  # Continúa operando
  operations_count: 4  # 2 cerradas/canceladas + 2 nuevas pendientes

# DESPUÉS (CORRECTO):
cycles:
  - id: CYC_001
    status: HEDGED  # Esperando recovery
    operations_count: 2  # Exactamente 2 mains

  - id: CYC_002
    status: PENDING  # Nuevo ciclo operando
    operations_count: 2  # Sus propias 2 mains
```

---

### 2. **tests/test_renewal_flow.py**

**Ubicación:** Líneas 57-209 (test_tp_triggers_main_renewal)

**Problema:**
- Línea 200: `assert len(main_new_ops) >= 2` - busca operaciones nuevas en el mismo repositorio
- Espera que las nuevas mains estén en la misma lista de operaciones
- No verifica existencia de C2

**Debe cambiarse a:**
```python
# ANTES (líneas 173-200):
all_ops = list(repo.operations.values())
new_ops = [op for op in all_ops if op.id not in original_op_ids]
main_new_ops = [op for op in new_ops if op.is_main]
assert len(main_new_ops) >= 2, f"Deben haber 2 nuevas ops main, encontradas: {len(main_new_ops)}"

# DESPUÉS:
# 1. Verificar que se creó C2
all_cycles = list(repo.cycles.values())
main_cycles = [c for c in all_cycles if c.cycle_type == CycleType.MAIN]
assert len(main_cycles) >= 2, f"Debe haber 2 ciclos MAIN (C1+C2), hay {len(main_cycles)}"

# 2. Verificar C1 tiene exactamente 2 mains
c1 = main_cycles[0]
c1_mains = [op for op in repo.operations.values() if op.cycle_id == c1.id and op.is_main]
assert len(c1_mains) == 2, f"C1 debe tener EXACTAMENTE 2 mains, tiene {len(c1_mains)}"

# 3. Verificar C2 existe y tiene 2 mains
c2 = main_cycles[1]
c2_mains = [op for op in repo.operations.values() if op.cycle_id == c2.id and op.is_main]
assert len(c2_mains) == 2, f"C2 debe tener 2 mains, tiene {len(c2_mains)}"

# 4. Verificar independencia
assert c2.id != c1.id, "C2 debe ser ciclo diferente de C1"
assert all(op.cycle_id == c2.id for op in c2_mains), "Mains de C2 deben pertenecer a C2"
```

---

## 🟡 IMPORTANTE - Requieren Actualización

### 3. **docs/ws_plumber_system.md**

**Ubicación:** Líneas 56-62 (Escenario 1: Resolución Simple)

**Problema:**
- Línea 61: "Se reinicia otro ciclo principal" (ambiguo)
- No especifica si es MISMO ciclo o NUEVO ciclo

**Debe aclararse:**
```markdown
# ANTES:
### Escenario 1: Resolución Simple
1. Se abren dos operaciones principales (buy stop y sell stop)
2. Una se activa y llega a TP (+10 pips)
3. Se cierra la otra pendiente
4. Se reinicia otro ciclo principal

# DESPUÉS:
### Escenario 1: Resolución Simple
1. Se abren dos operaciones principales (buy stop y sell stop) en Ciclo C1
2. Una se activa y llega a TP (+10 pips)
3. Se cierra la otra pendiente
4. ✅ Se crea un NUEVO CICLO independiente (C2) con nuevas mains
5. C1 queda con exactamente 2 mains (no se renuevan dentro de C1)
6. C2 opera independientemente mientras C1 espera recovery (si aplica)
```

---

### 4. **docs/debug_reference.md**

**Ubicación:** Línea 53-54, 324

**Estado:** ✅ YA ESTÁ CORRECTO
```
Línea 53: "6. Abrir nuevo ciclo (renovación)"
Línea 324: "Nuevo ciclo se abre"
```

**No requiere cambios** - Ya especifica que se abre un "nuevo ciclo".

---

## 🟢 OPCIONAL - Archivos de Auditoría/Históricos

### 5. **docs/backtest_500_audit.md**
### 6. **docs/backtest_quick_audit.md**
### 7. **docs/segment_1_audit.md**

**Estado:** Archivos de auditoría con logs del comportamiento ANTIGUO

**Decisión:**
- ❌ NO actualizar (son registros históricos del bug)
- ✅ Añadir nota al inicio indicando que reflejan comportamiento pre-fix

**Nota a añadir:**
```markdown
> ⚠️ **NOTA:** Este archivo documenta el comportamiento del sistema ANTES del fix
> de cycle renewal (2026-01-09). El comportamiento descrito aquí (renovación
> dentro del mismo ciclo) era INCORRECTO. Ver `docs/bug_fix_cycle_renewal.md`
> para el comportamiento correcto.
```

---

## 🔵 INFORMATIVOS - Archivos de Contexto

### 8. **docs/archive/FIXES_APPLIED_SUMMARY.md**

**Ubicación:** Archivo de resumen de fixes

**Acción:** Añadir entrada del fix:
```markdown
## FIX-CRITICAL: Cycle Renewal Creates New Cycle (2026-01-09)

**Issue:** Main TP renovaba operaciones dentro del mismo ciclo (C1), causando acumulación infinita.

**Fix:** Main TP ahora crea un NUEVO ciclo independiente (C2).

**Files Changed:**
- `cycle_orchestrator.py`: Reemplazada llamada `_renew_main_operations` por `_open_new_cycle`
- `cycle_orchestrator.py`: Validación contextual para permitir múltiples ciclos

**Impact:** CRÍTICO - Sistema ahora puede cerrar ciclos correctamente via FIFO.

**Documentation:** `docs/bug_fix_cycle_renewal.md`
```

---

## 📊 Resumen de Prioridades

| Archivo | Prioridad | Estado | Acción |
|---------|-----------|--------|--------|
| `expected_behavior_specification.md` | 🔴 CRÍTICO | ❌ Pendiente | Actualizar PASO 7 completo |
| `test_renewal_flow.py` | 🔴 CRÍTICO | ❌ Pendiente | Refactorizar validaciones |
| `ws_plumber_system.md` | 🟡 IMPORTANTE | ❌ Pendiente | Aclarar Escenario 1 |
| `debug_reference.md` | 🟢 INFO | ✅ Correcto | Sin cambios |
| `backtest_*_audit.md` | 🟢 HISTÓRICO | ⚠️ Añadir nota | Marcar como pre-fix |
| `FIXES_APPLIED_SUMMARY.md` | 🔵 INFO | ❌ Pendiente | Añadir entrada |

---

## 🚀 Plan de Ejecución

### Paso 1: Archivos Críticos (Hoy)
1. ✅ Actualizar `expected_behavior_specification.md` PASO 7
2. ✅ Actualizar `test_renewal_flow.py::test_tp_triggers_main_renewal`
3. ✅ Verificar que test pasa

### Paso 2: Documentación (Hoy)
4. ✅ Actualizar `ws_plumber_system.md` Escenario 1
5. ✅ Añadir nota en archivos de auditoría
6. ✅ Actualizar `FIXES_APPLIED_SUMMARY.md`

### Paso 3: Validación (Hoy)
7. ✅ Ejecutar suite completa de tests
8. ✅ Verificar que documentación es consistente
9. ✅ Commit de todos los cambios

---

## 📝 Notas Adicionales

- **Nomenclatura:** Usar "NUEVO CICLO (C2)" no "renovar en C1"
- **Tests:** Verificar `cycle_id` de operaciones nuevas
- **Estados:** C1 queda HEDGED/IN_RECOVERY, C2 en PENDING/ACTIVE
- **FIFO:** C1 se cierra cuando recovery compensa, C2 opera independiente

---

*Documento generado: 2026-01-09*
*Complementa: bug_fix_cycle_renewal.md*
