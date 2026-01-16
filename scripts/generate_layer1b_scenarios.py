"""
Generate all Layer 1B test scenarios:
- r03: Trailing active, but recovery hits normal TP (no overlap)
- r04: Profit never reaches threshold, no trailing occurs
- r05: OVERLAP with insufficient profit, should open new recovery
"""

import csv
from datetime import datetime, timedelta

def generate_scenario(filename, phases, description):
    ticks = []
    base_time = datetime(2026, 1, 20, 10, 0, 0)
    tick_idx = 0
    
    for phase in phases:
        for p in phase['prices']:
            ticks.append({
                'timestamp': (base_time + timedelta(seconds=tick_idx)).strftime('%Y-%m-%d %H:%M:%S'),
                'bid': f'{p:.4f}',
                'ask': f'{p + 0.0001:.4f}'
            })
            tick_idx += 1
    
    with open(f'tests/scenarios/{filename}.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'bid', 'ask'])
        writer.writeheader()
        writer.writerows(ticks)
    
    print(f"Created {filename}: {len(ticks)} ticks - {description}")

# ============================================
# r03: Trailing to normal TP (no overlap)
# Recovery advances, trailing happens, but reaches TP before counter activates
# ============================================
r03_phases = [
    {'name': 'init', 'prices': [1.1000] * 4},
    {'name': 'buy_activates', 'prices': [1.1003, 1.1005, 1.1006, 1.1005]},
    {'name': 'sell_activates_hedge', 'prices': [1.1000, 1.0997, 1.0995, 1.0996]},
    {'name': 'buy_tp', 'prices': [1.1005, 1.1010, 1.1013, 1.1015, 1.1016]},
    # Recovery opens at ~1.0995 (sell) and ~1.1035 (buy)
    {'name': 'rec_sell_activates', 'prices': [1.1010, 1.1000, 1.0995, 1.0993, 1.0990]},
    # Price drops continuously to recovery TP (80 pips from 1.0995 = 1.0915)
    {'name': 'rec_sell_profit', 'prices': [
        1.0985, 1.0980, 1.0975, 1.0970, 1.0965,
        1.0960, 1.0955, 1.0950, 1.0945, 1.0940,
        1.0935, 1.0930, 1.0925, 1.0920, 1.0915
    ]},
]
generate_scenario('r03_trailing_to_tp', r03_phases, 'Trailing happens, recovery hits normal TP')

# ============================================
# r04: No trailing (profit < threshold)
# Recovery activates but never gains enough profit for trailing
# ============================================
r04_phases = [
    {'name': 'init', 'prices': [1.1000] * 4},
    {'name': 'buy_activates', 'prices': [1.1003, 1.1005, 1.1006, 1.1005]},
    {'name': 'sell_activates_hedge', 'prices': [1.1000, 1.0997, 1.0995, 1.0996]},
    {'name': 'buy_tp', 'prices': [1.1005, 1.1010, 1.1013, 1.1015, 1.1016]},
    # Recovery opens
    {'name': 'rec_sell_activates', 'prices': [1.1010, 1.1000, 1.0995, 1.0993]},
    # Only 5 pips profit (below 10 threshold), then reverses
    {'name': 'small_profit', 'prices': [1.0990, 1.0988, 1.0990, 1.0992]},
    # Price reverses upward - counter activates at original distance (correction fail)
    {'name': 'reversal', 'prices': [
        1.0995, 1.1000, 1.1005, 1.1010, 1.1015,
        1.1020, 1.1025, 1.1030, 1.1035, 1.1040
    ]},
]
generate_scenario('r04_no_trailing', r04_phases, 'Profit < threshold, no trailing, correction fail')

# ============================================
# r05: OVERLAP with insufficient profit (needs new recovery)
# Small overlap, profit doesn't cover debt
# ============================================
r05_phases = [
    {'name': 'init', 'prices': [1.1000] * 4},
    {'name': 'buy_activates', 'prices': [1.1003, 1.1005, 1.1006, 1.1005]},
    {'name': 'sell_activates_hedge', 'prices': [1.1000, 1.0997, 1.0995, 1.0996]},
    {'name': 'buy_tp', 'prices': [1.1005, 1.1010, 1.1013, 1.1015, 1.1016]},
    # Recovery opens
    {'name': 'rec_sell_activates', 'prices': [1.1010, 1.1000, 1.0995, 1.0993, 1.0990]},
    # Small profit (10 pips), trailing kicks in
    {'name': 'trailing', 'prices': [1.0985, 1.0983, 1.0980]},
    # Quick reversal - counter activates close (overlap ~5 pips)
    {'name': 'quick_reversal', 'prices': [1.0985, 1.0990, 1.0995]},
    # Price continues, new recovery should open
    {'name': 'continue', 'prices': [1.1000, 1.1005, 1.1010, 1.1015, 1.1020]},
]
generate_scenario('r05_overlap_new_recovery', r05_phases, 'Small OVERLAP (5 pips), opens new recovery')

print("\nAll scenarios created!")
