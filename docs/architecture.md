# Arquitectura del Sistema

## Visión General

WSPlumber sigue una arquitectura de **capas limpias** (Clean Architecture) con separación clara entre dominio, aplicación e infraestructura.

## Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  FastAPI App  │  Dashboard HTML  │  WebSocket  │  StateBroadcaster   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION                                     │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌────────────────────┐  │
│  │   CycleOrchestrator   │  │    RiskManager    │  │   HistoryService   │  │
│  │  - Gestión de ciclos  │  │  - Control riesgo │  │  - Ingesta datos   │  │
│  │  - Coordinación ops   │  │  - Max drawdown   │  │  - Agregación      │  │
│  └───────────────────────┘  └───────────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                DOMAIN                                        │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐  │
│  │     Cycle      │  │   Operation    │  │       RecoveryState          │  │
│  │  - id, pair    │  │  - ticket      │  │  - level (1-6)               │  │
│  │  - state       │  │  - type, pnl   │  │  - blocked_pips              │  │
│  │  - operations  │  │  - status      │  │  - recovered_pips            │  │
│  └────────────────┘  └────────────────┘  └──────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         INTERFACES (Ports)                            │   │
│  │   IBroker  │  IRepository  │  INotifier  │  IAnalytics               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            INFRASTRUCTURE                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐  │
│  │   MT5Broker    │  │ SupabaseRepo   │  │       InMemoryRepo           │  │
│  │  - API MT5     │  │  - PostgreSQL  │  │  - Testing/Dev               │  │
│  │  - Órdenes     │  │  - RLS         │  │  - Sin dependencias          │  │
│  └────────────────┘  └────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Flujo de Datos

### 1. Flujo de Trading (Core)

```
MT5 Terminal
     │
     ▼ (ticks, precios)
┌─────────────┐
│  MT5Broker  │──────────────────────────────────────┐
└─────────────┘                                       │
     │                                                │
     ▼ (señal de entrada)                            │
┌─────────────────────┐                               │
│  CycleOrchestrator  │◀──────────────────────────────┤
│  - Evalúa ciclos    │                               │
│  - Gestiona recovery│     ┌─────────────┐          │
└─────────────────────┘     │ RiskManager │──────────┤
     │                      │ (validación)│          │
     ▼ (orden)              └─────────────┘          │
┌─────────────┐                                       │
│  MT5Broker  │◀──────────────────────────────────────┘
│  (ejecutar) │
└─────────────┘
     │
     ▼ (confirmación)
┌─────────────────┐
│  Repository     │──▶ Supabase (persistencia)
└─────────────────┘
```

### 2. Flujo del Dashboard

```
┌─────────────────────┐
│  CycleOrchestrator  │
│  (emite eventos)    │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  StateBroadcaster   │──▶ Calcula métricas agregadas
└─────────────────────┘
          │
          ▼ (WebSocket)
┌─────────────────────┐
│  Dashboard (HTML)   │──▶ Actualiza gauges, tablas, gráficos
└─────────────────────┘
```

---

## Entidades del Dominio

### Cycle

Representa un ciclo completo de trading para un par.

| Campo            | Tipo            | Descripción                          |
| ---------------- | --------------- | ------------------------------------ |
| `id`             | UUID            | Identificador único                  |
| `pair`           | str             | Par de divisas (EURUSD)              |
| `state`          | CycleState      | ACTIVE, RECOVERY, COMPLETED, BLOCKED |
| `operations`     | List[Operation] | Operaciones del ciclo                |
| `recovery_state` | RecoveryState   | Estado de recovery si aplica         |

### Operation

Representa una operación individual.

| Campo         | Tipo            | Descripción                           |
| ------------- | --------------- | ------------------------------------- |
| `ticket`      | int             | Ticket de MT5                         |
| `type`        | OperationType   | MAIN_BUY, MAIN_SELL, RECOVERY_1, etc. |
| `status`      | OperationStatus | PENDING, OPEN, CLOSED                 |
| `entry_price` | float           | Precio de entrada                     |
| `pnl`         | float           | Beneficio/pérdida                     |

### RecoveryState

Estado de recuperación de un ciclo.

| Campo            | Tipo  | Descripción            |
| ---------------- | ----- | ---------------------- |
| `level`          | int   | Nivel 1-6              |
| `blocked_pips`   | float | Pips bloqueados por SL |
| `recovered_pips` | float | Pips recuperados       |

---

## Patrones Utilizados

| Patrón                   | Uso                                   |
| ------------------------ | ------------------------------------- |
| **Repository**           | Abstracción de persistencia           |
| **Strategy**             | Lógica de trading intercambiable      |
| **Observer**             | Eventos de estado para dashboard      |
| **Dependency Injection** | Configuración flexible de componentes |
| **Factory**              | Creación de entidades complejas       |

---

## Módulos Principales

| Módulo                                        | Responsabilidad               |
| --------------------------------------------- | ----------------------------- |
| `core/strategy.py`                            | Lógica de decisión de trading |
| `core/risk/risk_manager.py`                   | Gestión de riesgo y límites   |
| `application/orchestrator.py`                 | Coordinación de ciclos        |
| `infrastructure/brokers/mt5_broker.py`        | Conexión con MetaTrader 5     |
| `infrastructure/persistence/supabase_repo.py` | Persistencia en Supabase      |
| `api/routers/websocket.py`                    | Comunicación en tiempo real   |
