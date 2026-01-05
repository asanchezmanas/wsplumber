# 💧 El Fontanero de Wall Street

> *"Mientras los grandes jugadores mueven millones de un contenedor a otro, las gotas siempre caen. Nosotros no competimos por el contenedor, simplemente ponemos el cubo debajo."*

Sistema de trading automatizado basado en coberturas y recuperaciones.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                         API (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│                      APPLICATION LAYER                      │
│              Use Cases, Services, Orchestration             │
├─────────────────────────────────────────────────────────────┤
│                       DOMAIN LAYER                          │
│           Entities, Value Objects, Interfaces               │
├─────────────────────────────────────────────────────────────┤
│                    💎 CORE (Protected)                      │
│              Strategy, Signals, Risk (Compiled)             │
├─────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                      │
│        Brokers, Persistence, Resilience, Logging           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Clonar y configurar

```bash
git clone https://github.com/tu-usuario/fontanero.git
cd fontanero

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -e ".[dev]"
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Configurar Supabase

1. Crear cuenta en [supabase.com](https://supabase.com)
2. Crear nuevo proyecto
3. Ir a SQL Editor
4. Ejecutar `scripts/supabase_schema.sql`
5. Copiar URL y keys a `.env`

### 4. Verificar configuración

```bash
python scripts/test_connection.py
```

### 5. Ejecutar tests

```bash
pytest tests/ -v
```

## 📁 Estructura del Proyecto

```
fontanero/
├── src/fontanero/
│   ├── core/                  # 💎 SECRETO - Lógica de estrategia
│   │   ├── strategy/          # Motor de decisiones
│   │   ├── signals/           # Generación de señales
│   │   └── risk/              # Gestión de riesgo
│   │
│   ├── domain/                # Entidades y reglas de negocio
│   │   ├── entities/          # Operation, Cycle
│   │   ├── value_objects/     # Price, Pips, Money
│   │   ├── events/            # Eventos de dominio
│   │   └── interfaces/        # Ports (contratos)
│   │
│   ├── application/           # Casos de uso
│   │   ├── use_cases/         # Operaciones de negocio
│   │   ├── services/          # Servicios de aplicación
│   │   └── dto/               # Data Transfer Objects
│   │
│   ├── infrastructure/        # Adaptadores externos
│   │   ├── brokers/           # MT5, Darwinex
│   │   ├── persistence/       # Supabase
│   │   ├── resilience/        # Retry, Circuit Breaker
│   │   └── logging/           # Safe Logger
│   │
│   ├── api/                   # FastAPI
│   │   ├── routers/           # Endpoints
│   │   └── websockets/        # Real-time
│   │
│   ├── backtesting/           # Motor de backtest
│   └── config/                # Configuración
│
├── tests/                     # Tests
├── scripts/                   # Scripts útiles
├── docs/                      # Documentación
└── config/                    # Archivos de configuración
```

## 🔧 Configuración

### Variables de Entorno

| Variable           | Descripción                    | Requerida     |
| ------------------ | ------------------------------ | ------------- |
| `SUPABASE_URL`     | URL de tu proyecto Supabase    | ✅             |
| `SUPABASE_KEY`     | Anon key de Supabase           | ✅             |
| `MT5_LOGIN`        | Login de MetaTrader 5          | Para MT5      |
| `MT5_PASSWORD`     | Password de MT5                | Para MT5      |
| `MT5_SERVER`       | Servidor del broker            | Para MT5      |
| `DARWINEX_API_KEY` | API key de Darwinex            | Para Darwinex |
| `ENVIRONMENT`      | development/staging/production | ✅             |

### Configuración por Par

Cada par tiene su configuración optimizada en `config/settings.py`:

```python
EURUSD:
  tp_main_pips: 10
  tp_recovery_pips: 80
  max_spread_pips: 1.5

GBPUSD:
  tp_main_pips: 12
  tp_recovery_pips: 85
  max_spread_pips: 2.0
```

## 🛡️ Sistema de Robustez

El sistema implementa múltiples capas de protección:

| Capa             | Componentes                     |
| ---------------- | ------------------------------- |
| **Prevención**   | Rate Limiter, Spread Controller |
| **Detección**    | Health Monitor, Watchdog        |
| **Contención**   | Circuit Breaker, Timeouts       |
| **Recuperación** | Retry Manager, Auto Reconnect   |
| **Consistencia** | Outbox Pattern, Checkpoints     |

## 📊 API Endpoints

```
POST   /api/v1/cycles          # Crear ciclo
GET    /api/v1/cycles          # Listar ciclos
GET    /api/v1/cycles/{id}     # Detalle ciclo
POST   /api/v1/cycles/{id}/pause

GET    /api/v1/operations      # Listar operaciones
GET    /api/v1/metrics/daily   # Métricas diarias
GET    /api/v1/health          # Health check

WS     /ws/realtime            # Updates en tiempo real
```

## 🧪 Testing

```bash
# Tests unitarios
pytest tests/unit -v

# Tests de integración
pytest tests/integration -v

# Tests de backtest
pytest tests/backtest -v

# Coverage
pytest --cov=src/fontanero tests/
```

## 📈 Backtest

```bash
# Ejecutar backtest
python -m fontanero.backtesting.cli --pair EURUSD --start 2020-01-01 --end 2024-12-31

# Con configuración custom
python -m fontanero.backtesting.cli --config config/backtest_eurusd.yaml
```

## 🔒 Seguridad

- **Core protegido**: La lógica de estrategia está en `/core/` y se compila con Cython
- **Logs sanitizados**: Información sensible se enmascara automáticamente
- **Terminología pública**: Los logs usan términos que no revelan la estrategia

## 📝 Logging

Los logs usan terminología pública para proteger la estrategia:

| Término Interno | Término Público  |
| --------------- | ---------------- |
| cycle           | position_group   |
| recovery        | correction       |
| hedge           | balance_position |
| neutralize      | offset           |

## 🚧 Roadmap

- [x] Fase 0: Setup inicial
- [ ] Fase 1: Backtest básico
- [ ] Fase 2: Backtest completo
- [ ] Fase 3: Core de trading
- [ ] Fase 4: API y monitoreo
- [ ] Fase 5: Paper trading
- [ ] Fase 6: Producción

## ⚠️ Disclaimer

Este software es para uso educativo y de investigación. El trading de divisas conlleva riesgos significativos. No inviertas dinero que no puedas permitirte perder.

## 📄 Licencia

Propietaria - Todos los derechos reservados.

---

*"Gota a gota, se llena el cubo"* 💧