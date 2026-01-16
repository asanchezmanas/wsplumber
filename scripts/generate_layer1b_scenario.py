"""
Generate a synthetic scenario that forces:
1. HEDGED state (both mains activate)
2. RECOVERY cycle opens
3. One recovery activates and advances (profit)
4. Layer 1B should trail the pending counter
"""

# Scenario design:
# T1: Start at 1.1000 (mains placed at 1.1005/1.0995)
# T5: Price rises to 1.1005 → BUY activates
# T10: Price drops to 1.0995 → SELL activates → HEDGED
# T15: Price rises to 1.1015 → BUY TP hit → Recovery opens
# T20: Price drops to ~1.0995 (recovery at 1.0995 ±20 = 1.0975 sell / 1.1015 buy)
# T25: Price drops to 1.0975 → REC_SELL activates
# T30-50: Price continues dropping → REC_SELL in profit → Layer 1B should trail REC_BUY

import csv
from datetime import datetime, timedelta

ticks = []
base_time = datetime(2026, 1, 20, 10, 0, 0)

# Phase 1: Initial - price oscillates near 1.1000 (T1-T4)
prices = [1.1000, 1.1002, 1.1001, 1.1003]
for i, p in enumerate(prices):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 2: Price rises to activate BUY (T5-T9)
prices = [1.1004, 1.1005, 1.1006, 1.1007, 1.1006]
for i, p in enumerate(prices, start=4):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 3: Price drops to activate SELL → HEDGED (T10-T14)
prices = [1.1003, 1.0998, 1.0995, 1.0996, 1.0998]
for i, p in enumerate(prices, start=9):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 4: Price rises to hit BUY TP @ 1.1015 (T15-T19)
prices = [1.1005, 1.1010, 1.1012, 1.1015, 1.1016]
for i, p in enumerate(prices, start=14):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 5: Price drops toward recovery sell entry @ ~1.0995 (T20-T24)
prices = [1.1010, 1.1000, 1.0990, 1.0980, 1.0975]
for i, p in enumerate(prices, start=19):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 6: Price continues dropping - REC_SELL activates and goes into profit (T25-T40)
# Layer 1B should be trailing the pending REC_BUY
prices = [1.0970, 1.0965, 1.0960, 1.0955, 1.0950, 
          1.0945, 1.0940, 1.0935, 1.0930, 1.0925,
          1.0920, 1.0915, 1.0910, 1.0905, 1.0900, 1.0895]
for i, p in enumerate(prices, start=24):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 7: Price continues to REC_SELL TP @ ~1.0895 (T41-T50)
prices = [1.0890, 1.0885, 1.0880, 1.0875, 1.0870, 
          1.0865, 1.0860, 1.0855, 1.0850, 1.0845]
for i, p in enumerate(prices, start=40):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Write to CSV
with open('tests/scenarios/r02_layer1b_full.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['timestamp', 'bid', 'ask'])
    writer.writeheader()
    writer.writerows(ticks)

print(f"Generated {len(ticks)} ticks")
print(f"Time range: {ticks[0]['timestamp']} to {ticks[-1]['timestamp']}")
print(f"Price range: {ticks[0]['bid']} to {ticks[-1]['bid']}")
