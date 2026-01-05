# Configuración

## Variables de Entorno

Todas las configuraciones se manejan mediante variables de entorno. Copia `.env.example` a `.env` y ajusta los valores.

---

## MetaTrader 5

| Variable       | Requerida | Default     | Descripción             |
| -------------- | --------- | ----------- | ----------------------- |
| `MT5_LOGIN`    | ✅         | -           | Número de cuenta MT5    |
| `MT5_PASSWORD` | ✅         | -           | Contraseña de la cuenta |
| `MT5_SERVER`   | ✅         | -           | Servidor del broker     |
| `MT5_PATH`     | ❌         | Auto-detect | Ruta al terminal64.exe  |

```env
MT5_LOGIN=12345678
MT5_PASSWORD=tu_password
MT5_SERVER=ICMarkets-Demo
```

---

## Supabase

| Variable       | Requerida | Default | Descripción        |
| -------------- | --------- | ------- | ------------------ |
| `SUPABASE_URL` | ❌         | -       | URL del proyecto   |
| `SUPABASE_KEY` | ❌         | -       | Anon key (público) |

Si no se configura Supabase, el sistema usa `InMemoryRepository` (sin persistencia).

---

## Parámetros de Trading

| Variable        | Default              | Descripción                  |
| --------------- | -------------------- | ---------------------------- |
| `TP_PIPS`       | 10                   | Take Profit en pips          |
| `SL_PIPS`       | 50                   | Stop Loss inicial en pips    |
| `LOT_SIZE`      | 0.01                 | Tamaño de lote base          |
| `MAX_CYCLES`    | 10                   | Máximo de ciclos simultáneos |
| `ALLOWED_PAIRS` | EURUSD,GBPUSD,USDJPY | Pares operables              |

```env
TP_PIPS=10
SL_PIPS=50
LOT_SIZE=0.01
MAX_CYCLES=10
ALLOWED_PAIRS=EURUSD,GBPUSD,USDJPY,AUDUSD
```

---

## Gestión de Riesgo

| Variable               | Default | Descripción                   |
| ---------------------- | ------- | ----------------------------- |
| `MAX_DRAWDOWN_PERCENT` | 10      | Drawdown máximo permitido (%) |
| `MAX_DAILY_LOSS`       | 100     | Pérdida diaria máxima (€)     |
| `MAX_EXPOSURE_LOTS`    | 5.0     | Exposición máxima total       |
| `RECOVERY_MAX_LEVEL`   | 6       | Nivel máximo de recovery      |

```env
MAX_DRAWDOWN_PERCENT=10
MAX_DAILY_LOSS=100.0
MAX_EXPOSURE_LOTS=5.0
RECOVERY_MAX_LEVEL=6
```

---

## API y Dashboard

| Variable       | Default | Descripción         |
| -------------- | ------- | ------------------- |
| `API_HOST`     | 0.0.0.0 | Host del servidor   |
| `API_PORT`     | 8000    | Puerto del servidor |
| `DEBUG`        | false   | Modo debug          |
| `CORS_ORIGINS` | *       | Orígenes permitidos |

```env
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

---

## Logging

| Variable     | Default            | Descripción                                |
| ------------ | ------------------ | ------------------------------------------ |
| `LOG_LEVEL`  | INFO               | Nivel de log (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE`   | logs/wsplumber.log | Archivo de logs                            |
| `LOG_FORMAT` | standard           | Formato (standard, json)                   |

```env
LOG_LEVEL=INFO
LOG_FILE=logs/wsplumber.log
```

---

## Configuración Programática

También puedes configurar el sistema en código:

```python
from wsplumber.core.config import TradingConfig, RiskConfig

trading_config = TradingConfig(
    tp_pips=10,
    sl_pips=50,
    lot_size=0.01,
    allowed_pairs=["EURUSD", "GBPUSD"]
)

risk_config = RiskConfig(
    max_drawdown_percent=10.0,
    max_daily_loss=100.0,
    max_exposure_lots=5.0
)
```

---

## Perfiles de Configuración

### Desarrollo
```env
DEBUG=true
LOG_LEVEL=DEBUG
# Sin Supabase (usa InMemoryRepo)
```

### Testing
```env
DEBUG=true
LOG_LEVEL=DEBUG
MT5_LOGIN=demo_account
```

### Producción
```env
DEBUG=false
LOG_LEVEL=INFO
MAX_DRAWDOWN_PERCENT=5
MAX_DAILY_LOSS=50
```
