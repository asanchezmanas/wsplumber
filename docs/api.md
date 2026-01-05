# API Reference

## Base URL

```
http://localhost:8000
```

---

## REST Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "2h 34m",
  "mt5_connected": true
}
```

---

### Dashboard

```http
GET /
```

Retorna la página HTML del dashboard.

---

### Métricas Actuales

```http
GET /api/metrics
```

**Response:**
```json
{
  "balance": 10543.25,
  "equity": 10511.15,
  "floating_pnl": -32.10,
  "margin_used": 450.00,
  "margin_free": 10061.15,
  "total_pips": 245,
  "open_cycles": 5,
  "recovery_cycles": 3
}
```

---

### Ciclos

```http
GET /api/cycles
```

**Response:**
```json
{
  "cycles": [
    {
      "id": "uuid",
      "pair": "EURUSD",
      "state": "ACTIVE",
      "operations_count": 3,
      "total_pnl": 25.50
    }
  ]
}
```

```http
GET /api/cycles/{cycle_id}
```

**Response:**
```json
{
  "id": "uuid",
  "pair": "EURUSD",
  "state": "ACTIVE",
  "created_at": "2024-01-05T10:00:00Z",
  "operations": [
    {
      "ticket": 12345,
      "type": "MAIN_BUY",
      "status": "CLOSED",
      "pnl": 8.50
    }
  ],
  "recovery_state": null
}
```

---

### Operaciones

```http
GET /api/operations
```

Query params:
- `status`: PENDING, OPEN, CLOSED
- `pair`: EURUSD, GBPUSD, etc.
- `limit`: número (default 50)

**Response:**
```json
{
  "operations": [
    {
      "ticket": 12345,
      "pair": "EURUSD",
      "type": "MAIN_BUY",
      "status": "OPEN",
      "entry_price": 1.0854,
      "current_price": 1.0862,
      "pnl": 8.00,
      "opened_at": "2024-01-05T14:30:00Z"
    }
  ]
}
```

---

## WebSocket

### Conexión

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### Mensajes del Servidor

#### Estado Inicial

```json
{
  "type": "initial_state",
  "data": {
    "balance": 10543.25,
    "pips_total": 245,
    "exposure_lots": 2.5,
    "recovery_pips": -120,
    "cycles": [...],
    "operations": [...]
  }
}
```

#### Actualización de Métricas

```json
{
  "type": "metrics_update",
  "data": {
    "balance": 10551.75,
    "equity": 10519.65,
    "floating_pnl": -32.10,
    "timestamp": "2024-01-05T14:32:15Z"
  }
}
```

#### Evento de Operación

```json
{
  "type": "operation_event",
  "data": {
    "event": "TP_HIT",
    "ticket": 12345,
    "pair": "EURUSD",
    "pnl": 10.00,
    "message": "TP alcanzado EURUSD +10 pips"
  }
}
```

#### Tipos de Eventos

| Tipo                | Descripción             |
| ------------------- | ----------------------- |
| `TRADE_OPEN`        | Nueva operación abierta |
| `TRADE_CLOSE`       | Operación cerrada       |
| `TP_HIT`            | Take Profit alcanzado   |
| `SL_HIT`            | Stop Loss alcanzado     |
| `RECOVERY_START`    | Ciclo entra en recovery |
| `RECOVERY_COMPLETE` | Recovery completado     |
| `CYCLE_OPEN`        | Nuevo ciclo iniciado    |
| `CYCLE_CLOSE`       | Ciclo cerrado           |

---

## Autenticación

Actualmente la API no requiere autenticación. Para producción, configura:

```env
API_AUTH_ENABLED=true
API_TOKEN=tu_token_secreto
```

Headers requeridos:
```http
Authorization: Bearer tu_token_secreto
```

---

## Rate Limits

| Endpoint  | Límite      |
| --------- | ----------- |
| REST API  | 100 req/min |
| WebSocket | Sin límite  |

---

## Códigos de Error

| Código | Significado           |
| ------ | --------------------- |
| 200    | OK                    |
| 400    | Bad Request           |
| 401    | Unauthorized          |
| 404    | Not Found             |
| 500    | Internal Server Error |
| 503    | MT5 Disconnected      |
