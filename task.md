# Backtest API con Streaming

## Objetivo
Implementar endpoints de FastAPI para ejecutar backtests remotamente con streaming de progreso.

## Tareas

- [x] **Implementar Backtest API con Streaming**
  - [x] Crear `api/routers/backtest.py` con endpoints
  - [x] Crear `BacktestService` con generador async
  - [x] Implementar SSE streaming para progreso
  - [x] Registrar router en `app.py`
  - [x] Crear `partition_csv_by_year.py` para datos por año

- [x] **Fix Broker and Orchestrator Issues**
  - [x] Añadir `modify_position` a `SimulatedBroker`
  - [x] Corregir cierre automático de TP en `SimulatedBroker`
  - [x] Verificar sincronización Broker-Orchestrator

- [x] **FASE 10: Auditoría Segmentada de Supervivencia (2015)**
    - [x] Identificar ventanas de tiempo críticas (SNB Black Thursday, ECB QE, FOMC Hike)
    - [x] Implementar `scripts/audit_segmented.py` con sincronización broker-repo (FIXED)
    - [x] Ejecutar auditorías focalizadas:
        - [x] Sem 1: Reset arquitectónico por NFP (OK)
        - [x] Sem 2: Actividad intensa (+182.83 EUR profit, 14 ciclos) (OK)
        - [x] Sem 3: Supervivencia absoluta al SNB Crash (OK)
        - [x] Sem 4: Normalización post-crash y gestión de deuda residual (OK: +1000.89 Profit)
    - [x] Resolver misterio del "parón" del tick 816 e inactividad aparente.

- [x] **FASE 11: Corrección de Errores Lógicos Críticos (Escenarios)**
    - [x] Probar bypass de L3 Guard con escenario `proof_l3_bypass.csv` (Bug Confirmado)
    - [x] Identificar leak de registro en `_open_recovery_cycle` (Bug Confirmado)
    - [x] Implementar blind-gap validation antes de sync de operaciones
    - [x] Validar solución con los mismos escenarios sintéticos

- [x] **FASE 12: Refactor de Fidelidad (Arquitectura y Metadatos)**
    - [x] Auditar `TradingService.close_operation` vs `debug_reference.md` (Gap Identificado)
    - [x] Auditar `CycleAccounting` FIFO 20/40 (Válido)
    - [x] Sincronizar metadatos de cierre en toda la cadena de ejecución
    - [x] Estandarizar terminología de logs según la página 156-166 de la "Biblia"
    - [x] Validar con escenario `c01_tp_simple_buy.csv` (No más "manual" closures)

- [x] **FASE 9: Auditoría Masiva de Escenarios (300+ archivos)**
    - [x] Ejecutar auditoría sobre logic/factorial y generar resumen (100% OK)
    - [x] Auditoría Microscópica "Uno por Uno" (Validación Matemática Profunda)
        - [x] Escenario R02 Perfect: Fuga de Overlap corregida y verificada
        - [x] Escenario R03 Gap: Math OK (+14.50 EUR exactos)
        - [x] Escenario H01: Hedge Lock OK (12 pips exactos)
        - [x] Escenario R03 Cascading: Atomic Units OK (Debt stays whole)
        - [x] Escenario R02 Holy Grail: Open Profit vs Debt OK
        - [x] Escenario F01/F03: Verificada creación de ciclos y distancias
    - [x] Auditoría Final: Año 2015 Completo (Full Parquet)
  - [x] Habilitar logs de "prueba de control" en `scenario_verifier.py`
  - [x] Verificar categorías core: `c`, `cy`, `h`, `r`
  - [x] Verificar categorías auxiliares: `j` (JPY), `mm` (Money), `rm` (Risk), `f` (FIFO)
  - [x] Generar reporte final de "Prueba de Orquestación"

- [ ] **Análisis Comparativo 2015 (EURUSD)**
  - [x] Identificar causa del drain masivo (Gap de 93.5 pips - 6 Marzo 2015)
  - [x] Deducir impacto de "Masa Crítica de Recoveries" (500+ ciclos activos)
  - [/] Ejecutar Baseline (Layer 1 OFF) -> 25% completado
  - [ ] Ejecutar Comparativa con Layer 1 (Adaptive Trailing)
  - [x] Documentar estrategias de mitigación (L2 y L3)

- [ ] **Evolución: Sistema Inmune L2 y L3**
  - [x] Documentar Layer 2 (Event Guard) en `immune_system_layers_2_3.md`
  - [x] Documentar Layer 3 (Blind Gap Guard)
  - [ ] Planificar implementación de Calendario de Eventos (NFP/FED)
  - [ ] Diseñar motor de Órdenes Virtuales (Market Execution)
