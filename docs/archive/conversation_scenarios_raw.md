Análisis de tu situación
Tienes:

Índice completo: 62 escenarios catalogados con prioridades
Especificación detallada: 4 escenarios explicados exhaustivamente con logs, checks y estados
Código implementado: Con los 3 fixes aplicados (FIX-001, FIX-002, FIX-003)

Mis recomendaciones
📋 Sobre documentar los 62 escenarios
NO necesitas explicar los 62 con el mismo nivel de detalle que los 4 actuales. Sería:

❌ Repetitivo (muchos son variaciones)
❌ Difícil de mantener
❌ No agrega valor real

En su lugar, te recomiendo:
markdown# Estrategia de Documentación en Capas

## Capa 1: Índice Maestro (ya lo tienes)
- Lista de 62 escenarios con ID, prioridad y descripción breve
- Sirve como mapa de cobertura

## Capa 2: Especificación Detallada (4-6 escenarios críticos)
- Escenarios que definen el comportamiento core
- Con logs completos, checks y estados esperados
- Los que ya tienes: E1 (Ciclo simple), E2 (Hedge), E3 (Recovery FIFO), E4 (Multinivel)
- Podrías añadir 1-2 más si representan casos únicos

## Capa 3: Matriz de Checks (para el resto)
- Tabla compacta con: Escenario | Input | Output esperado | Checks críticos
- Sin logs detallados, solo assertions clave
🎯 Lo que SÍ deberías crear
1. Matriz Compacta de Escenarios (en el mismo expected_behavior_specification_fixed.md)
Añade al final del documento actual:
markdown# APÉNDICE: MATRIZ DE VALIDACIÓN (58 ESCENARIOS RESTANTES)

## Core (1 restante)

| ID | Input | Output Esperado | Checks Críticos |
|----|-------|-----------------|-----------------|
| c04_no_activation | price=1.09990 (no alcanza entry) | status=PENDING | ✓ No broker calls<br>✓ status unchanged |

## Cycles (2 restantes)

| ID | Input | Output Esperado | Checks Críticos |
|----|-------|-----------------|-----------------|
| cy04_cancel_counter_main | SELL TP hit | BUY cancelled | ✓ buy.status=CANCELLED<br>✓ cancel_reason="counterpart_tp_hit" |
| cy06_multiple_cycles | EURUSD + GBPUSD | 2 ciclos independientes | ✓ len(cycles)==2<br>✓ pares aislados |

[... continuar para los 58 restantes ...]
2. Script Generador de CSVs
SÍ, es excelente idea. Te permite:

✅ Generar los 62 archivos rápidamente
✅ Mantener consistencia en formato
✅ Modificar parámetros fácilmente

python# tests/fixtures/scenario_generator.py
"""
Generador de CSVs para los 62 escenarios de auditoría.
Usa la matriz de validación como especificación.
"""

SCENARIOS = {
    'c01_tp_simple_buy': {
        'pair': 'EURUSD',
        'start': 1.10000,
        'sequence': [
            (0, 'Start'),
            (0.00020, 'BUY activates at 1.10020'),
            (0.00100, 'TP hit at 1.10120')
        ]
    },
    # ... 61 más
}
3. Template de Test Parametrizado
SÍ, muy útil:
python# tests/test_scenarios/test_all_scenarios.py
import pytest
from tests.fixtures.scenario_loader import load_scenario

@pytest.mark.parametrize('scenario_id', [
    'c01_tp_simple_buy',
    'c01_tp_simple_sell',
    # ... los 62
])
async def test_scenario(scenario_id, backtest_engine):
    """Test genérico que carga CSV y valida contra matriz."""
    
    # 1. Cargar escenario
    scenario = load_scenario(scenario_id)
    csv_path = f'tests/scenarios/{scenario_id}.csv'
    
    # 2. Ejecutar backtest
    await backtest_engine.run(csv_path, max_bars=scenario.max_bars)
    
    # 3. Validar checks de la matriz
    for check in scenario.checks:
        assert check.validate(backtest_engine.repository)

📝 Plan de Acción Recomendado
FASE 1: Documentación (1-2 horas)
markdown1. ✅ Mantener los 4 escenarios detallados actuales
2. ➕ Añadir Apéndice con Matriz Compacta (tabla de 58 filas)
   - Formato: ID | Input | Output | 2-3 checks críticos
3. 📌 Marcar en el índice cuáles tienen spec detallada vs matriz
FASE 2: Infraestructura de Tests (2-3 horas)
python1. Script generador de CSVs (tests/fixtures/scenario_generator.py)
   - YAML con specs compactas
   - Genera 62 CSVs en tests/scenarios/
   
2. Loader de escenarios (tests/fixtures/scenario_loader.py)
   - Lee YAML
   - Carga checks esperados
   
3. Test parametrizado (tests/test_scenarios/test_all_scenarios.py)
   - 1 función, 62 ejecuciones
   - Reutiliza backtest_engine
FASE 3: Ejecución (30 min - 1 hora)
bashpytest tests/test_scenarios/ -v --tb=short
# Genera reporte de cobertura

🎯 Respuesta Directa a tus Preguntas
1. ¿Explicar los 62 con palabras en expected_behavior_specification_fixed.md?
NO completo, pero SÍ añadir matriz compacta:
markdown# Al final del documento actual

---

# MATRIZ DE VALIDACIÓN RÁPIDA (58 ESCENARIOS RESTANTES)

Esta matriz complementa los 4 escenarios detallados arriba.
Para cada escenario:
- **Input**: Precio inicial y secuencia de movimientos
- **Output**: Estado esperado final
- **Checks**: 2-3 assertions críticas

[Tabla compacta aquí]
```

**Ventajas:**
- ✅ Todo en un documento
- ✅ Fácil de revisar
- ✅ No duplica esfuerzo

### 2. ¿Crear generador de CSVs y template?

**SÍ, 100% recomendado:**
```
tests/
├── fixtures/
│   ├── scenario_specs.yaml          # ← Specs compactas (62 entries)
│   ├── scenario_generator.py        # ← Genera CSVs desde YAML
│   └── scenario_loader.py           # ← Carga specs en tests
├── scenarios/                        # ← 62 CSVs generados
│   ├── c01_tp_simple_buy.csv
│   └── ...
└── test_scenarios/
    └── test_all_scenarios.py        # ← 1 test parametrizado
```

---

## 💡 Estructura Final Propuesta
```
docs/
└── expected_behavior_specification_fixed.md
    ├── [EXISTENTE] Escenario 1: Ciclo Simple (detallado)
    ├── [EXISTENTE] Escenario 2: Hedge (detallado)
    ├── [EXISTENTE] Escenario 3: Recovery FIFO (detallado)
    ├── [EXISTENTE] Escenario 4: Multinivel (detallado)
    └── [NUEVO] Apéndice: Matriz de Validación (58 restantes)
        - Formato tabla compacta
        - ID | Input | Output | Checks (2-3 líneas por escenario)

¿Quieres que te ayude con alguna de estas partes?
Puedo crear:

Template de la Matriz Compacta (en Markdown) con 5-10 ejemplos
YAML de especificaciones para el generador
Script generador completo
Template de test parametrizado

¿Con cuál prefieres empezar? 🚀Template de la Matriz Compacta (en Markdown) con 5-10 ejemplos7 eneTemplate de Matriz Compacta - Escenarios de Auditoría
Aquí tienes el template para el Apéndice que agregarías al final de expected_behavior_specification_fixed.md:

markdown---

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

🎯 Resumen del Template
Estructura por Escenario:

Tabla Principal con 6 filas:

Prioridad (con emoji)
Descripción breve
Input (condiciones iniciales + secuencia)
Output (estado final esperado)
Checks (2-4 assertions críticas)
CSV (especificación del archivo de datos)


Formato Compacto:

Sin logs detallados (esos están en los 4 escenarios principales)
Solo lo necesario para validar
Máximo 10 líneas por escenario


Fácil de Escanear:

Emojis para prioridad
Checks con ✓
Código inline resaltado



¿Quieres que continúe con los otros 48 escenarios restantes, o prefieres pasar al YAML del generador? 🚀 los otros 48 escenarios restantes7 ene2 / 2MATRIZ COMPLETA - 58 ESCENARIOS RESTANTES
Aquí está la matriz completa para agregar al final de expected_behavior_specification_fixed.md:
markdown---

# APÉNDICE: MATRIZ DE VALIDACIÓN RÁPIDA (58 ESCENARIOS RESTANTES)

## Propósito

Esta matriz complementa los 4 escenarios detallados anteriores (E1-E4), proporcionando especificaciones compactas para los 58 escenarios restantes. Cada fila define:

- **Input**: Condiciones iniciales y secuencia de precios
- **Output**: Estado final esperado del sistema
- **Checks Críticos**: 2-4 assertions que DEBEN pasar

**Leyenda de Prioridades:**
- 🔴 **CRÍTICA**: Funcionalidad core, debe pasar siempre
- 🟡 **ALTA**: Comportamiento importante, alta prioridad
- 🟢 **MEDIA**: Caso edge, importante pero no bloqueante
- ⚪ **BAJA**: Nice-to-have, puede diferirse

**Nota:** Los escenarios E1 (c01_tp_simple_buy/sell), E2 (h01-h04), E3 (r01-r03, f01-f02), y E4 (multinivel) ya están detallados en las secciones anteriores.

---

## CORE (1 escenario restante)

### c04_no_activation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Precio se mantiene en rango, no activa ninguna operación |
| **Input** | • Balance: 10000 EUR<br>• Precio inicial: 1.10000<br>• Órdenes: BUY@1.10020, SELL@1.09980<br>• Movimiento: ±5 pips (rango 1.09990-1.10010) |
| **Output** | • Ambas operaciones: `PENDING`<br>• Balance: 10000 (sin cambios)<br>• Broker calls: 0 ejecuciones |
| **Checks** | ✓ `buy_op.status == PENDING`<br>✓ `sell_op.status == PENDING`<br>✓ `len(broker.order_history) == 0`<br>✓ `account.balance == 10000.0` |
| **CSV** | 20 ticks en rango 1.09990 - 1.10010, sin cruces |

### c05_gap_tp

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Gap de mercado salta directamente sobre el TP |
| **Input** | • BUY activada @ 1.10020<br>• TP @ 1.10120<br>• Gap: 1.10050 → 1.10150 (salta TP) |
| **Output** | • Operación cerrada @ 1.10150 (post-gap)<br>• Profit: ~13 pips (en lugar de 10)<br>• Metadata: `gap_detected=true` |
| **Checks** | ✓ `operation.status == CLOSED`<br>✓ `operation.profit_pips >= 10.0`<br>✓ `operation.actual_close_price > operation.tp_price`<br>✓ `operation.metadata.get('gap_detected') == True` |
| **CSV** | Tick 1: 1.10050 → Tick 2: 1.10150 (sin intermedios) |

---

## CYCLES (2 escenarios restantes)

### cy04_cancel_counter_main

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Cuando un main toca TP, la main contraria pendiente se cancela (FIX-001) |
| **Input** | • BUY activada: entry=1.10020, status=ACTIVE<br>• SELL pendiente: entry=1.09980, status=PENDING<br>• Precio sube: 1.10020 → 1.10120 (TP de BUY) |
| **Output** | • BUY: `TP_HIT`, profit=10 pips<br>• SELL: `CANCELLED`, reason="counterpart_tp_hit"<br>• 2 nuevas mains creadas (renovación dual FIX-001) |
| **Checks** | ✓ `buy.status == TP_HIT`<br>✓ `sell.status == CANCELLED`<br>✓ `sell.metadata['cancel_reason'] == "counterpart_tp_hit"`<br>✓ `len([op for op in cycle.operations if op.is_main and op.status == PENDING]) == 2` |
| **CSV** | 1.10000 → 1.10020 (activa BUY) → 1.10120 (TP) |

### cy05_complete_10_tps

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Ciclo completa 10 TPs exitosos consecutivos sin hedge |
| **Input** | • Ciclo EURUSD<br>• Secuencia: 10 activaciones alternadas (5 BUY + 5 SELL)<br>• Cada una alcanza TP +10 pips |
| **Output** | • Total TPs: 10<br>• Total pips: 100<br>• Balance: 10000 + 100 EUR (aprox)<br>• Ciclo: sigue ACTIVE |
| **Checks** | ✓ `cycle.accounting.total_main_tps == 10`<br>✓ `cycle.accounting.total_pips_won >= 100.0`<br>✓ `account.balance >= 10100.0`<br>✓ `cycle.status == ACTIVE` |
| **CSV** | 10 secuencias completas de activación → TP → renovación |

### cy06_multiple_cycles

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Múltiples pares operan independientemente sin interferencia |
| **Input** | • Par 1: EURUSD @ 1.10000, ciclo activo<br>• Par 2: GBPUSD @ 1.25000, ciclo activo<br>• Ambos con operaciones activas |
| **Output** | • 2 ciclos independientes<br>• EURUSD: 1 TP exitoso<br>• GBPUSD: 1 TP exitoso<br>• Sin cross-contamination entre pares |
| **Checks** | ✓ `len(active_cycles) == 2`<br>✓ `eurusd_cycle.pair == "EURUSD"`<br>✓ `gbpusd_cycle.pair == "GBPUSD"`<br>✓ `eurusd_cycle.accounting.total_tp_count >= 1`<br>✓ `gbpusd_cycle.accounting.total_tp_count >= 1` |
| **CSV** | 2 archivos paralelos: `cy06_eurusd.csv` + `cy06_gbpusd.csv` |

---

## HEDGED (6 escenarios restantes)

### h02_create_hedge_operations

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Al entrar en HEDGED, se crean operaciones HEDGE_BUY y HEDGE_SELL |
| **Input** | • Ambas mains activadas (BUY @ 1.10020, SELL @ 1.09980)<br>• Estado cambia a HEDGED |
| **Output** | • 2 operaciones hedge creadas:<br>  - HEDGE_BUY (covering MAIN_SELL)<br>  - HEDGE_SELL (covering MAIN_BUY)<br>• Ambas con status PENDING |
| **Checks** | ✓ `len([op for op in cycle.operations if op.is_hedge]) == 2`<br>✓ `hedge_buy.op_type == HEDGE_BUY`<br>✓ `hedge_sell.op_type == HEDGE_SELL`<br>✓ `hedge_buy.linked_operation_id == main_sell.id` |
| **CSV** | Precio cruza ambas entries → HEDGED |

### h03_neutralize_mains

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Al activar hedge, las operaciones main se marcan como NEUTRALIZED |
| **Input** | • Estado: HEDGED alcanzado<br>• Main BUY: ACTIVE<br>• Main SELL: ACTIVE |
| **Output** | • Main BUY: `NEUTRALIZED`<br>• Main SELL: `NEUTRALIZED`<br>• Cada una vinculada a su hedge |
| **Checks** | ✓ `main_buy.status == NEUTRALIZED`<br>✓ `main_sell.status == NEUTRALIZED`<br>✓ `main_buy.linked_operation_id == hedge_sell.id`<br>✓ `main_sell.linked_operation_id == hedge_buy.id` |
| **CSV** | Secuencia completa hasta HEDGED |

### h04_lock_20_pips

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Al entrar en HEDGED, se bloquean exactamente 20 pips |
| **Input** | • Main separation: 4 pips<br>• TP distance: 10 pips<br>• Margin: 6 pips<br>• Total: 20 pips |
| **Output** | • `pips_locked = 20.0`<br>• Metadata incluye debt_composition |
| **Checks** | ✓ `cycle.accounting.pips_locked == 20.0`<br>✓ `cycle.metadata['debt_composition']['separation'] == 4.0`<br>✓ `cycle.metadata['debt_composition']['tp_distance'] == 10.0`<br>✓ `cycle.metadata['debt_composition']['margin'] == 6.0` |
| **CSV** | Estado HEDGED alcanzado |

### h05_sequential_activation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Ambas mains se activan secuencialmente (no gap simultáneo) |
| **Input** | • Start: 1.10000<br>• T1 (10 ticks): 1.10020 (activa BUY)<br>• T2 (20 ticks): precio vuelve a 1.09980 (activa SELL)<br>• Tiempo entre activaciones: ~10 segundos |
| **Output** | • Estado: `HEDGED`<br>• pips_locked: 20<br>• HEDGE_BUY + HEDGE_SELL creados<br>• Timestamps diferentes en activaciones |
| **Checks** | ✓ `cycle.status == HEDGED`<br>✓ `main_buy.activated_at < main_sell.activated_at`<br>✓ `(main_sell.activated_at - main_buy.activated_at).seconds >= 5`<br>✓ `cycle.accounting.pips_locked == 20.0` |
| **CSV** | 1.10000 → 1.10020 (10 ticks) → 1.09980 (10 ticks) |

### h06_simultaneous_gap

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Gap de fin de semana activa ambas mains en el mismo tick |
| **Input** | • Viernes 22:00: 1.10000<br>• Lunes 00:01: 1.10050 (gap +50 pips)<br>• Ambas entries (1.10020 y 1.09980) cruzadas |
| **Output** | • Estado: `HEDGED` inmediato<br>• pips_locked: 20 + gap_adjustment<br>• Metadata: `gap_detected=true`, `gap_size=50` |
| **Checks** | ✓ `cycle.status == HEDGED`<br>✓ `cycle.metadata['gap_detected'] == True`<br>✓ `cycle.metadata['gap_size'] == 50.0`<br>✓ `main_buy.activated_at == main_sell.activated_at` (mismo timestamp) |
| **CSV** | Tick 1: 1.10000 → Tick 2: 1.10050 (sin intermedios) |

### h07_buy_tp_hedge_sell (FIX-002)

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Main BUY toca TP en estado HEDGED → cancelar HEDGE_SELL pendiente |
| **Input** | • Estado: HEDGED<br>• Main BUY: ACTIVE<br>• Main SELL: NEUTRALIZED<br>• HEDGE_SELL: PENDING (entry=1.10100)<br>• Precio: 1.10020 → 1.10120 (TP del BUY) |
| **Output** | • Main BUY: `TP_HIT`<br>• HEDGE_SELL: `CANCELLED`<br>• Metadata: `cancel_reason="counterpart_main_tp_hit"`<br>• cancelled_by_operation: main_buy.id |
| **Checks** | ✓ `main_buy.status == TP_HIT`<br>✓ `hedge_sell.status == CANCELLED`<br>✓ `hedge_sell.metadata['cancel_reason'] == "counterpart_main_tp_hit"`<br>✓ `hedge_sell.metadata['cancelled_by_operation'] == str(main_buy.id)` |
| **CSV** | 1.10000 → HEDGED → 1.10120 (TP del BUY) |

### h08_sell_tp_hedge_buy

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Main SELL toca TP en HEDGED → cancelar HEDGE_BUY pendiente |
| **Input** | • Estado: HEDGED<br>• Main SELL: ACTIVE @ 1.09980<br>• Main BUY: NEUTRALIZED<br>• HEDGE_BUY: PENDING<br>• Precio: 1.09980 → 1.09880 (TP del SELL) |
| **Output** | • Main SELL: `TP_HIT`<br>• HEDGE_BUY: `CANCELLED`<br>• Metadata: `cancel_reason="counterpart_main_tp_hit"` |
| **Checks** | ✓ `main_sell.status == TP_HIT`<br>✓ `hedge_buy.status == CANCELLED`<br>✓ `hedge_buy.metadata['cancel_reason'] == "counterpart_main_tp_hit"`<br>✓ `hedge_buy.metadata['cancelled_by_operation'] == str(main_sell.id)` |
| **CSV** | 1.10000 → HEDGED → 1.09880 (TP del SELL) |

---

## RECOVERY (7 escenarios restantes)

### r02_recovery_distance_20

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Recovery se coloca exactamente a 20 pips del precio TP del main |
| **Input** | • Main BUY TP alcanzado @ 1.10120<br>• Main SELL neutralizada<br>• Recovery debe colocarse desde TP, no desde precio actual |
| **Output** | • Recovery BUY entry: 1.10140 (TP + 20 pips)<br>• Recovery SELL entry: 1.10100 (TP - 20 pips)<br>• Metadata: `reference_price = 1.10120` |
| **Checks** | ✓ `recovery_buy.entry_price == 1.10140`<br>✓ `recovery_sell.entry_price == 1.10100`<br>✓ `recovery_buy.metadata['reference_price'] == 1.10120`<br>✓ Distancia exacta: 20 pips desde TP |
| **CSV** | Main alcanza TP @ 1.10120, recoveries desde ahí |

### r04_recovery_n1_tp_sell

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Recovery N1 SELL exitoso (variante de r03) |
| **Input** | • Recovery N1 SELL entry: 1.10100<br>• TP: 1.10020 (-80 pips desde entry)<br>• Precio baja desde 1.10100 → 1.10020 |
| **Output** | • Recovery SELL: `TP_HIT`<br>• profit_pips: 80.0<br>• FIFO ejecutado: Main + Hedge cerrados (costo 20 pips)<br>• pips_recovered: 20 |
| **Checks** | ✓ `recovery.status == TP_HIT`<br>✓ `recovery.profit_pips == 80.0`<br>✓ `parent_cycle.accounting.pips_recovered == 20.0`<br>✓ `len(parent_cycle.accounting.recovery_queue) == 0` |
| **CSV** | Precio baja 80 pips desde entry 1.10100 → 1.10020 |

### r05_recovery_n1_fails_n2

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Recovery N1 no alcanza TP, distancia de 40 pips activa N2 |
| **Input** | • Recovery N1 @ 1.10140 (BUY), activada<br>• Precio: 1.10140 → 1.10120 (no alcanza TP @ 1.10220)<br>• Distancia: 40 pips desde N1 → activa N2 |
| **Output** | • N1: sigue `ACTIVE`, no TP<br>• N2 creado @ 1.10180 (40 pips desde N1)<br>• recovery_queue: ["N1_debt", "N2_debt"] |
| **Checks** | ✓ `n1.status == ACTIVE`<br>✓ `n2.status == PENDING`<br>✓ `n2.entry_price == 1.10180`<br>✓ `len(parent_cycle.accounting.recovery_queue) == 2`<br>✓ `parent_cycle.recovery_level == 2` |
| **CSV** | 1.10140 → 1.10120 (N1 activa, no TP) → continúa subiendo hasta 1.10180 |

### r06_recovery_n2_success

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | N2 alcanza TP y recupera deuda de N1 + parte de main |
| **Input** | • N1 activa @ 1.10140<br>• N2 activa @ 1.10180<br>• N2 alcanza TP @ 1.10260 (+80 pips) |
| **Output** | • N2: `TP_HIT`, 80 pips<br>• FIFO cierra: N1 (40 pips) + Main+Hedge (20 pips)<br>• pips_recovered: 60<br>• Profit neto: 20 pips |
| **Checks** | ✓ `n2.status == TP_HIT`<br>✓ `parent_cycle.accounting.pips_recovered == 60.0`<br>✓ `parent_cycle.accounting.recovery_queue == []`<br>✓ Net profit: 20 pips (80 - 60) |
| **CSV** | N2 @ 1.10180 → 1.10260 (TP) |

### r07_cascade_n1_n2_n3

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cascada de 3 niveles de recovery antes de resolución exitosa |
| **Input** | • N1 @ 1.10140, activa<br>• N2 @ 1.10180, activa<br>• N3 @ 1.10220, activa<br>• N3 alcanza TP @ 1.10300 (+80 pips) |
| **Output** | • N3: `TP_HIT`<br>• FIFO cierra: N2 (40) + N1 (40)<br>• pips_recovered: 80<br>• Profit neto: 0 (80 - 80 costo) |
| **Checks** | ✓ `n3.status == TP_HIT`<br>✓ `parent_cycle.accounting.pips_recovered == 80.0`<br>✓ `len([op for op in closed_ops if op.is_recovery]) == 2`<br>✓ Main+Hedge aún en cola |
| **CSV** | Cascada +40 pips cada nivel (1.10140 → 1.10180 → 1.10220), luego TP @ 1.10300 |

### r08_recovery_max_n6

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Alcanza nivel máximo de recovery (N6) sin excederlo |
| **Input** | • Recoveries N1-N5 activos<br>• Distancia para N6 alcanzada (+40 pips desde N5)<br>• Precio continúa moviéndose adversamente |
| **Output** | • N6 creado @ entry calculado<br>• recovery_level: 6<br>• Sistema: alerta `max_recovery_level_reached`<br>• NO se crea N7 aunque precio siga |
| **Checks** | ✓ `parent_cycle.recovery_level == 6`<br>✓ `len(recovery_queue) == 6` (N1-N6 + Main)<br>✓ Alerta creada: `severity=WARNING`, `type=max_recovery_level`<br>✓ NO existe N7 aunque distancia lo permita |
| **CSV** | Cascada extrema +240 pips (40*6) desde main |

### r09_cancel_recovery_counter

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Recovery BUY toca TP → cancelar recovery SELL pendiente |
| **Input** | • Recovery BUY: entry @ 1.10140, alcanza TP @ 1.10220<br>• Recovery SELL: PENDING @ 1.10100<br>• Ambas del mismo nivel N1 |
| **Output** | • Recovery BUY: `TP_HIT`<br>• Recovery SELL: `CANCELLED`<br>• Metadata: `cancel_reason="counterpart_tp_hit"` |
| **Checks** | ✓ `recovery_buy.status == TP_HIT`<br>✓ `recovery_sell.status == CANCELLED`<br>✓ `recovery_sell.metadata['cancel_reason'] == "counterpart_tp_hit"`<br>✓ Orden cancelada en broker |
| **CSV** | Recovery BUY alcanza TP unilateralmente |

### r10_multiple_recovery_pairs

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟢 MEDIA |
| **Descripción** | Múltiples pares con recoveries simultáneos independientes |
| **Input** | • EURUSD: N1+N2 activos (recovery_level=2)<br>• GBPUSD: N1 activo (recovery_level=1)<br>• Ambos operando simultáneamente |
| **Output** | • 3 recoveries totales activos<br>• Sin interferencia cross-pair<br>• Recovery queues separadas |
| **Checks** | ✓ `eurusd_cycle.recovery_level == 2`<br>✓ `gbpusd_cycle.recovery_level == 1`<br>✓ `len(eurusd_cycle.recovery_queue) == 2`<br>✓ `len(gbpusd_cycle.recovery_queue) == 1`<br>✓ Total recoveries activos: 3 |
| **CSV** | 2 archivos paralelos: `r10_eurusd.csv` + `r10_gbpusd.csv` |

---

## FIFO (2 escenarios restantes)

### f03_fifo_atomic_close

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cierre atómico de Main + Hedge como unidad indivisible (FIX-003) |
| **Input** | • Main SELL: NEUTRALIZED @ 1.09980<br>• Hedge BUY: ACTIVE @ 1.10020 (cubre main)<br>• Recovery TP: 80 pips disponibles<br>• Costo de unidad: 20 pips (primer recovery) |
| **Output** | • Main + Hedge cerrados en mismo timestamp (±1ms)<br>• debt_unit_id compartido<br>• close_method: "atomic_with_hedge" / "atomic_with_main" |
| **Checks** | ✓ `main.status == CLOSED`<br>✓ `hedge.status == CLOSED`<br>✓ `abs((main.closed_at - hedge.closed_at).total_seconds()) <= 0.001`<br>✓ `main.metadata['debt_unit_id'] == hedge.metadata['debt_unit_id']`<br>✓ `main.metadata['close_method'] == "atomic_with_hedge"` |
| **CSV** | Recovery alcanza TP con deuda pendiente (Main+Hedge) |

### f04_fifo_multiple_close

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Un recovery TP cierra múltiples unidades de deuda en orden FIFO |
| **Input** | • Queue: [Main+Hedge (20 pips), N1 (40 pips)]<br>• Recovery N2 alcanza TP: 80 pips disponibles<br>• Total costo: 60 pips (20 + 40) |
| **Output** | • Ambas unidades cerradas<br>• Profit neto: 20 pips (80 - 60)<br>• recovery_queue vacía |
| **Checks** | ✓ `pips_recovered == 60.0` (20 + 40)<br>✓ `recovery_queue == []`<br>✓ `len(closed_units) == 2`<br>✓ `net_profit_pips == 20.0`<br>✓ `cycle.accounting.recoveries_closed_count == 2` |
| **CSV** | Recovery N2 con deuda acumulada 60 pips en cola |

---

## RISK MANAGEMENT (5 escenarios)

### rm01_exposure_limit

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Límite de exposición (30% margin/equity) rechaza nuevas operaciones |
| **Input** | • Equity: 10000 EUR<br>• Margin usado: 3000 EUR (30%)<br>• Nueva operación requiere: 100 EUR<br>• Total sería: 31% |
| **Output** | • Nueva operación: rechazada<br>• Log: "Max exposure reached"<br>• can_open_position: False |
| **Checks** | ✓ `can_open_result.success == False`<br>✓ `can_open_result.error_code == "RISK_EXPOSURE_LIMIT"`<br>✓ `current_exposure >= 30.0`<br>✓ No nueva operación creada |
| **CSV** | N/A (test unitario, mock de account_info) |

### rm02_drawdown_limit

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Drawdown >20% pausa automáticamente el sistema |
| **Input** | • Balance inicial: 10000 EUR<br>• Balance actual: 7900 EUR<br>• Drawdown: 21% (>20% threshold) |
| **Output** | • Sistema: `PAUSED`<br>• Alerta: severity=CRITICAL, type=drawdown_limit<br>• No nuevas operaciones hasta revisión manual |
| **Checks** | ✓ Alerta creada con `severity=CRITICAL`<br>✓ `system.status == PAUSED`<br>✓ `system.metadata['pause_reason'] == "drawdown_limit"`<br>✓ `can_open_position() == False` |
| **CSV** | Secuencia de pérdidas acumuladas -21% |

### rm03_daily_loss_limit

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Pérdida diaria excede límite (100 pips) → pausa hasta mañana |
| **Input** | • Inicio del día: balance 10000<br>• Pérdidas acumuladas en el día: -100 pips<br>• Límite diario: 100 pips |
| **Output** | • Sistema: `PAUSED`<br>• Metadata: `pause_reason="daily_loss_limit"`, `resume_at="tomorrow"`<br>• No nuevas operaciones hasta cambio de día |
| **Checks** | ✓ Alerta generada: `severity=CRITICAL`, `type=daily_loss_limit`<br>✓ `system.status == PAUSED`<br>✓ `can_open_position() == False`<br>✓sigue en un nuevo documento y yo los uno despues7 ene2 / 2MATRIZ COMPLETA - PARTE 2
Continuación de la matriz de validación:
markdown---

## RISK MANAGEMENT (continuación)

### rm03_daily_loss_limit (continuación)

| **Checks** | ✓ Alerta generada: `severity=CRITICAL`, `type=daily_loss_limit`<br>✓ `system.status == PAUSED`<br>✓ `can_open_position() == False`<br>✓ `metadata['resume_at']` contiene fecha del día siguiente |
| **CSV** | Secuencia de 10 pérdidas consecutivas totalizando -100 pips |

### rm04_margin_insufficient

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Margen libre insuficiente rechaza nueva operación antes de enviar al broker |
| **Input** | • Free margin: 50 EUR<br>• Nueva operación 0.01 lotes requiere: 100 EUR margin<br>• Insuficiente por 50 EUR |
| **Output** | • Operación: rechazada por RiskManager<br>• Log: "Insufficient margin"<br>• NO se envía al broker |
| **Checks** | ✓ `result.success == False`<br>✓ `result.error_code == "RISK_INSUFFICIENT_MARGIN"`<br>✓ `len(broker.orders_sent) == 0`<br>✓ Operation no creada en DB |
| **CSV** | N/A (test unitario con mock de account_info) |

### rm05_recovery_exposure

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Exposición incluye recoveries activos en el cálculo total |
| **Input** | • 2 ciclos main activos: 0.02 lotes cada uno<br>• 3 recoveries activos: 0.01 lotes cada uno<br>• Total lotes: 0.07<br>• Equity: 10000, Margin usado: 2800 (28%) |
| **Output** | • Exposición calculada correctamente: 28%<br>• Debajo del límite 30%<br>• Nueva operación permitida |
| **Checks** | ✓ `calculated_exposure == 28.0`<br>✓ `total_lots == 0.07`<br>✓ `can_open_position() == True`<br>✓ Recoveries incluidos en cálculo |
| **CSV** | N/A (test unitario) |

---

## MONEY MANAGEMENT (8 escenarios)

### mm01_balance_read

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Sistema lee balance inicial correctamente del broker al inicio |
| **Input** | • Broker retorna: balance=10000.00, equity=10000.00, margin=0.0 |
| **Output** | • Sistema inicializado con balance correcto<br>• Primera operación usa balance para cálculo de lote |
| **Checks** | ✓ `account.balance == 10000.0`<br>✓ `account.equity == 10000.0`<br>✓ `account.margin_free == 10000.0`<br>✓ Primera operación usa lote calculado desde balance real |
| **CSV** | Tick inicial con lectura de account_info |

### mm02_pnl_tp

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Cálculo correcto de P&L cuando operación alcanza TP (+10 pips = +2 EUR) |
| **Input** | • Operación: 0.01 lotes<br>• Entry: 1.10000<br>• TP: 1.10100 (+10 pips)<br>• Pip value: 0.10 EUR/pip para 0.01 lotes |
| **Output** | • profit_pips: 10.0<br>• profit_eur: 1.0 EUR (sin comisiones)<br>• profit_eur_net: -13.0 EUR (con comisiones -7 open -7 close) |
| **Checks** | ✓ `operation.profit_pips == 10.0`<br>✓ `operation.profit_eur == 1.0`<br>✓ `operation.total_cost == 14.0` (comisiones)<br>✓ `operation.net_profit_eur == -13.0` |
| **CSV** | Operación simple BUY: entry → TP |

### mm03_pnl_hedged

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Cálculo de pips bloqueados en estado HEDGED (pérdida flotante neutralizada) |
| **Input** | • Main BUY: entry 1.10020, precio actual 1.10050 (+3 pips flotante)<br>• Main SELL: entry 1.09980, precio actual 1.10050 (-7 pips flotante)<br>• Hedge BUY cubre SELL<br>• Hedge SELL cubre BUY |
| **Output** | • pips_locked: 20 (composición de deuda)<br>• Floating P&L main BUY: +3 pips<br>• Floating P&L main SELL: -7 pips<br>• Net floating: neutralizado por hedges |
| **Checks** | ✓ `cycle.accounting.pips_locked == 20.0`<br>✓ `main_buy.current_pips > 0`<br>✓ `main_sell.current_pips < 0`<br>✓ `hedge_buy.current_pips + main_sell.current_pips ≈ 0` (neutralizado) |
| **CSV** | Estado HEDGED con precio moviéndose |

### mm04_balance_update_tp

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Balance se actualiza correctamente tras TP (incluyendo comisiones) |
| **Input** | • Balance inicial: 10000.00<br>• TP hit: +10 pips = +1.0 EUR gross<br>• Comisiones: -14.0 EUR (open + close)<br>• Net P&L: -13.0 EUR |
| **Output** | • Balance final: 9987.0 EUR<br>• Equity: 9987.0 EUR (sin posiciones abiertas) |
| **Checks** | ✓ `account.balance == 9987.0`<br>✓ `account.equity == 9987.0`<br>✓ Delta balance: -13.0 EUR<br>✓ Comisiones reflejadas correctamente |
| **CSV** | Operación completa: open → TP → balance update |

### mm05_equity_calculation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🔴 CRÍTICA |
| **Descripción** | Equity = Balance + Floating P&L (todas posiciones abiertas) |
| **Input** | • Balance: 10000.0<br>• Posición 1 (BUY): +5 pips flotante = +0.5 EUR<br>• Posición 2 (SELL): -3 pips flotante = -0.3 EUR<br>• Net floating: +0.2 EUR |
| **Output** | • Equity: 10000.2 EUR<br>• Floating P&L: +0.2 EUR |
| **Checks** | ✓ `account.equity == 10000.2`<br>✓ `account.balance == 10000.0`<br>✓ `floating_pnl == 0.2`<br>✓ Equity actualiza en tiempo real con ticks |
| **CSV** | Múltiples posiciones abiertas con floating P&L |

### mm06_margin_calculation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cálculo correcto de margin usado: (lot × contract_size) / leverage |
| **Input** | • Operación: 0.01 lotes<br>• Contract size: 100,000 (standard)<br>• Leverage: 1:100<br>• Formula: (0.01 × 100,000) / 100 = 10 EUR |
| **Output** | • Margin usado por operación: 10 EUR<br>• 3 operaciones: 30 EUR total |
| **Checks** | ✓ `margin_per_operation == 10.0`<br>✓ `total_margin_used == 30.0` (3 ops)<br>✓ `account.margin == 30.0`<br>✓ Cálculo consistente con broker |
| **CSV** | N/A (test unitario) |

### mm07_free_margin

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Free margin = Equity - Margin usado (disponible para nuevas operaciones) |
| **Input** | • Equity: 10000.0<br>• Margin usado: 150.0 (15 operaciones × 10)<br>• Free margin esperado: 9850.0 |
| **Output** | • Free margin: 9850.0<br>• Suficiente para nuevas operaciones |
| **Checks** | ✓ `account.margin_free == 9850.0`<br>✓ `account.equity - account.margin == account.margin_free`<br>✓ Cálculo correcto en tiempo real |
| **CSV** | N/A (test unitario) |

### mm08_recovery_pnl_accumulation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | P&L de recoveries acumula correctamente según FIFO (costo vs ganancia) |
| **Input** | • N1 TP: +80 pips<br>  - Costo FIFO: -20 pips (Main+Hedge)<br>  - Neto: +60 pips<br>• N2 TP: +80 pips<br>  - Costo FIFO: -40 pips (N1)<br>  - Neto: +40 pips |
| **Output** | • Total recovered: 60 pips (20 + 40 costos)<br>• Profit neto acumulado: 100 pips (60 + 40)<br>• Balance incrementado: +100 EUR (aprox) |
| **Checks** | ✓ `cycle.accounting.pips_recovered == 60.0`<br>✓ `total_net_profit_pips == 100.0`<br>✓ `account.balance == 10100.0` (aprox, considerando comisiones)<br>✓ FIFO aplicado correctamente en ambos |
| **CSV** | 2 recoveries exitosos secuenciales con costos FIFO |

---

## EDGE CASES (8 escenarios)

### e01_spread_rejection

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟢 MEDIA |
| **Descripción** | Spread >3 pips rechaza señal de apertura (filtro de estrategia) |
| **Input** | • Spread actual: 3.5 pips<br>• Límite configurado: 3.0 pips<br>• Señal: OPEN_CYCLE generada |
| **Output** | • Señal transformada a NO_ACTION<br>• Log: "high_spread"<br>• NO se envía orden al broker |
| **Checks** | ✓ `signal.signal_type == NO_ACTION`<br>✓ `signal.metadata['reason'] == "high_spread"`<br>✓ `signal.metadata['spread'] == 3.5`<br>✓ `len(broker.orders) == 0` |
| **CSV** | Ticks con spread artificialmente alto (bid-ask > 3 pips) |

### e02_high_spread_rejection

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Spread extremo (>5 pips) pausa operaciones temporalmente |
| **Input** | • Spread: 7 pips (evento de alta volatilidad)<br>• Duración: 10 ticks<br>• Spread vuelve a normal: 2 pips |
| **Output** | • Durante spread alto: todas señales → NO_ACTION<br>• Tras normalización: operaciones se reanudan<br>• Metadata: spread_events registrados |
| **Checks** | ✓ Durante alta spread: `can_trade == False`<br>✓ Después: `can_trade == True`<br>✓ No operaciones ejecutadas durante spread alto<br>✓ Sistema se recupera automáticamente |
| **CSV** | Spread: 2 pips → 7 pips (10 ticks) → 2 pips |

### e03_weekend_gap

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Gap de fin de semana atraviesa múltiples niveles (TP + Recovery entries) |
| **Input** | • Viernes 21:59: 1.10000<br>• Lunes 00:01: 1.10200 (gap +200 pips)<br>• Cruza: TP @ 1.10120, Recovery @ 1.10140, 1.10180 |
| **Output** | • Gap detectado: metadata `gap_detected=true`, `gap_size=200`<br>• Operaciones activadas con precio post-gap<br>• Slippage registrado para cada una |
| **Checks** | ✓ `tick_data.metadata['gap_detected'] == True`<br>✓ `tick_data.metadata['gap_size'] == 200.0`<br>✓ Operaciones activadas @ 1.10200 (no @ entry esperado)<br>✓ `slippage_pips > 0` para cada operación |
| **CSV** | Viernes: 1.10000 → Lunes: 1.10200 (sin ticks intermedios) |

### e04_mega_move

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Movimiento extremo >200 pips en una sesión (evento de alta volatilidad) |
| **Input** | • Precio: 1.10000 → 1.12000 (+200 pips) en 100 ticks<br>• Múltiples niveles atravesados rápidamente |
| **Output** | • Múltiples TPs alcanzados<br>• Múltiples recoveries activados<br>• Sistema sigue operando correctamente<br>• Performance degradation: aceptable |
| **Checks** | ✓ `total_tps >= 5`<br>✓ `max_recovery_level >= 3`<br>✓ Sistema no crashea<br>✓ Todas operaciones procesadas correctamente<br>✓ Tiempo de procesamiento < 5 segundos |
| **CSV** | Movimiento extremo +200 pips en 100 ticks (~2 pips/tick) |

### e05_return_to_origin

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟢 MEDIA |
| **Descripción** | Precio retorna al origen después de movimiento amplio (whipsaw) |
| **Input** | • Inicio: 1.10000<br>• Sube: 1.10000 → 1.10150 (+150 pips)<br>• Baja: 1.10150 → 1.10000 (-150 pips)<br>• Termina en origen |
| **Output** | • Múltiples TPs en ambas direcciones<br>• Posible HEDGED intermedio<br>• Balance final > balance inicial (TPs netos) |
| **Checks** | ✓ `final_price ≈ initial_price` (±5 pips)<br>✓ `total_tps >= 2`<br>✓ `account.balance > initial_balance`<br>✓ Sin posiciones abiertas al final |
| **CSV** | 1.10000 → 1.10150 → 1.10000 (movimiento completo ida y vuelta) |

### e06_lateral_market

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟢 MEDIA |
| **Descripción** | Mercado lateral genera múltiples TPs pequeños sin tendencia clara |
| **Input** | • Rango: 1.09980 - 1.10120 (14 pips de amplitud)<br>• 50 activaciones alternadas<br>• Sin tendencia definida |
| **Output** | • 20+ TPs exitosos<br>• Sin recoveries (no hay HEDGED)<br>• Balance incrementado consistentemente |
| **Checks** | ✓ `total_tps >= 20`<br>✓ `recovery_level == 0` (sin recoveries)<br>✓ `account.balance > initial_balance + 200` (múltiples TPs)<br>✓ Sin estado HEDGED en ningún momento |
| **CSV** | Oscilación en rango 1.09980-1.10120, 50 ticks |

### e07_connection_lost

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟢 MEDIA |
| **Descripción** | Pérdida de conexión con broker → reconexión → sincronización de estado |
| **Input** | • Operación BUY activa<br>• Conexión se pierde 10 segundos<br>• Durante desconexión: TP alcanzado en broker<br>• Reconexión exitosa |
| **Output** | • Sync detecta TP alcanzado<br>• Estado sincronizado correctamente<br>• Balance actualizado<br>• Sistema continúa operando |
| **Checks** | ✓ `sync_result.success == True`<br>✓ `operation.status == TP_HIT` (detectado en sync)<br>✓ `account.balance` actualizado correctamente<br>✓ `broker.is_connected() == True` después |
| **CSV** | N/A (test de integración con mock de desconexión) |

### e08_rollover_swap

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | ⚪ BAJA |
| **Descripción** | Swap/Rollover aplicado correctamente a posición abierta durante la noche |
| **Input** | • Operación abierta 23:00<br>• Pasa medianoche (rollover)<br>• Swap: -2.5 EUR (posición SELL en par con interés negativo)<br>• Posición cierra al día siguiente |
| **Output** | • Swap acumulado: -2.5 EUR<br>• Total cost incluye swap<br>• Net P&L ajustado por swap |
| **Checks** | ✓ `operation.swap_total == -2.5`<br>✓ `operation.total_cost` incluye swap<br>✓ `operation.net_profit_eur` ajustado correctamente<br>✓ Metadata: `rollover_applied=true` |
| **CSV** | Operación con timestamp cruzando medianoche |

---

## MULTI-PAIR (4 escenarios)

### mp01_dual_pair

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | EURUSD + GBPUSD operan simultáneamente sin conflictos ni interferencias |
| **Input** | • EURUSD: ciclo @ 1.10000, 1 TP exitoso (+10 pips)<br>• GBPUSD: ciclo @ 1.25000, 1 TP exitoso (+10 pips)<br>• Operaciones en paralelo |
| **Output** | • 2 ciclos independientes activos<br>• EURUSD balance delta: +10 EUR (aprox)<br>• GBPUSD balance delta: +10 EUR (aprox)<br>• Total: +20 EUR |
| **Checks** | ✓ `len(active_cycles) == 2`<br>✓ `eurusd_cycle.pair == "EURUSD"`<br>✓ `gbpusd_cycle.pair == "GBPUSD"`<br>✓ `eurusd_cycle.accounting.total_main_tps == 1`<br>✓ `gbpusd_cycle.accounting.total_main_tps == 1`<br>✓ Sin cross-contamination |
| **CSV** | 2 archivos: `mp01_eurusd.csv` + `mp01_gbpusd.csv` |

### mp02_correlation_hedged

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Ambos pares (EURUSD + GBPUSD) entran en HEDGED simultáneamente |
| **Input** | • EURUSD: ambas mains activan → HEDGED (pips_locked=20)<br>• GBPUSD: ambas mains activan → HEDGED (pips_locked=20)<br>• Total pips locked: 40 |
| **Output** | • 2 ciclos en estado HEDGED independientes<br>• Total pips locked: 40<br>• 4 operaciones hedge activas (2 por par)<br>• Sin interferencia |
| **Checks** | ✓ `eurusd_cycle.status == HEDGED`<br>✓ `gbpusd_cycle.status == HEDGED`<br>✓ `total_pips_locked == 40.0`<br>✓ `len(hedge_operations) == 4`<br>✓ Cada hedge vinculado a su par correcto |
| **CSV** | Ambos pares entran en HEDGED en ventana de 20 ticks |

### mp03_jpy_calculation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Cálculo de pips correcto para par JPY (2 decimales, multiplicador ×100) |
| **Input** | • USDJPY @ 110.00<br>• Entry: 110.00<br>• TP: 110.10 (+0.10 en precio = 10 pips)<br>• Multiplicador JPY: 100 (no 10000) |
| **Output** | • profit_pips: 10.0 (correctamente calculado)<br>• Fórmula: (110.10 - 110.00) × 100 = 10 pips |
| **Checks** | ✓ `operation.profit_pips == 10.0`<br>✓ Multiplicador correcto: 100 (no 10000)<br>✓ `_pips_between(110.00, 110.10, "USDJPY") == 10.0`<br>✓ Consistente con broker |
| **CSV** | USDJPY: 110.00 → 110.10 (TP alcanzado) |

### mp04_total_exposure

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Exposición total calcula correctamente suma de todos los pares activos |
| **Input** | • EURUSD: 3 ops × 0.01 lotes = 0.03<br>• GBPUSD: 2 ops × 0.01 lotes = 0.02<br>• USDJPY: 1 op × 0.01 lotes = 0.01<br>• Total: 0.06 lotes |
| **Output** | • Total lots: 0.06<br>• Total margin: 60 EUR (0.06 × 1000)<br>• Exposure %: 0.6% (60 / 10000) |
| **Checks** | ✓ `total_lots == 0.06`<br>✓ `total_margin_used == 60.0`<br>✓ `exposure_pct == 0.6`<br>✓ `exposure_pct < 30.0` (límite)<br>✓ Suma de todos los pares correcta |
| **CSV** | 3 archivos paralelos (EURUSD + GBPUSD + USDJPY) |

---

## JPY PAIRS (4 escenarios)

### j01_usdjpy_tp

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | USDJPY alcanza TP con cálculo correcto de pips (2 decimales) |
| **Input** | • Par: USDJPY<br>• Entry: 110.00<br>• TP: 110.10 (+10 pips)<br>• Precio alcanza: 110.10 |
| **Output** | • Operation: TP_HIT<br>• profit_pips: 10.0<br>• Cálculo: (110.10 - 110.00) × 100 = 10 pips |
| **Checks** | ✓ `operation.status == TP_HIT`<br>✓ `operation.profit_pips == 10.0`<br>✓ `operation.tp_price == 110.10`<br>✓ Precisión: 2 decimales mantenida |
| **CSV** | USDJPY: 110.00 → 110.10 |

### j02_usdjpy_hedged

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | USDJPY entra en estado HEDGED con cálculo correcto de pips locked |
| **Input** | • USDJPY @ 110.00<br>• BUY @ 110.05 activada<br>• SELL @ 109.95 activada<br>• Separación: 0.10 (10 pips en JPY) |
| **Output** | • Estado: HEDGED<br>• pips_locked: 20.0 (composición correcta para JPY)<br>• Multiplicador ×100 aplicado |
| **Checks** | ✓ `cycle.status == HEDGED`<br>✓ `cycle.accounting.pips_locked == 20.0`<br>✓ Separación calculada: 0.10 × 100 = 10 pips<br>✓ TP distance: 0.10 × 100 = 10 pips |
| **CSV** | USDJPY: 110.00 → ambas entries activadas |

### j03_usdjpy_recovery

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | USDJPY abre recovery con distancia correcta (20 pips = 0.20 en precio) |
| **Input** | • Main TP alcanzado @ 110.10<br>• Recovery debe colocarse a 20 pips = 0.20 desde TP<br>• Recovery BUY entry: 110.30 (110.10 + 0.20) |
| **Output** | • Recovery BUY: entry @ 110.30<br>• Recovery SELL: entry @ 109.90<br>• TP de recovery: 0.80 desde entry (80 pips) |
| **Checks** | ✓ `recovery_buy.entry_price == 110.30`<br>✓ `recovery_sell.entry_price == 109.90`<br>✓ `recovery_buy.tp_price == 111.10` (110.30 + 0.80)<br>✓ Distancia: 0.20 (20 pips × 0.01) |
| **CSV** | USDJPY: Main TP @ 110.10 → Recovery desde ahí |

### j04_usdjpy_pips_calculation

| Aspecto | Detalle |
|---------|---------|
| **Prioridad** | 🟡 ALTA |
| **Descripción** | Función `_pips_between()` usa multiplicador correcto (×100) para JPY |
| **Input** | • Price 1: 110.00<br>• Price 2: 110.50<br>• Diferencia: 0.50<br>• Par: USDJPY |
| **Output** | • Pips calculados: 50.0<br>• Fórmula: 0.50 × 100 = 50 pips<br>• NO usar 10000 (sería 5000 pips incorrecto) |
| **Checks** | ✓ `_pips_between(110.00, 110.50, "USDJPY") == 50.0`<br>✓ `_pips_between(110.00, 110.10, "USDJPY") == 10.0`<br>✓ Multiplicador detectado correctamente: `"JPY" in pair → ×100`<br>✓ Consistente con cálculos del broker |
| **CSV** | N/A (test unitario de función) |

---

## NOTAS FINALES

### Formato de Ejecución de Tests
```bash
# Test individual
pytest tests/test_scenarios/test_all_scenarios.py::test_scenario[c04_no_activation] -v

# Por categoría
pytest tests/test_scenarios/ -k "CORE" -v
pytest tests/test_scenarios/ -k "HEDGED" -v
pytest tests/test_scenarios/ -k "RECOVERY" -v

# Por prioridad
pytest tests/test_scenarios/ -m critical -v
pytest tests/test_scenarios/ -m high -v

# Todos los escenarios (62 tests)
pytest tests/test_scenarios/test_all_scenarios.py -v --tb=short

# Con reporte de cobertura
pytest tests/test_scenarios/ --cov=wsplumber --cov-report=html
```

### Markers de Pytest
```python
# En pytest.ini o conftest.py
[pytest]
markers =
    critical: Escenarios críticos que DEBEN pasar siempreContinuar7 ene1 / 5high: Escenarios de alta prioridad
medium: Escenarios de prioridad media
low: Escenarios de baja prioridad
integration: Tests de integración multi-componente
unit: Tests unitarios aislados

### Estructura de Reportes Esperada
===================== test session starts ======================
tests/test_scenarios/test_all_scenarios.py::test_scenario[c01_tp_simple_buy] PASSED [  1%]
tests/test_scenarios/test_all_scenarios.py::test_scenario[c01_tp_simple_sell] PASSED [  3%]
tests/test_scenarios/test_all_scenarios.py::test_scenario[c04_no_activation] PASSED [  4%]
tests/test_scenarios/test_all_scenarios.py::test_scenario[c05_gap_tp] PASSED [  6%]
...
tests/test_scenarios/test_all_scenarios.py::test_scenario[j04_usdjpy_pips_calculation] PASSED [100%]
===================== 62 passed in 87.34s ======================

### Priorización para Implementación

**FASE 1** (25 escenarios críticos 🔴):
- Todos los marcados como CRÍTICA
- Deben pasar al 100% antes de despliegue

**FASE 2** (32 escenarios alta prioridad 🟡):
- Implementar después de FASE 1
- Comportamiento importante pero no bloqueante

**FASE 3** (4 escenarios media + 1 baja):
- Edge cases y nice-to-have
- Pueden implementarse incrementalmente

---

## SIGUIENTE PASO: GENERADOR DE CSVs

Con esta matriz completa, el siguiente paso es crear:

1. **YAML de especificaciones** (`tests/fixtures/scenario_specs.yaml`)
   - Define cada escenario en formato estructurado
   - Incluye: pair, start_price, tick_sequence, expected_checks

2. **Script generador** (`tests/fixtures/scenario_generator.py`)
   - Lee el YAML
   - Genera los 62 archivos CSV en `tests/scenarios/`

3. **Loader de escenarios** (`tests/fixtures/scenario_loader.py`)
   - Carga specs desde YAML
   - Proporciona checks esperados para validación

4. **Test parametrizado** (`tests/test_scenarios/test_all_scenarios.py`)
   - Un solo test con `@pytest.mark.parametrize`
   - 62 ejecuciones automáticas

¿Quieres que continue con el **YAML de especificaciones** y el **script generador**? 🚀

FIN DE LA MATRIZ COMPLETA
Total: 58 escenarios documentados en formato compacto (los 4 detallados ya estaban en el documento principal).
¿Procedo con el YAML y el generador de CSVs? 🎯hacer los 10 detallados y cubrir todo el espectro. que solo queden modificaioneso variaciones de los detallados y sea redundante?7 enePLAN DE ESCENARIOS DETALLADOS - COBERTURA COMPLETA
Voy a analizar qué 10 escenarios detallados cubren TODO el espectro sin redundancia:

ANÁLISIS DE COBERTURA
Escenarios Actuales Detallados (4)

E1: Ciclo Simple Exitoso - Cubre:

✅ TP Main
✅ Renovación dual (FIX-001)
✅ Cancelación counter main


E2: Ambas Mains Activan (Hedge) - Cubre:

✅ Estado HEDGED
✅ Creación de hedges
✅ Neutralización de mains
✅ Bloqueo de 20 pips
✅ Cancelación hedge pendiente (FIX-002)


E3: Recovery N1 Exitoso - Cubre:

✅ Apertura recovery desde TP
✅ Distancia 20 pips
✅ FIFO cierre atómico Main+Hedge (FIX-003)
✅ Recovery TP 80 pips
✅ Costo primer recovery: 20 pips


E4: Recovery Multinivel - Cubre:

✅ Cascada N1→N2→N3
✅ FIFO múltiple
✅ Costo recoveries subsecuentes: 40 pips




LOS 6 ESCENARIOS ADICIONALES NECESARIOS
SELECCIÓN ESTRATÉGICA (Cobertura sin redundancia)
E5: Gap Atraviesa TP 🔴 CRÍTICA
¿Por qué es único?

Cubre comportamiento de gaps (no cubierto en E1-E4)
Manejo de slippage extremo
Detección de gap y ajuste de precios

Qué NO cubre E1:

E1 asume ejecución exacta en TP
E5 cubre precio post-gap > TP

E6: Gap Simultáneo Activa Ambas Mains (Hedge con Gap) 🟡 ALTA
¿Por qué es único?

Combina E2 (HEDGED) + gap
Activación simultánea en un tick
Metadata de gap en estado HEDGED

Qué NO cubre E2:

E2 asume activación secuencial normal
E6 cubre timestamps idénticos + gap_detected

E7: Recovery Falla N1 → Activa N2 🔴 CRÍTICA
¿Por qué es único?

Fallo de recovery (E3/E4 solo cubren éxitos)
Distancia de 40 pips para siguiente nivel
Queue con múltiples debt units activas

Qué NO cubre E4:

E4 asume todos alcanzan TP eventualmente
E7 cubre recovery que NO alcanza TP + cascada por distancia

E8: Ciclo Completa 10 TPs Sin Hedge 🟡 ALTA
¿Por qué es único?

Operación prolongada sin nunca entrar en HEDGED
Renovación dual múltiple (10 veces)
Acumulación de profit limpio

Qué NO cubre E1:

E1 muestra 1 solo TP
E8 valida consistencia en múltiples iteraciones

E9: USDJPY - Par JPY Completo 🟡 ALTA
¿Por qué es único?

Multiplicador ×100 (vs ×10000)
2 decimales (vs 4/5)
Todo el flujo: Main → HEDGED → Recovery con JPY

Qué NO cubren E1-E4:

Todos usan EURUSD (4-5 decimales)
E9 valida cálculo diferencial de pips

E10: Múltiples Pares Simultáneos + Exposición Total 🟡 ALTA
¿Por qué es único?

Multi-pair con EURUSD + GBPUSD + USDJPY
Cálculo de exposición agregada
Independencia de ciclos

Qué NO cubren E1-E4:

Todos single-pair
E10 valida aislamiento y exposición cross-pair


MATRIZ DE COBERTURA FINAL (10 ESCENARIOS)
EscenarioCoreHedgeRecoveryFIFOGapJPYMultiExposiciónE1: Ciclo Simple✅ TP✅ Renovación dual❌❌❌❌❌❌❌E2: Hedge❌✅ HEDGED✅ Neutraliza✅ 20 pips✅ Cancela counter❌❌❌❌❌❌E3: Recovery N1❌✅ (desde)✅ Desde TP✅ 20 pips dist✅ 80 pips TP✅ Atómico✅ Costo 20❌❌❌❌E4: Multinivel❌❌✅ N1→N2→N3✅ Éxito✅ Múltiple✅ Costo 40❌❌❌❌E5: Gap TP✅ Gap❌❌❌✅ Detección✅ Slippage❌❌❌E6: Gap Hedge❌✅ Gap simult❌❌✅ HEDGED+Gap❌❌❌E7: Recovery Falla❌❌✅ N1 no TP✅ N2 por dist❌❌❌❌❌E8: 10 TPs✅ Múltiple✅ Consistencia❌❌❌❌❌❌❌E9: USDJPY✅ (JPY)✅ (JPY)✅ (JPY)✅ (JPY)❌✅ Todo flujo✅ Mult ×100❌❌E10: Multi-Pair❌❌❌❌❌❌✅ 3 pares✅ Aislamiento✅ Agregada

COBERTURA DE LOS 62 ESCENARIOS
Con estos 10 detallados, el resto son variaciones o edge cases:
✅ CUBIERTO por E1-E10 (comportamiento core)
CategoríaCubiertosVariaciones/EdgeCORE (5)E1, E5• c04: no_activation (variación sin cruces)• c01_sell: espejo de c01_buyCYCLES (6)E1, E8• cy04: cancelación (ya en E1)• cy06: multi-pair (subset de E10)HEDGED (8)E2, E6• h05-h08: variaciones de secuencia/timingRECOVERY (10)E3, E4, E7• r04: SELL (espejo de r03)• r06-r10: variaciones de nivelesFIFO (4)E3, E4• f03-f04: casos específicos del mecanismo ya cubiertoRISK (5)E10 (exposición)• rm01-rm05: límites y validaciones (tests unitarios)MONEY (8)E1, E3• mm01-mm08: cálculos específicos (tests unitarios)EDGE (8)E5, E6• e01-e08: casos extremos, la mayoría unitariosMULTI (4)E10• mp01-mp04: subsets de E10JPY (4)E9• j01-j04: flujo completo en E9
❌ NO REQUIEREN DETALLE (son variaciones o unitarios)
Total variaciones: 52 escenarios

20 son espejos (BUY vs SELL, timing variations)
18 son subsets de detallados (parte del flujo ya cubierto)
14 son tests unitarios (no requieren CSV, ej: cálculos matemáticos)


PLAN DE ACCIÓN
1. Documentar E5-E10 con mismo nivel de detalle que E1-E4
Estructura por escenario:
markdown# ESCENARIO X: Nombre

## Referencia Documento Madre
- Líneas específicas

## Condiciones Iniciales
```yaml
...
```

## Secuencia de Pasos
### PASO 1: ...
### PASO 2: ...
...

## Estado Final Esperado
```yaml
...
```

## Checks Críticos
- [ ] Check 1
- [ ] Check 2
2. Mantener Matriz Compacta para los 52 restantes
Con los 10 detallados, la matriz solo necesita:

ID del escenario
Referencia a qué detallado extiende
Delta específico (qué cambia)

Ejemplo:
markdown### c01_tp_simple_sell

| Aspecto | Detalle |
|---------|---------|
| **Base** | E1: Ciclo Simple Exitoso |
| **Delta** | • Dirección: SELL (en lugar de BUY)<br>• Precio baja 10 pips (en lugar de subir) |
| **Checks únicos** | ✓ `operation.direction == "sell"`<br>✓ `operation.tp_price < operation.entry_price` |

RESUMEN
10 Escenarios Detallados:

✅ E1: Ciclo Simple (existente)
✅ E2: Hedge (existente)
✅ E3: Recovery N1 (existente)
✅ E4: Multinivel (existente)
➕ E5: Gap TP
➕ E6: Gap Hedge Simultáneo
➕ E7: Recovery Falla → N2
➕ E8: 10 TPs Sin Hedge
➕ E9: USDJPY Flujo Completo
➕ E10: Multi-Pair + Exposición

52 Escenarios en Matriz Compacta:

Referencia a base (E1-E10)
Solo documentan el delta
Validación simplificada


¿Quieres que proceda a crear los 6 escenarios detallados adicionales (E5-E10) con el mismo nivel de profundidad que E1-E4? 🚀si7 eneESCENARIOS DETALLADOS ADICIONALES (E5-E10)

ESCENARIO 5: Gap Atraviesa TP
Referencia Documento Madre

Líneas 301-315: Manejo de gaps y slippage
Sección "Eventos de mercado extraordinarios"
Nota: Gaps pueden causar ejecuciones más allá del TP esperado

Condiciones Iniciales
yamlaccount:
  balance: 10000.0
  equity: 10000.0
  margin_free: 10000.0
  
market:
  pair: EURUSD
  friday_close: 1.10050
  monday_open: 1.10150  # Gap de +100 pips
  
cycle:
  id: CYC_GAP_001
  status: ACTIVE
  
operations:
  - id: OP_BUY_001
    type: MAIN_BUY
    status: ACTIVE
    entry_price: 1.10020
    tp_price: 1.10120  # TP en medio del gap
    activated_at: "2025-01-05 14:00:00"
```

## Secuencia de Pasos

### PASO 1: Operación BUY Activa (Viernes)
**Trigger:** Precio cruza entry
```
[14:00:00.000] [INFO] [BrokerAdapter] Order filled: ticket=30001
[14:00:00.001] [INFO] [CycleOrchestrator] OP_BUY_001 activated
[14:00:00.002] [DEBUG] [CycleOrchestrator] Entry: 1.10020, TP: 1.10120
[14:00:00.003] [DEBUG] [CycleOrchestrator] Status: PENDING → ACTIVE
```

**Checks:**
- [ ] `op_buy.status == ACTIVE`
- [ ] `op_buy.entry_price == 1.10020`
- [ ] `op_buy.tp_price == 1.10120`
- [ ] `op_buy.broker_ticket == "30001"`

---

### PASO 2: Mercado Cierra (Viernes 22:00)
**Trigger:** Cierre semanal
```
[22:00:00.000] [INFO] [PriceMonitor] Market closing for weekend
[22:00:00.001] [DEBUG] [PriceMonitor] Last price: bid=1.10050, ask=1.10070
[22:00:00.002] [INFO] [System] Active positions: 1 (OP_BUY_001)
[22:00:00.003] [INFO] [System] Weekend mode: monitoring disabled until Monday
```

**Checks:**
- [ ] `op_buy.status == ACTIVE` (sin cambios)
- [ ] Última precio: 1.10050 (50 pips por debajo del TP)

---

### PASO 3: Gap de Apertura (Lunes 00:01)
**Trigger:** Mercado reabre con gap alcista
```
[00:01:00.000] [INFO] [PriceMonitor] Market reopening
[00:01:00.001] [WARN] [PriceMonitor] GAP DETECTED!
[00:01:00.002] [DEBUG] [PriceMonitor] Previous close: 1.10050
[00:01:00.003] [DEBUG] [PriceMonitor] Current open: 1.10150
[00:01:00.004] [WARN] [PriceMonitor] Gap size: +100 pips (0.00100)
[00:01:00.005] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10150, ask=1.10170
```

**Checks:**
- [ ] Gap detectado: `tick.metadata['gap_detected'] == True`
- [ ] `tick.metadata['gap_size'] == 100.0`
- [ ] `tick.metadata['previous_price'] == 1.10050`
- [ ] Precio actual: 1.10150 (cruza el TP @ 1.10120)

---

### PASO 4: Broker Ejecuta TP con Slippage
**Trigger:** TP atravesado por gap
```
[00:01:00.100] [INFO] [BrokerAdapter] Position closed by TP: ticket=30001
[00:01:00.101] [WARN] [BrokerAdapter] TP executed with SLIPPAGE
[00:01:00.102] [DEBUG] [BrokerAdapter] Expected TP: 1.10120
[00:01:00.103] [DEBUG] [BrokerAdapter] Actual close: 1.10150
[00:01:00.104] [DEBUG] [BrokerAdapter] Slippage: +30 pips (favorable)
[00:01:00.105] [INFO] [BrokerAdapter] Close price: 1.10150, timestamp: 2025-01-08 00:01:00
```

**Checks:**
- [ ] `op_buy.status == TP_HIT` (broker marca como TP)
- [ ] `op_buy.actual_close_price == 1.10150`
- [ ] `op_buy.tp_price == 1.10120` (original sin cambios)
- [ ] Slippage calculado: +30 pips

---

### PASO 5: Sistema Sincroniza y Detecta Slippage
**Trigger:** Sync detecta cierre con gap
```
[00:01:00.200] [INFO] [TradingService] Syncing active positions
[00:01:00.201] [INFO] [TradingService] Position 30001 found in broker history
[00:01:00.202] [DEBUG] [TradingService] Status: CLOSED, Close price: 1.10150
[00:01:00.203] [INFO] [CycleOrchestrator] Processing TP_HIT for OP_BUY_001
[00:01:00.204] [WARN] [CycleOrchestrator] Gap execution detected
[00:01:00.205] [DEBUG] [CycleOrchestrator] TP expected: 1.10120
[00:01:00.206] [DEBUG] [CycleOrchestrator] Actual close: 1.10150
[00:01:00.207] [DEBUG] [CycleOrchestrator] Favorable slippage: +30 pips
```

**Checks:**
- [ ] `op_buy.status == TP_HIT`
- [ ] `op_buy.metadata['gap_execution'] == True`
- [ ] `op_buy.metadata['expected_tp'] == 1.10120`
- [ ] `op_buy.metadata['actual_close'] == 1.10150`

---

### PASO 6: Calcular Profit con Slippage
**Trigger:** Actualización de P&L
```
[00:01:00.300] [INFO] [PnLCalculator] Calculating profit with slippage
[00:01:00.301] [DEBUG] [PnLCalculator] Entry: 1.10020
[00:01:00.302] [DEBUG] [PnLCalculator] Close: 1.10150
[00:01:00.303] [DEBUG] [PnLCalculator] Gross profit: 0.00130 = 13.0 pips
[00:01:00.304] [DEBUG] [PnLCalculator] Expected: 10.0 pips
[00:01:00.305] [DEBUG] [PnLCalculator] Slippage bonus: +3.0 pips
[00:01:00.306] [INFO] [PnLCalculator] Profit: 13.0 pips, €1.30 (0.01 lots)
[00:01:00.307] [DEBUG] [PnLCalculator] Commissions: -€14.00
[00:01:00.308] [INFO] [PnLCalculator] Net P&L: -€12.70
```

**Checks:**
- [ ] `op_buy.profit_pips == 13.0` (no 10.0)
- [ ] `op_buy.profit_eur == 1.30`
- [ ] `op_buy.slippage_pips == 3.0` (favorable)
- [ ] `op_buy.net_profit_eur == -12.70` (con comisiones)

---

### PASO 7: Actualizar Balance y Renovar Operaciones
**Trigger:** Contabilidad post-TP
```
[00:01:00.400] [INFO] [AccountingService] Updating account balance
[00:01:00.401] [DEBUG] [AccountingService] Balance: 10000.00 → 9987.30
[00:01:00.402] [DEBUG] [AccountingService] Net P&L: -12.70 (profit - commissions)
[00:01:00.403] [INFO] [CycleOrchestrator] *** RENOVANDO OPERACIONES MAIN (BUY + SELL) ***
[00:01:00.404] [DEBUG] [CycleOrchestrator] Precio actual post-gap: bid=1.10150, ask=1.10170
[00:01:00.405] [INFO] [BrokerAdapter] Enviando BUY_STOP: entry=1.10170, tp=1.10270
[00:01:00.406] [INFO] [BrokerAdapter] Enviando SELL_STOP: entry=1.10150, tp=1.10050
[00:01:00.500] [INFO] [BrokerAdapter] BUY_STOP confirmado: ticket=30002
[00:01:00.501] [INFO] [BrokerAdapter] SELL_STOP confirmado: ticket=30003
[00:01:00.502] [INFO] [CycleOrchestrator] Operaciones main renovadas desde precio post-gap
```

**Checks:**
- [ ] `account.balance == 9987.30`
- [ ] Nueva BUY: `entry=1.10170, tp=1.10270, status=PENDING`
- [ ] Nueva SELL: `entry=1.10150, tp=1.10050, status=PENDING`
- [ ] Ambas colocadas desde precio post-gap (no desde pre-gap)

---

### PASO 8: Registrar Metadata de Gap
**Trigger:** Auditoría del evento
```
[00:01:00.600] [INFO] [CycleOrchestrator] Recording gap event metadata
[00:01:00.601] [DEBUG] [CycleOrchestrator] Gap event stored in cycle metadata
[00:01:00.602] [INFO] [AlertsService] Creating gap alert
[00:01:00.603] [INFO] [AlertsService] Alert created: severity=INFO, type=gap_execution
Checks:

 cycle.metadata['gap_events'] contiene entrada
 Gap event: {'timestamp': '2025-01-08 00:01:00', 'size': 100.0, 'operation_id': 'OP_BUY_001'}
 Alerta creada: severity=INFO, type=gap_execution


ESTADO FINAL ESPERADO
yamlcycle:
  id: CYC_GAP_001
  status: ACTIVE  # Continúa operando
  total_tps: 1
  pips_won: 13.0  # Con slippage favorable
  
operations:
  # === OPERACIÓN CERRADA CON GAP ===
  - id: OP_BUY_001
    type: MAIN_BUY
    status: TP_HIT
    entry_price: 1.10020
    tp_price: 1.10120  # TP esperado
    actual_close_price: 1.10150  # Real con gap
    profit_pips: 13.0  # 10 + 3 slippage
    slippage_pips: 3.0  # Favorable
    metadata:
      gap_execution: true
      expected_tp: 1.10120
      actual_close: 1.10150
      gap_size: 100.0
      
  # === NUEVA ITERACIÓN (Post-Gap) ===
  - id: OP_BUY_002
    type: MAIN_BUY
    status: PENDING
    entry_price: 1.10170  # Desde precio post-gap
    tp_price: 1.10270
    
  - id: OP_SELL_002
    type: MAIN_SELL
    status: PENDING
    entry_price: 1.10150  # Desde precio post-gap
    tp_price: 1.10050
    
account:
  balance: 9987.30  # 10000 + 1.30 profit - 14.00 commissions
  equity: 9987.30
  
metadata:
  gap_events:
    - timestamp: "2025-01-08 00:01:00"
      size: 100.0
      direction: "up"
      operation_affected: "OP_BUY_001"
      slippage: 3.0
      favorable: true

CHECKS CRÍTICOS
Gap Detection

 tick.metadata['gap_detected'] == True
 tick.metadata['gap_size'] == 100.0
 Gap registrado en cycle metadata

Slippage Calculation

 op_buy.slippage_pips == 3.0
 op_buy.actual_close_price > op_buy.tp_price
 Slippage favorable (positivo para profit)

P&L Adjustment

 op_buy.profit_pips == 13.0 (no 10.0 estándar)
 Balance ajustado correctamente con slippage

Renovación Post-Gap

 Nuevas operaciones desde precio post-gap (1.10150/1.10170)
 NO desde precio pre-gap (1.10050)

Metadata y Auditoría

 op_buy.metadata['gap_execution'] == True
 Alerta creada: type=gap_execution
 Evento registrado en cycle.metadata


ESCENARIO 6: Gap Simultáneo Activa Ambas Mains (Hedge con Gap)
Referencia Documento Madre

Líneas 124-133: Cobertura cuando ambas se activan
Líneas 301-315: Manejo de gaps
Caso especial: Gap activa ambas direcciones en un tick

Condiciones Iniciales
yamlaccount:
  balance: 10000.0
  equity: 10000.0
  
market:
  pair: EURUSD
  friday_close: 1.10000
  monday_open: 1.10050  # Gap de +50 pips
  
cycle:
  id: CYC_GAP_HEDGE_001
  status: ACTIVE
  
operations:
  - id: OP_BUY_001
    type: MAIN_BUY
    status: PENDING
    entry_price: 1.10020  # Será cruzado por gap
    tp_price: 1.10120
    
  - id: OP_SELL_001
    type: MAIN_SELL
    status: PENDING
    entry_price: 1.09980  # También cruzado por gap
    tp_price: 1.09880
```

## Secuencia de Pasos

### PASO 1: Operaciones Pendientes (Viernes)
**Trigger:** Ciclo iniciado, órdenes colocadas
```
[21:00:00.000] [INFO] [CycleOrchestrator] New cycle opened: CYC_GAP_HEDGE_001
[21:00:00.001] [INFO] [BrokerAdapter] BUY_STOP placed: ticket=40001, entry=1.10020
[21:00:00.002] [INFO] [BrokerAdapter] SELL_STOP placed: ticket=40002, entry=1.09980
[21:00:00.003] [DEBUG] [CycleOrchestrator] Waiting for price to cross entries
[21:00:00.004] [INFO] [System] Current price: 1.10000 (between entries)
```

**Checks:**
- [ ] `op_buy.status == PENDING`
- [ ] `op_sell.status == PENDING`
- [ ] Precio actual: 1.10000 (no activa ninguna)

---

### PASO 2: Mercado Cierra (Viernes 22:00)
**Trigger:** Cierre semanal
```
[22:00:00.000] [INFO] [PriceMonitor] Market closing for weekend
[22:00:00.001] [DEBUG] [PriceMonitor] Last price: 1.10000
[22:00:00.002] [INFO] [System] Pending orders: 2 (BUY @ 1.10020, SELL @ 1.09980)
[22:00:00.003] [INFO] [System] Weekend mode activated
```

**Checks:**
- [ ] Ambas siguen `PENDING`
- [ ] Precio de cierre: 1.10000

---

### PASO 3: Gap Masivo en Apertura (Lunes 00:01)
**Trigger:** Gap atraviesa ambas entries
```
[00:01:00.000] [INFO] [PriceMonitor] Market reopening
[00:01:00.001] [CRITICAL] [PriceMonitor] *** MEGA GAP DETECTED ***
[00:01:00.002] [DEBUG] [PriceMonitor] Previous close: 1.10000
[00:01:00.003] [DEBUG] [PriceMonitor] Current open: 1.10050
[00:01:00.004] [WARN] [PriceMonitor] Gap size: +50 pips
[00:01:00.005] [WARN] [PriceMonitor] Gap crosses BOTH entries!
[00:01:00.006] [DEBUG] [PriceMonitor] BUY entry @ 1.10020: CROSSED (gap +30 pips above)
[00:01:00.007] [DEBUG] [PriceMonitor] SELL entry @ 1.09980: CROSSED (gap +70 pips above)
[00:01:00.008] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10050, ask=1.10070
```

**Checks:**
- [ ] Gap detectado: +50 pips
- [ ] Gap > BUY entry (1.10020)
- [ ] Gap > SELL entry (1.09980)
- [ ] Ambas entries cruzadas en mismo tick

---

### PASO 4: Broker Ejecuta Ambas Órdenes Simultáneamente
**Trigger:** Stop orders activadas por gap
```
[00:01:00.100] [INFO] [BrokerAdapter] BUY_STOP triggered: ticket=40001
[00:01:00.101] [INFO] [BrokerAdapter] SELL_STOP triggered: ticket=40002
[00:01:00.102] [WARN] [BrokerAdapter] SIMULTANEOUS FILLS (gap execution)
[00:01:00.103] [DEBUG] [BrokerAdapter] BUY filled @ 1.10050 (gap slippage +30 pips from entry)
[00:01:00.104] [DEBUG] [BrokerAdapter] SELL filled @ 1.10050 (gap slippage +70 pips from entry)
[00:01:00.105] [INFO] [BrokerAdapter] Fill timestamp: 2025-01-08 00:01:00.100 (SAME)
```

**Checks:**
- [ ] BUY: `status == ACTIVE`, `actual_entry_price == 1.10050`
- [ ] SELL: `status == ACTIVE`, `actual_entry_price == 1.10050`
- [ ] `buy.activated_at == sell.activated_at` (timestamps idénticos)
- [ ] BUY slippage: +30 pips (1.10050 vs 1.10020)
- [ ] SELL slippage: +70 pips (1.10050 vs 1.09980)

---

### PASO 5: Sistema Detecta Activación Dual → HEDGED
**Trigger:** Sync detecta ambas activas
```
[00:01:00.200] [INFO] [TradingService] Syncing active positions
[00:01:00.201] [INFO] [TradingService] Position 40001 (BUY): ACTIVE @ 1.10050
[00:01:00.202] [INFO] [TradingService] Position 40002 (SELL): ACTIVE @ 1.10050
[00:01:00.203] [CRITICAL] [CycleOrchestrator] *** BOTH MAINS ACTIVE → HEDGE ***
[00:01:00.204] [WARN] [CycleOrchestrator] SIMULTANEOUS ACTIVATION (gap event)
[00:01:00.205] [DEBUG] [CycleOrchestrator] Activation timestamps match: 00:01:00.100
[00:01:00.206] [INFO] [CycleOrchestrator] Transitioning: ACTIVE → HEDGED
```

**Checks:**
- [ ] `cycle.status == HEDGED`
- [ ] Ambas operaciones activadas en mismo tick
- [ ] Metadata: `simultaneous_activation = True`

---

### PASO 6: Crear Operaciones de Hedge
**Trigger:** Estado HEDGED requiere hedges
```
[00:01:00.300] [INFO] [CycleOrchestrator] Creating hedge operations
[00:01:00.301] [DEBUG] [CycleOrchestrator] HEDGE_BUY to cover SELL @ 1.10050
[00:01:00.302] [DEBUG] [CycleOrchestrator] HEDGE_SELL to cover BUY @ 1.10050
[00:01:00.303] [INFO] [BrokerAdapter] Placing HEDGE_BUY: entry=1.10050, tp=1.10120
[00:01:00.304] [INFO] [BrokerAdapter] Placing HEDGE_SELL: entry=1.10050, tp=1.09980
[00:01:00.400] [INFO] [BrokerAdapter] HEDGE_BUY confirmed: ticket=40003
[00:01:00.401] [INFO] [BrokerAdapter] HEDGE_SELL confirmed: ticket=40004
```

**Checks:**
- [ ] `hedge_buy.status == PENDING`
- [ ] `hedge_sell.status == PENDING`
- [ ] `hedge_buy.entry_price == 1.10050` (mismo punto de activación)
- [ ] `hedge_sell.entry_price == 1.10050`

---

### PASO 7: Neutralizar Mains
**Trigger:** Hedges creados
```
[00:01:00.500] [INFO] [CycleOrchestrator] Neutralizing main operations
[00:01:00.501] [DEBUG] [CycleOrchestrator] OP_BUY_001: ACTIVE → NEUTRALIZED
[00:01:00.502] [DEBUG] [CycleOrchestrator] Covered by: OP_HEDGE_SELL_001
[00:01:00.503] [DEBUG] [CycleOrchestrator] OP_SELL_001: ACTIVE → NEUTRALIZED
[00:01:00.504] [DEBUG] [CycleOrchestrator] Covered by: OP_HEDGE_BUY_001
```

**Checks:**
- [ ] `op_buy.status == NEUTRALIZED`
- [ ] `op_sell.status == NEUTRALIZED`
- [ ] `op_buy.linked_operation_id == hedge_sell.id`
- [ ] `op_sell.linked_operation_id == hedge_buy.id`

---

### PASO 8: Calcular Pips Bloqueados con Gap Adjustment
**Trigger:** Contabilidad de deuda
```
[00:01:00.600] [INFO] [AccountingService] Calculating pips_locked with GAP adjustment
[00:01:00.601] [DEBUG] [AccountingService] === DEBT COMPOSITION ===
[00:01:00.602] [DEBUG] [AccountingService] Standard calculation:
[00:01:00.603] [DEBUG] [AccountingService]   • Separation (expected): 4 pips
[00:01:00.604] [DEBUG] [AccountingService]   • TP distance: 10 pips
[00:01:00.605] [DEBUG] [AccountingService]   • Margin: 6 pips
[00:01:00.606] [DEBUG] [AccountingService]   • Base total: 20 pips
[00:01:00.607] [WARN] [AccountingService] GAP ADJUSTMENT:
[00:01:00.608] [DEBUG] [AccountingService]   • Actual separation (gap): 0 pips (both @ 1.10050)
[00:01:00.609] [DEBUG] [AccountingService]   • BUY slippage cost: +30 pips
[00:01:00.610] [DEBUG] [AccountingService]   • SELL slippage cost: +70 pips
[00:01:00.611] [DEBUG] [AccountingService]   • Additional gap cost: +100 pips
[00:01:00.612] [INFO] [AccountingService] TOTAL pips_locked: 20 + 100 = 120 pips
[00:01:00.613] [WARN] [AccountingService] *** HIGH GAP COST DETECTED ***
```

**Checks:**
- [ ] `cycle.accounting.pips_locked == 120.0` (no 20.0 estándar)
- [ ] `cycle.accounting.metadata['gap_adjustment'] == 100.0`
- [ ] `cycle.accounting.metadata['base_cost'] == 20.0`
- [ ] Composición incluye slippage de ambas operaciones

---

### PASO 9: Registrar Evento de Gap en Metadata
**Trigger:** Auditoría completa
```
[00:01:00.700] [INFO] [CycleOrchestrator] Recording gap hedge event
[00:01:00.701] [DEBUG] [CycleOrchestrator] Metadata updated
[00:01:00.702] [INFO] [AlertsService] Creating CRITICAL alert: gap_hedge_activation
[00:01:00.703] [WARN] [AlertsService] High cost event: 120 pips locked
Checks:

 cycle.metadata['gap_hedge_event'] existe
 Event data: {'gap_size': 50, 'cost_adjustment': 100, 'simultaneous': True}
 Alerta creada: severity=CRITICAL, type=gap_hedge_activation


ESTADO FINAL ESPERADO
yamlcycle:
  id: CYC_GAP_HEDGE_001
  status: HEDGED
  pips_locked: 120.0  # 20 base + 100 gap adjustment
  
operations:
  # === MAIN OPERATIONS (Neutralizadas) ===
  - id: OP_BUY_001
    type: MAIN_BUY
    status: NEUTRALIZED
    entry_price: 1.10020  # Entry esperado
    actual_entry_price: 1.10050  # Fill real con gap
    slippage_pips: 30.0  # Desfavorable para entry
    activated_at: "2025-01-08 00:01:00.100"
    neutralized_by: "OP_HEDGE_SELL_001"
    metadata:
      gap_fill: true
      expected_entry: 1.10020
      actual_entry: 1.10050
      
  - id: OP_SELL_001
    type: MAIN_SELL
    status: NEUTRALIZED
    entry_price: 1.09980
    actual_entry_price: 1.10050
    slippage_pips: 70.0  # Muy desfavorable
    activated_at: "2025-01-08 00:01:00.100"  # MISMO timestamp
    neutralized_by: "OP_HEDGE_BUY_001"
    metadata:
      gap_fill: true
      expected_entry: 1.09980
      actual_entry: 1.10050
      
  # === HEDGE OPERATIONS (Pendientes) ===
  - id: OP_HEDGE_BUY_001
    type: HEDGE_BUY
    status: PENDING
    entry_price: 1.10050
    tp_price: 1.10120
    linked_operation_id: "OP_SELL_001"
    metadata:
      covering_operation: "OP_SELL_001"
      
  - id: OP_HEDGE_SELL_001
    type: HEDGE_SELL
    status: PENDING
    entry_price: 1.10050
    tp_price: 1.09980
    linked_operation_id: "OP_BUY_001"
    metadata:
      covering_operation: "OP_BUY_001"
      
account:
  balance: 10000.0  # Sin cambios (posiciones abiertas)
  equity: 10000.0  # Floating neutralizado por hedge
  
metadata:
  gap_hedge_event:
    timestamp: "2025-01-08 00:01:00"
    gap_size: 50.0
    simultaneous_activation: true
    buy_slippage: 30.0
    sell_slippage: 70.0
    total_gap_cost: 100.0
    base_cost: 20.0
    total_pips_locked: 120.0
    operations_affected: ["OP_BUY_001", "OP_SELL_001"]

CHECKS CRÍTICOS
Gap Detection

 tick.metadata['gap_detected'] == True
 tick.metadata['gap_size'] == 50.0
 Gap atraviesa ambas entries

Simultaneous Activation

 op_buy.activated_at == op_sell.activated_at
 Timestamps idénticos (mismo tick)
 cycle.metadata['simultaneous_activation'] == True

Slippage Calculation

 BUY: slippage_pips == 30.0 (entry 1.10020 vs fill 1.10050)
 SELL: slippage_pips == 70.0 (entry 1.09980 vs fill 1.10050)
 Ambos slippages desfavorables (aumentan costo)

Pips Locked Adjustment

 pips_locked == 120.0 (no 20.0 estándar)
 Composición: 20 (base) + 100 (gap adjustment)
 metadata['gap_adjustment'] == 100.0

Hedge Creation

 2 hedges creados desde precio post-gap (1.10050)
 Ambos hedges vinculados a mains correctas
 Status: PENDING (esperando activación)

Metadata y Auditoría

 cycle.metadata['gap_hedge_event'] completo
 Alerta CRITICAL creada
 Slippages de ambas operaciones registrados


Continuaré con E7 en el siguiente mensaje...si7 eneESCENARIO 7: Recovery Falla N1 → Activa N2
Referencia Documento Madre

Líneas 156-166: Sistema FIFO y recoveries
Líneas 178-189: Cascada de recoveries
Sección "Recovery que no alcanza TP activa siguiente nivel"

Condiciones Iniciales
yamlaccount:
  balance: 10000.0
  equity: 10000.0
  
market:
  pair: EURUSD
  current_price: 1.10120  # Precio de referencia (TP del main)
  
parent_cycle:
  id: CYC_PARENT_001
  status: IN_RECOVERY
  pips_locked: 20.0
  recovery_level: 0
  recovery_queue: ["OP_MAIN_SELL_001_debt_unit"]
  
operations_existing:
  - id: OP_MAIN_SELL_001
    type: MAIN_SELL
    status: NEUTRALIZED
    entry_price: 1.09980
    
  - id: OP_HEDGE_BUY_001
    type: HEDGE_BUY
    status: ACTIVE
    entry_price: 1.10020
    covering_operation: "OP_MAIN_SELL_001"
    
recovery_cycle:
  id: REC_N1_001
  status: ACTIVE
  recovery_level: 1
  parent_cycle_id: "CYC_PARENT_001"
```

## Secuencia de Pasos

### PASO 1: Recovery N1 Creado y Colocado
**Trigger:** Ciclo entra en recovery tras HEDGED
```
[10:00:00.000] [INFO] [CycleOrchestrator] Opening recovery cycle N1
[10:00:00.001] [DEBUG] [CycleOrchestrator] Parent cycle: CYC_PARENT_001
[10:00:00.002] [DEBUG] [CycleOrchestrator] Reference price (main TP): 1.10120
[10:00:00.003] [DEBUG] [CycleOrchestrator] Recovery distance: 20 pips
[10:00:00.004] [INFO] [CycleOrchestrator] === RECOVERY N1 PLACEMENT ===
[10:00:00.005] [DEBUG] [CycleOrchestrator] BUY entry: 1.10120 + 0.00020 = 1.10140
[10:00:00.006] [DEBUG] [CycleOrchestrator] SELL entry: 1.10120 - 0.00020 = 1.10100
[10:00:00.007] [DEBUG] [CycleOrchestrator] BUY TP: 1.10140 + 0.00080 = 1.10220
[10:00:00.008] [DEBUG] [CycleOrchestrator] SELL TP: 1.10100 - 0.00080 = 1.10020
[10:00:00.009] [INFO] [BrokerAdapter] Placing RECOVERY_BUY: entry=1.10140
[10:00:00.010] [INFO] [BrokerAdapter] Placing RECOVERY_SELL: entry=1.10100
[10:00:00.100] [INFO] [BrokerAdapter] RECOVERY_BUY confirmed: ticket=50001
[10:00:00.101] [INFO] [BrokerAdapter] RECOVERY_SELL confirmed: ticket=50002
```

**Checks:**
- [ ] `rec_buy.entry_price == 1.10140` (TP + 20 pips)
- [ ] `rec_sell.entry_price == 1.10100` (TP - 20 pips)
- [ ] `rec_buy.tp_price == 1.10220` (entry + 80 pips)
- [ ] `rec_sell.tp_price == 1.10020` (entry - 80 pips)
- [ ] Ambos: `status == PENDING`

---

### PASO 2: Precio Activa Recovery N1 BUY
**Trigger:** Precio alcanza 1.10140
```
[10:05:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10140, ask=1.10160
[10:05:00.001] [INFO] [BrokerAdapter] Order filled: ticket=50001
[10:05:00.002] [INFO] [CycleOrchestrator] Recovery N1 BUY activated
[10:05:00.003] [DEBUG] [CycleOrchestrator] OP_REC_N1_BUY_001: PENDING → ACTIVE
[10:05:00.004] [DEBUG] [CycleOrchestrator] Entry: 1.10140, TP: 1.10220 (+80 pips target)
[10:05:00.005] [INFO] [CycleOrchestrator] Recovery N1 in progress, monitoring price
```

**Checks:**
- [ ] `rec_n1_buy.status == ACTIVE`
- [ ] `rec_n1_buy.actual_entry_price == 1.10140`
- [ ] `rec_n1_buy.broker_ticket == "50001"`
- [ ] `rec_n1_sell.status == PENDING` (aún no activa)

---

### PASO 3: Precio Sube Pero NO Alcanza TP de N1
**Trigger:** Movimiento insuficiente para TP
```
[10:10:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10170, ask=1.10190
[10:10:00.001] [DEBUG] [PriceMonitor] Recovery N1 BUY floating: +30 pips
[10:10:00.002] [DEBUG] [PriceMonitor] Distance to TP: 50 pips (need 1.10220)
[10:10:00.003] [INFO] [PriceMonitor] Recovery N1 BUY: ACTIVE, no TP yet

[10:15:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10160, ask=1.10180
[10:15:00.001] [DEBUG] [PriceMonitor] Price retracing, floating: +20 pips
[10:15:00.002] [WARN] [PriceMonitor] Recovery N1 not making progress toward TP

[10:20:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10150, ask=1.10170
[10:20:00.001] [DEBUG] [PriceMonitor] Price continued retrace, floating: +10 pips
[10:20:00.002] [WARN] [PriceMonitor] Recovery N1 losing ground
```

**Checks:**
- [ ] `rec_n1_buy.status == ACTIVE` (sin cambios)
- [ ] Precio actual < TP (1.10170 < 1.10220)
- [ ] Floating P&L positivo pero insuficiente
- [ ] TP no alcanzado

---

### PASO 4: Precio Continúa Adverso → Distancia para N2
**Trigger:** Precio alcanza +40 pips desde N1 entry
```
[10:30:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10180, ask=1.10200
[10:30:00.001] [WARN] [StrategyEngine] Price moved +40 pips from N1 entry
[10:30:00.002] [DEBUG] [StrategyEngine] N1 entry: 1.10140
[10:30:00.003] [DEBUG] [StrategyEngine] Current: 1.10180
[10:30:00.004] [DEBUG] [StrategyEngine] Distance: 40 pips
[10:30:00.005] [CRITICAL] [StrategyEngine] *** RECOVERY LEVEL STEP THRESHOLD MET ***
[10:30:00.006] [INFO] [StrategyEngine] Generating signal: OPEN_RECOVERY (N2)
```

**Checks:**
- [ ] Distancia desde N1 entry: 40 pips
- [ ] N1 sigue `ACTIVE` (no cerrado)
- [ ] Señal generada: `OPEN_RECOVERY` para N2
- [ ] `parent_cycle.recovery_level == 1` (antes de crear N2)

---

### PASO 5: Sistema Crea Recovery N2
**Trigger:** Señal OPEN_RECOVERY procesada
```
[10:30:00.100] [INFO] [CycleOrchestrator] Processing OPEN_RECOVERY signal
[10:30:00.101] [DEBUG] [CycleOrchestrator] Current recovery level: 1
[10:30:00.102] [INFO] [CycleOrchestrator] === CREATING RECOVERY N2 ===
[10:30:00.103] [DEBUG] [CycleOrchestrator] Reference: N1 entry (1.10140)
[10:30:00.104] [DEBUG] [CycleOrchestrator] N2 distance: 40 pips from N1
[10:30:00.105] [DEBUG] [CycleOrchestrator] N2 BUY entry: 1.10140 + 0.00040 = 1.10180
[10:30:00.106] [DEBUG] [CycleOrchestrator] N2 SELL entry: 1.10140 - 0.00040 = 1.10100
[10:30:00.107] [DEBUG] [CycleOrchestrator] N2 BUY TP: 1.10180 + 0.00080 = 1.10260
[10:30:00.108] [DEBUG] [CycleOrchestrator] N2 SELL TP: 1.10100 - 0.00080 = 1.10020
[10:30:00.109] [INFO] [BrokerAdapter] Placing RECOVERY_BUY N2: entry=1.10180
[10:30:00.110] [INFO] [BrokerAdapter] Placing RECOVERY_SELL N2: entry=1.10100
```

**Checks:**
- [ ] `rec_n2_buy.entry_price == 1.10180` (N1 + 40 pips)
- [ ] `rec_n2_sell.entry_price == 1.10100` (N1 - 40 pips)
- [ ] `rec_n2_buy.tp_price == 1.10260` (+80 pips)
- [ ] `rec_n2_sell.tp_price == 1.10020` (-80 pips)

---

### PASO 6: N2 Confirmado y Agregado a Queue
**Trigger:** Broker confirma órdenes
```
[10:30:00.200] [INFO] [BrokerAdapter] RECOVERY_BUY N2 confirmed: ticket=50003
[10:30:00.201] [INFO] [BrokerAdapter] RECOVERY_SELL N2 confirmed: ticket=50004
[10:30:00.202] [INFO] [CycleOrchestrator] Recovery N2 operations placed
[10:30:00.203] [DEBUG] [CycleOrchestrator] Adding N2 to recovery queue
[10:30:00.204] [INFO] [CycleOrchestrator] === RECOVERY QUEUE UPDATED ===
[10:30:00.205] [DEBUG] [CycleOrchestrator] Queue before: ["OP_MAIN_SELL_001_debt_unit"]
[10:30:00.206] [DEBUG] [CycleOrchestrator] Queue after: ["OP_MAIN_SELL_001_debt_unit", "REC_N1_001_debt_unit"]
[10:30:00.207] [INFO] [CycleOrchestrator] Parent cycle recovery_level: 1 → 2
```

**Checks:**
- [ ] `rec_n2_buy.broker_ticket == "50003"`
- [ ] `rec_n2_sell.broker_ticket == "50004"`
- [ ] Ambos N2: `status == PENDING`
- [ ] `parent_cycle.recovery_level == 2`
- [ ] `len(parent_cycle.recovery_queue) == 2`

---

### PASO 7: Recovery Queue Composition
**Trigger:** Validación de estructura FIFO
```
[10:30:00.300] [INFO] [AccountingService] Validating recovery queue composition
[10:30:00.301] [DEBUG] [AccountingService] === QUEUE STRUCTURE ===
[10:30:00.302] [DEBUG] [AccountingService] [0] "OP_MAIN_SELL_001_debt_unit"
[10:30:00.303] [DEBUG] [AccountingService]     - Type: Main + Hedge
[10:30:00.304] [DEBUG] [AccountingService]     - Cost: 20 pips
[10:30:00.305] [DEBUG] [AccountingService]     - Components: separation(4) + tp(10) + margin(6)
[10:30:00.306] [DEBUG] [AccountingService] [1] "REC_N1_001_debt_unit"
[10:30:00.307] [DEBUG] [AccountingService]     - Type: Recovery N1 (not closed)
[10:30:00.308] [DEBUG] [AccountingService]     - Cost: 40 pips
[10:30:00.309] [DEBUG] [AccountingService]     - Status: ACTIVE (waiting for resolution)
[10:30:00.310] [INFO] [AccountingService] Total debt in queue: 60 pips (20 + 40)
[10:30:00.311] [INFO] [AccountingService] Next recovery (N2) must earn 80 pips to clear queue
```

**Checks:**
- [ ] Queue position [0]: Main+Hedge debt unit (20 pips)
- [ ] Queue position [1]: N1 debt unit (40 pips)
- [ ] Total cost to clear: 60 pips
- [ ] N2 TP = 80 pips (sufficient to clear queue + 20 profit)

---

### PASO 8: Actualizar Metadata del Ciclo
**Trigger:** Registro de cascada
```
[10:30:00.400] [INFO] [CycleOrchestrator] Recording recovery cascade event
[10:30:00.401] [DEBUG] [CycleOrchestrator] Metadata updated
[10:30:00.402] [INFO] [CycleOrchestrator] Recovery cascade: N1 → N2
[10:30:00.403] [DEBUG] [CycleOrchestrator] N1 status: ACTIVE (no TP)
[10:30:00.404] [DEBUG] [CycleOrchestrator] N2 status: PENDING
[10:30:00.405] [INFO] [CycleOrchestrator] N2 waiting to activate @ 1.10180
```

**Checks:**
- [ ] `parent_cycle.metadata['recovery_cascade']` existe
- [ ] Cascade data: `{'from': 'N1', 'to': 'N2', 'reason': 'distance_threshold'}`
- [ ] `parent_cycle.metadata['recovery_levels_active'] == 2`

---

### PASO 9: Precio Activa N2 BUY
**Trigger:** Precio continúa subiendo hasta 1.10180
```
[10:35:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10180, ask=1.10200
[10:35:00.001] [INFO] [BrokerAdapter] Order filled: ticket=50003
[10:35:00.002] [INFO] [CycleOrchestrator] Recovery N2 BUY activated
[10:35:00.003] [DEBUG] [CycleOrchestrator] OP_REC_N2_BUY_001: PENDING → ACTIVE
[10:35:00.004] [INFO] [CycleOrchestrator] === MULTI-LEVEL RECOVERY ACTIVE ===
[10:35:00.005] [DEBUG] [CycleOrchestrator] N1 BUY: ACTIVE @ 1.10140
[10:35:00.006] [DEBUG] [CycleOrchestrator] N2 BUY: ACTIVE @ 1.10180
[10:35:00.007] [WARN] [CycleOrchestrator] 2 recovery levels active simultaneously
Checks:

 rec_n2_buy.status == ACTIVE
 rec_n1_buy.status == ACTIVE (ambos activos)
 rec_n2_buy.actual_entry_price == 1.10180
 Total recoveries activos: 2


ESTADO FINAL ESPERADO
yamlparent_cycle:
  id: CYC_PARENT_001
  status: IN_RECOVERY
  recovery_level: 2  # N1 + N2 activos
  pips_locked: 20.0  # Sin cambios (deuda original)
  
  accounting:
    pips_locked: 20.0
    pips_recovered: 0.0  # Aún no hay TPs de recovery
    recovery_queue:
      - "OP_MAIN_SELL_001_debt_unit"  # 20 pips
      - "REC_N1_001_debt_unit"         # 40 pips
    total_debt_cost: 60.0  # 20 + 40
    
  metadata:
    recovery_cascade:
      from: "N1"
      to: "N2"
      reason: "distance_threshold"
      timestamp: "2025-01-05 10:30:00"
    recovery_levels_active: 2
    
operations:
  # === MAIN + HEDGE (Neutralizadas, en queue) ===
  - id: OP_MAIN_SELL_001
    type: MAIN_SELL
    status: NEUTRALIZED
    entry_price: 1.09980
    
  - id: OP_HEDGE_BUY_001
    type: HEDGE_BUY
    status: ACTIVE
    entry_price: 1.10020
    covering_operation: "OP_MAIN_SELL_001"
    
  # === RECOVERY N1 (Activo, no TP) ===
  - id: OP_REC_N1_BUY_001
    type: RECOVERY_BUY
    status: ACTIVE
    recovery_level: 1
    entry_price: 1.10140
    tp_price: 1.10220
    actual_entry_price: 1.10140
    current_floating_pips: +40  # @ 1.10180
    metadata:
      failed_to_reach_tp: true
      triggered_next_level: true
      
  - id: OP_REC_N1_SELL_001
    type: RECOVERY_SELL
    status: PENDING
    recovery_level: 1
    entry_price: 1.10100
    tp_price: 1.10020
    
  # === RECOVERY N2 (Activo) ===
  - id: OP_REC_N2_BUY_001
    type: RECOVERY_BUY
    status: ACTIVE
    recovery_level: 2
    entry_price: 1.10180
    tp_price: 1.10260
    actual_entry_price: 1.10180
    current_floating_pips: 0  # Justo activado
    metadata:
      triggered_by: "distance_from_N1"
      distance_threshold: 40.0
      
  - id: OP_REC_N2_SELL_001
    type: RECOVERY_SELL
    status: PENDING
    recovery_level: 2
    entry_price: 1.10100
    tp_price: 1.10020
    
account:
  balance: 10000.0  # Sin cambios (no TPs aún)
  equity: 10000.0 - floating_losses
  margin_used: increased (más operaciones activas)

CHECKS CRÍTICOS
Recovery N1 No Alcanza TP

 rec_n1_buy.status == ACTIVE (no TP_HIT)
 rec_n1_buy.current_floating_pips > 0 (pero insuficiente)
 Precio no alcanzó 1.10220
 rec_n1_buy.metadata['failed_to_reach_tp'] == True

Distancia de 40 Pips

 Distancia desde N1 entry (1.10140) al precio actual (1.10180) = 40 pips
 Threshold alcanzado para activar N2
 strategy_signal.signal_type == OPEN_RECOVERY

Recovery N2 Creado

 rec_n2_buy.entry_price == 1.10180 (N1 + 40 pips)
 rec_n2_buy.recovery_level == 2
 rec_n2_buy.metadata['triggered_by'] == "distance_from_N1"

Recovery Level Incrementado

 parent_cycle.recovery_level == 2 (fue 1)
 Incremento registrado correctamente
 Metadata incluye cascada

Recovery Queue Actualizada

 len(recovery_queue) == 2
 Queue [0]: Main+Hedge (20 pips)
 Queue [1]: N1 debt unit (40 pips)
 Total debt: 60 pips
 N2 TP (80 pips) > Total debt (60 pips) ✓

Múltiples Recoveries Activos

 N1 BUY: ACTIVE
 N2 BUY: ACTIVE
 Ambos coexistiendo simultáneamente
 Sin interferencia entre niveles

Metadata de Cascada

 parent_cycle.metadata['recovery_cascade'] existe
 Incluye: from, to, reason, timestamp
 recovery_levels_active == 2


ESCENARIO 8: Ciclo Completa 10 TPs Sin Hedge
Referencia Documento Madre

Líneas 45-52: Operación Main con TP 10 pips
Línea 115: "Cuando un ciclo principal toca TP, inmediatamente se abre otro nuevo"
Sección "Resolución Simple" - operación continua

Condiciones Iniciales
yamlaccount:
  balance: 10000.0
  equity: 10000.0
  
market:
  pair: EURUSD
  start_price: 1.10000
  
cycle:
  id: CYC_MARATHON_001
  status: PENDING
  total_tps: 0
  pips_won: 0
```

## Secuencia de Pasos

### PASO 1: Ciclo Inicial - Primera Iteración
**Trigger:** Apertura de ciclo
```
[09:00:00.000] [INFO] [CycleOrchestrator] Opening new cycle: CYC_MARATHON_001
[09:00:00.001] [INFO] [BrokerAdapter] BUY_STOP placed: entry=1.10020, tp=1.10120
[09:00:00.002] [INFO] [BrokerAdapter] SELL_STOP placed: entry=1.09980, tp=1.09880
[09:00:00.003] [INFO] [CycleOrchestrator] Waiting for price movement
```

**Checks:**
- [ ] Ciclo creado: `status == PENDING`
- [ ] 2 operaciones pendientes (BUY + SELL)
- [ ] `total_tps == 0`

---

### PASO 2-11: Iteraciones 1-10 (TP alternados)
**Trigger:** Precio oscila activando alternadamente BUY y SELL

**Patrón repetitivo (10 veces):**

#### **Iteración 1: BUY TP**
```
[09:05:00.000] [INFO] [PriceMonitor] Tick: 1.10020 → BUY activates
[09:10:00.000] [INFO] [PriceMonitor] Tick: 1.10120 → BUY TP hit
[09:10:00.001] [INFO] [CycleOrchestrator] TP #1: +10 pips
[09:10:00.002] [INFO] [AccountingService] Balance: 10000.00 → 9987.00 (net after commissions)
[09:10:00.003] [INFO] [CycleOrchestrator] *** RENOVANDO MAIN (BUY + SELL) ***
[09:10:00.100] [INFO] [BrokerAdapter] New BUY: entry=1.10140, tp=1.10240
[09:10:00.101] [INFO] [BrokerAdapter] New SELL: entry=1.10120, tp=1.10020
```

**Checks Iteración 1:**
- [ ] `cycle.accounting.total_main_tps == 1`
- [ ] `cycle.accounting.total_pips_won == 10.0`
- [ ] Balance ajustado: -13 EUR (profit - commissions)
- [ ] 2 nuevas operaciones creadas

#### **Iteración 2: SELL TP**
```
[09:15:00.000] [INFO] [PriceMonitor] Tick: 1.10120 → SELL activates
[09:20:00.000] [INFO] [PriceMonitor] Tick: 1.10020 → SELL TP hit
[09:20:00.001] [INFO] [CycleOrchestrator] TP #2: +10 pips
[09:20:00.002] [INFO] [AccountingService] Balance: 9987.00 → 9974.00
[09:20:00.003] [INFO] [CycleOrchestrator] *** RENOVANDO MAIN (BUY + SELL) ***
```

**Checks Iteración 2:**
- [ ] `cycle.accounting.total_main_tps == 2`
- [ ] `cycle.accounting.total_pips_won == 20.0`
- [ ] Balance: 9974.00

#### **Iteración 3: BUY TP**
```
[09:25:00.000] [INFO] [PriceMonitor] Tick: 1.10040 → BUY activates
[09:30:00.000] [INFO] [PriceMonitor] Tick: 1.10140 → BUY TP hit
[09:30:00.001] [INFO] [CycleOrchestrator] TP #3: +10 pips
```

**Checks Iteración 3:**
- [ ] `total_main_tps == 3`
- [ ] `total_pips_won == 30.0`

#### **Iteración 4: SELL TP**
```
[09:35:00.000] [INFO] [PriceMonitor] Tick: 1.10140 → SELL activates
[09:40:00.000] [INFO] [PriceMonitor] Tick: 1.10040 → SELL TP hit
[09:40:00.001] [INFO] [CycleOrchestrator] TP #4: +10 pips
```

**Checks Iteración 4:**
- [ ] `total_main_tps == 4`
- [ ] `total_pips_won == 40.0`

#### **Iteración 5: BUY TP**
```
[09:45:00.000] [INFO] [CycleOrchestrator] TP #5: +10 pips
```

**Checks Iteración 5:**
- [ ] `total_main_tps == 5`
- [ ] `total_pips_won == 50.0`
- [ ] Balance aprox: 9935.00

#### **Iteración 6: SELL TP**
```
[09:50:00.000] [INFO] [CycleOrchestrator] TP #6: +10 pips
```

**Checks Iteración 6:**
- [ ] `total_main_tps == 6`
- [ ] `total_pips_won == 60.0`

#### **Iteración 7: BUY TP**
```
[09:55:00.000] [INFO] [CycleOrchestrator] TP #7: +10 pips
```

**Checks Iteración 7:**
- [ ] `total_main_tps == 7`
- [ ] `total_pips_won == 70.0`

#### **Iteración 8: SELL TP**
```
[10:00:00.000] [INFO] [CycleOrchestrator] TP #8: +10 pips
```

**Checks Iteración 8:**
- [ ] `total_main_tps == 8`
- [ ] `total_pips_won == 80.0`

#### **Iteración 9: BUY TP**
```
[10:05:00.000] [INFO] [CycleOrchestrator] TP #9: +10 pips
```

**Checks Iteración 9:**
- [ ] `total_main_tps == 9`
- [ ] `total_pips_won == 90.0`

#### **Iteración 10: SELL TP (Final)**
```
[10:10:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10020, ask=1.10040
[10:10:00.001] [INFO] [BrokerAdapter] TP alcanzado: ticket=marathon_20
[10:10:00.002] [INFO] [CycleOrchestrator] *** TP #10 ALCANZADO ***
[10:10:00.003] [INFO] [CycleOrchestrator] === MILESTONE: 10 TPs COMPLETADOS ===
[10:10:00.004] [DEBUG] [AccountingService] Total TPs: 10
[10:10:00.005] [DEBUG] [AccountingService] Total pips won: 100.0
[10:10:00.006] [DEBUG] [AccountingService] Gross profit: €10.00 (10 TPs × €1.00)
[10:10:00.007] [DEBUG] [AccountingService] Total commissions: €140.00 (10 TPs × €14.00)
[10:10:00.008] [INFO] [AccountingService] Net P&L: -€130.00
[10:10:00.009] [INFO] [AccountingService] Final balance: €9,870.00
Checks Iteración 10:

 cycle.accounting.total_main_tps == 10
 cycle.accounting.total_pips_won == 100.0
 Balance final: 9870.00 (10000 - 130)


PASO 12: Validación de Consistencia
Trigger: Verificación post-milestone
[10:10:00.100] [INFO] [CycleOrchestrator] Running consistency checks
[10:10:00.101] [DEBUG] [CycleOrchestrator] === CYCLE HEALTH CHECK ===
[10:10:00.102] [DEBUG] [CycleOrContinuar en uno nuevo, yo los uno7 ene2 / 2ESCENARIOS DETALLADOS - PARTE 3 (E8 continuación + E9-E10)

ESCENARIO 8: Ciclo Completa 10 TPs Sin Hedge (continuación)
PASO 12: Validación de Consistencia (continuación)
Trigger: Verificación post-milestone
[10:10:00.100] [INFO] [CycleOrchestrator] Running consistency checks
[10:10:00.101] [DEBUG] [CycleOrchestrator] === CYCLE HEALTH CHECK ===
[10:10:00.102] [DEBUG] [CycleOrchestrator] Total iterations: 10
[10:10:00.103] [DEBUG] [CycleOrchestrator] Status: ACTIVE (never entered HEDGED)
[10:10:00.104] [DEBUG] [CycleOrchestrator] Recovery level: 0 (never needed recovery)
[10:10:00.105] [DEBUG] [CycleOrchestrator] Neutralized operations: 0
[10:10:00.106] [DEBUG] [CycleOrchestrator] Pips locked: 0.0
[10:10:00.107] [INFO] [CycleOrchestrator] ✓ Clean cycle: no hedge, no recovery
[10:10:00.108] [INFO] [CycleOrchestrator] ✓ All TPs achieved successfully
[10:10:00.109] [INFO] [CycleOrchestrator] ✓ Renovations: 10 (dual operations each time)
Checks:

 cycle.status == ACTIVE (nunca cambió a HEDGED)
 cycle.recovery_level == 0
 cycle.accounting.pips_locked == 0.0
 len(cycle.neutralized_operations) == 0
 Total operaciones creadas: 22 (2 iniciales + 20 renovadas)


PASO 13: Contabilidad Detallada
Trigger: Análisis financiero completo
[10:10:00.200] [INFO] [AccountingService] === DETAILED ACCOUNTING ===
[10:10:00.201] [DEBUG] [AccountingService] 
[10:10:00.202] [DEBUG] [AccountingService] === PER-TP BREAKDOWN ===
[10:10:00.203] [DEBUG] [AccountingService] TP #1  (BUY):  +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.204] [DEBUG] [AccountingService] TP #2  (SELL): +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.205] [DEBUG] [AccountingService] TP #3  (BUY):  +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.206] [DEBUG] [AccountingService] TP #4  (SELL): +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.207] [DEBUG] [AccountingService] TP #5  (BUY):  +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.208] [DEBUG] [AccountingService] TP #6  (SELL): +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.209] [DEBUG] [AccountingService] TP #7  (BUY):  +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.210] [DEBUG] [AccountingService] TP #8  (SELL): +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.211] [DEBUG] [AccountingService] TP #9  (BUY):  +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.212] [DEBUG] [AccountingService] TP #10 (SELL): +10 pips, +€1.00, -€14.00 comm = -€13.00
[10:10:00.213] [DEBUG] [AccountingService] 
[10:10:00.214] [INFO] [AccountingService] === TOTALS ===
[10:10:00.215] [INFO] [AccountingService] Gross pips:        +100.0
[10:10:00.216] [INFO] [AccountingService] Gross profit:      +€10.00
[10:10:00.217] [INFO] [AccountingService] Total commissions: -€140.00
[10:10:00.218] [INFO] [AccountingService] Net P&L:          -€130.00
[10:10:00.219] [INFO] [AccountingService] Balance change:    €10,000 → €9,870
[10:10:00.220] [INFO] [AccountingService] ROI:               -1.30%
Checks:

 Cada TP: +10 pips, -13 EUR net
 Gross profit total: 10.00 EUR
 Commissions total: 140.00 EUR (10 × 14)
 Net P&L: -130.00 EUR
 Balance final: 9870.00 EUR


PASO 14: Renovaciones Dual - Validación
Trigger: Verificar FIX-001 en todas las iteraciones
[10:10:00.300] [INFO] [CycleOrchestrator] Validating FIX-001 compliance (dual renewals)
[10:10:00.301] [DEBUG] [CycleOrchestrator] === RENEWAL HISTORY ===
[10:10:00.302] [DEBUG] [CycleOrchestrator] Iteration 1:  TP → Created BUY + SELL ✓
[10:10:00.303] [DEBUG] [CycleOrchestrator] Iteration 2:  TP → Created BUY + SELL ✓
[10:10:00.304] [DEBUG] [CycleOrchestrator] Iteration 3:  TP → Created BUY + SELL ✓
[10:10:00.305] [DEBUG] [CycleOrchestrator] Iteration 4:  TP → Created BUY + SELL ✓
[10:10:00.306] [DEBUG] [CycleOrchestrator] Iteration 5:  TP → Created BUY + SELL ✓
[10:10:00.307] [DEBUG] [CycleOrchestrator] Iteration 6:  TP → Created BUY + SELL ✓
[10:10:00.308] [DEBUG] [CycleOrchestrator] Iteration 7:  TP → Created BUY + SELL ✓
[10:10:00.309] [DEBUG] [CycleOrchestrator] Iteration 8:  TP → Created BUY + SELL ✓
[10:10:00.310] [DEBUG] [CycleOrchestrator] Iteration 9:  TP → Created BUY + SELL ✓
[10:10:00.311] [DEBUG] [CycleOrchestrator] Iteration 10: TP → Created BUY + SELL ✓
[10:10:00.312] [INFO] [CycleOrchestrator] ✓ FIX-001 applied correctly in all 10 iterations
[10:10:00.313] [INFO] [CycleOrchestrator] ✓ Dual renewal: 100% compliance
Checks:

 Cada TP generó exactamente 2 nuevas operaciones (BUY + SELL)
 Nunca se creó solo 1 operación
 FIX-001 compliance: 100% (10/10)


ESTADO FINAL ESPERADO
yamlcycle:
  id: CYC_MARATHON_001
  status: ACTIVE  # Sigue operando después de 10 TPs
  total_tps: 10
  pips_won: 100.0
  
  accounting:
    total_main_tps: 10
    total_recovery_tps: 0
    total_pips_won: 100.0
    pips_locked: 0.0
    pips_recovered: 0.0
    total_commissions: €140.00
    net_profit: -€130.00
    
  operations_history:
    # Total: 22 operaciones (2 iniciales + 20 renovadas)
    # 12 cerradas con TP (10 TPs + 2 canceladas por contrapartida)
    # 10 canceladas (contrapartes de TPs)
    # 2 pendientes actuales (última renovación)
    
operations_current:
  - id: OP_BUY_011
    type: MAIN_BUY
    status: PENDING
    entry_price: 1.10040  # Última renovación
    tp_price: 1.10140
    
  - id: OP_SELL_011
    type: MAIN_SELL
    status: PENDING
    entry_price: 1.10020  # Última renovación
    tp_price: 1.09920
    
account:
  balance: 9870.00  # 10000 - 130
  equity: 9870.00
  margin_free: 9870.00  # Sin posiciones abiertas
  
metadata:
  milestone_10_tps:
    achieved_at: "2025-01-05 10:10:00"
    total_duration: "70 minutes"
    average_tp_interval: "7 minutes"
    never_hedged: true
    never_recovery: true
    clean_cycle: true
    fix_001_compliance: "100%"
    
statistics:
  total_iterations: 10
  buy_tps: 5
  sell_tps: 5
  alternating_pattern: true
  max_floating_loss: 0.0  # Nunca en pérdida
  total_operations_created: 22
  operations_closed_tp: 10
  operations_cancelled: 10
  operations_pending: 2

CHECKS CRÍTICOS
10 TPs Completados

 cycle.accounting.total_main_tps == 10
 cycle.accounting.total_pips_won == 100.0
 Todos alcanzados exitosamente

Sin Estado HEDGED

 cycle.status == ACTIVE en todo momento
 Nunca transitó a HEDGED
 cycle.metadata['never_hedged'] == True

Sin Recoveries

 cycle.recovery_level == 0
 cycle.accounting.pips_locked == 0.0
 len(cycle.recovery_operations) == 0

Renovaciones Dual (FIX-001)

 Cada TP generó 2 nuevas operaciones (BUY + SELL)
 Total operaciones: 22 (2 inicial + 10 TPs × 2)
 FIX-001 compliance: 100%

Contabilidad Consistente

 Gross profit: 10.00 EUR (10 × 1.00)
 Commissions: 140.00 EUR (10 × 14.00)
 Net P&L: -130.00 EUR
 Balance: 9870.00 EUR

Alternancia BUY/SELL

 5 TPs BUY
 5 TPs SELL
 Patrón alternado consistente

Operaciones Finales

 2 operaciones pendientes (última renovación)
 Ambas desde precio actual
 Listas para siguiente iteración


ESCENARIO 9: USDJPY - Par JPY Flujo Completo
Referencia Documento Madre

Líneas 265-280: Pares JPY con 2 decimales
Nota: Multiplicador ×100 (no ×10000)
Toda la mecánica core aplicada a par JPY

Condiciones Iniciales
yamlaccount:
  balance: 10000.0
  equity: 10000.0
  
market:
  pair: USDJPY
  start_price: 110.00  # 2 decimales
  
cycle:
  id: CYC_JPY_001
  status: PENDING
  
notes:
  - "JPY usa 2 decimales (110.00 no 1.10000)"
  - "Multiplicador pips: ×100 (no ×10000)"
  - "1 pip = 0.01 (no 0.0001)"
  - "TP de 10 pips = 0.10 en precio (no 0.0010)"
```

## Secuencia de Pasos

### PASO 1: Apertura de Ciclo USDJPY
**Trigger:** Nuevo ciclo con par JPY
```
[09:00:00.000] [INFO] [CycleOrchestrator] Opening new cycle: CYC_JPY_001
[09:00:00.001] [DEBUG] [CycleOrchestrator] Pair: USDJPY (JPY pair detected)
[09:00:00.002] [DEBUG] [CycleOrchestrator] Price precision: 2 decimals
[09:00:00.003] [DEBUG] [CycleOrchestrator] Pip multiplier: 100
[09:00:00.004] [INFO] [CycleOrchestrator] === JPY PAIR CONFIGURATION ===
[09:00:00.005] [DEBUG] [CycleOrchestrator] Current price: 110.00
[09:00:00.006] [DEBUG] [CycleOrchestrator] TP distance: 10 pips = 0.10 price units
[09:00:00.007] [DEBUG] [CycleOrchestrator] BUY entry: 110.05 (5 pips above)
[09:00:00.008] [DEBUG] [CycleOrchestrator] BUY TP: 110.15 (110.05 + 0.10)
[09:00:00.009] [DEBUG] [CycleOrchestrator] SELL entry: 109.95 (5 pips below)
[09:00:00.010] [DEBUG] [CycleOrchestrator] SELL TP: 109.85 (109.95 - 0.10)
[09:00:00.011] [INFO] [BrokerAdapter] Placing BUY_STOP: entry=110.05, tp=110.15
[09:00:00.012] [INFO] [BrokerAdapter] Placing SELL_STOP: entry=109.95, tp=109.85
```

**Checks:**
- [ ] Precios con 2 decimales (110.05 no 1.10050)
- [ ] TP distance: 0.10 (10 pips para JPY)
- [ ] Multiplicador detectado: ×100
- [ ] `cycle.pair == "USDJPY"`

---

### PASO 2: BUY Activa (JPY)
**Trigger:** Precio alcanza 110.05
```
[09:05:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=110.05, ask=110.07
[09:05:00.001] [INFO] [BrokerAdapter] Order filled: ticket=60001
[09:05:00.002] [INFO] [CycleOrchestrator] OP_JPY_BUY_001 activated
[09:05:00.003] [DEBUG] [CycleOrchestrator] Entry: 110.05 (2 decimals)
[09:05:00.004] [DEBUG] [CycleOrchestrator] TP: 110.15 (+0.10 = +10 pips JPY)
[09:05:00.005] [DEBUG] [PipsCalculator] Using JPY multiplier: ×100
[09:05:00.006] [DEBUG] [PipsCalculator] Entry to TP distance: 0.10 × 100 = 10 pips ✓
```

**Checks:**
- [ ] `op_buy.status == ACTIVE`
- [ ] `op_buy.entry_price == 110.05`
- [ ] `op_buy.tp_price == 110.15`
- [ ] Diferencia: 0.10 (10 pips en JPY)

---

### PASO 3: Precio Sube → Ambas Activan → HEDGED (JPY)
**Trigger:** Precio baja activando SELL
```
[09:10:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=109.95, ask=109.97
[09:10:00.001] [INFO] [BrokerAdapter] Order filled: ticket=60002
[09:10:00.002] [INFO] [CycleOrchestrator] OP_JPY_SELL_001 activated
[09:10:00.003] [CRITICAL] [CycleOrchestrator] *** BOTH MAINS ACTIVE (JPY) → HEDGE ***
[09:10:00.004] [DEBUG] [CycleOrchestrator] BUY @ 110.05, SELL @ 109.95
[09:10:00.005] [DEBUG] [CycleOrchestrator] Separation: 0.10 × 100 = 10 pips ✓
[09:10:00.006] [INFO] [CycleOrchestrator] Transitioning: ACTIVE → HEDGED
```

**Checks:**
- [ ] `op_sell.status == ACTIVE`
- [ ] `cycle.status == HEDGED`
- [ ] Separación: 10 pips (calculado con ×100)

---

### PASO 4: Calcular Pips Locked (JPY)
**Trigger:** Contabilidad de deuda en JPY
```
[09:10:00.100] [INFO] [AccountingService] Calculating pips_locked (JPY pair)
[09:10:00.101] [DEBUG] [AccountingService] === DEBT COMPOSITION (JPY) ===
[09:10:00.102] [DEBUG] [AccountingService] Main BUY: entry=110.05
[09:10:00.103] [DEBUG] [AccountingService] Main SELL: entry=109.95
[09:10:00.104] [DEBUG] [AccountingService] Separation: 0.10 price units
[09:10:00.105] [DEBUG] [AccountingService] Separation in pips: 0.10 × 100 = 10 pips ✓
[09:10:00.106] [DEBUG] [AccountingService] TP distance: 0.10 × 100 = 10 pips ✓
[09:10:00.107] [DEBUG] [AccountingService] Margin: 6 pips (standard)
[09:10:00.108] [DEBUG] [AccountingService] WRONG calculation: 0.10 × 10000 = 1000 pips ✗
[09:10:00.109] [DEBUG] [AccountingService] CORRECT calculation: 0.10 × 100 = 10 pips ✓
[09:10:00.110] [INFO] [AccountingService] Total pips_locked: 4 + 10 + 6 = 20 pips
[09:10:00.111] [INFO] [AccountingService] ✓ JPY multiplier applied correctly
```

**Checks:**
- [ ] `cycle.accounting.pips_locked == 20.0`
- [ ] Separación calculada: (110.05 - 109.95) × 100 = 10 pips
- [ ] TP distance: 0.10 × 100 = 10 pips
- [ ] NO usar ×10000 (daría 1000 pips incorrecto)

---

### PASO 5: BUY Main Alcanza TP (JPY)
**Trigger:** Precio sube a 110.15
```
[09:15:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=110.15, ask=110.17
[09:15:00.001] [INFO] [BrokerAdapter] TP alcanzado: ticket=60001
[09:15:00.002] [INFO] [CycleOrchestrator] OP_JPY_BUY_001: TP_HIT
[09:15:00.003] [DEBUG] [PnLCalculator] === PROFIT CALCULATION (JPY) ===
[09:15:00.004] [DEBUG] [PnLCalculator] Entry: 110.05
[09:15:00.005] [DEBUG] [PnLCalculator] Close: 110.15
[09:15:00.006] [DEBUG] [PnLCalculator] Difference: 0.10
[09:15:00.007] [DEBUG] [PnLCalculator] CORRECT: 0.10 × 100 = 10 pips ✓
[09:15:00.008] [DEBUG] [PnLCalculator] WRONG: 0.10 × 10000 = 1000 pips ✗
[09:15:00.009] [INFO] [PnLCalculator] Profit: 10.0 pips
```

**Checks:**
- [ ] `op_buy.status == TP_HIT`
- [ ] `op_buy.profit_pips == 10.0` (no 1000)
- [ ] Cálculo: (110.15 - 110.05) × 100 = 10 pips
- [ ] Multiplicador correcto aplicado

---

### PASO 6: Crear Recoveries (JPY)
**Trigger:** Ciclo entra en recovery
```
[09:15:00.100] [INFO] [CycleOrchestrator] Opening recovery cycle (JPY)
[09:15:00.101] [DEBUG] [CycleOrchestrator] Reference price (main TP): 110.15
[09:15:00.102] [DEBUG] [CycleOrchestrator] Recovery distance: 20 pips JPY = 0.20
[09:15:00.103] [DEBUG] [CycleOrchestrator] === RECOVERY PLACEMENT (JPY) ===
[09:15:00.104] [DEBUG] [CycleOrchestrator] Recovery BUY: 110.15 + 0.20 = 110.35
[09:15:00.105] [DEBUG] [CycleOrchestrator] Recovery SELL: 110.15 - 0.20 = 109.95
[09:15:00.106] [DEBUG] [CycleOrchestrator] Recovery BUY TP: 110.35 + 0.80 = 111.15
[09:15:00.107] [DEBUG] [CycleOrchestrator] Recovery SELL TP: 109.95 - 0.80 = 109.15
[09:15:00.108] [INFO] [BrokerAdapter] RECOVERY_BUY: entry=110.35, tp=111.15
[09:15:00.109] [INFO] [BrokerAdapter] RECOVERY_SELL: entry=109.95, tp=109.15
```

**Checks:**
- [ ] Recovery distance: 0.20 (20 pips en JPY)
- [ ] Recovery TP distance: 0.80 (80 pips en JPY)
- [ ] `rec_buy.entry_price == 110.35`
- [ ] `rec_buy.tp_price == 111.15` (diferencia 0.80)

---

### PASO 7: Recovery BUY Activa y Alcanza TP (JPY)
**Trigger:** Precio sube a 111.15
```
[09:25:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=110.35 → Recovery activates
[09:30:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=111.15 → Recovery TP
[09:30:00.001] [INFO] [CycleOrchestrator] Recovery N1 BUY: TP_HIT
[09:30:00.002] [DEBUG] [PnLCalculator] === RECOVERY PROFIT (JPY) ===
[09:30:00.003] [DEBUG] [PnLCalculator] Entry: 110.35
[09:30:00.004] [DEBUG] [PnLCalculator] Close: 111.15
[09:30:00.005] [DEBUG] [PnLCalculator] Difference: 0.80
[09:30:00.006] [DEBUG] [PnLCalculator] Pips: 0.80 × 100 = 80 pips ✓
[09:30:00.007] [INFO] [PnLCalculator] Recovery profit: 80.0 pips
```

**Checks:**
- [ ] `rec_buy.status == TP_HIT`
- [ ] `rec_buy.profit_pips == 80.0`
- [ ] Cálculo: (111.15 - 110.35) × 100 = 80 pips
- [ ] Multiplicador JPY consistente

---

### PASO 8: FIFO Execution (JPY)
**Trigger:** Recovery TP activa FIFO
```
[09:30:00.100] [INFO] [FIFOProcessor] Processing FIFO (JPY pair)
[09:30:00.101] [DEBUG] [FIFOProcessor] Recovery profit available: 80 pips
[09:30:00.102] [DEBUG] [FIFOProcessor] === FIFO QUEUE (JPY) ===
[09:30:00.103] [DEBUG] [FIFOProcessor] [0] Main SELL + Hedge BUY: 20 pips
[09:30:00.104] [DEBUG] [FIFOProcessor] FIFO: 80 - 20 = 60 pips net profit
[09:30:00.105] [INFO] [FIFOProcessor] ╔═══════════════════════════════════════╗
[09:30:00.106] [INFO] [FIFOProcessor] ║ CLOSING DEBT UNIT (JPY) - ATOMIC    ║
[09:30:00.107] [INFO] [FIFOProcessor] ╚═══════════════════════════════════════╝
[09:30:00.108] [INFO] [BrokerAdapter] Closing Main SELL (USDJPY): ticket=60002
[09:30:00.109] [INFO] [BrokerAdapter] Closing Hedge BUY (USDJPY): ticket=60003
[09:30:00.110] [INFO] [FIFOProcessor] ✓ Debt unit closed (JPY pair)
[09:30:00.111] [INFO] [AccountingService] pips_locked: 20 → 0
[09:30:00.112] [INFO] [AccountingService] pips_recovered: 0 → 20
[09:30:00.113] [INFO] [AccountingService] Net profit: 60 pips
Checks:

 FIFO ejecutado con costos JPY correctos
 parent_cycle.accounting.pips_recovered == 20.0
 parent_cycle.accounting.pips_locked == 0.0
 Net profit: 60 pips (80 - 20)


ESTADO FINAL ESPERADO
yamlcycle:
  id: CYC_JPY_001
  pair: USDJPY
  status: ACTIVE  # Fully recovered
  
  accounting:
    pips_locked: 0.0
    pips_recovered: 20.0
    total_main_tps: 1
    total_recovery_tps: 1
    is_fully_recovered: true
    
operations:
  # === MAIN OPERATIONS (Cerradas) ===
  - id: OP_JPY_BUY_001
    type: MAIN_BUY
    status: TP_HIT
    entry_price: 110.05  # 2 decimales
    tp_price: 110.15
    profit_pips: 10.0  # Calculado con ×100
    
  - id: OP_JPY_SELL_001
    type: MAIN_SELL
    status: CLOSED  # Por FIFO
    entry_price: 109.95
    neutralized_by: "OP_JPY_HEDGE_BUY_001"
    
  # === HEDGE (Cerrado por FIFO) ===
  - id: OP_JPY_HEDGE_BUY_001
    type: HEDGE_BUY
    status: CLOSED
    entry_price: 110.05
    close_reason: "fifo_recovery_tp"
    
  # === RECOVERY (TP Hit) ===
  - id: OP_JPY_REC_BUY_001
    type: RECOVERY_BUY
    status: TP_HIT
    entry_price: 110.35
    tp_price: 111.15
    profit_pips: 80.0  # Calculado con ×100
    
  # === NUEVA ITERACIÓN ===
  - id: OP_JPY_BUY_002
    type: MAIN_BUY
    status: PENDING
    entry_price: 111.17  # Desde precio actual
    tp_price: 111.27  # +0.10 (10 pips JPY)
    
  - id: OP_JPY_SELL_002
    type: MAIN_SELL
    status: PENDING
    entry_price: 111.15
    tp_price: 111.05  # -0.10 (10 pips JPY)
    
metadata:
  jpy_pair_config:
    decimals: 2
    pip_multiplier: 100
    pip_value_price: 0.01
    tp_distance_price: 0.10
    recovery_distance_price: 0.20
    recovery_tp_distance_price: 0.80

CHECKS CRÍTICOS
Multiplicador JPY

 Todos los cálculos usan ×100 (no ×10000)
 _pips_between(110.00, 110.10, "USDJPY") == 10.0
 _pips_between(110.00, 110.80, "USDJPY") == 80.0

Precisión de Precios

 Todos los precios: 2 decimales (110.05 no 1.10050)
 TP distance: 0.10 (10 pips)
 Recovery distance: 0.20 (20 pips)
 Recovery TP: 0.80 (80 pips)

Pips Locked (JPY)

 pips_locked == 20.0 (calculado correctamente con ×100)
 Separación: (110.05 - 109.95) × 100 = 10 pips
 NO 1000 pips (error común con
Continuar7 ene


FIFO con JPY

 Costo primer recovery: 20 pips (igual que EUR pares)
 Recovery TP: 80 pips (igual lógica)
 Cierre atómico Main+Hedge funciona con JPY

Renovaciones con JPY

 Nuevas operaciones desde precio actual JPY
 TP calculado: entry ± 0.10
 Dual renewal (BUY + SELL) aplicado

Consistencia de Multiplicador

 Detección automática: "JPY" in pair → ×100
 Aplicado en: pips_between, TP calc, profit calc, FIFO
 Nunca mezcla ×100 y ×10000


Continuaré con E10 en el siguiente mensaje...si7 eneESCENARIO 10: Múltiples Pares Simultáneos + Exposición Total
Referencia Documento Madre

Líneas 285-295: Trading multi-par
Líneas 342-355: Cálculo de exposición agregada
Sección "Gestión de múltiples pares independientes"

Condiciones Iniciales
yamlaccount:
  balance: 10000.0
  equity: 10000.0
  margin_free: 10000.0
  leverage: 100
  
market:
  pairs:
    - pair: EURUSD
      price: 1.10000
    - pair: GBPUSD
      price: 1.25000
    - pair: USDJPY
      price: 110.00
      
system:
  active_cycles: 0
  total_exposure_pct: 0.0
```

## Secuencia de Pasos

### PASO 1: Apertura de Ciclo EURUSD
**Trigger:** Primer par activo
```
[09:00:00.000] [INFO] [CycleOrchestrator] Opening cycle for EURUSD
[09:00:00.001] [DEBUG] [CycleOrchestrator] Pair 1/3: EURUSD @ 1.10000
[09:00:00.002] [INFO] [RiskManager] Calculating lot size
[09:00:00.003] [DEBUG] [RiskManager] Balance: €10,000, Lot: 0.01
[09:00:00.004] [INFO] [BrokerAdapter] EURUSD BUY_STOP: entry=1.10020, lot=0.01
[09:00:00.005] [INFO] [BrokerAdapter] EURUSD SELL_STOP: entry=1.09980, lot=0.01
[09:00:00.100] [INFO] [BrokerAdapter] Orders confirmed: tickets 70001, 70002
[09:00:00.101] [INFO] [CycleOrchestrator] EURUSD cycle: CYC_EUR_001 created
```

**Checks:**
- [ ] `cycle_eur.pair == "EURUSD"`
- [ ] `cycle_eur.status == PENDING`
- [ ] 2 operaciones creadas (BUY + SELL)
- [ ] `len(active_cycles) == 1`

---

### PASO 2: Apertura de Ciclo GBPUSD
**Trigger:** Segundo par activo
```
[09:01:00.000] [INFO] [CycleOrchestrator] Opening cycle for GBPUSD
[09:01:00.001] [DEBUG] [CycleOrchestrator] Pair 2/3: GBPUSD @ 1.25000
[09:01:00.002] [INFO] [RiskManager] Calculating lot size
[09:01:00.003] [DEBUG] [RiskManager] Balance: €10,000, Lot: 0.01
[09:01:00.004] [INFO] [BrokerAdapter] GBPUSD BUY_STOP: entry=1.25020, lot=0.01
[09:01:00.005] [INFO] [BrokerAdapter] GBPUSD SELL_STOP: entry=1.24980, lot=0.01
[09:01:00.100] [INFO] [BrokerAdapter] Orders confirmed: tickets 70003, 70004
[09:01:00.101] [INFO] [CycleOrchestrator] GBPUSD cycle: CYC_GBP_001 created
[09:01:00.102] [DEBUG] [System] Active cycles: 2 (EURUSD, GBPUSD)
```

**Checks:**
- [ ] `cycle_gbp.pair == "GBPUSD"`
- [ ] `cycle_gbp.status == PENDING`
- [ ] `len(active_cycles) == 2`
- [ ] Ciclos independientes (IDs diferentes)

---

### PASO 3: Apertura de Ciclo USDJPY
**Trigger:** Tercer par activo
```
[09:02:00.000] [INFO] [CycleOrchestrator] Opening cycle for USDJPY
[09:02:00.001] [DEBUG] [CycleOrchestrator] Pair 3/3: USDJPY @ 110.00 (JPY pair)
[09:02:00.002] [INFO] [RiskManager] Calculating lot size
[09:02:00.003] [DEBUG] [RiskManager] Balance: €10,000, Lot: 0.01
[09:02:00.004] [INFO] [BrokerAdapter] USDJPY BUY_STOP: entry=110.05, lot=0.01
[09:02:00.005] [INFO] [BrokerAdapter] USDJPY SELL_STOP: entry=109.95, lot=0.01
[09:02:00.100] [INFO] [BrokerAdapter] Orders confirmed: tickets 70005, 70006
[09:02:00.101] [INFO] [CycleOrchestrator] USDJPY cycle: CYC_JPY_001 created
[09:02:00.102] [INFO] [System] === MULTI-PAIR SETUP COMPLETE ===
[09:02:00.103] [DEBUG] [System] Active cycles: 3 (EURUSD, GBPUSD, USDJPY)
[09:02:00.104] [DEBUG] [System] Total pending orders: 6 (2 per pair)
```

**Checks:**
- [ ] `cycle_jpy.pair == "USDJPY"`
- [ ] `cycle_jpy.status == PENDING`
- [ ] `len(active_cycles) == 3`
- [ ] Todos independientes

---

### PASO 4: Cálculo de Exposición Inicial
**Trigger:** Validación de riesgo multi-par
```
[09:02:00.200] [INFO] [RiskManager] Calculating total exposure (multi-pair)
[09:02:00.201] [DEBUG] [RiskManager] === EXPOSURE BREAKDOWN ===
[09:02:00.202] [DEBUG] [RiskManager] EURUSD: 2 ops × 0.01 lots = 0.02 total
[09:02:00.203] [DEBUG] [RiskManager]   → Margin: 0.02 × 100,000 / 100 = €20
[09:02:00.204] [DEBUG] [RiskManager] GBPUSD: 2 ops × 0.01 lots = 0.02 total
[09:02:00.205] [DEBUG] [RiskManager]   → Margin: 0.02 × 100,000 / 100 = €20
[09:02:00.206] [DEBUG] [RiskManager] USDJPY: 2 ops × 0.01 lots = 0.02 total
[09:02:00.207] [DEBUG] [RiskManager]   → Margin: 0.02 × 100,000 / 100 = €20
[09:02:00.208] [INFO] [RiskManager] === TOTALS ===
[09:02:00.209] [INFO] [RiskManager] Total lots: 0.06 (6 ops × 0.01)
[09:02:00.210] [INFO] [RiskManager] Total margin: €60
[09:02:00.211] [INFO] [RiskManager] Equity: €10,000
[09:02:00.212] [INFO] [RiskManager] Exposure: 0.6% (60 / 10,000)
[09:02:00.213] [INFO] [RiskManager] ✓ Well below 30% limit
```

**Checks:**
- [ ] Total lots: 0.06 (suma de 3 pares)
- [ ] Total margin: 60.00 EUR
- [ ] Exposure: 0.6%
- [ ] `exposure_pct < 30.0` (límite)

---

### PASO 5: EURUSD BUY Activa y Alcanza TP
**Trigger:** Primer TP en EURUSD
```
[09:05:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10020
[09:05:00.001] [INFO] [BrokerAdapter] EURUSD BUY activated: ticket=70001
[09:10:00.000] [INFO] [PriceMonitor] Tick: EURUSD bid=1.10120
[09:10:00.001] [INFO] [BrokerAdapter] EURUSD BUY TP hit: ticket=70001
[09:10:00.002] [INFO] [CycleOrchestrator] CYC_EUR_001: TP #1 (+10 pips)
[09:10:00.003] [INFO] [AccountingService] Balance: €10,000 → €9,987 (net)
[09:10:00.004] [INFO] [CycleOrchestrator] Renovating EURUSD operations
[09:10:00.005] [DEBUG] [System] Other pairs unaffected (GBPUSD, USDJPY)
```

**Checks:**
- [ ] `cycle_eur.accounting.total_main_tps == 1`
- [ ] `cycle_eur.accounting.total_pips_won == 10.0`
- [ ] Balance global actualizado
- [ ] GBPUSD y USDJPY: sin cambios

---

### PASO 6: GBPUSD SELL Activa y Alcanza TP
**Trigger:** Primer TP en GBPUSD (independiente)
```
[09:15:00.000] [INFO] [PriceMonitor] Tick: GBPUSD bid=1.24980
[09:15:00.001] [INFO] [BrokerAdapter] GBPUSD SELL activated: ticket=70004
[09:20:00.000] [INFO] [PriceMonitor] Tick: GBPUSD bid=1.24880
[09:20:00.001] [INFO] [BrokerAdapter] GBPUSD SELL TP hit: ticket=70004
[09:20:00.002] [INFO] [CycleOrchestrator] CYC_GBP_001: TP #1 (+10 pips)
[09:20:00.003] [INFO] [AccountingService] Balance: €9,987 → €9,974
[09:20:00.004] [DEBUG] [System] === MULTI-PAIR STATUS ===
[09:20:00.005] [DEBUG] [System] EURUSD: 1 TP ✓
[09:20:00.006] [DEBUG] [System] GBPUSD: 1 TP ✓
[09:20:00.007] [DEBUG] [System] USDJPY: 0 TPs (pending)
```

**Checks:**
- [ ] `cycle_gbp.accounting.total_main_tps == 1`
- [ ] `cycle_gbp.accounting.total_pips_won == 10.0`
- [ ] `cycle_eur` no afectado por TP de GBPUSD
- [ ] Balance global: 9974.00

---

### PASO 7: USDJPY Entra en HEDGED
**Trigger:** Ambas mains USDJPY activan
```
[09:25:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=110.05
[09:25:00.001] [INFO] [BrokerAdapter] USDJPY BUY activated: ticket=70005
[09:26:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=109.95
[09:26:00.001] [INFO] [BrokerAdapter] USDJPY SELL activated: ticket=70006
[09:26:00.002] [CRITICAL] [CycleOrchestrator] CYC_JPY_001: BOTH ACTIVE → HEDGED
[09:26:00.003] [INFO] [CycleOrchestrator] Creating USDJPY hedges
[09:26:00.004] [DEBUG] [System] === PAIR STATUS ===
[09:26:00.005] [DEBUG] [System] EURUSD: ACTIVE (clean, 1 TP)
[09:26:00.006] [DEBUG] [System] GBPUSD: ACTIVE (clean, 1 TP)
[09:26:00.007] [DEBUG] [System] USDJPY: HEDGED (pips_locked=20)
[09:26:00.008] [INFO] [System] ✓ Independent states per pair
```

**Checks:**
- [ ] `cycle_jpy.status == HEDGED`
- [ ] `cycle_jpy.accounting.pips_locked == 20.0`
- [ ] `cycle_eur.status == ACTIVE` (sin cambios)
- [ ] `cycle_gbp.status == ACTIVE` (sin cambios)
- [ ] Independencia total confirmada

---

### PASO 8: Recalcular Exposición Total
**Trigger:** Más operaciones activas (hedges)
```
[09:26:00.100] [INFO] [RiskManager] Recalculating total exposure
[09:26:00.101] [DEBUG] [RiskManager] === UPDATED EXPOSURE ===
[09:26:00.102] [DEBUG] [RiskManager] EURUSD: 2 ops (renewed) × 0.01 = 0.02 lots
[09:26:00.103] [DEBUG] [RiskManager] GBPUSD: 2 ops (renewed) × 0.01 = 0.02 lots
[09:26:00.104] [DEBUG] [RiskManager] USDJPY: 4 ops (2 main + 2 hedge) × 0.01 = 0.04 lots
[09:26:00.105] [INFO] [RiskManager] === TOTALS ===
[09:26:00.106] [INFO] [RiskManager] Total lots: 0.08
[09:26:00.107] [INFO] [RiskManager] Total margin: €80
[09:26:00.108] [INFO] [RiskManager] Equity: €9,974
[09:26:00.109] [INFO] [RiskManager] Exposure: 0.8% (80 / 9,974)
[09:26:00.110] [INFO] [RiskManager] ✓ Still well below 30% limit
```

**Checks:**
- [ ] Total lots: 0.08 (incrementó por hedges)
- [ ] Total margin: 80.00 EUR
- [ ] Exposure: 0.8%
- [ ] Incluye todas las operaciones de todos los pares

---

### PASO 9: USDJPY Abre Recovery
**Trigger:** Recovery para USDJPY
```
[09:30:00.000] [INFO] [CycleOrchestrator] Opening recovery for USDJPY
[09:30:00.001] [DEBUG] [CycleOrchestrator] Parent: CYC_JPY_001
[09:30:00.002] [INFO] [BrokerAdapter] USDJPY RECOVERY_BUY: entry=110.35
[09:30:00.003] [INFO] [BrokerAdapter] USDJPY RECOVERY_SELL: entry=109.95
[09:30:00.004] [INFO] [RiskManager] Recalculating exposure with recovery
[09:30:00.005] [DEBUG] [RiskManager] USDJPY now: 6 ops (2 main + 2 hedge + 2 rec)
[09:30:00.006] [DEBUG] [RiskManager] Total lots: 0.10
[09:30:00.007] [DEBUG] [RiskManager] Total margin: €100
[09:30:00.008] [INFO] [RiskManager] Exposure: 1.0%
[09:30:00.009] [DEBUG] [System] === MULTI-PAIR + RECOVERY ===
[09:30:00.010] [DEBUG] [System] EURUSD: ACTIVE (clean)
[09:30:00.011] [DEBUG] [System] GBPUSD: ACTIVE (clean)
[09:30:00.012] [DEBUG] [System] USDJPY: IN_RECOVERY (level 1)
```

**Checks:**
- [ ] Recovery creado solo para USDJPY
- [ ] EURUSD y GBPUSD no afectados
- [ ] Total lots: 0.10 (incluye recovery)
- [ ] Exposure: 1.0%

---

### PASO 10: Validación de Independencia
**Trigger:** Verificación de aislamiento
```
[09:35:00.000] [INFO] [System] Running multi-pair independence check
[09:35:00.001] [DEBUG] [System] === INDEPENDENCE VALIDATION ===
[09:35:00.002] [DEBUG] [System] EURUSD operations: 2 (own cycle only)
[09:35:00.003] [DEBUG] [System] GBPUSD operations: 2 (own cycle only)
[09:35:00.004] [DEBUG] [System] USDJPY operations: 6 (own cycle only)
[09:35:00.005] [INFO] [System] ✓ No cross-contamination
[09:35:00.006] [DEBUG] [System] EURUSD accounting: isolated
[09:35:00.007] [DEBUG] [System] GBPUSD accounting: isolated
[09:35:00.008] [DEBUG] [System] USDJPY accounting: isolated
[09:35:00.009] [INFO] [System] ✓ Each cycle manages own queue
[09:35:00.010] [INFO] [System] ✓ Each cycle has own recovery_level
[09:35:00.011] [INFO] [System] ✓ No shared operations between pairs
```

**Checks:**
- [ ] Cada ciclo tiene solo sus propias operaciones
- [ ] `cycle_eur.operations` no incluye GBP/JPY ops
- [ ] `cycle_gbp.operations` no incluye EUR/JPY ops
- [ ] `cycle_jpy.operations` no incluye EUR/GBP ops
- [ ] Accounting separado por ciclo

---

### PASO 11: USDJPY Recovery TP → FIFO
**Trigger:** Recovery exitoso USDJPY
```
[09:40:00.000] [INFO] [PriceMonitor] Tick: USDJPY bid=111.15
[09:40:00.001] [INFO] [BrokerAdapter] USDJPY RECOVERY_BUY TP: ticket=70007
[09:40:00.002] [INFO] [CycleOrchestrator] Processing USDJPY recovery TP
[09:40:00.003] [INFO] [FIFOProcessor] FIFO execution for USDJPY (80 pips)
[09:40:00.004] [INFO] [FIFOProcessor] Closing USDJPY Main+Hedge (20 pips cost)
[09:40:00.005] [INFO] [AccountingService] CYC_JPY_001: pips_locked 20 → 0
[09:40:00.006] [DEBUG] [System] === AFTER USDJPY RECOVERY ===
[09:40:00.007] [DEBUG] [System] EURUSD: ACTIVE (unaffected)
[09:40:00.008] [DEBUG] [System] GBPUSD: ACTIVE (unaffected)
[09:40:00.009] [DEBUG] [System] USDJPY: ACTIVE (fully recovered)
[09:40:00.010] [INFO] [System] ✓ FIFO only affected USDJPY cycle
```

**Checks:**
- [ ] FIFO ejecutado solo en USDJPY
- [ ] `cycle_jpy.accounting.pips_locked == 0.0`
- [ ] `cycle_jpy.accounting.pips_recovered == 20.0`
- [ ] EURUSD y GBPUSD: sin cambios en accounting
- [ ] FIFO no cruza pares

---

### PASO 12: Exposición Final y Resumen
**Trigger:** Estado final del sistema
```
[09:45:00.000] [INFO] [System] === MULTI-PAIR FINAL STATUS ===
[09:45:00.001] [DEBUG] [System] 
[09:45:00.002] [DEBUG] [System] ╔════════════════════════════════════════╗
[09:45:00.003] [DEBUG] [System] ║ PAIR     │ STATUS │ TPs │ Pips │ Rec ║
[09:45:00.004] [DEBUG] [System] ╠════════════════════════════════════════╣
[09:45:00.005] [DEBUG] [System] ║ EURUSD   │ ACTIVE │  1  │ +10  │  0  ║
[09:45:00.006] [DEBUG] [System] ║ GBPUSD   │ ACTIVE │  1  │ +10  │  0  ║
[09:45:00.007] [DEBUG] [System] ║ USDJPY   │ ACTIVE │  1  │ +10  │  1  ║
[09:45:00.008] [DEBUG] [System] ╚════════════════════════════════════════╝
[09:45:00.009] [DEBUG] [System] 
[09:45:00.010] [INFO] [System] Total TPs: 3 (1 per pair)
[09:45:00.011] [INFO] [System] Total pips won: 30.0 (main TPs only)
[09:45:00.012] [INFO] [System] Total recovery TPs: 1 (USDJPY)
[09:45:00.013] [INFO] [System] 
[09:45:00.014] [INFO] [RiskManager] === FINAL EXPOSURE ===
[09:45:00.015] [INFO] [RiskManager] Total active operations: 6 (2 per pair)
[09:45:00.016] [INFO] [RiskManager] Total lots: 0.06
[09:45:00.017] [INFO] [RiskManager] Total margin: €60
[09:45:00.018] [INFO] [RiskManager] Balance: €9,961 (approx)
[09:45:00.019] [INFO] [RiskManager] Exposure: 0.6%
[09:45:00.020] [INFO] [RiskManager] ✓ Multi-pair exposure controlled
Checks:

 3 ciclos activos (1 por par)
 Total TPs: 3 (sumando todos los pares)
 Total pips: 30 (main TPs)
 Exposure final: 0.6%
 Cada par independiente y funcional


ESTADO FINAL ESPERADO
yamlsystem:
  active_cycles: 3
  total_exposure_pct: 0.6
  
cycles:
  # === EURUSD ===
  - id: CYC_EUR_001
    pair: EURUSD
    status: ACTIVE
    accounting:
      total_main_tps: 1
      total_pips_won: 10.0
      pips_locked: 0.0
      recovery_level: 0
    operations: 2  # 2 pending (renovadas)
    
  # === GBPUSD ===
  - id: CYC_GBP_001
    pair: GBPUSD
    status: ACTIVE
    accounting:
      total_main_tps: 1
      total_pips_won: 10.0
      pips_locked: 0.0
      recovery_level: 0
    operations: 2  # 2 pending (renovadas)
    
  # === USDJPY ===
  - id: CYC_JPY_001
    pair: USDJPY
    status: ACTIVE  # Fully recovered
    accounting:
      total_main_tps: 1
      total_recovery_tps: 1
      total_pips_won: 10.0
      pips_locked: 0.0
      pips_recovered: 20.0
      recovery_level: 1
      is_fully_recovered: true
    operations: 2  # 2 pending (renovadas post-recovery)
    
account:
  balance: 9961.00  # 10000 - 39 (3 TPs net)
  equity: 9961.00
  margin_used: 60.00
  margin_free: 9901.00
  
exposure:
  eurusd:
    lots: 0.02
    margin: 20.00
    operations: 2
  gbpusd:
    lots: 0.02
    margin: 20.00
    operations: 2
  usdjpy:
    lots: 0.02
    margin: 20.00
    operations: 2
  total:
    lots: 0.06
    margin: 60.00
    operations: 6
    exposure_pct: 0.6
    
metadata:
  multi_pair_execution:
    pairs_active: 3
    independence_verified: true
    cross_contamination: false
    aggregate_exposure_controlled: true

CHECKS CRÍTICOS
Independencia de Ciclos

 3 ciclos completamente separados
 cycle_eur.operations solo EURUSD
 cycle_gbp.operations solo GBPUSD
 cycle_jpy.operations solo USDJPY
 Sin operaciones compartidas

Accounting Separado

 Cada ciclo tiene su propio accounting
 pips_won acumulado por ciclo
 recovery_queue independiente por ciclo
 recovery_level independiente

Estados Diferentes

 EURUSD: ACTIVE (clean)
 GBPUSD: ACTIVE (clean)
 USDJPY: ACTIVE (post-recovery)
 Estados no se interfieren

Exposición Agregada

 Total lots: suma de todos los pares
 Total margin: suma de todos los pares
 Exposure %: calculado sobre total
 total_exposure < 30% (límite global)

FIFO Aislado

 FIFO de USDJPY solo cerró ops USDJPY
 No afectó EURUSD operations
 No afectó GBPUSD operations
 Queue FIFO separada por ciclo

Renovaciones Independientes

 Cada TP renovó solo su propio par
 TP EURUSD → renovó EURUSD (no GBP/JPY)
 TP GBPUSD → renovó GBPUSD (no EUR/JPY)
 TP USDJPY (recovery) → renovó USDJPY (no EUR/GBP)

Balance Global

 Balance actualizado con TPs de todos los pares
 3 TPs main: -39 EUR net (3 × -13)
 1 recovery TP: +60 pips neto
 Balance final consistente

Cálculo de Exposición

 Incluye todas las operaciones activas
 EURUSD: 2 ops
 GBPUSD: 2 ops
 USDJPY: 2 ops (después de recovery)
 Total: 6 ops = 0.06 lots = 60 EUR margin


FIN DE LOS 10 ESCENARIOS DETALLADOS

RESUMEN DE COBERTURA COMPLETA
Escenarios Detallados (10)
IDNombreCubreE1Ciclo Simple ExitosoTP Main, Renovación dual (FIX-001), Cancelación counterE2HedgeHEDGED, Neutralización, 20 pips locked, FIX-002E3Recovery N1 ExitosoRecovery desde TP, FIFO atómico (FIX-003), Costo 20 pipsE4MultinivelCascada N1→N2→N3, FIFO múltiple, Costo 40 pipsE5Gap TPGap detection, Slippage, Ejecución post-gapE6Gap HedgeGap simultáneo, HEDGED con gap, Metadata gapE7Recovery Falla → N2N1 no TP, Distancia 40 pips, Cascada por distanciaE810 TPs Sin HedgeMúltiples iteraciones, Consistencia renovación, Sin HEDGEDE9USDJPY CompletoMultiplicador ×100, 2 decimales, Todo flujo JPYE10Multi-Pair3 pares, Independencia, Exposición agregada
Cobertura de los 62 Escenarios

Core (5): E1 cubre BUY/SELL TP, E5 cubre gap TP. Resto son variaciones.
Cycles (6): E1, E8 cubren renovación y múltiples TPs. Resto son casos específicos.
Hedged (8): E2, E6 cubren HEDGED normal y con gap. Resto son timing variations.
Recovery (10): E3, E4, E7 cubren éxito, multinivel y fallo. Resto son variaciones.
FIFO (4): E3, E4 cubren atómico y múltiple. Resto son casos específicos.
Risk (5): E10 cubre exposición. Resto son tests unitarios.
Money (8): E1, E3 cubren P&L. Resto son tests de cálculos.
Edge (8): E5, E6 cubren gaps. Resto son casos extremos.
Multi-Pair (4): E10 cubre todo. Resto son subsets.
JPY (4): E9 cubre flujo completo JPY. Resto son casos específicos.

Total: 10 detallados + 52 en matriz compacta = 62 escenarios completos