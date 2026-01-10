import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal

def generate_monte_carlo_csv(output_path: str, ticks: int = 10000, initial_price: float = 1.1000, volatility_pips: float = 1.0):
    """
    Generates a Monte Carlo Random Walk CSV for WSPlumber stress testing.
    """
    print(f"Generating {ticks} random ticks to {output_path}...")
    
    path = Path(output_path)
    price = Decimal(str(initial_price))
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    
    with open(path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["pair", "bid", "ask", "timestamp", "spread_pips"])
        
        for i in range(ticks):
            # Brownian motion step
            change_pips = Decimal(str(random.uniform(-volatility_pips, volatility_pips))) / 10000
            price += change_pips
            
            # Simulated spread (1.0 to 1.5 pips)
            spread = Decimal(str(random.uniform(1.0, 1.5)))
            bid = price
            ask = price + (spread / 10000)
            
            timestamp = start_time + timedelta(seconds=i)
            writer.writerow(["EURUSD", f"{bid:.5f}", f"{ask:.5f}", timestamp.isoformat(), f"{spread:.1f}"])
            
    print("Done.")

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    name = sys.argv[2] if len(sys.argv) > 2 else "monte_carlo_stress_10k.csv"
    generate_monte_carlo_csv(name, ticks=count)
