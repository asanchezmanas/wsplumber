# Audit: Current Implementation Logs (Real)

Este documento refleja los logs que el código ACTUAL está configurado para emitir.

## 1. Ciclo Principal (Main Cycle)

### 1.1. Apertura de Ciclo
- `INFO`: "Signal received" -> `data: {type: open_cycle, pair: ...}` (En `_process_tick_for_pair`) [Ambiguo: no indica razón]
- `INFO`: "Placing order" -> `operation_id: CYC_..._B, pair: ...` (En `TradingService.open_operation`)
- `INFO`: "New dual cycle opened" -> `cycle_id: CYC_..., pair: ...` (En `_open_new_cycle`)

### 1.2. Activación de Operación y Hedge
- `INFO`: "First operation activated, transitioning cycle to ACTIVE" (En `_check_operations_status`)
- `INFO`: "Both main operations active, transitioning cycle to HEDGED" (En `_check_operations_status`)
- `INFO`: "Placing order" -> `operation_id: CYC_..._H_...` (En `TradingService.open_operation`)

### 1.3. Take Profit de Ciclo Principal
- `INFO`: "Notifying strategy about operation closure" -> `op_id: ..., ticket: ...`
- `INFO`: "Cancelling counter-order" -> `op_id: ..., cycle_id: ...`
- `INFO`: "Cycle closed successfully" (En `_close_cycle_operations`)
- `INFO`: "Signal received" -> `data: {type: open_cycle, ...}` (Auto-renovación detectada)

---

## 2. Flujo de Recovery (FIFO)

### 2.1. Activación de Hedge Real (Neutralización)
- No hay un log explícito indicando "Hedge order activated" con ese nombre, pero se ve por "Notifying strategy about operation closure" si el hedge se cierra, o por la sincronización.
- `INFO`: "Main operations neutralized" -> No existe este log literal, la neutralización es silenciosa en la entidad.

### 2.2. Inicio de Recovery
- `INFO`: "Opening recovery level 1" (En `_open_recovery_cycle`)
- `INFO`: "Placing order" -> `operation_id: REC_...`

### 2.3. Cierre de Recovery por TP
- `INFO`: "Recovery TP hit, applying FIFO logic" (En `_handle_recovery_tp`)
- `INFO`: "FIFO: Closing recovery debt" -> `closed_rec_id: ..., cost: ..., remaining_pips: ...`
- `INFO`: "Cycle FULLY RECOVERED! Closing" (Al final de `_handle_recovery_tp`)
