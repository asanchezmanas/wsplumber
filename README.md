# 🔧 WSPlumber - El Fontanero de Wall Street

> Sistema de trading automatizado con estrategia de recuperación inteligente.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![MT5](https://img.shields.io/badge/MetaTrader-5-orange.svg)](https://www.metatrader5.com)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#license)

---

## 📋 Descripción

WSPlumber es un bot de trading automatizado que opera en Forex con una estrategia basada en **ciclos de operaciones** y un sistema de **recuperación progresiva** cuando el mercado va en contra.

### Características Principales

- 🔄 **Ciclos de Trading**: Secuencias de operaciones con TPs de 10 pips
- 🛡️ **Recovery System**: Recuperación progresiva de pips perdidos
- 📊 **Dashboard en Tiempo Real**: Visualización de métricas y operaciones
- 🔌 **WebSocket**: Actualizaciones en vivo sin recargar
- 💾 **Persistencia Híbrida**: Supabase + Parquet para datos históricos

---

## 🚀 Instalación Rápida

### Requisitos Previos

- Python 3.11+
- MetaTrader 5 instalado
- Cuenta de broker compatible con MT5

### Pasos

```powershell
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/wsplumber.git
cd wsplumber

# 2. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales

# 5. Ejecutar
python -m wsplumber.main
```

---

## ⚙️ Configuración

Copia `.env.example` a `.env` y configura:

```env
# MetaTrader 5
MT5_LOGIN=tu_numero_cuenta
MT5_PASSWORD=tu_password
MT5_SERVER=nombre_servidor_broker

# Supabase (opcional)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=tu_anon_key
```

Ver [docs/configuration.md](docs/configuration.md) para opciones avanzadas.

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Cycle     │  │  Operation  │  │   RecoveryState     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           ▲
                           │
┌──────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                        │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │  CycleOrchestrator  │  │        RiskManager           │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           ▲
                           │
┌──────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  MT5Broker   │  │ SupabaseRepo │  │  FastAPI + WS    │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Ver [docs/architecture.md](docs/architecture.md) para diagramas detallados.

---

## 📊 Dashboard

Accede al dashboard en `http://localhost:8000` después de iniciar el sistema.

![Dashboard Preview](docs/assets/dashboard_preview.png)

### Funcionalidades

- **Gauges**: Balance, Pips, Exposición, Recovery pendiente
- **Gráfico de Equity**: Curva de rendimiento histórico
- **Tabla de Operaciones**: Ciclos activos y en recovery
- **Alertas en Tiempo Real**: Notificaciones de eventos

---

## 📁 Estructura del Proyecto

```
wsplumber/
├── src/wsplumber/
│   ├── core/               # Estrategia y lógica de negocio
│   ├── domain/             # Entidades y interfaces
│   ├── application/        # Orquestador y servicios
│   ├── infrastructure/     # Brokers, repos, API
│   └── api/                # FastAPI + Dashboard
├── scripts/                # Utilidades (CSV→Parquet, ingesta)
├── tests/                  # Tests unitarios e integración
├── docs/                   # Documentación adicional
└── data/                   # Datos históricos (Parquet)
```

---

## 🧪 Testing

```powershell
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=src/wsplumber

# Solo tests unitarios
pytest tests/unit/
```

---

## 📚 Documentación

| Documento                              | Descripción           |
| -------------------------------------- | --------------------- |
| [Arquitectura](docs/architecture.md)   | Diseño del sistema    |
| [Configuración](docs/configuration.md) | Parámetros y opciones |
| [Despliegue](docs/deployment.md)       | VPS y producción      |
| [API Reference](docs/api.md)           | Endpoints y WebSocket |

---

## 🔒 Seguridad

- Las credenciales de MT5 **nunca** se suben al repositorio
- Usa `.env` para variables sensibles
- Row Level Security (RLS) habilitado en Supabase
- Módulos core protegidos con Cython (opcional)

---

## 📄 License

Este proyecto es **software propietario**. No está permitida su redistribución sin autorización expresa.

---

## 👤 Autor

**El Fontanero de Wall Street** - Trading automatizado desde 2024.

---

## 🤝 Contribuciones

Este es un proyecto personal. Si tienes sugerencias, abre un Issue.