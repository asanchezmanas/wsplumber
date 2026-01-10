"""
WSPlumber - Generador de Simulación 10k
Genera un CSV de 10,000 ticks con volatilidad aleatoria para stress-test del core.
"""
import csv
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

def generate_10k_scenario(filename="tests/scenarios/stress_10k_random.csv", pair="EURUSD"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    base_price = Decimal("1.10000")
    spread = Decimal("0.0002")
    base_time = datetime(2026, 1, 1, 0, 0, 0)
    
    # Parámetros de volatilidad
    # Queremos que el precio se mueva lo suficiente para activar decenas de ciclos y recoveries
    step_sigma = 2.0 # pips por tick
    
    print(f"Generando {filename}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'pair', 'bid', 'ask', 'spread_pips'])
        
        current_price = base_price
        for i in range(10000):
            # Movimiento aleatorio (Random Walk)
            delta_pips = random.gauss(0, step_sigma)
            current_price += Decimal(str(round(delta_pips, 1))) * Decimal("0.0001")
            
            ts = (base_time + timedelta(seconds=i)).isoformat()
            bid = current_price
            ask = current_price + spread
            
            writer.writerow([
                ts, 
                pair, 
                f"{bid:.5f}", 
                f"{ask:.5f}", 
                "2.0"
            ])
            
    print(f"[OK] 10,000 ticks generados en {filename}")

if __name__ == "__main__":
    generate_10k_scenario()
