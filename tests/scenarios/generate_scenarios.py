import csv
import os
from datetime import datetime, timedelta
from decimal import Decimal

def generate_csv(filename, pair, start_price, ticks_data):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
        
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        curr_price = Decimal(str(start_price))
        spread = Decimal("0.0002")
        
        for i, (price_change, event) in enumerate(ticks_data):
            curr_price += Decimal(str(price_change))
            ts = (base_time + timedelta(seconds=i)).isoformat()
            writer.writerow([ts, pair, curr_price, curr_price + spread])

# 1. Scenario: TP Hit (+10 pips)
# Starts at 1.1000. 
# Buy Stop at 1.1005 (5 pips away)
# TP at 1.1015 (10 pips gain)
# Sell Stop at 1.0995 (5 pips away)
generate_csv(
    'tests/scenarios/scenario_tp_hit.csv',
    'EURUSD',
    1.1000,
    [
        (0, "Start"),
        (0.0002, ""),
        (0.0003, "Buy Activated at 1.1005"),
        (0.0005, ""),
        (0.0005, "TP Hit at 1.1015"),
        (0.0001, "Final tick")
    ]
)

# 2. Scenario: Coverage Activation
# Starts at 1.1000.
# Both activate, then one hits TP.
generate_csv(
    'tests/scenarios/scenario_coverage.csv',
    'EURUSD',
    1.1000,
    [
        (0, "Start"),
        (0.0005, "Buy Activated (1.1005)"),
        (-0.0010, "Sell Activated (1.0995)"),
        (0.0015, ""),
        (0.0005, "Buy TP Hit (1.1015) -> Sell Coverage should appear at 1.1015 entry"),
        (-0.0005, "Market turns back")
    ]
)

# 3. Scenario: Recovery N1 Success
# Main SL -> Recovery N1 -> Recovery TP (+80 pips)
generate_csv(
    'tests/scenarios/scenario_recovery_win.csv',
    'EURUSD',
    1.1000,
    [
        (0, "Start"),
        (0.0005, "Buy Activated"),
        (-0.0050, "Moving down"),
        (-0.0050, "Buy SL hit / Recovery Starts at 1.0905 approx"),
        (0.0080, "Moving up 80 pips"),
        (0.0010, "Final")
    ]
)

print("Scenarios generated in tests/scenarios/")
