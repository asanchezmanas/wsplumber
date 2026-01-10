"""
WSPlumber - Convertidor M1 OHLC a Tick Format
Convierte datos históricos en formato MetaTrader (OHLC) al formato de tick de wsplumber.

Uso: python scripts/convert_ohlc_to_ticks.py <archivo_ohlc.csv> [max_lineas]
"""
import csv
import sys
import os
from datetime import datetime
from decimal import Decimal

def convert_ohlc_to_ticks(input_path: str, output_path: str = None, max_lines: int = None):
    """
    Convierte OHLC M1 a formato tick.
    
    Formato entrada: Date,Time,O,H,L,C,V (sin cabecera)
    Formato salida: timestamp,pair,bid,ask,spread_pips
    
    Por cada barra M1, genera 4 ticks: Open, High, Low, Close
    """
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = f"{base}_ticks.csv"
    
    pair = "EURUSD"
    if "JPY" in input_path.upper():
        pair = "USDJPY"
    elif "GBP" in input_path.upper():
        pair = "GBPUSD"
    
    spread = Decimal("0.0002")  # 2 pips típico
    
    line_count = 0
    tick_count = 0
    
    print(f"Convirtiendo {input_path}...")
    print(f"Par detectado: {pair}")
    print(f"Límite de líneas: {max_lines or 'Sin límite'}")
    
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', newline='', encoding='utf-8') as fout:
        
        writer = csv.writer(fout)
        writer.writerow(['timestamp', 'pair', 'bid', 'ask', 'spread_pips'])
        
        for line in fin:
            if max_lines and line_count >= max_lines:
                break
            
            parts = line.strip().split(',')
            if len(parts) < 6:
                continue
            
            # Parse: Date,Time,O,H,L,C,V
            date_str, time_str = parts[0], parts[1]
            o, h, l, c = Decimal(parts[2]), Decimal(parts[3]), Decimal(parts[4]), Decimal(parts[5])
            
            # Crear timestamp ISO
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H:%M")
            except ValueError:
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
                except ValueError:
                    continue
            
            ts_base = dt.isoformat()
            
            # Generar 4 ticks por barra (O, H, L, C)
            # Esto simula el movimiento intrabarra
            prices = [o, h, l, c]
            for i, price in enumerate(prices):
                ts = f"{ts_base}.{i:03d}"
                bid = price
                ask = price + spread
                writer.writerow([ts, pair, f"{bid:.5f}", f"{ask:.5f}", "2.0"])
                tick_count += 1
            
            line_count += 1
            
            if line_count % 50000 == 0:
                print(f"  Procesadas {line_count:,} barras ({tick_count:,} ticks)...")
    
    print(f"\n[OK] Conversión completada:")
    print(f"  Barras procesadas: {line_count:,}")
    print(f"  Ticks generados:   {tick_count:,}")
    print(f"  Archivo salida:    {output_path}")
    
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/convert_ohlc_to_ticks.py <archivo_ohlc.csv> [max_lineas]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    convert_ohlc_to_ticks(input_file, max_lines=max_lines)
