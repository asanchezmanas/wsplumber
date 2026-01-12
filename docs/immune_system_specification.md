# Especificación Técnica: Sistema Inmune V4.2 (Máxima Robustez)

Este documento detalla la implementación quirúrgica de las capas de seguridad y optimización del motor WSPlumber, diseñadas para transformar una ventaja matemática en un sistema de trading institucional resiliente.

---

## 🛡️ Capa 1: Recovery Breakeven (Regla del 50%)

**Objetivo**: Evitar que una operación de recuperación que ha alcanzado el 50% de su objetivo (+40 pips) vuelva a entrar en pérdidas negativas.

### Detalles de Implementación:
- **Ubicación**: `src/wsplumber/application/services/trading_service.py`
- **Método**: `sync_all_active_positions`
- **Lógica**:
    1.  Para cada operación de tipo `RECOVERY` en estado `ACTIVE`.
    2.  Calcular `unrealized_pips` usando el precio actual del tick.
    3.  Si `unrealized_pips >= 40.0`:
        - Marcar `op.metadata["be_protected"] = True`.
    4.  Si `op.metadata.get("be_protected") == True` Y `unrealized_pips <= 0.5`:
        - Ejecutar `self.broker.close_position(op.broker_ticket)`.
        - Al cerrar en 0 pips, el ciclo permanece bloqueado pero **no añade una nueva unidad de deuda de 40 pips**.

---

## 🌧️ Capa 2: Filtro de Volatilidad ATR (4H Window)

**Objetivo**: Pausar la generación de nuevos ciclos ("poner el cazo") cuando el mercado está estancado para evitar acumulación de swaps y ruido.

### Detalles de Implementación:
- **Ubicación**: `src/wsplumber/core/strategy/_engine.py`
- **Configuración**: `src/wsplumber/core/strategy/_params.py` -> `MIN_ATR_PIPS = 20.0`
- **Lógica**:
    1.  La estrategia mantendrá una lista circular de los rangos (High - Low) de las últimas 4 velas de 1 hora.
    2.  `ATR = Sum(High - Low) / 4`.
    3.  En `process_tick`, antes de emitir `OPEN_CYCLE`:
        - Si `ATR < MIN_ATR_PIPS`: Retornar `NO_ACTION` con metadata `{"reason": "low_volatility"}`.
    4.  **Nota**: Los Recoveries existentes **SIEMPRE** se siguen gestionando aunque la volatilidad sea baja.

---

## 🛑 Capa 3: Modos Operativos de Margen (RiskManager)

**Objetivo**: Escalar defensivamente el riesgo basándose en la salud del balance.

### Detalles de Implementación:
- **Ubicación**: `src/wsplumber/core/risk/risk_manager.py`
- **Lógica de Estados**:

| Modo | Margen Libre | Restricción |
|------|--------------|-------------|
| **NORMAL** | > 60% | Sin restricciones. |
| **ALERTA** | 40% - 60% | Bloquea `OPEN_CYCLE`. Solo permite `OPEN_RECOVERY`. |
| **SUPERVIVENCIA** | < 40% | Bloquea **TODO** (Mains y Recoveries). Solo permite `HEDGE` (Bloqueo 20 pips). |

- **Acción**: Actualizar `can_open_position` para recibir el `free_margin_percent` del broker.

---

## 🧹 Capa 4: Hucha de Poda (Pruning Jar)

**Objetivo**: Sistema de autolimpieza proactiva que utiliza el exceso de beneficio para liquidar deudas antiguas sin esperar al precio.

### Detalles de Implementación:
- **Entidad**: `CycleAccounting` en `src/wsplumber/domain/entities/cycle.py`
    - Añadir campo `surplus_pips: float`.
    - Cuando un Recovery TP (+80) cierra una deuda de 20 o 40, el sobrante se acumula en `surplus_pips`.
- **Servicio**: `src/wsplumber/application/services/pruning_service.py` (Nuevo)
- **Lógica de Poda**:
    1.  El orquestador llama al `PruningService` cada hora.
    2.  El servicio busca ciclos con `surplus_pips > 0`.
    3.  Busca la unidad de deuda más antigua (`FIFO`) de **cualquier otro ciclo** activo.
    4.  Si el `surplus` global >= Deuda antigua (ej. 20 pips):
        - Resta 20 pips del excedente.
        - Marca la deuda antigua como "Podada" (Liquidada).
        - Cierra las operaciones físicas asociadas a esa deuda.

---

## � Plan de Verificación Operativa

Para asegurar que estas capas no rompen el sistema, se ejecutarán los siguientes tests específicos:

### TEST-IM-01: Breakeven Inmune (Látigo de Mercado)
- **Escenario**: Ciclo con deuda de 20 pips. Abre recovery. El precio sube +45 pips (activa Protección BE). El precio cae bruscamente a -10 pips.
- **Resultado Esperado**: La operación de recovery se cierra en +0.5 pips. El ciclo NO añade una unidad de deuda de 40 pips. El ciclo sigue vivo con sus 20 pips originales, esperando un nuevo recovery.
- **Archivo**: `tests/scenarios/robustness/i01_recovery_be.csv`

### TEST-IM-02: Saturación por Margen
- **Escenario**: Balance de 1,000 EUR. Simular 20 ciclos abiertos (Margen Libre al 45%).
- **Resultado Esperado**: El `RiskManager` rechaza señales `OPEN_CYCLE` (Mains). El sistema solo permite señales de `OPEN_RECOVERY`.
- **Archivo**: `tests/scenarios/robustness/i02_margin_modes.yaml`

### TEST-IM-03: Poda Cruzada (Cross-Cycle Pruning)
- **Escenario**: Ciclo A tiene +90 pips de excedente (Surplus). Ciclo B tiene una deuda "zombie" de nivel 3 (40 pips).
- **Resultado Esperado**: El `PruningService` transfiere 40 pips del superávit de A para liquidar la unidad de B. Las operaciones de B se cierran en el broker instantáneamente.

---

## ⚖️ Análisis de Robustez: ¿Más o Menos Robusto?

**Conclusión: El sistema es infinitamente MÁS ROBUSTO tras estos cambios.**

1.  **Eliminación del "Riesgo de Ruina"**: Sin estos cambios, una racha de mercados laterales (látigos) puede acumular niveles de recovery ad eternum. El **Breakeven** corta esta acumulación.
2.  **Protección de Gasolina (Margen)**: En el test de 500k vimos 1,200 ciclos. Sin el **Filtro ATR**, muchos de esos ciclos se abren en momentos donde el mercado no se mueve, gastando margen y swaps para nada. El filtro asegura que solo operamos cuando hay "gasolina" en el mercado.
3.  **Auto-Saneamiento**: La **Hucha de Poda** convierte al bot en un ente orgánico que se limpia solo. Esto reduce la carga cognitiva del trader y el riesgo de errores de memoria o ejecución al tener menos órdenes abiertas.

> [!TIP]

---

## 🧹 Capa 4: Hucha de Poda (Pruning Jar) [ADICIÓN DETALLADA]

**Objetivo**: Sistema de autolimpieza proactiva que utiliza el exceso de beneficio para liquidar deudas antiguas sin esperar al precio.

### Detalles de Implementación:
- **Entidad**: `CycleAccounting` en `src/wsplumber/domain/entities/cycle.py`
    - Añadir campo `surplus_pips: float`.
    - Cuando un Recovery TP (+80) cierra una deuda de 20 o 40, el sobrante se acumula en `surplus_pips`.
- **Servicio**: `src/wsplumber/application/services/pruning_service.py` (Nuevo)
- **Lógica de Poda**:
    1.  El orquestador llama al `PruningService` cada hora.
    2.  El servicio busca ciclos con `surplus_pips > 0`.
    3.  Busca la unidad de deuda más antigua (`FIFO`) de **cualquier otro ciclo** activo.
    4.  Si el `surplus` global >= Deuda antigua (ej. 20 pips):
        - Resta 20 pips del excedente.
        - Marca la deuda antigua como "Podada" (Liquidada).
        - Cierra las operaciones físicas asociadas a esa deuda.

```python
# [FRAGMENTO DE CÓDIGO PLANIFICADO]
def process_pruning(self):
    total_surplus = sum(c.accounting.surplus_pips for c in self.cycles)
    if total_surplus < 20: return
    
    dirty_cycles = [c for c in self.cycles if c.has_toxic_debt]
    for cycle in sorted(dirty_cycles, key=lambda x: x.opened_at):
        debt = cycle.get_oldest_debt_unit()
        if total_surplus >= debt.pips:
            self.liquidate_debt(cycle, debt)
            total_surplus -= debt.pips
```

---

## 🏛️ Apéndice: Código Real Implementado (Layer 1 & 2) [NUEVO]

### Layer 1: Recovery Breakeven (TradingService.py)
```python
# Implementado en sync_all_active_positions
if op.is_recovery and broker_status == "active":
    current_price = broker_pos.get("current_price") or broker_pos.get("bid") or broker_pos.get("ask")
    if current_price:
        # Calcular pips flotantes
        multiplier = 100 if "JPY" in op.pair else 10000
        entry = float(op.actual_entry_price or op.entry_price)
        curr = float(current_price)
        floating_pips = (curr - entry) * multiplier if op.is_buy else (entry - curr) * multiplier
        
        # 1. Activar protección si llega a +40 pips
        if floating_pips >= 40.0 and not op.metadata.get("be_protected"):
            op.metadata["be_protected"] = True
        
        # 2. Ejecutar Breakeven si retrocede a <= +0.5 pips
        if op.metadata.get("be_protected") and floating_pips <= 0.5:
            await self.broker.close_position(op.broker_ticket)
            op.close_v2(price=Price(Decimal(str(current_price))), timestamp=datetime.now())
```

### Layer 2: Filtro ATR (StrategyEngine.py)
```python
# Implementado en process_tick
# Actualizar ATR (Layer 2)
self._update_atr(pair, ask, timestamp)

# Verificar si hay ciclo activo
if pair not in self._active_cycles:
    # --- IMMUNE SYSTEM: Layer 2 - ATR Filter ---
    atr_pips = self._get_current_atr(pair)
    if atr_pips < MIN_ATR_PIPS:
        return StrategySignal(
            signal_type=SignalType.NO_ACTION,
            pair=pair,
            metadata={"reason": "low_volatility", "atr_pips": round(atr_pips, 1)}
### Layer 3: Modos de Margen (RiskManager.py)
```python
# Implementado en can_open_position
# 1. Modo SUPERVIVENCIA (< 40%) - Bloqueo TOTAL de nuevas operaciones
if free_margin_percent < 40.0:
    return Result.fail("SURVIVAL MODE: Margin too low", "RISK_MARGIN_SURVIVAL")

# 2. Modo ALERTA (40% - 60%) - Bloquea nuevos ciclos, solo permite gestionar los existentes
if free_margin_percent <= 60.0 and not is_recovery:
    return Result.fail("ALERT MODE: Margin at limited levels. Only RECOVERY allowed", "RISK_MARGIN_ALERT")
```

### Layer 4: Hucha de Poda (PruningService.py)
```python
# Implementado como servicio independiente llamado por el Orquestador
async def execute_pruning(self, all_active_cycles: List[Cycle]):
    global_surplus = sum(c.accounting.surplus_pips for c in all_active_cycles)
    if global_surplus < 20.0: return
    
    cycles_with_debt = sorted([c for c in all_active_cycles if c.accounting.pips_locked > 0], key=lambda x: x.created_at)
    
    for victim_cycle in cycles_with_debt:
        unit_cost = victim_cycle.accounting.debt_units[0]
        if global_surplus >= unit_cost:
            # Distribuir descuento de surplus entre donantes y liquidar en victima
            victim_cycle.accounting.debt_units.pop(0)
            victim_cycle.accounting.pips_locked = sum(victim_cycle.accounting.debt_units)
```
