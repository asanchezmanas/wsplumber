# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [Unreleased]

### Added
- Dashboard V3 con estética light moderna
- Documentación completa del repositorio
- Plan de despliegue en VPS Windows (Fase 5)
- Plan de pipeline de datos en background

### Changed
- Migración de dashboard V2 (glassmorphism) a V3 (light clean)
- Actualizado mapeo de secciones para contexto de trading

---

## [0.4.0] - 2024-01-05

### Added
- Fase 4: Ingesta de datos históricos
- `HistoryService` para orquestar ingesta MT5 → Supabase
- Script `csv_to_parquet.py` para conversión de tick data
- Script `test_ingestion.py` para pruebas de ingesta
- Métodos `get_historical_rates` y `get_historical_ticks` en `IBroker`
- Métodos `save_historical_rates` y `save_historical_ticks` en `IRepository`
- Nuevo proyecto Supabase `wsplumber-core` con esquema dedicado

### Changed
- Actualizado `.env` con credenciales de Supabase
- Documentación de arquitectura híbrida (Parquet + Supabase)

---

## [0.3.0] - 2024-01-04

### Added
- Fase 3: API y Dashboard
- Dashboard V2 con estética Dark Glassmorphism
- `StateBroadcaster` para métricas en tiempo real
- WebSocket router para actualizaciones en vivo
- `dashboard.js` para conexión WebSocket y actualización de UI
- Integración del broadcaster con `CycleOrchestrator`

### Changed
- Layout del dashboard: 3 columnas (sidebar, main, widgets)
- Gauges circulares para métricas principales

---

## [0.2.0] - 2024-01-03

### Added
- Fase 2: Operativa Normal
- `CycleOrchestrator` para gestión de ciclos
- `RiskManager` con límites de drawdown y exposición
- `RecoveryState` para tracking de recuperación
- `MT5Broker` con conexión a MetaTrader 5
- `SupabaseRepository` para persistencia

### Changed
- Refactor de entidades del dominio
- Implementación de interfaces (ports)

---

## [0.1.0] - 2024-01-01

### Added
- Estructura inicial del proyecto
- Configuración de entorno virtual
- FastAPI base
- Entidades core: `Cycle`, `Operation`
- Arquitectura de capas definida

---

## Formato de Versiones

- **MAJOR**: Cambios incompatibles con versiones anteriores
- **MINOR**: Nueva funcionalidad compatible
- **PATCH**: Correcciones de bugs
