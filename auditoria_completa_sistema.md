# Auditoría Completa del Sistema - wsplumber

*Fecha: 2026-01-05*
*Versión auditada: Post-fix cycle_orchestrator.py*

---

## Resumen Ejecutivo

| Componente | Bugs Críticos | Bugs Menores | Estado |
|------------|---------------|--------------|--------|
| cycle_orchestrator.py | 0 | 0 | ✅ AUDITADO (fix aplicado) |
| trading_service.py | 1 | 2 | ⚠️ REVISAR |
| simulated_broker.py | 2 | 1 | ⚠️ REVISAR |
| _engine.py (Strategy) | 1 | 2 | ⚠️ REVISAR |
| risk_manager.py | 0 | 2 | ✅ OK (placeholders) |
| cycle.py | 0 | 1 | ✅ OK |
| operation.py | 0 | 1 | ✅ OK |
| types.py | 0 | 0 | ✅ OK |
| test_scenarios.py | 2 | 1 | ⚠️ REVISAR |
| in_memory_repo.py | 1 | 0 | ⚠️ REVISAR |
| backtest_engine.py | 0 | 1 | ✅ OK |
| m1_data_loader.py | 0 | 1 | ✅ OK |
| state_broadcaster.py | 0 | 1 | ✅ OK |

**Total: 7 bugs críticos, 13 bugs menores**

---

## 1. trading_service.py

### BUG-TS-01 (CRÍTICO): Sync no detecta TPs correctamente

**Ubicación:** Líneas 85-120
**Problema:** El método `sync_all_active_positions()` busca en el historial del broker para detectar cierres, pero:
1. Llama a `get_order_history()` múltiples veces en el mismo sync (ineficiente)
2. No distingue entre TP_HIT y cierre manual
3. Usa `close_price` como fallback a `op.tp_price` lo cual puede ser incorrecto

```python
# Línea 108 - Problema
close_price = h_pos.get("actual_close_price") or h_pos.get("close_price") or op.tp_price
# Si no encuentra precio, asume TP - INCORRECTO
```

**Impacto:** Operaciones cerradas manualmente podrían registrarse como TP_HIT.

**Fix sugerido:**
```python
close_price = h_pos.get("actual_close_price") or h_pos.get("close_price")
if close_price is None:
    logger.warning("No close price found, skipping", op_id=op.id)
    continue
```

### BUG-TS-02 (MENOR): Llamada redundante a get_order_history

**Ubicación:** Líneas 92 y 114
**Problema:** Se llama a `get_order_history()` dos veces: una para pendientes y otra para activas.

**Fix sugerido:** Llamar una sola vez al inicio y reusar el resultado.

### BUG-TS-03 (MENOR): No hay manejo de error si broker desconecta durante sync

**Ubicación:** Todo el método `sync_all_active_positions()`
**Problema:** Si el broker se desconecta a mitad del sync, no hay rollback ni recuperación.

---

## 2. simulated_broker.py

### BUG-SB-01 (CRÍTICO): Broker cierra posiciones antes que orquestador las detecte

**Ubicación:** Líneas 195-210 (`_process_executions`)
**Problema:** El broker simulado ejecuta `close_position()` internamente cuando detecta TP, pero el orquestador espera detectar el cierre vía sync.

```python
# Línea 208
for t in tickets_to_close:
    await self.close_position(t)  # Cierra ANTES de que orquestador lo vea
```

**Impacto:** 
- El orquestador nunca ve la operación en estado TP_HIT
- No se ejecuta la lógica de renovación de mains
- El ciclo queda huérfano

**Fix sugerido:**
```python
# En lugar de cerrar, marcar para cierre
for t in tickets_to_close:
    pos = self.open_positions[t]
    pos.status = OperationStatus.TP_HIT  # Solo marcar
    pos.actual_close_price = tick.bid if pos.order_type.is_buy else tick.ask
    # NO llamar a close_position() aquí - dejar que orquestador lo haga
```

### BUG-SB-02 (CRÍTICO): get_open_positions no incluye posiciones marcadas como TP_HIT

**Ubicación:** Línea 154
**Problema:** `get_open_positions()` retorna `self.open_positions` pero el sync del orquestador busca posiciones que YA NO están ahí porque fueron cerradas.

**Impacto:** La reconciliación falla silenciosamente.

### BUG-SB-03 (MENOR): Cálculo de P&L no considera spread

**Ubicación:** Líneas 182-190
**Problema:** El cálculo de pips usa bid para buy y ask para sell, pero no considera el spread pagado al abrir.

---

## 3. _engine.py (Strategy)

### BUG-EN-01 (CRÍTICO): process_tp_hit retorna OPEN_CYCLE sin pair

**Ubicación:** Líneas 88-96
**Problema:**
```python
def process_tp_hit(self, operation_id, profit_pips, timestamp) -> StrategySignal:
    return StrategySignal(
        signal_type=SignalType.OPEN_CYCLE,
        pair=CurrencyPair(""),  # ← VACÍO
        metadata={...}
    )
```

**Impacto:** El orquestador recibe una señal sin par, causando comportamiento indefinido.

**Fix sugerido:**
```python
# El orquestador debe pasar el pair, o extraerlo del operation_id
# Por ahora, retornar NO_ACTION y dejar que el orquestador maneje la renovación
return StrategySignal(
    signal_type=SignalType.NO_ACTION,  # El orquestador ya tiene _renew_main_operations
    pair=CurrencyPair(""),
    metadata={"tp_operation": operation_id, "profit_pips": profit_pips}
)
```

### BUG-EN-02 (MENOR): _analyze_cycle_for_recovery no verifica status del ciclo

**Ubicación:** Líneas 140-175
**Problema:** Genera señales de recovery incluso si el ciclo está CLOSED o PAUSED.

```python
def _analyze_cycle_for_recovery(self, cycle, current_price, pair):
    if not cycle.needs_recovery and not cycle.is_hedged:
        return None
    # Falta: if cycle.status in (CycleStatus.CLOSED, CycleStatus.PAUSED): return None
```

### BUG-EN-03 (MENOR): register_cycle usa str(pair) como key

**Ubicación:** Línea 191
**Problema:** Inconsistencia - a veces usa `str(pair)`, a veces `pair` directamente.

---

## 4. risk_manager.py

### BUG-RM-01 (MENOR): Límites prácticamente eliminados

**Ubicación:** Líneas 23-26
```python
EMERGENCY_LIMITS = {
    'max_concurrent_recovery': 999999,  # Sin límite real
    'max_exposure_percent': 999999.0    # Sin límite real
}
```

**Nota:** Esto fue intencional según el usuario, pero debería documentarse.

### BUG-RM-02 (MENOR): check_daily_limits() siempre retorna True

**Ubicación:** Líneas 72-76
**Problema:** Placeholder que nunca valida límites diarios.

---

## 5. cycle.py

### BUG-CY-01 (MENOR): get_recovery_cost() no usa la cola

**Ubicación:** Líneas 85-92
**Problema:** El costo se calcula basándose en `pips_recovered`, no en la posición en la cola.

```python
def get_recovery_cost(self) -> Pips:
    if float(self.pips_recovered) < 20.0:
        return Pips(20.0)
    return Pips(40.0)
```

**Comportamiento esperado:** El primer elemento de la cola cuesta 20, los demás 40.
**Comportamiento actual:** Si ya se recuperaron 20+ pips, todos cuestan 40.

**Posible problema:** Si se cierra un recovery parcialmente y se abre otro, el costo podría ser incorrecto.

---

## 6. operation.py

### BUG-OP-01 (MENOR): close() detecta TP con tolerancia fija

**Ubicación:** Líneas 168-177
```python
if pips_diff < 1.0:  # Tolerancia de 1 pip
    self.status = OperationStatus.TP_HIT
```

**Problema:** Para pares JPY, 1 pip equivale a 0.01, no 0.0001. La tolerancia debería ajustarse.

---

## 7. test_scenarios.py

### BUG-TEST-01 (CRÍTICO): Comparación de enum como string

**Ubicación:** Línea 39
```python
found = [c for c in self.cycles.values() if c.status != "closed"]
```

**Problema:** `c.status` es `CycleStatus.CLOSED` (enum), no `"closed"` (string).

**Fix:**
```python
found = [c for c in self.cycles.values() if c.status != CycleStatus.CLOSED]
```

### BUG-TEST-02 (CRÍTICO): InMemoryRepository duplicado

**Ubicación:** Líneas 20-85
**Problema:** Hay una implementación de `InMemoryRepository` en `test_scenarios.py` Y otra en `infrastructure/persistence/in_memory_repo.py`. Son diferentes.

**Diferencias:**
- La de tests NO importa `CycleStatus` correctamente
- La de infrastructure sí usa `OperationStatus.ACTIVE` correctamente

### BUG-TEST-03 (MENOR): import de CycleStatus faltante

**Ubicación:** Línea ~30
```python
# Falta:
from wsplumber.domain.entities.cycle import CycleStatus
```

---

## 8. in_memory_repo.py (infrastructure)

### BUG-IMR-01 (CRÍTICO): get_active_cycles usa string comparison

**Ubicación:** Línea 26
```python
found = [c for c in self.cycles.values() if c.status.name not in ["CLOSED", "PAUSED"]]
```

**Problema:** Usa `.name` que funciona, pero es frágil. Mejor usar el enum directamente.

---

## 9. backtest_engine.py

### BUG-BE-01 (MENOR): No usa el InMemoryRepository de infrastructure

**Ubicación:** Línea 14
```python
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
```

**Estado:** Correcto - usa el de infrastructure, no el de tests.

---

## 10. m1_data_loader.py

### BUG-ML-01 (MENOR): spread_pips siempre 1.0

**Ubicación:** Línea 55
```python
spread_pips = 1.0  # Hardcoded
```

**Problema:** No refleja el spread real del CSV si existe.

---

## 11. state_broadcaster.py

### BUG-SB-01 (MENOR): active_recoveries cuenta incorrecto

**Ubicación:** Líneas 87-90
```python
for pair, cycle in self._orchestrator._active_cycles.items():
    if hasattr(cycle, 'recovery_operations'):
        active_recoveries += len(cycle.recovery_operations)
```

**Problema:** `recovery_operations` es una property que filtra por tipo, no cuenta recoveries activos específicamente.

---

## 12. generate_scenarios.py

### BUG-GS-01 (DOCUMENTACIÓN): Comentarios incorrectos

**Ubicación:** Líneas 10-20
**Problema:** Los comentarios hablan de "Buy Stop" y "Sell Stop" pero el sistema usa órdenes de mercado.

---

## 13. Scenario CSVs

### BUG-CSV-01 (MENOR): Precisión decimal

**Ubicación:** Todos los CSVs de scenarios
**Problema:** Usan `1.1` en lugar de `1.10000` lo cual puede causar problemas con Decimal.

```csv
# Actual
2024-01-01T10:00:00,EURUSD,1.1,1.1002

# Recomendado
2024-01-01T10:00:00,EURUSD,1.10000,1.10020
```

---

## Bugs por Prioridad

### P0 - Críticos (Bloquean funcionamiento)

| ID | Componente | Descripción |
|----|------------|-------------|
| BUG-SB-01 | simulated_broker | Broker cierra antes que orquestador detecte |
| BUG-SB-02 | simulated_broker | get_open_positions no incluye TP_HIT |
| BUG-EN-01 | _engine.py | process_tp_hit retorna pair vacío |
| BUG-TEST-01 | test_scenarios | Comparación enum como string |
| BUG-TEST-02 | test_scenarios | InMemoryRepository duplicado |
| BUG-TS-01 | trading_service | Sync no detecta TPs correctamente |
| BUG-IMR-01 | in_memory_repo | get_active_cycles usa string comparison |

### P1 - Importantes (Pueden causar bugs en producción)

| ID | Componente | Descripción |
|----|------------|-------------|
| BUG-EN-02 | _engine.py | No verifica status del ciclo |
| BUG-CY-01 | cycle.py | get_recovery_cost no usa cola correctamente |
| BUG-OP-01 | operation.py | Tolerancia TP no ajusta para JPY |

### P2 - Menores (Mejoras de código)

| ID | Componente | Descripción |
|----|------------|-------------|
| BUG-TS-02 | trading_service | Llamada redundante a get_order_history |
| BUG-TS-03 | trading_service | No hay manejo de desconexión |
| BUG-SB-03 | simulated_broker | P&L no considera spread |
| BUG-EN-03 | _engine.py | Inconsistencia en uso de str(pair) |
| BUG-RM-01 | risk_manager | Límites eliminados sin documentar |
| BUG-RM-02 | risk_manager | check_daily_limits placeholder |
| BUG-ML-01 | m1_data_loader | spread hardcoded |
| BUG-SB-01 | state_broadcaster | Conteo incorrecto de recoveries |
| BUG-CSV-01 | scenarios | Precisión decimal |
| BUG-GS-01 | generate_scenarios | Comentarios incorrectos |
| BUG-TEST-03 | test_scenarios | Import faltante |

---

## Diagrama de Interacción con Bugs

```
┌──────────────────────────────────────────────────────────────┐
│                     FLUJO DE TP DETECTION                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Tick Llega                                                  │
│      │                                                       │
│      ▼                                                       │
│  SimulatedBroker._process_executions()                       │
│      │                                                       │
│      ├─► Detecta TP                                          │
│      │       │                                               │
│      │       ▼                                               │
│      │   ❌ BUG-SB-01: close_position() interno              │
│      │       │                                               │
│      │       ▼                                               │
│      │   Posición removida de open_positions                 │
│      │                                                       │
│      ▼                                                       │
│  CycleOrchestrator._check_operations_status()                │
│      │                                                       │
│      ▼                                                       │
│  TradingService.sync_all_active_positions()                  │
│      │                                                       │
│      ├─► get_open_positions()                                │
│      │       │                                               │
│      │       ▼                                               │
│      │   ❌ BUG-SB-02: Posición YA NO ESTÁ                   │
│      │                                                       │
│      ├─► get_order_history()                                 │
│      │       │                                               │
│      │       ▼                                               │
│      │   ❌ BUG-TS-01: Asume TP si no hay precio             │
│      │                                                       │
│      ▼                                                       │
│  Operación marcada como cerrada (pero sin proceso correcto)  │
│      │                                                       │
│      ▼                                                       │
│  ❌ _renew_main_operations() NO SE LLAMA                     │
│      │                                                       │
│      ▼                                                       │
│  Ciclo queda sin operaciones → Sistema se detiene            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Recomendaciones de Fix

### Fix Prioritario: SimulatedBroker

El fix más importante es cambiar cómo el broker simulado maneja los TPs:

```python
# En simulated_broker.py, línea ~200

async def _process_executions(self, tick: TickData):
    # ... código existente para activar órdenes ...
    
    # 2. Actualizar P&L y MARCAR TPs (no cerrar)
    for ticket, pos in self.open_positions.items():
        # ... cálculo de pips ...
        
        # Verificar TP - SOLO MARCAR, NO CERRAR
        tp_hit = False
        if pos.order_type.is_buy and tick.bid >= pos.tp_price:
            tp_hit = True
        elif pos.order_type.is_sell and tick.ask <= pos.tp_price:
            tp_hit = True
            
        if tp_hit:
            pos.status = OperationStatus.TP_HIT
            pos.actual_close_price = tick.bid if pos.order_type.is_buy else tick.ask
            pos.close_time = tick.timestamp
            # NO llamar close_position() aquí
            logger.info(f"Position {ticket} marked as TP_HIT (not closed yet)")
```

Luego, modificar `get_open_positions()` para incluir posiciones TP_HIT:

```python
async def get_open_positions(self) -> Result[List[Dict[str, Any]]]:
    result = []
    for pos in self.open_positions.values():
        result.append({
            "ticket": pos.ticket,
            "symbol": pos.pair,
            "volume": pos.lot_size,
            "type": "buy" if pos.order_type.is_buy else "sell",
            "entry_price": float(pos.entry_price),
            "tp": float(pos.tp_price),
            "profit": pos.current_pnl_money,
            "status": pos.status.value,  # NUEVO: incluir status
            # Para TPs detectados:
            "close_price": float(pos.actual_close_price) if pos.status == OperationStatus.TP_HIT else None,
            "close_time": pos.close_time if hasattr(pos, 'close_time') else None
        })
    return Result.ok(result)
```

Y en el orquestador, detectar el TP y ENTONCES cerrar:

```python
# En cycle_orchestrator.py, _check_operations_status()

# Después de sync, verificar si hay posiciones marcadas como TP
positions_res = await self.trading_service.broker.get_open_positions()
if positions_res.success:
    for pos_data in positions_res.value:
        if pos_data.get("status") == "tp_hit":
            # Ahora sí procesar el TP
            # ... lógica de _renew_main_operations, etc ...
            # Finalmente cerrar en broker
            await self.trading_service.broker.close_position(pos_data["ticket"])
```

---

## Próximos Pasos

1. **Inmediato:** Aplicar fix a SimulatedBroker (BUG-SB-01, BUG-SB-02)
2. **Corto plazo:** Corregir tests (BUG-TEST-01, BUG-TEST-02)
3. **Medio plazo:** Revisar trading_service sync (BUG-TS-01)
4. **Largo plazo:** Documentar y corregir bugs menores

---

*Auditoría completada - 2026-01-05*
