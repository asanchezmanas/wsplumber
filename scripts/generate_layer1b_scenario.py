"""
Generate a synthetic scenario for Layer 1B that:
1. Forces HEDGED state
2. Opens RECOVERY
3. Lets one recovery gain +30 pips profit (enough for trailing)
4. Trailing should kick in
"""

import csv
from datetime import datetime, timedelta

ticks = []
base_time = datetime(2026, 1, 20, 10, 0, 0)

# Phase 1: Initial - price at 1.1000 (T0-T3)
# Mains placed at 1.1005 (buy) and 1.0995 (sell)
for i in range(4):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': '1.1000',
        'ask': '1.1001'
    })

# Phase 2: Price rises to 1.1005 - BUY activates (T4-T7)
prices = [1.1003, 1.1005, 1.1006, 1.1005]
for i, p in enumerate(prices, start=4):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 3: Price drops to 1.0995 - SELL activates = HEDGED (T8-T11)
prices = [1.1000, 1.0997, 1.0995, 1.0996]
for i, p in enumerate(prices, start=8):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 4: Price rises to ~1.1015 - BUY TP hits, opens recovery (T12-T18)
prices = [1.1005, 1.1010, 1.1013, 1.1015, 1.1016, 1.1014, 1.1012]
for i, p in enumerate(prices, start=12):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 5: Price drops slowly to activate REC_SELL at ~1.0995 (T19-T30)
# Recovery placed at 1.1015 - 20 = 1.0995 for sell, 1.1015 + 20 = 1.1035 for buy
prices = [1.1005, 1.1000, 1.0998, 1.0997, 1.0996, 1.0995, 
          1.0994, 1.0993, 1.0992, 1.0990, 1.0988, 1.0985]
for i, p in enumerate(prices, start=19):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 6: REC_SELL is active, price continues dropping gradually +1 pip at a time (T31-T60)
# This gives REC_SELL profit and should trigger Layer 1B trailing
start_price = 1.0983
for i in range(30):
    p = start_price - (i * 0.0001)  # 1 pip at a time
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=31+i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': f'{p:.4f}',
        'ask': f'{p + 0.0001:.4f}'
    })

# Phase 7: Price stabilizes for a few ticks (T61-T65)
for i in range(5):
    ticks.append({
        'timestamp': (base_time + timedelta(seconds=61+i)).strftime('%Y-%m-%d %H:%M:%S'),
        'bid': '1.0954',
        'ask': '1.0955'
    })

# Write to CSV
with open('tests/scenarios/r02_layer1b_full.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['timestamp', 'bid', 'ask'])
    writer.writeheader()
    writer.writerows(ticks)

print(f"Generated {len(ticks)} ticks")
print(f"Time range: {ticks[0]['timestamp']} to {ticks[-1]['timestamp']}")
print(f"Price range: {ticks[0]['bid']} to {ticks[-1]['bid']}")
print(f"\nExpected flow:")
print("T4-7: BUY activates")
print("T8-11: SELL activates = HEDGED")
print("T15: BUY TP @ 1.1015")
print("T24: REC_SELL activates @ ~1.0995")
print("T34+: REC_SELL profit >10 pips = Layer 1B should trail REC_BUY")
