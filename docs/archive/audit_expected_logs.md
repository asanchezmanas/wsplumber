# Audit: Expected Logs Specification (Theoretical)

Este documento define la secuencia lógica ideal de logs que el sistema DEBE emitir según el diseño del Documento Madre.

## 1. Ciclo Principal (Main Cycle)

### 1.1. Apertura de Ciclo
- `INFO`: "Signal received" -> `data: {type: OPEN_CYCLE, reason: no_active_cycle}`
- `INFO`: "Placing order" -> `operation_id: CYC_..._B`
- `INFO`: "Placing order" -> `operation_id: CYC_..._S`
- `INFO`: "New dual cycle opened" -> `cycle_id: CYC_...`

### 1.2. Activación de Operación y Colocación de Hedge (Limit)
- `INFO`: "Operation activated" -> `op_type: MAIN_BUY` (o SELL)
- `INFO`: "Operation activated" -> `op_type: MAIN_SELL` (o BUY)
- `INFO`: "Cycle transitioned to HEDGED"
- `INFO`: "Placing hedge orders" -> `limit_buy_at: ..., limit_sell_at: ...`

### 1.3. Take Profit de Ciclo Principal
- `INFO`: "Operation closed with TP" -> `op_type: MAIN_BUY` (o SELL)
- `INFO`: "Cycle closed successfully"
- `INFO`: "Cancelling counter pending order"
- `INFO`: "Signal received" -> `data: {type: OPEN_CYCLE, reason: tp_hit}` (Auto-renovación)

---

## 2. Flujo de Recovery (FIFO)

### 2.1. Activación de Hedge Real (Neutralización)
- `INFO`: "Hedge order activated" -> `op_type: HEDGE_BUY` (o SELL)
- `INFO`: "Main operations neutralized" -> `cycle_id: ...`
- `INFO`: "Calculated recovery debt" -> `cost_pips: 20`

### 2.2. Inicio de Recovery
- `INFO`: "Signal received" -> `data: {type: OPEN_RECOVERY, reason: neutralization}`
- `INFO`: "Opening recovery level 1"
- `INFO`: "Placing recovery order" -> `op_type: RECOVERY_BUY` (o SELL)

### 2.3. Cierre de Recovery por TP
- `INFO`: "Recovery TP hit" -> `level: 1`
- `INFO`: "Processing FIFO recovery closure"
- `INFO`: "Closed neutralized debt" -> `debt_index: 0, cost: 20`
- `INFO`: "Cycle fully recovered and closed"
