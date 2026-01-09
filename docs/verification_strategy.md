# Estrategia de Verificación Robusta - WSPlumber

**Fecha:** 2026-01-09
**Contexto:** Fix Cycle Renewal (C1 → C2)

---

## 🎯 Objetivo

Responder a la pregunta crítica:
> "¿Cómo verificamos que el sistema se comporta correctamente más allá de que los tests pasen?"

---

## ❌ Problema: Tests Pueden Pasar con Bugs Críticos

### Ejemplo Real: Gap Crítico
**Situación:** Tests pasaban pero había gaps críticos en el comportamiento.

**Por qué pasaban:**
- Tests verificaban condiciones **mínimas** (ej. "operación existe")
- NO verificaban **invariantes críticos** (ej. "exactamente 2 mains por ciclo")
- NO verificaban **flujo completo** (ej. "C1 cerró → C2 abierto → C1 NO acumula")

**Resultado:** Falsa sensación de seguridad ❌

---

## ✅ Solución: Verificación en Múltiples Capas

### Capa 1: Tests Unitarios con Validaciones Críticas ⭐

**Principio:** Cada test debe verificar **invariantes del sistema**, no solo "funciona".

#### Ejemplo: Test de Renovación ANTES del fix
```python
# ❌ MALO - Validación débil
assert len(main_new_ops) >= 2  # Solo verifica que hay operaciones nuevas

# ✅ BUENO - Validación de invariantes
assert len(main_cycles) == 2, "Debe haber exactamente 2 ciclos (C1+C2)"
assert len(c1_mains) == 2, "C1 debe tener EXACTAMENTE 2 mains (no acumulación)"
assert len(c2_mains) == 2, "C2 debe tener 2 mains propios"
assert c2.id != c1.id, "C2 debe ser ciclo independiente"
assert all(op.cycle_id == c2.id for op in c2_mains), "Mains de C2 pertenecen a C2"
```

**Invariantes Críticos del Sistema WSPlumber:**

| Invariante | Validación | ¿Por qué es crítico? |
|------------|------------|----------------------|
| Cada ciclo tiene exactamente 2 mains | `len(cycle.mains) == 2` | Evita acumulación infinita |
| Mains pertenecen al ciclo correcto | `op.cycle_id == cycle.id` | FIFO contabilidad correcta |
| Un solo ciclo activo en PENDING/ACTIVE por par | `len([c for c in cycles if c.status in [PENDING, ACTIVE] and c.pair == pair]) <= 1` | Evita duplicados |
| Recovery solo cuando HEDGED | `cycle.status == HEDGED before recovery` | Lógica de cobertura correcta |
| C1 NO acumula tras renewal | `len(c1.mains) == 2 after renewal` | Fix crítico verificado |

---

### Capa 2: Backtest con Auditoría Detallada 📊

**Principio:** Ejecutar flujos reales y **auditar cada paso**.

#### Paso 1: Backtest Instrumentado
```bash
# Backtest corto con logging detallado
python -m wsplumber.backtest \
  --data "2026.1.5EURUSD_M1.csv" \
  --max-ticks 100 \
  --log-level DEBUG \
  --output backtest_audit_100ticks.log
```

#### Paso 2: Auditoría Manual con Checklist

**Checklist de Auditoría Post-Backtest:**

- [ ] **Conteo de Ciclos**
  - Total ciclos creados: `grep "Ciclo .* creado" backtest_audit.log | wc -l`
  - Ciclos MAIN vs RECOVERY: Verificar proporción esperada

- [ ] **Validación de Mains por Ciclo**
  ```bash
  # Por cada ciclo, contar sus mains
  for cycle_id in $(grep "Ciclo" backtest_audit.log | awk '{print $2}' | sort -u); do
    count=$(grep "cycle_id=$cycle_id.*MAIN" backtest_audit.log | wc -l)
    if [ $count -ne 2 ]; then
      echo "❌ ERROR: Ciclo $cycle_id tiene $count mains (esperado: 2)"
    fi
  done
  ```

- [ ] **Flujo de Renovación**
  ```bash
  # Verificar que cada renovación crea un NUEVO ciclo
  grep "renewal_after_main_tp" backtest_audit.log | while read line; do
    # Verificar que el siguiente log es "Ciclo X creado" con X diferente
  done
  ```

- [ ] **Estados Finales**
  - Ciclos en IN_RECOVERY: ¿Tienen recovery pendiente?
  - Ciclos CLOSED: ¿FIFO resolvió deuda?
  - Operaciones huérfanas: ¿Hay operaciones sin ciclo?

---

### Capa 3: Snapshots de Estado 📸

**Principio:** Capturar estado del sistema en puntos críticos y comparar con estado esperado.

#### Implementación

```python
# En cycle_orchestrator.py - Añadir snapshot en momentos clave
def _take_snapshot(self, event: str, tick: TickData):
    """Captura snapshot del estado del sistema."""
    snapshot = {
        "timestamp": tick.timestamp,
        "event": event,
        "cycles": [
            {
                "id": c.id,
                "status": c.status.value,
                "mains_count": len([op for op in c.operations if op.is_main]),
                "mains_ids": [op.id for op in c.operations if op.is_main]
            }
            for c in self.repository.cycles.values()
        ],
        "total_operations": len(self.repository.operations)
    }

    # Guardar en JSON para auditoría
    with open(f"snapshots/snapshot_{event}_{tick.timestamp}.json", "w") as f:
        json.dump(snapshot, f, indent=2)

    return snapshot

# Llamar en momentos críticos:
# - Antes/después de crear ciclo
# - Antes/después de TP
# - Antes/después de activar hedge
# - Antes/después de recovery
```

**Ventaja:** Puedes reproducir el estado exacto y compararlo con expectativa.

---

### Capa 4: Diff de Comportamiento (Antes vs Después) 🔍

**Principio:** Ejecutar mismo backtest ANTES y DESPUÉS del fix, comparar outputs.

#### Paso 1: Backtest Pre-Fix (baseline)
```bash
# Checkout a commit ANTES del fix
git checkout <commit-before-fix>
python -m wsplumber.backtest --data test.csv --output baseline.json

# Estructura del output:
{
  "cycles": [{"id": "C1", "mains_count": 4}],  # ❌ Acumulación
  "total_tps": 2
}
```

#### Paso 2: Backtest Post-Fix
```bash
# Checkout a commit DESPUÉS del fix
git checkout <commit-after-fix>
python -m wsplumber.backtest --data test.csv --output fixed.json

# Estructura del output:
{
  "cycles": [
    {"id": "C1", "mains_count": 2},
    {"id": "C2", "mains_count": 2}
  ],
  "total_tps": 2
}
```

#### Paso 3: Diff Automático
```python
# diff_behavior.py
import json

baseline = json.load(open("baseline.json"))
fixed = json.load(open("fixed.json"))

# Validar fix
assert len(fixed["cycles"]) > len(baseline["cycles"]), "Debe crear más ciclos"
for cycle in fixed["cycles"]:
    assert cycle["mains_count"] == 2, f"Ciclo {cycle['id']} tiene {cycle['mains_count']} mains"

print("✅ Fix verificado: Comportamiento cambió como esperado")
```

---

### Capa 5: Property-Based Testing 🎲

**Principio:** Generar casos aleatorios y verificar que invariantes SIEMPRE se cumplen.

#### Ejemplo con Hypothesis

```python
from hypothesis import given, strategies as st

@given(
    num_ticks=st.integers(min_value=10, max_value=1000),
    price_movements=st.lists(st.floats(min_value=0.999, max_value=1.001), min_size=10, max_size=1000)
)
def test_cycle_renewal_invariants(num_ticks, price_movements):
    """Test con datos aleatorios - invariantes deben cumplirse SIEMPRE."""

    # Setup con movimientos de precio aleatorios
    broker = SimulatedBroker()
    orchestrator = setup_orchestrator()

    # Ejecutar backtest con precios aleatorios
    for i, movement in enumerate(price_movements[:num_ticks]):
        tick = create_tick_with_movement(movement)
        await orchestrator.process_tick(tick)

    # INVARIANTES que DEBEN cumplirse SIEMPRE
    all_cycles = list(repo.cycles.values())

    # Invariante 1: Cada ciclo tiene exactamente 2 mains
    for cycle in all_cycles:
        mains = [op for op in repo.operations.values()
                 if op.cycle_id == cycle.id and op.is_main]
        assert len(mains) == 2, f"Ciclo {cycle.id} tiene {len(mains)} mains"

    # Invariante 2: No hay ciclos duplicados para el mismo par en PENDING/ACTIVE
    active_cycles_by_pair = {}
    for cycle in all_cycles:
        if cycle.status in [CycleStatus.PENDING, CycleStatus.ACTIVE]:
            if cycle.pair in active_cycles_by_pair:
                assert False, f"Par {cycle.pair} tiene múltiples ciclos activos"
            active_cycles_by_pair[cycle.pair] = cycle

    # Invariante 3: Operaciones pertenecen al ciclo correcto
    for op in repo.operations.values():
        assert op.cycle_id in [c.id for c in all_cycles], \
            f"Operación {op.id} huérfana (cycle_id={op.cycle_id})"
```

**Ventaja:** Encuentra edge cases que no pensaste manualmente.

---

## 📋 Checklist de Verificación Completa

### Pre-Commit
- [ ] Tests unitarios pasan con validaciones de invariantes
- [ ] No hay warnings de tipo/linter
- [ ] Código revisado manualmente

### Post-Commit (Antes de Merge)
- [ ] Backtest corto (100 ticks) auditado manualmente
- [ ] Snapshots de estado verificados en puntos críticos
- [ ] Diff de comportamiento vs baseline confirmado

### Pre-Producción
- [ ] Backtest largo (5000+ ticks) sin errores
- [ ] Property-based tests ejecutados (100+ casos aleatorios)
- [ ] Métricas de producción monitoreadas:
  - Ciclos activos por par (no debe crecer infinitamente)
  - Tiempo promedio en IN_RECOVERY
  - Ratio de ciclos cerrados correctamente

---

## 🚀 Herramientas Recomendadas

### 1. Script de Auditoría Automática
```bash
#!/bin/bash
# audit_backtest.sh

echo "🔍 Auditando backtest..."

# Ejecutar backtest con logging detallado
python -m wsplumber.backtest \
  --data "$1" \
  --max-ticks 100 \
  --log-level DEBUG \
  --output audit.log

# Verificar invariantes
echo "\n📊 Verificando invariantes..."

# Invariante 1: Mains por ciclo
echo "- Mains por ciclo:"
python << 'EOF'
import re
logs = open("audit.log").read()

cycles = {}
for line in logs.split("\n"):
    if "cycle_id=" in line and "MAIN" in line:
        cycle_id = re.search(r'cycle_id=([A-Z0-9_]+)', line).group(1)
        cycles[cycle_id] = cycles.get(cycle_id, 0) + 1

errors = []
for cycle_id, count in cycles.items():
    if count != 2:
        errors.append(f"  ❌ {cycle_id}: {count} mains (esperado: 2)")
    else:
        print(f"  ✅ {cycle_id}: 2 mains")

if errors:
    print("\n".join(errors))
    exit(1)
EOF

echo "\n✅ Auditoría completada - Sin errores"
```

### 2. Dashboard de Monitoreo
```python
# monitoring_dashboard.py
import streamlit as st
import pandas as pd

# Cargar datos de backtest
df = pd.read_json("backtest_results.json")

st.title("WSPlumber - Monitoring Dashboard")

# Métrica 1: Ciclos activos por tiempo
st.line_chart(df.groupby("timestamp")["active_cycles"].count())

# Métrica 2: Distribución de mains por ciclo
mains_per_cycle = df.groupby("cycle_id")["mains_count"].first()
st.bar_chart(mains_per_cycle.value_counts())

# ❌ ALERTA si algún ciclo tiene != 2 mains
if (mains_per_cycle != 2).any():
    st.error(f"⚠️ ALERTA: Ciclos con mains != 2: {mains_per_cycle[mains_per_cycle != 2].to_dict()}")
```

---

## 🎓 Lecciones del Fix Cycle Renewal

### ¿Qué funcionó?
1. ✅ **Test con validaciones de invariantes** (`test_cycle_renewal_fix.py`)
   - Verificó EXACTAMENTE 2 mains en C1
   - Verificó C2 independiente
   - Verificó NO acumulación

2. ✅ **Descripción detallada paso a paso**
   - Logs en cada tick mostraron flujo completo
   - Debug output visible ayudó a detectar timing issues

### ¿Qué faltó?
1. ❌ **Backtest instrumentado** - Ejecutar en datos reales
2. ❌ **Snapshots de estado** - Capturar estado en cada paso
3. ❌ **Property-based testing** - Probar con casos aleatorios

---

## 📖 Recomendación Final

**Para cada fix crítico:**

1. **Primero:** Test unitario con invariantes (como `test_cycle_renewal_fix.py`) ✅
2. **Segundo:** Backtest corto (100 ticks) con auditoría manual 📊
3. **Tercero:** Snapshots en puntos críticos + diff vs baseline 📸
4. **Cuarto:** Property-based testing (opcional, para alta criticidad) 🎲

**Tiempo estimado:**
- Test unitario: 1-2 horas ✅ (ya hecho)
- Backtest + auditoría: 30 minutos
- Snapshots: 1 hora
- Property-based: 2-3 horas (opcional)

---

## 🔗 Referencias

- Test de verificación: `tests/test_cycle_renewal_fix.py`
- Fix documentado: `docs/bug_fix_cycle_renewal.md`
- Archivos actualizados: `docs/files_to_update_cycle_renewal.md`

---

*Documento creado: 2026-01-09*
*Autor: Claude (Assistant)*
*Propósito: Guía para verificación robusta más allá de "tests passing"*
