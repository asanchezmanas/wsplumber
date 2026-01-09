(venv) PS C:\Users\Artur\wsplumber> cd 'c:\Users\Artur\wsplumber'
(venv) PS C:\Users\Artur\wsplumber> cd c:\Users\Artur\wsplumber; $env:PYTHONPATH="c:\Users\Artur\wsplumber"; python -c "
>> import asyncio
>> import sys
>> sys.path.insert(0, 'c:/Users/Artur/wsplumber')
>>
>> # Silenciar logs
>> import logging
>> logging.disable(logging.CRITICAL)
>>
>> from tests.test_cycle_renewal_fix import test_cycle_renewal_creates_new_cycle
>>
>> async def run():
>>     try:
>>         result = await test_cycle_renewal_creates_new_cycle()
>>         print('TEST PASSED' if result else 'TEST FAILED')
>>     except Exception as e:
>>         print(f'TEST FAILED: {e}')
>>         import traceback
>>         traceback.print_exc()
>>
>> asyncio.run(run())
>> " 2>&1

============================================================
TEST: Cycle Renewal Fix (C1 -> C2)
============================================================

TICK 1: Crear ciclo C1
  C1 creado: CYC_EURUSD_20260109125359_529
  C1 status: pending
  Operaciones totales: 2

TICK 2: Activar BUY
  C1 status: active

TICK 3: Activar SELL -> HEDGED
  C1 status: hedged

TICK 4: BUY toca TP -> DEBE CREAR C2
  DEBUG: BUY TP price = 1.10170
  DEBUG: BUY status before = neutralized
  DEBUG: Tick4 bid=1.102, ask=1.1022
  DEBUG: C1 status before tick4: hedged
  DEBUG: BUY status after = tp_hit
  DEBUG: BUY tp_processed = True
  DEBUG: Total cycles after tick4: 2
  DEBUG: Cycle IDs: ['CYC_EURUSD_20260109125359_529', 'CYC_EURUSD_20260109125359_473']
  DEBUG: Cycle types: ['main', 'main']

============================================================
VERIFICACIONES CRÍTICAS
============================================================

[V1] Ciclos MAIN totales: 2
     IDs: ['CYC_EURUSD_20260109125359_529', 'CYC_EURUSD_20260109125359_473']
     OK: Se creo C2

[V2] C1 (CYC_EURUSD_20260109125359_529)
     Mains en C1: 2
     IDs: ['CYC_EURUSD_20260109125359_529_B', 'CYC_EURUSD_20260109125359_529_S']
     OK: C1 tiene exactamente 2 mains

[V3] C1 status: hedged
     OK: C1 en hedged

[V4] C2 (CYC_EURUSD_20260109125359_473)
     Mains en C2: 2
     IDs: ['CYC_EURUSD_20260109125359_473_B', 'CYC_EURUSD_20260109125359_473_S']
     OK: C2 tiene 2 mains propios

[V5] C2 status: pending
     OK: C2 operando normalmente

[V6] Cycle IDs de mains de C2: ['CYC_EURUSD_20260109125359_473', 'CYC_EURUSD_20260109125359_473']
     Diferentes de C1 (CYC_EURUSD_20260109125359_529): True
     OK: C2 independiente de C1

============================================================
TODAS LAS VERIFICACIONES PASARON
============================================================

FIX CONFIRMADO:
  - C1 tiene exactamente 2 mains (no acumula renovaciones)
  - C2 se creo como NUEVO ciclo independiente
  - C1 queda IN_RECOVERY esperando recovery
  - C2 opera normalmente con sus propias mains
============================================================
TEST PASSED
(venv) PS C:\Users\Artur\wsplumber> cd 'c:\Users\Artur\wsplumber'
(venv) PS C:\Users\Artur\wsplumber> cd c:\Users\Artur\wsplumber; $env:PYTHONPATH="c:\Users\Artur\wsplumber"; python scripts/backtest_trace_detailed.py 500 2>&1

🚀 Backtest con trazabilidad detallada (500 barras)...
   Total ticks: 2000

================================================================================
📋 REPORTE DE TRAZABILIDAD DETALLADA
================================================================================

📜 TIMELINE DE EVENTOS:
--------------------------------------------------------------------------------
#    1 | 📍 NUEVO CICLO: C1 (main)
#    1 |    ➕ C1_BUY_1 creada PENDING | entry=1.24428 tp=1.24528
#    1 |    ➕ C1_SELL_1 creada PENDING | entry=1.24318 tp=1.24218
#  102 |    ▶️  C1_SELL_1 ACTIVADA
#  371 |    🔒 C1_BUY_1 NEUTRALIZADA (hedged)
#  371 |    🔒 C1_SELL_1 NEUTRALIZADA (hedged)
#  371 |    ➕ C1_H_SELL creada PENDING | entry=1.24428 tp=0.00000
#  371 |    ➕ C1_H_BUY creada PENDING | entry=1.24318 tp=0.00000
#  374 |    ▶️  C1_H_SELL ACTIVADA
#  971 | 📍 NUEVO CICLO: C2 (main)
#  971 |    ✅ C1_BUY_1 TP_HIT | +10.9 pips (+1.09 EUR) | Total: +10.9 pips
#  971 |    ➕ C1_BUY_2 creada PENDING | entry=1.24597 tp=1.24697
#  971 |    ➕ C1_SELL_2 creada PENDING | entry=1.24487 tp=1.24387
#  971 | 💰 BALANCE: 10000.00 → 10001.09 (+1.09 EUR)
# 1298 |    ▶️  C1_SELL_2 ACTIVADA
# 1842 |    ❌ C1_BUY_2 CANCELADA (contra-orden)
# 1842 |    ✅ C1_SELL_2 TP_HIT | +10.6 pips (+1.06 EUR) | Total: +21.5 pips
# 1842 | 💰 BALANCE: 10001.09 → 10002.15 (+1.06 EUR)
# 1914 | 📍 NUEVO CICLO: C3 (main)
# 1914 |    ✅ C1_SELL_1 TP_HIT | +11.4 pips (+1.14 EUR) | Total: +32.9 pips
# 1914 |    ➕ C1_BUY_3 creada PENDING | entry=1.24254 tp=1.24354
# 1914 |    ➕ C1_SELL_3 creada PENDING | entry=1.24144 tp=1.24044
# 1914 | 💰 BALANCE: 10002.15 → 10003.29 (+1.14 EUR)
# 1915 |    ▶️  C1_BUY_3 ACTIVADA
# 1971 |    ✅ C1_BUY_3 TP_HIT | +14.6 pips (+1.46 EUR) | Total: +47.5 pips
# 1971 |    ❌ C1_SELL_3 CANCELADA (contra-orden)
# 1971 | 💰 BALANCE: 10003.29 → 10004.75 (+1.46 EUR)

--------------------------------------------------------------------------------
📊 P&L POR CICLO:
--------------------------------------------------------------------------------
   C1: +47.5 pips (+4.75 EUR)
      Operaciones: C1_BUY_1, C1_SELL_1, C1_H_SELL, C1_H_BUY, C1_BUY_2, C1_SELL_2, C1_BUY_3, C1_SELL_3
   C2: ABIERTO
   C3: ABIERTO

================================================================================
📊 RESULTADO FINAL
================================================================================
   Balance Inicial:    10,000.00 EUR
   Balance Final:      10,004.75 EUR
   P&L Realizado:      +4.75 EUR (+47.5 pips)
   Equity Final:       10,005.75 EUR
   Flotante:           +1.00 EUR
   Posiciones Abiertas: 2
================================================================================
(venv) PS C:\Users\Artur\wsplumber> cd 'c:\Users\Artur\wsplumber'
(venv) PS C:\Users\Artur\wsplumber> cd c:\Users\Artur\wsplumber; $env:PYTHONPATH="c:\Users\Artur\wsplumber"; python -c "
>> import asyncio
>> import logging
>> logging.disable(logging.CRITICAL)
>>
>> from wsplumber.core.backtest.backtest_engine import BacktestEngine
>> from wsplumber.domain.types import CurrencyPair
>> from wsplumber.domain.entities.cycle import CycleType
>>
>> async def main():
>>     engine = BacktestEngine(initial_balance=10000.0)
>>     pair = CurrencyPair('EURUSD')
>>     engine.broker.load_m1_csv('2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv', pair, max_bars=500)
>>     await engine.broker.connect()
>>
>>     tick_count = 0
>>     while True:
>>         tick = await engine.broker.advance_tick()
>>         if not tick:
>>             break
>>         await engine.orchestrator.process_tick(tick)
>>         tick_count += 1
>>
>>     print('='*60)
>>     print('VERIFICACION DE MAINS POR CICLO (Post-Fix)')
>>     print('='*60)
>>
>>     # Obtener todos los ciclos
>>     all_cycles = list(engine.repository.cycles.values())
>>     main_cycles = [c for c in all_cycles if c.cycle_type == CycleType.MAIN]
>>
>>     print(f'\nCiclos MAIN totales: {len(main_cycles)}')
>>     
>>     for i, cycle in enumerate(main_cycles):
>>         # Contar mains de este ciclo
>>         all_ops = list(engine.repository.operations.values())
>>         cycle_mains = [op for op in all_ops if op.cycle_id == cycle.id and op.is_main]
>>
>>         print(f'\n  C{i+1}: {cycle.id[:40]}')
>>         print(f'      Status: {cycle.status.value}')
>>         print(f'      Mains: {len(cycle_mains)}')
>>
>>         for op in cycle_mains:
>>             print(f'        - {op.id[:50]} ({op.status.value})')
>>
>>         if len(cycle_mains) != 2:
>>             print(f'       ERROR: Debe tener 2 mains, tiene {len(cycle_mains)}')
>>         else:
>>             print(f'       OK: Exactamente 2 mains')
>>
>>     print('\n' + '='*60)
>>     if all(len([op for op in engine.repository.operations.values() if op.cycle_id == c.id and op.is_main]) == 2 for c in main_cycles):
>>         print(' INVARIANTE VERIFICADO: Todos los ciclos MAIN tienen exactamente 2 mains')
>>     else:
>>         print(' INVARIANTE ROTO: Hay ciclos con != 2 mains')
>>     print('='*60)
>>
>> asyncio.run(main())
>> " 2>&1
============================================================
VERIFICACION DE MAINS POR CICLO (Post-Fix)
============================================================

Ciclos MAIN totales: 3

  C1: CYC_EURUSD_20260109125557_365
      Status: hedged
      Mains: 2
        - CYC_EURUSD_20260109125557_365_B (tp_hit)
        - CYC_EURUSD_20260109125557_365_S (tp_hit)
       OK: Exactamente 2 mains

  C2: CYC_EURUSD_20260109125557_439
      Status: active
      Mains: 2
        - CYC_EURUSD_20260109125557_439_B (cancelled)
        - CYC_EURUSD_20260109125557_439_S (tp_hit)
       OK: Exactamente 2 mains

  C3: CYC_EURUSD_20260109125557_768
      Status: active
      Mains: 2
        - CYC_EURUSD_20260109125557_768_B (tp_hit)
        - CYC_EURUSD_20260109125557_768_S (cancelled)
       OK: Exactamente 2 mains

============================================================
 INVARIANTE VERIFICADO: Todos los ciclos MAIN tienen exactamente 2 mains
============================================================