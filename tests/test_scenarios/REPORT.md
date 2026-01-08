# WSPlumber - Reporte de Escenarios de Test

**Total:** 5 | **Passed:** 0 | **Failed:** 5

## Tests Fallidos

### 1.1 - tp_buy [CRITICA]
- **Archivo:** `scenario_1_1_tp_buy.csv`
- **Error:** Validations failed

**Validaciones:**
- [FAIL] <lambda>: Balance: 1000.0 <= 1000.0
- [FAIL] <lambda>: No TP_HIT operations

### 1.2 - tp_sell [CRITICA]
- **Archivo:** `scenario_1_2_tp_sell.csv`
- **Error:** Validations failed

**Validaciones:**
- [FAIL] <lambda>: Balance: 1000.0 <= 1000.0
- [FAIL] <lambda>: No TP_HIT operations

### 2.1 - hedged [CRITICA]
- **Archivo:** `scenario_2_1_both_active_hedged.csv`
- **Error:** Validations failed

**Validaciones:**
- [FAIL] <lambda>: No HEDGED cycles
- [FAIL] <lambda>: No pips locked

### 3.1 - hedge_sell_recovery [CRITICA]
- **Archivo:** `scenario_3_1_buy_tp_hedge_sell_activates.csv`
- **Error:** Validations failed

**Validaciones:**
- [OK] <lambda>: TP_HIT operations: 2
- [FAIL] <lambda>: No recovery operations

### 5.1 - recovery_tp [CRITICA]
- **Archivo:** `scenario_5_1_recovery_n1_tp.csv`
- **Error:** Validations failed

**Validaciones:**
- [OK] <lambda>: Balance: 1012.8000000000000003 > 1000.0
- [FAIL] <lambda>: No recovery operations

## Tests Exitosos

