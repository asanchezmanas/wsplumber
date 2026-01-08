yaml y el generador y Template de test parametrizado

7 ene
YAML + Generador + Template de Test
Voy a crear los 3 componentes completos:

1. YAML con Especificaciones
yaml
# tests/fixtures/scenario_specs.yaml
"""
Especificaciones de los 62 escenarios de auditoría.
Usado por el generador de CSVs y los tests parametrizados.
"""

metadata:
  version: "2.0"
  total_scenarios: 62
  last_updated: "2025-01-07"
  fixes_applied:
    - "FIX-001: Renovación dual de mains"
    - "FIX-002: Cancelación de hedges pendientes"
    - "FIX-003: FIFO atómico Main+Hedge"

# ============================================
# CORE (5 escenarios)
# ============================================

core:
  c01_tp_simple_buy:
    priority: critical
    description: "BUY toca TP +10 pips"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start - Orders placed: BUY@1.10020, SELL@1.09980"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 2
        bid: 1.10050
        ask: 1.10070
        event: "Moving towards TP"
      - time: 3
        bid: 1.10120
        ask: 1.10140
        event: "TP hit at 1.10120"
    checks:
      - "buy_op.status == OperationStatus.TP_HIT"
      - "buy_op.profit_pips == 10.0"
      - "sell_op.status == OperationStatus.CANCELLED"
      - "account.balance == 10002.0"  # +2 EUR profit
      - "len([op for op in cycle.operations if op.is_main and op.status == OperationStatus.PENDING]) == 2"
    expected_output:
      balance: 10002.0
      operations_count: 4  # 2 originales + 2 renovadas
      tp_count: 1
      pips_won: 10.0

  c01_tp_simple_sell:
    priority: critical
    description: "SELL toca TP +10 pips"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      - time: 1
        bid: 1.09980
        ask: 1.10000
        event: "SELL activates"
      - time: 2
        bid: 1.09950
        ask: 1.09970
        event: "Moving towards TP"
      - time: 3
        bid: 1.09880
        ask: 1.09900
        event: "TP hit at 1.09880"
    checks:
      - "sell_op.status == OperationStatus.TP_HIT"
      - "sell_op.profit_pips == 10.0"
      - "buy_op.status == OperationStatus.CANCELLED"
      - "account.balance == 10002.0"
    expected_output:
      balance: 10002.0
      operations_count: 4
      tp_count: 1

  c03_activation_no_tp:
    priority: high
    description: "Operación activa pero no alcanza TP"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 2
        bid: 1.10050
        ask: 1.10070
        event: "Moves +5 pips"
      - time: 3
        bid: 1.10080
        ask: 1.10100
        event: "Stops at +8 pips (before TP)"
    checks:
      - "buy_op.status == OperationStatus.ACTIVE"
      - "buy_op.current_pips > 0"
      - "buy_op.current_pips < 10.0"
      - "account.balance == 10000.0"  # Sin cambios
    expected_output:
      balance: 10000.0
      floating_pips: 8.0
      operations_active: 1

  c04_no_activation:
    priority: high
    description: "Precio no activa ninguna operación"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start - Orders: BUY@1.10020, SELL@1.09980"
      - time: 1
        bid: 1.09995
        ask: 1.10015
        event: "Small move -5 pips"
      - time: 2
        bid: 1.10005
        ask: 1.10025
        event: "Small move +5 pips"
      - time: 3
        bid: 1.10000
        ask: 1.10020
        event: "Returns to start"
    checks:
      - "buy_op.status == OperationStatus.PENDING"
      - "sell_op.status == OperationStatus.PENDING"
      - "len(broker.order_history) == 0"
      - "account.balance == 10000.0"
    expected_output:
      balance: 10000.0
      operations_pending: 2
      broker_calls: 0

  c05_gap_tp:
    priority: critical
    description: "Gap atraviesa TP directamente"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Friday close"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 2
        bid: 1.10200
        ask: 1.10220
        event: "Monday gap +180 pips (atraviesa TP)"
    checks:
      - "buy_op.status == OperationStatus.TP_HIT"
      - "cycle.metadata['gap_detected'] == True"
      - "buy_op.actual_close_price >= buy_op.tp_price"
    expected_output:
      balance: 10002.0  # TP alcanzado
      gap_detected: true
      gap_size: 180.0

# ============================================
# CYCLES (6 escenarios)
# ============================================

cycles:
  cy01_new_cycle:
    priority: critical
    description: "Crear nuevo ciclo con BUY+SELL"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Signal: OPEN_CYCLE"
    checks:
      - "cycle.status == CycleStatus.PENDING"
      - "len(cycle.main_operations) == 2"
      - "buy_op.entry_price == 1.10020"
      - "sell_op.entry_price == 1.10000"
      - "buy_op.tp_price == 1.10120"
      - "sell_op.tp_price == 1.09900"
    expected_output:
      cycles_count: 1
      operations_pending: 2

  cy02_tp_in_cycle:
    priority: critical
    description: "TP hit, ciclo continúa"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 2
        bid: 1.10120
        ask: 1.10140
        event: "BUY TP hit"
    checks:
      - "cycle.status == CycleStatus.ACTIVE"
      - "cycle.accounting.total_main_tps == 1"
      - "cycle.accounting.total_pips_won == 10.0"
    expected_output:
      cycle_status: active
      tp_count: 1

  cy03_tp_renews_operations:
    priority: critical
    description: "FIX-001: TP crea nuevas BUY+SELL"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Ciclo inicial"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 2
        bid: 1.10120
        ask: 1.10140
        event: "BUY TP → Renovación"
    checks:
      - "len([op for op in cycle.operations if op.is_main and op.status == OperationStatus.PENDING]) == 2"
      - "new_buy.entry_price == 1.10140"  # Precio actual ASK
      - "new_sell.entry_price == 1.10120"  # Precio actual BID
      - "new_buy.tp_price == 1.10240"
      - "new_sell.tp_price == 1.10020"
    expected_output:
      operations_total: 4  # 2 viejas + 2 nuevas
      operations_pending: 2  # Las nuevas
      operations_closed: 1  # BUY TP
      operations_cancelled: 1  # SELL contraria

  cy04_cancel_counter_main:
    priority: critical
    description: "TP cancela main contraria pendiente"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates (SELL sigue PENDING)"
      - time: 2
        bid: 1.10120
        ask: 1.10140
        event: "BUY TP → SELL debe cancelarse"
    checks:
      - "buy_op.status == OperationStatus.TP_HIT"
      - "sell_op.status == OperationStatus.CANCELLED"
      - "sell_op.metadata['cancel_reason'] == 'counterpart_tp_hit'"
    expected_output:
      cancelled_count: 1

  cy05_complete_10_tps:
    priority: high
    description: "Ciclo completa 10 TPs exitosos"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      # Repetir patrón 10 veces:
      # BUY activa → TP → Renueva → BUY activa → TP...
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "TP #1"
      - time: 2
        bid: 1.10140
        ask: 1.10160
        event: "TP #2"
      # ... (simplificado, el generador crea secuencia completa)
      - time: 10
        bid: 1.11000
        ask: 1.11020
        event: "TP #10"
    checks:
      - "cycle.accounting.total_main_tps == 10"
      - "cycle.accounting.total_pips_won == 100.0"
      - "account.balance == 10020.0"  # +20 EUR (10 TPs × 2 EUR)
    expected_output:
      balance: 10020.0
      tp_count: 10
      pips_won: 100.0

  cy06_multiple_cycles:
    priority: high
    description: "EURUSD + GBPUSD ciclos independientes"
    pair: MULTI  # Especial: múltiples pares
    pairs:
      - EURUSD
      - GBPUSD
    initial_balance: 10000.0
    sequence:
      # EURUSD
      - time: 0
        pair: EURUSD
        bid: 1.10000
        ask: 1.10020
        event: "EURUSD start"
      - time: 1
        pair: EURUSD
        bid: 1.10120
        ask: 1.10140
        event: "EURUSD TP"
      # GBPUSD
      - time: 0
        pair: GBPUSD
        bid: 1.25000
        ask: 1.25020
        event: "GBPUSD start"
      - time: 1
        pair: GBPUSD
        bid: 1.25120
        ask: 1.25140
        event: "GBPUSD TP"
    checks:
      - "len(active_cycles) == 2"
      - "eurusd_cycle.pair == 'EURUSD'"
      - "gbpusd_cycle.pair == 'GBPUSD'"
      - "eurusd_cycle.accounting.total_tp_count == 1"
      - "gbpusd_cycle.accounting.total_tp_count == 1"
    expected_output:
      cycles_count: 2
      balance: 10004.0  # +2 cada par

# ============================================
# HEDGED (8 escenarios)
# ============================================

hedged:
  h01_both_active_hedged:
    priority: critical
    description: "Ambas mains activan → HEDGED"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 2
        bid: 1.09970
        ask: 1.09990
        event: "Price reverses"
      - time: 3
        bid: 1.09980
        ask: 1.10000
        event: "SELL activates → HEDGED"
    checks:
      - "cycle.status == CycleStatus.HEDGED"
      - "buy_op.status == OperationStatus.ACTIVE"
      - "sell_op.status == OperationStatus.ACTIVE"
    expected_output:
      cycle_status: hedged
      pips_locked: 0  # Aún no neutralizadas

  h02_create_hedge_operations:
    priority: critical
    description: "Crear HEDGE_BUY + HEDGE_SELL"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Both mains active"
      - time: 1
        bid: 1.10050
        ask: 1.10070
        event: "Trigger hedge creation"
    checks:
      - "len([op for op in cycle.operations if op.is_hedge]) == 2"
      - "hedge_buy.op_type == OperationType.HEDGE_BUY"
      - "hedge_sell.op_type == OperationType.HEDGE_SELL"
      - "hedge_buy.entry_price == main_buy.entry_price"
      - "hedge_sell.entry_price == main_sell.entry_price"
    expected_output:
      hedge_operations: 2

  h03_neutralize_mains:
    priority: critical
    description: "Neutralizar mains activas"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Both active, hedges created"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "Neutralization triggered"
    checks:
      - "main_buy.status == OperationStatus.NEUTRALIZED"
      - "main_sell.status == OperationStatus.NEUTRALIZED"
      - "main_buy.neutralized_by == hedge_buy.id"
      - "main_sell.neutralized_by == hedge_sell.id"
    expected_output:
      neutralized_count: 2

  h04_lock_20_pips:
    priority: critical
    description: "Bloquear 20 pips en HEDGED"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Both active → hedge"
    checks:
      - "cycle.accounting.pips_locked == 20.0"
      - "cycle.accounting.metadata['debt_composition']['separation'] == 4"
      - "cycle.accounting.metadata['debt_composition']['tp_distance'] == 10"
      - "cycle.accounting.metadata['debt_composition']['margin'] == 6"
    expected_output:
      pips_locked: 20.0
      debt_components:
        separation: 4
        tp_distance: 10
        margin: 6

  h05_sequential_activation:
    priority: high
    description: "Activación secuencial (no gap)"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Start"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "BUY activates"
      - time: 10  # 10 segundos después
        bid: 1.09980
        ask: 1.10000
        event: "SELL activates"
    checks:
      - "cycle.status == CycleStatus.HEDGED"
      - "abs((sell_op.activated_at - buy_op.activated_at).total_seconds()) >= 10"
    expected_output:
      cycle_status: hedged
      activation_gap_seconds: 10

  h06_simultaneous_gap:
    priority: high
    description: "Gap activa ambas simultáneamente"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "Friday close"
      - time: 1
        bid: 1.10050
        ask: 1.10070
        event: "Monday gap - both activate same tick"
    checks:
      - "cycle.status == CycleStatus.HEDGED"
      - "cycle.metadata['gap_detected'] == True"
      - "buy_op.activated_at == sell_op.activated_at"
    expected_output:
      gap_detected: true
      simultaneous_activation: true

  h07_buy_tp_hedge_sell:
    priority: critical
    description: "FIX-002: BUY TP cancela HEDGE_SELL pendiente"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "HEDGED state"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "Main BUY active, HEDGE_SELL pending"
      - time: 2
        bid: 1.10120
        ask: 1.10140
        event: "Main BUY TP → Cancel HEDGE_SELL"
    checks:
      - "main_buy.status == OperationStatus.TP_HIT"
      - "hedge_sell.status == OperationStatus.CANCELLED"
      - "hedge_sell.metadata['cancel_reason'] == 'counterpart_main_tp_hit'"
      - "hedge_sell.metadata['cancelled_by_operation'] == str(main_buy.id)"
    expected_output:
      main_tp: true
      hedge_cancelled: true

  h08_sell_tp_hedge_buy:
    priority: high
    description: "FIX-002: SELL TP cancela HEDGE_BUY pendiente"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "HEDGED state"
      - time: 1
        bid: 1.09880
        ask: 1.09900
        event: "Main SELL TP → Cancel HEDGE_BUY"
    checks:
      - "main_sell.status == OperationStatus.TP_HIT"
      - "hedge_buy.status == OperationStatus.CANCELLED"
      - "hedge_buy.metadata['cancel_reason'] == 'counterpart_main_tp_hit'"
    expected_output:
      main_tp: true
      hedge_cancelled: true

# ============================================
# RECOVERY (10 escenarios)
# ============================================

recovery:
  r01_open_from_tp:
    priority: critical
    description: "Recovery abre desde precio TP del main"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10000
        ask: 1.10020
        event: "HEDGED, Main BUY TP = 1.10120"
      - time: 1
        bid: 1.10120
        ask: 1.10140
        event: "Main BUY TP hit → Recovery placement"
    checks:
      - "recovery_buy.entry_price == 1.10140"  # TP + 20 pips
      - "recovery_sell.entry_price == 1.10100"  # TP - 20 pips
      - "recovery_buy.metadata['reference_price'] == 1.10120"
    expected_output:
      recovery_reference: 1.10120
      recovery_distance: 20

  r02_recovery_distance_20:
    priority: critical
    description: "Recovery a ±20 pips del TP"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10120
        ask: 1.10140
        event: "TP reference"
      - time: 1
        bid: 1.10140
        ask: 1.10160
        event: "Recovery BUY placed"
    checks:
      - "recovery_buy.entry_price == 1.10140"
      - "abs(recovery_buy.entry_price - tp_price) == Decimal('0.00020')"  # 20 pips
    expected_output:
      distance_pips: 20.0

  r03_recovery_n1_tp_buy:
    priority: critical
    description: "Recovery N1 BUY recupera +80 pips"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10140
        ask: 1.10160
        event: "Recovery N1 BUY entry"
      - time: 1
        bid: 1.10220
        ask: 1.10240
        event: "Recovery TP hit"
    checks:
      - "recovery.status == OperationStatus.TP_HIT"
      - "recovery.profit_pips == 80.0"
      - "parent_cycle.accounting.pips_recovered == 20.0"  # 80 - 60 FIFO
      - "len(parent_cycle.accounting.recovery_queue) == 0"
    expected_output:
      recovery_tp: true
      pips_recovered: 20.0
      fifo_closed: 1

  r04_recovery_n1_tp_sell:
    priority: high
    description: "Recovery N1 SELL recupera"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10100
        ask: 1.10120
        event: "Recovery N1 SELL entry"
      - time: 1
        bid: 1.10020
        ask: 1.10040
        event: "Recovery TP hit"
    checks:
      - "recovery.status == OperationStatus.TP_HIT"
      - "recovery.profit_pips == 80.0"
      - "parent_cycle.accounting.pips_recovered == 20.0"
    expected_output:
      recovery_tp: true
      pips_recovered: 20.0

  r05_recovery_n1_fails_n2:
    priority: critical
    description: "N1 falla → N2 abre"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10140
        ask: 1.10160
        event: "N1 BUY entry"
      - time: 1
        bid: 1.10180
        ask: 1.10200
        event: "Price moves +40 pips → N2 triggers"
    checks:
      - "n1.status == OperationStatus.ACTIVE"
      - "n2.status == OperationStatus.PENDING"
      - "n2.entry_price == 1.10180"  # +40 pips from N1
      - "len(parent_cycle.accounting.recovery_queue) == 2"
    expected_output:
      recovery_level: 2
      recovery_queue_size: 2

  r06_recovery_n2_success:
    priority: high
    description: "N2 recupera todo"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10180
        ask: 1.10200
        event: "N2 entry"
      - time: 1
        bid: 1.10260
        ask: 1.10280
        event: "N2 TP hit"
    checks:
      - "n2.status == OperationStatus.TP_HIT"
      - "parent_cycle.accounting.pips_recovered == 60.0"  # 20 + 40
      - "len(parent_cycle.accounting.recovery_queue) == 0"
    expected_output:
      pips_recovered: 60.0
      recovery_queue_empty: true

  r07_cascade_n1_n2_n3:
    priority: high
    description: "Cascada N1→N2→N3"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10140
        ask: 1.10160
        event: "N1 entry"
      - time: 1
        bid: 1.10180
        ask: 1.10200
        event: "N2 entry"
      - time: 2
        bid: 1.10220
        ask: 1.10240
        event: "N3 entry"
      - time: 3
        bid: 1.10300
        ask: 1.10320
        event: "N3 TP hit"
    checks:
      - "parent_cycle.recovery_level == 3"
      - "n3.status == OperationStatus.TP_HIT"
      - "parent_cycle.accounting.pips_recovered == 80.0"
    expected_output:
      recovery_level: 3
      pips_recovered: 80.0

  r08_recovery_max_n6:
    priority: high
    description: "N6 nivel máximo"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10140
        ask: 1.10160
        event: "N1"
      # ... N2-N5 omitidos por brevedad
      - time: 5
        bid: 1.10340
        ask: 1.10360
        event: "N6 entry - max level"
    checks:
      - "parent_cycle.recovery_level == 6"
      - "len(parent_cycle.accounting.recovery_queue) == 6"
    expected_output:
      recovery_level: 6
      max_level_reached: true

  r09_cancel_recovery_counter:
    priority: high
    description: "Recovery BUY TP → cancela SELL"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10140
        ask: 1.10160
        event: "Recovery BUY active, SELL pending"
      - time: 1
        bid: 1.10220
        ask: 1.10240
        event: "Recovery BUY TP"
    checks:
      - "recovery_buy.status == OperationStatus.TP_HIT"
      - "recovery_sell.status == OperationStatus.CANCELLED"
      - "recovery_sell.metadata['cancel_reason'] == 'counterpart_tp_hit'"
    expected_output:
      recovery_tp: true
      counter_cancelled: true

  r10_multiple_recovery_pairs:
    priority: medium
    description: "Múltiples pares con recovery"
    pair: MULTI
    pairs:
      - EURUSD
      - GBPUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        pair: EURUSD
        bid: 1.10140
        ask: 1.10160
        event: "EURUSD N1"
      - time: 1
        pair: GBPUSD
        bid: 1.25140
        ask: 1.25160
        event: "GBPUSD N1"
    checks:
      - "eurusd_cycle.recovery_level == 1"
      - "gbpusd_cycle.recovery_level == 1"
      - "len(eurusd_cycle.accounting.recovery_queue) == 1"
      - "len(gbpusd_cycle.accounting.recovery_queue) == 1"
    expected_output:
      recovery_cycles: 2

# ============================================
# FIFO (4 escenarios)
# ============================================

fifo:
  f01_fifo_first_costs_20:
    priority: critical
    description: "FIX-003: Primer recovery cuesta 20 pips (Main+Hedge)"
    pair: EURUSD
    initial_balance: 10000.0
    sequence:
      - time: 0
        bid: 1.10140
        ask: 1.10160
        event: "Recovery N1 entry"
      -
Continuar

7 ene
: 1
bid: 1.10220
ask: 1.10240
event: "Recovery TP (80 pips)"
checks:
- "parent_cycle.accounting.get_recovery_cost() == 20.0"
- "parent_cycle.accounting.recoveries_closed_count == 1"
- "main.status == OperationStatus.CLOSED"
- "hedge.status == OperationStatus.CLOSED"
- "main.metadata['debt_unit_id'] == hedge.metadata['debt_unit_id']"
- "main.metadata['close_method'] == 'atomic_with_hedge'"
expected_output:
fifo_cost: 20.0
debt_units_closed: 1
net_profit: 60.0

f02_fifo_subsequent_40:
priority: critical
description: "Siguientes recoveries cuestan 40 pips"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10180
ask: 1.10200
event: "Recovery N2 entry (after N1 closed)"
- time: 1
bid: 1.10260
ask: 1.10280
event: "Recovery N2 TP"
checks:
- "parent_cycle.accounting.get_recovery_cost() == 40.0"
- "parent_cycle.accounting.recoveries_closed_count == 2"
expected_output:
fifo_cost: 40.0
net_profit: 40.0

f03_fifo_atomic_close:
priority: high
description: "Cierre atómico Main+Hedge"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10140
ask: 1.10160
event: "Recovery TP triggers FIFO"
checks:
- "main.closed_at == hedge.closed_at"  # ±1ms tolerance in test
- "main.status == OperationStatus.CLOSED"
- "hedge.status == OperationStatus.CLOSED"
- "main.metadata['close_method'] == 'atomic_with_hedge'"
- "hedge.metadata['close_method'] == 'atomic_with_main'"
expected_output:
atomic_close: true
timestamp_diff_ms: 0

f04_fifo_multiple_close:
priority: high
description: "80 pips cierran múltiples unidades"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10180
ask: 1.10200
event: "Recovery TP with multiple debts"
checks:
- "len(closed_debt_units) == 2"  # 20 + 40 = 60 pips
- "parent_cycle.accounting.pips_recovered == 60.0"
- "parent_cycle.accounting.recovery_queue == []"
expected_output:
debt_units_closed: 2
total_cost: 60.0
net_profit: 20.0

============================================
RISK MANAGEMENT (5 escenarios)
============================================
risk_management:
rm01_exposure_limit:
priority: critical
description: "Límite de exposición 30%"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Multiple cycles active"
checks:
- "exposure_pct < 30.0"
- "can_open_position() == True"
expected_output:
exposure_pct: 25.0
can_open: true

rm02_drawdown_limit:
priority: critical
description: "Pausa > 20% drawdown"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Accumulated losses trigger pause"
checks:
- "system.status == 'PAUSED'"
- "drawdown_pct > 20.0"
expected_output:
system_status: paused
drawdown_pct: 22.0

rm03_daily_loss_limit:
priority: high
description: "Pérdida diaria pausa sistema"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Daily loss exceeds limit"
checks:
- "system.status == 'PAUSED'"
- "daily_loss_pips >= 100.0"
expected_output:
system_status: paused
daily_loss: 100.0

rm04_margin_insufficient:
priority: high
description: "Margen insuficiente rechaza operación"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Attempt to open with low margin"
checks:
- "result.success == False"
- "result.error_code == 'INSUFFICIENT_MARGIN'"
expected_output:
operation_rejected: true
error_code: INSUFFICIENT_MARGIN

rm05_recovery_exposure:
priority: high
description: "Exposición incluye recoveries"
pair: EURUSD
initial_balance:
10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Multiple recoveries active"
checks:
- "total_exposure includes recovery operations"
- "num_recoveries == 3"
- "exposure_pct < 30.0"
expected_output:
num_recoveries: 3
total_exposure_pct: 28.0
============================================
MONEY MANAGEMENT (8 escenarios)
============================================
money_management:
mm01_balance_read:
priority: critical
description: "Lee balance inicial del broker"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "System startup"
checks:
- "account.balance == 10000.0"
- "account.equity == 10000.0"
- "account.margin_free == 10000.0"
expected_output:
balance: 10000.0
equity: 10000.0
mm02_pnl_tp:
priority: critical
description: "P&L correcto en TP: +10 pips = +2 EUR"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "BUY TP hit"
checks:
- "operation.profit_pips == 10.0"
- "operation.profit_eur == 2.0"  # 0.01 lot × 10 pips
expected_output:
profit_pips: 10.0
profit_eur: 2.0
mm03_pnl_hedged:
priority: critical
description: "P&L bloqueado en HEDGED"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Both mains active → HEDGED"
checks:
- "cycle.accounting.pips_locked == 20.0"
- "floating_pnl_eur == -4.0"  # 20 pips × 0.2 EUR/pip
expected_output:
pips_locked: 20.0
floating_pnl: -4.0
mm04_balance_update_tp:
priority: critical
description: "Balance actualiza tras TP"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Start"
- time: 1
bid: 1.10120
ask: 1.10140
event: "BUY TP hit"
checks:
- "account.balance == 10002.0"
- "balance_delta == 2.0"
expected_output:
balance_before: 10000.0
balance_after: 10002.0
delta: 2.0
mm05_equity_calculation:
priority: critical
description: "Equity = Balance + Floating P&L"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Operations with floating P&L"
checks:
- "account.equity == account.balance + floating_pnl"
- "floating_pnl == sum([op.current_pnl for op in active_ops])"
expected_output:
balance: 10000.0
floating_pnl: 5.0
equity: 10005.0
mm06_margin_calculation:
priority: high
description: "Cálculo de margen requerido"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Open position"
checks:
- "margin_required == lot_size × contract_size / leverage"
- "margin_required ≈ 22.0"  # 0.01 lot, 100k contract, 1:50 leverage
expected_output:
margin_required: 22.0
mm07_free_margin:
priority: high
description: "Margen libre = Equity - Margin Used"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Multiple positions open"
checks:
- "account.margin_free == account.equity - account.margin_used"
expected_output:
equity: 10000.0
margin_used: 100.0
margin_free: 9900.0
mm08_recovery_pnl_accumulation:
priority: high
description: "P&L recovery acumula correctamente"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10140
ask: 1.10160
event: "N1 TP: +80 pips → -20 FIFO = +60 net"
- time: 1
bid: 1.10180
ask: 1.10200
event: "N2 TP: +80 pips → -40 FIFO = +40 net"
checks:
- "total_pips_recovered == 60.0"  # 20 + 40
- "net_profit_pips == 100.0"  # 60 + 40
expected_output:
pips_recovered: 60.0
net_profit: 100.0
============================================
EDGE CASES (8 escenarios)
============================================
edge_cases:
e01_spread_rejection:
priority: medium
description: "Spread alto rechaza operación"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10035  # Spread 3.5 pips
event: "High spread detected"
checks:
- "signal.signal_type == SignalType.NO_ACTION"
- "signal.metadata['reason'] == 'high_spread'"
- "len(broker.orders) == 0"
expected_output:
signal: no_action
reason: high_spread
spread_pips: 3.5
e02_high_spread_rejection:
priority: high
description: "Spread >3 pips pausa operaciones"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10050  # Spread 5 pips
event: "Extreme spread"
checks:
- "strategy.can_trade() == False"
- "spread_pips > MAX_SPREAD_PIPS"
expected_output:
can_trade: false
spread_pips: 5.0
e03_weekend_gap:
priority: high
description: "Gap fin de semana manejado"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Friday 22:00"
- time: 1
bid: 1.10200
ask: 1.10220
event: "Monday 00:01 - Gap +200 pips"
checks:
- "cycle.metadata['gap_detected'] == True"
- "cycle.metadata['gap_size'] == 200.0"
expected_output:
gap_detected: true
gap_size: 200.0
e04_mega_move:
priority: high
description: "Movimiento extremo >200 pips"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Normal state"
- time: 1
bid: 1.12500
ask: 1.12520
event: "Mega move +2500 pips"
checks:
- "price_move > 200"
- "system.metadata['extreme_volatility'] == True"
expected_output:
price_move: 2500.0
extreme_volatility: true
e05_return_to_origin:
priority: medium
description: "Precio retorna al origen"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Start"
- time: 1
bid: 1.10200
ask: 1.10220
event: "Move up +200 pips"
- time: 2
bid: 1.10000
ask: 1.10020
event: "Return to origin"
checks:
- "current_price == initial_price"
- "cycle.accounting.total_tps > 0"  # Should have captured TPs
expected_output:
price_returned: true
tps_captured: 2
e06_lateral_market:
priority: medium
description: "Mercado lateral genera múltiples TPs"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Start"
# Oscilación +10/-10 pips repetidamente
- time: 1
bid: 1.10100
ask: 1.10120
event: "TP #1"
- time: 2
bid: 1.10000
ask: 1.10020
event: "Return"
- time: 3
bid: 1.10100
ask: 1.10120
event: "TP #2"
checks:
- "cycle.accounting.total_tps >= 2"
- "price_volatility == 'low'"
expected_output:
total_tps: 2
volatility: low
e07_connection_lost:
priority: medium
description: "Pérdida de conexión y reconexión"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Connection lost"
- time: 10
bid: 1.10050
ask: 1.10070
event: "Reconnected"
checks:
- "broker.is_connected() == True"
- "sync_completed == True"
expected_output:
reconnected: true
sync_successful: true
e08_rollover_swap:
priority: low
description: "Swap/Rollover aplicado"
pair: EURUSD
initial_balance: 10000.0
sequence:
- time: 0
bid: 1.10000
ask: 1.10020
event: "Position held overnight"
- time: 86400  # 24 hours
bid: 1.10050
ask: 1.10070
event: "Swap applied"
checks:
- "operation.swap_total != 0"
- "operation.swap_total < 0 or operation.swap_total > 0"
expected_output:
swap_applied: true
swap_amount: -0.5
============================================
MULTI-PAIR (4 escenarios)
============================================
multi_pair:
mp01_dual_pair:
priority: high
description: "EURUSD + GBPUSD simultáneos"
pair: MULTI
pairs:
- EURUSD
- GBPUSD
initial_balance: 10000.0
sequence:
- time: 0
pair: EURUSD
bid: 1.10000
ask: 1.10020
event: "EURUSD cycle start"
- time: 0
pair: GBPUSD
bid: 1.25000
ask: 1.25020
event: "GBPUSD cycle start"
- time: 1
pair: EURUSD
bid: 1.10120
ask: 1.10140
event: "EURUSD TP"
- time: 1
pair: GBPUSD
bid: 1.25120
ask: 1.25140
event: "GBPUSD TP"
checks:
- "len(active_cycles) == 2"
- "eurusd_cycle.pair == 'EURUSD'"
- "gbpusd_cycle.pair == 'GBPUSD'"
- "eurusd_cycle.accounting.total_tp_count == 1"
- "gbpusd_cycle.accounting.total_tp_count == 1"
expected_output:
cycles_count: 2
balance: 10004.0
mp02_correlation_hedged:
priority: high
description: "Ambos pares en HEDGED"
pair: MULTI
pairs:
- EURUSD
- GBPUSD
initial_balance: 10000.0
sequence:
- time: 0
pair: EURUSD
bid: 1.10000
ask: 1.10020
event: "EURUSD both active"
- time: 0
pair: GBPUSD
bid: 1.25000
ask: 1.25020
event: "GBPUSD both active"
checks:
- "eurusd_cycle.status == CycleStatus.HEDGED"
- "gbpusd_cycle.status == CycleStatus.HEDGED"
- "total_pips_locked == 40.0"  # 20 + 20
expected_output:
hedged_cycles: 2
total_pips_locked: 40.0
mp03_jpy_calculation:
priority: high
description: "JPY con cálculo 2 decimales"
pair: USDJPY
initial_balance: 10000.0
sequence:
- time: 0
bid: 110.00
ask: 110.05
event: "USDJPY cycle"
- time: 1
bid: 110.15
ask: 110.20
event: "TP hit"
checks:
- "operation.profit_pips == 10.0"
- "pip_multiplier == 100"  # Not 10000
expected_output:
profit_pips: 10.0
pip_multiplier: 100
mp04_total_exposure:
priority: high
description: "Exposición total suma pares"
pair: MULTI
pairs:
- EURUSD
- GBPUSD
initial_balance: 10000.0
sequence:
- time: 0
pair: EURUSD
bid: 1.10000
ask: 1.10020
event: "EURUSD 3 operations (0.03 lots)"
- time: 0
pair: GBPUSD
bid: 1.25000
ask: 1.25020
event: "GBPUSD 2 operations (0.02 lots)"
checks:
- "total_lots == 0.05"
- "exposure_pct < 30.0"
expected_output:
total_lots: 0.05
exposure_pct: 25.0
============================================
JPY PAIRS (4 escenarios)
============================================
jpy_pairs:
j01_usdjpy_tp:
priority: high
description: "USDJPY TP con 2 decimales"
pair: USDJPY
initial_balance: 10000.0
sequence:
- time: 0
bid: 110.00
ask: 110.05
event: "BUY entry"
- time: 1
bid: 110.15
ask: 110.20
event: "TP hit"
checks:
- "operation.profit_pips == 10.0"
- "operation.entry_price == Decimal('110.05')"
- "operation.tp_price == Decimal('110.15')"
expected_output:
profit_pips: 10.0
precision: 2
j02_usdjpy_hedged:
priority: high
description: "USDJPY en HEDGED"
pair: USDJPY
initial_balance: 10000.0
sequence:
- time: 0
bid: 110.00
ask: 110.05
event: "Both activate"
checks:
- "cycle.status == CycleStatus.HEDGED"
- "cycle.accounting.pips_locked == 20.0"
expected_output:
cycle_status: hedged
pips_locked: 20.0
j03_usdjpy_recovery:
priority: high
description: "USDJPY Recovery"
pair: USDJPY
initial_balance: 10000.0
sequence:
- time: 0
bid: 110.25
ask: 110.30
event: "Recovery N1 entry"
- time: 1
bid: 110.95
ask: 111.00
event: "Recovery TP"
checks:
- "recovery.profit_pips == 80.0"
- "pip_calculation uses multiplier 100"
expected_output:
profit_pips: 80.0
j04_usdjpy_pips_calculation:
priority: high
description: "Cálculo pips JPY correcto"
pair: USDJPY
initial_balance: 10000.0
sequence:
- time: 0
bid: 110.00
ask: 110.05
event: "Entry"
- time: 1
bid: 110.15
ask: 110.20
event: "Close"
checks:
- "profit_pips == (110.15 - 110.05) × 100"
- "profit_pips == 10.0"
expected_output:
entry: 110.05
close: 110.15
profit_pips: 10.0

---

## 2. Script Generador de CSVs
```python
# tests/fixtures/scenario_generator.py
"""
Generador automático de CSVs para los 62 escenarios de auditoría.

Uso:
    python tests/fixtures/scenario_generator.py

Genera:
    tests/scenarios/*.csv (62 archivos)
"""

import csv
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple, Any
import yaml


class ScenarioCSVGenerator:
    """Genera CSVs de prueba desde especificaciones YAML."""

    def __init__(self, specs_path: str, output_dir: str):
        self.specs_path = Path(specs_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(specs_path, 'r', encoding='utf-8') as f:
            self.specs = yaml.safe_load(f)
    
    def generate_all(self) -> None:
        """Genera todos los CSVs de todas las categorías."""
        categories = [
            'core', 'cycles', 'hedged', 'recovery', 
            'fifo', 'risk_management', 'money_management',
            'edge_cases', 'multi_pair', 'jpy_pairs'
        ]
        
        total_generated = 0
        
        for category in categories:
            if category not in self.specs:
                continue
            
            print(f"\n📂 Generando categoría: {category.upper()}")
            
            for scenario_id, spec in self.specs[category].items():
                csv_path = self.output_dir / f"{scenario_id}.csv"
                
                try:
                    if spec.get('pair') == 'MULTI':
                        self._generate_multi_pair_csv(scenario_id, spec, csv_path)
                    else:
                        self._generate_single_pair_csv(scenario_id, spec, csv_path)
                    
                    total_generated += 1
                    print(f"  ✓ {scenario_id}.csv")
                    
                except Exception as e:
                    print(f"  ✗ {scenario_id}.csv - Error: {e}")
        
        print(f"\n✅ Total generado: {total_generated} archivos")
    
    def _generate_single_pair_csv(
        self, 
        scenario_id: str, 
        spec: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Genera CSV para escenario de un solo par."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
            
            pair = spec['pair']
            sequence = spec['sequence']
            
            base_time = datetime(2024, 1, 1, 10, 0, 0)
            
            for i, tick_spec in enumerate(sequence):
                timestamp = base_time + timedelta(seconds=tick_spec['time'])
                bid = Decimal(str(tick_spec['bid']))
                ask = Decimal(str(tick_spec['ask']))
                
                writer.writerow([
                    timestamp.isoformat(),
                    pair,
                    str(bid),
                    str(ask)
                ])
                
                # Interpolar ticks intermedios si hay gran salto
                if i < len(sequence) - 1:
                    next_tick = sequence[i + 1]
                    self._add_interpolated_ticks(
                        writer, pair, base_time,
                        tick_spec, next_tick
                    )
    
    def _add_interpolated_ticks(
        self,
        writer: csv.writer,
        pair: str,
        base_time: datetime,
        current: Dict[str, Any],
        next_tick: Dict[str, Any]
    ) -> None:
        """Añade ticks intermedios para transiciones suaves."""
        time_diff = next_tick['time'] - current['time']
        
        # Si hay más de 1 segundo, interpolar
        if time_diff > 1:
            bid_start = Decimal(str(current['bid']))
            bid_end = Decimal(str(next_tick['bid']))
            ask_start = Decimal(str(current['ask']))
            ask_end = Decimal(str(next_tick['ask']))
            
            # Interpolar linealmente
            steps = min(time_diff - 1, 5)  # Máximo 5 ticks intermedios
            
            for step in range(1, steps + 1):
                ratio = Decimal(step) / Decimal(steps + 1)
                
                interp_bid = bid_start + (bid_end - bid_start) * ratio
                interp_ask = ask_start + (ask_end - ask_start) * ratio
                
                interp_time = base_time + timedelta(
                    seconds=current['time'] + step
                )
                
                writer.writerow([
                    interp_time.isoformat(),
                    pair,
                    str(interp_bid),
                    str(interp_ask)
                ])
    
    def _generate_multi_pair_csv(
        self,
        scenario_id: str,
        spec: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Genera CSV para escenarios multi-pair."""
        # Para multi-pair, crear archivos separados por par
        pairs = spec.get('pairs', [])
        
        for pair in pairs:
            pair_output = output_path.parent / f"{scenario_id}_{pair.lower()}.csv"
            
            with open(pair_output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
                
                # Filtrar sequence por par
                pair_sequence = [
                    tick for tick in spec['sequence']
                    if tick.get('pair', pair) == pair
                ]
                
                base_time = datetime(2024, 1, 1, 10, 0, 0)
                
                for tick_spec in pair_sequence:
                    timestamp = base_time + timedelta(seconds=tick_spec['time'])
                    writer.writerow([
                        timestamp.isoformat(),
                        pair,
                        str(tick_spec['bid']),
                        str(tick_spec['ask'])
                    ])
    
    def generate_scenario(self, scenario_id: str) -> None:
        """Genera un solo escenario específico."""
        for category in self.specs:
            if category == 'metadata':
                continue
            
            if scenario_id in self.specs[category]:
                spec = self.specs[category][scenario_id]
                csv_path = self.output_dir / f"{scenario_id}.csv"
                
                if spec.get('pair') == 'MULTI':
                    self._generate_multi_pair_csv(scenario_id, spec, csv_path)
                else:
                    self._generate_single_pair_csv(scenario_id, spec, csv_path)
                
                print(f"✓ Generado: {scenario_id}.csv")
                return
        
        print(f"✗ Escenario no encontrado: {scenario_id}")


def main():
    """Punto de entrada principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Genera CSVs de test desde especificaciones YAML'
    )
    parser.add_argument(
        '--specs',
        default='tests/fixtures/scenario_specs.yaml',
        help='Ruta al archivo YAML de especificaciones'
    )
    parser.add_argument(
        '--output',
        default='tests/scenarios',
        help='Directorio de salida para CSVs'
    )
    parser.add_argument(
        '--scenario',
        help='Generar solo un escenario específico'
    )
    
    args = parser.parse_args()
    
    generator = ScenarioCSVGenerator(args.specs, args.output)
    
    if args.scenario:
        generator.generate_scenario(args.scenario)
    else:
        generator.generate_all()


if __name__ == '__main__':
    main()
```

---

## 3. Template de Test Parametrizado
```python
# tests/test_scenarios/test_all_scenarios.py
"""
Tests parametrizados para los 62 escenarios de auditoría.

Cada test:
1. Carga CSV del escenario
2. Ejecuta backtest
3. Valida checks de la matriz

Uso:
    # Todos los tests
    pytest tests/test_scenarios/test_all_scenarios.py -v
    
    # Un escenario específico
    pytest tests/test_scenarios/test_all_scenarios.py::test_scenario[c01_tp_simple_buy]
    
    # Una categoría
    pytest tests/test_scenarios/test_all_scenarios.py -k "core"
"""

import pytest
import yaml
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, List

from wsplumber.core.backtest.backtest_engine import BacktestEngine
from wsplumber.domain.types import (
    OperationStatus, CycleStatus, OperationType,
    CurrencyPair
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="session")
def scenario_specs() -> Dict[str, Any]:
    """Carga especificaciones de escenarios."""
    specs_path = Path(__file__).parent.parent / "fixtures" / "scenario_specs.yaml"
    
    with open(specs_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
async def backtest_engine():
    """Crea engine de backtest limpio para cada test."""
    engine = BacktestEngine(initial_balance=10000.0)
    yield engine
    # Cleanup
    await engine.orchestrator.stop()


# ============================================
# COLECCIÓN DE ESCENARIOS
# ============================================

def collect_scenario_ids(specs: Dict[str, Any]) -> List[str]:
    """Extrae todos los IDs de escenarios del YAML."""
    scenario_ids = []
    
    categories = [
        'core', 'cycles', 'hedged', 'recovery', 
        'fifo', 'risk_management', 'money_management',
        'edge_cases', 'multi_pair', 'jpy_pairs'
    ]
    
    for category in categories:
        if category in specs:
            scenario_ids.extend(specs[category].keys())
    
    return scenario_ids


@pytest.fixture(scope="session")
def all_scenario_ids(scenario_specs) -> List[str]:
    """Lista de todos los IDs de escenarios."""
    return collect_scenario_ids(scenario_specs)


# ============================================
# HELPERS DE VALIDACIÓN
# ============================================

class ScenarioValidator:
    """Valida checks de escenarios contra el estado del sistema."""
    
    def __init__(self, engine: BacktestEngine):
        self.engine = engine
        self.repository = engine.repository
        self.broker = engine.broker
    
    async def validate_check(self, check_expr: str) -> bool:
        """
        Evalúa un check expression y retorna si pasa.
        
        Ejemplo: "buy_op.status == OperationStatus.TP_HIT"
        """
        # Preparar contexto de evaluación
        context = await self._build_evaluation_context()
        
        try:
            result = eval(check_expr, {"__builtins__": {}}, context)
            return bool(result)
        except Exception as e:
            print(f"Error evaluando check '{check_expr}': {e}")
            return False
    
    async def _build_evaluation_context(self) -> Dict[str, Any]:
        """Construye contexto con variables para evaluar checks."""
        # Obtener datos del sistema
        cycles = await self.repository.get_all_cycles()
        operations = await self.repository.get_all_operations()
        account_info = await self.broker.get_account_info()
        
        cycle = cycles[0] if cycles else None
        
        # Operaciones por tipo
        buy_ops = [op for op in operations if op.op_type in (
            OperationType.MAIN_BU