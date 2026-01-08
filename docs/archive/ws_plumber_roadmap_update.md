---

## Roadmap y Estado de Ejecución (Source of Truth)

> **Última Actualización:** 2026-01-06

### ✅ Logros Técnicos

#### Fase 0-3: Completadas
- **[2026-01-05]** Creación de `requirements.txt` con todas las dependencias (Supabase, FastAPI, MT5, etc.).
- **[2026-01-05]** Instalación exitosa de dependencias en el entorno virtual `venv`.
- **[2026-01-05]** Creación de todos los `__init__.py` (17 archivos) para estructura de paquetes correcta.
- **[2026-01-05]** Avance en **Fase 2: Operativa Normal**: Implementación de `_renew_cycle`, `_open_recovery_cycle` y `_handle_recovery_tp` con lógica FIFO.
- **[2026-01-05]** Completada **Fase 1: Inicio**: Apertura dual de operaciones (Buy/Sell), límites de riesgo de emergencia (`EMERGENCY_LIMITS`) y monitoreo de ejecución activo.
- **[2026-01-05]** Configuración global del proyecto: Creación de `pyproject.toml` en la raíz con configuraciones para `black`, `ruff`, `mypy` y `pytest`.
- **[2026-01-05]** Implementación de la capa de aplicación y orquestación: **TradingService**, **RiskManager** y **CycleOrchestrator**.
- **[2026-01-05]** Creación del punto de entrada principal `main.py` para el arranque coordinado del sistema.
- **[2026-01-05]** Implementación del adaptador **MetaTrader 5 (MT5Broker)** cumpliendo con la interfaz `IBroker`.
- **[2026-01-05]** Migración e integración de activos avanzados desde el directorio `new/`.
- **[2026-01-05]** Dashboard V2 y V3 implementados con WebSocket integration.

#### Fase 4: Auditoría Completa (2026-01-06)
- **[2026-01-06]** Auditoría exhaustiva de **12 componentes** del sistema.
- **[2026-01-06]** Identificados **7 bugs críticos (P0)** y **13 bugs menores (P1/P2)**.
- **[2026-01-06]** **Bug raíz identificado**: `SimulatedBroker` cerraba TPs internamente antes de que el orquestador los procesara.
- **[2026-01-06]** Generados **9 archivos de corrección** en directorio `fixes/`.
- **[2026-01-06]** Documentado el flujo corregido broker↔orquestador.
- **[2026-01-06]** Creado script automático de aplicación de fixes (`apply_fixes.py`).

### 🔴 Bugs Críticos Encontrados y Corregidos

| ID | Componente | Bug | Estado |
|----|------------|-----|--------|
| BUG-SB-01 | SimulatedBroker | Cierra TPs internamente antes que orquestador | ✅ Fix generado |
| BUG-SB-02 | SimulatedBroker | get_open_positions() no incluye TP_HIT | ✅ Fix generado |
| BUG-TS-01 | TradingService | Asume TP si no hay close_price | ✅ Fix generado |
| BUG-EN-01 | Strategy Engine | process_tp_hit retorna pair="" | ✅ Fix generado |
| BUG-EN-02 | Strategy Engine | Genera recovery para ciclos cerrados | ✅ Fix generado |
| BUG-TEST-01 | Tests | Compara enum vs string | ✅ Fix generado |
| BUG-IMR-01 | InMemoryRepo | Comparación frágil de status | ✅ Fix generado |

### 🚀 Próximos Pasos (Pendientes)

- [ ] **Aplicar fixes** al código base
- [ ] **Ejecutar tests** de verificación post-fix
- [ ] **Validar flujo completo** con backtest
- [ ] Configuración del dashboard en tiempo real (WebSockets con datos reales)
- [ ] Paper Trading en cuenta demo

---

## 📊 Estado por Fases (Actualizado 2026-01-06)

| Fase | Descripción | Estado | Fecha |
|------|-------------|--------|-------|
| **Fase 0** | Infraestructura y Alineación | ✅ Completada | 2026-01-05 |
| **Fase 1** | Inicio (Apertura Dual, Riesgo) | ✅ Completada | 2026-01-05 |
| **Fase 2** | Operativa Normal (Recovery, FIFO) | ✅ Completada | 2026-01-05 |
| **Fase 3** | API y Dashboard | ✅ Completada | 2026-01-05 |
| **Fase 4** | Auditoría y Correcciones | ✅ Completada | 2026-01-06 |
| **Fase 5** | Verificación Post-Fix | ⏳ Pendiente | - |
| **Fase 6** | Paper Trading | ⏳ Pendiente | - |
| **Fase 7** | Producción | ⏳ Pendiente | - |

---

## 📁 Archivos de Corrección Disponibles

```
fixes/
├── simulated_broker_fixed.py      # FIX-SB-01, SB-02, SB-03
├── trading_service_fixed.py       # FIX-TS-01, TS-02, TS-03
├── strategy_engine_fixed.py       # FIX-EN-01, EN-02, EN-03
├── in_memory_repo_fixed.py        # FIX-IMR-01
├── test_scenarios_fixed.py        # FIX-TEST-01, TEST-02, TEST-03
├── cycle_accounting_fix.py        # FIX-CY-01 (instrucciones)
├── operation_close_fix.py         # FIX-OP-01 (instrucciones)
├── apply_fixes.py                 # Script automático
└── INSTRUCCIONES_APLICACION.md    # Guía paso a paso
```

### Comando de Aplicación Rápida

```bash
# Crear backup y aplicar fixes
python fixes/apply_fixes.py --backup

# Verificar
pytest tests/ -v
```

---

## 🔍 Validación de Integridad Post-Auditoría

### Interacción Broker ↔ Orquestador (CORREGIDA)

| Evento | Antes (Bug) | Después (Fix) |
|--------|-------------|---------------|
| TP detectado | Broker cierra posición | Broker marca como TP_HIT |
| Sync posiciones | No encuentra posición | Incluye TP_HIT con precio |
| Orquestador | Nunca renueva ciclo | Detecta TP, llama renovación |
| Sistema | Se detiene | Continúa operando |

### Tests de Validación Requeridos

```bash
# 1. Test unitarios del core
pytest tests/unit/test_strategy_core.py -v

# 2. Test de contabilidad FIFO
pytest tests/unit/test_cycle_accounting.py -v

# 3. Test de señales del engine
pytest tests/unit/test_engine_signals.py -v

# 4. Test de integración con broker simulado
pytest tests/integration/test_scenarios.py -v

# 5. Backtest con escenario TP
python -m wsplumber.core.backtest.backtest_engine tests/scenarios/scenario_tp_hit.csv EURUSD
```

---

## 📝 Lecciones Aprendidas (Auditoría 2026-01-06)

### 1. Separación de Responsabilidades
> **El broker REPORTA eventos, el orquestador ACTÚA sobre ellos.**

El bug raíz ocurrió porque el broker tomaba decisiones de negocio (cerrar posiciones) que deberían ser exclusivas del orquestador.

### 2. Estado Explícito vs Implícito
> **Nunca asumir estado basándose en la ausencia de datos.**

El hecho de que una posición no estuviera en `open_positions` no significaba que estuviera cerrada correctamente. Siempre marcar estado explícitamente.

### 3. Enums para Estados
> **Siempre usar enums, nunca strings, para comparaciones de estado.**

```python
# ❌ Frágil
if status != "closed":

# ✅ Robusto
if status != CycleStatus.CLOSED:
```

### 4. Logging de Transiciones
> **Cada cambio de estado debe loguearse con contexto completo.**

Esto permitió rastrear exactamente dónde fallaba el flujo durante la auditoría.

### 5. Tests de Flujo Completo
> **Los tests unitarios no capturan problemas de integración.**

El sistema pasaba tests unitarios pero fallaba en producción porque los componentes no se comunicaban correctamente.

---

## 🎯 Criterios de Éxito para Fase 5 (Verificación)

| Criterio | Métrica | Target |
|----------|---------|--------|
| Tests pasan | pytest exit code | 0 |
| Ciclos renuevan | Logs de renovación | ✓ presentes |
| Recovery funciona | FIFO correcto | ✓ verificado |
| Sin duplicados | Operaciones únicas | ✓ verificado |
| Balance correcto | Cálculo matemático | ✓ verificado |

---
