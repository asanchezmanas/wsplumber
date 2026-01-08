# WSPlumber - Reporte de Escenarios de Test

**Total:** 5 | **Passed:** 3 | **Failed:** 2

## Tests Fallidos

### 3.1 - hedge_sell_recovery [CRITICA]
- **Archivo:** `scenario_3_1_buy_tp_hedge_sell_activates.csv`
- **Error:** Validations failed

**Validaciones:**
- [OK] <lambda>: TP/CLOSED operations: 1
- [FAIL] <lambda>: No recovery operations

### 5.1 - recovery_tp [CRITICA]
- **Archivo:** `scenario_5_1_recovery_n1_tp.csv`
- **Error:** Validations failed

**Validaciones:**
- [FAIL] <lambda>: Balance: 1000.0 <= 1000.0
- [OK] <lambda>: Recovery ops: 12

## Tests Exitosos

- [CRITICA] 1.1 - tp_buy
- [CRITICA] 1.2 - tp_sell
- [CRITICA] 2.1 - hedged
