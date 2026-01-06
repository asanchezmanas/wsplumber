# WSPlumber - Test Scenarios

Escenarios de test generados automáticamente.

**Generado:** 2026-01-06T19:02:20.571241

## Índice de Escenarios

| Archivo | Par | Ticks | Descripción |
|---------|-----|-------|-------------|
| scenario_1_1_tp_buy.csv | EURUSD | 5 | ↑1 pip → Final, balance +10 pips |
| scenario_1_2_tp_sell.csv | EURUSD | 5 | ↓1 pip → Final, balance +10 pips |
| scenario_2_1_both_active_hedged.csv | EURUSD | 4 | ↓2 pips → Estado HEDGED confirmado, pips_locked=20 |
| scenario_3_1_buy_tp_hedge_sell_activates.csv | EURUSD | 7 | ↑2 pips → Recovery N1 creado |
| scenario_5_1_recovery_n1_tp.csv | EURUSD | 12 | ↑5 pips → FIFO cierra deuda, neto +60 pips |
| scenario_8_1_fifo_multiple_close.csv | EURUSD | 12 | ↓5 pips → FIFO cierra Main(-20) y N1(-40), neto +20 |
| scenario_1_3_buy_no_tp.csv | EURUSD | 6 | ↓2 pips → pips_locked=20 |
| scenario_1_4_sell_no_tp.csv | EURUSD | 6 | ↑2 pips → pips_locked=20 |
| scenario_6_1_recovery_n1_fails.csv | EURUSD | 11 | Deuda acumulada: -60 pips |
| scenario_11_1_usdjpy_tp.csv | USDJPY | 5 | ↑1 pip → Balance +10 pips |

## Cómo Usar

```python
from tests.fixtures.simulated_broker import SimulatedBroker

broker = SimulatedBroker()
broker.load_csv('tests/test_scenarios/scenario_1_1_tp_buy.csv')
```
