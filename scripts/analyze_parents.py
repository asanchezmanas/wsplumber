
import re

log_file = "audit_logs_2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.log"

last_row = None

with open(log_file, "r") as f:
    for line in f:
        # Buscamos líneas que tengan muchos pipes y empiecen con espacios
        parts = line.split("|")
        if len(parts) >= 12:
            try:
                # El primer campo es el tick (puede tener comas)
                tick_str = parts[0].strip().replace(",", "")
                if tick_str.isdigit():
                    # Es una línea de tabla
                    data = [p.strip() for p in parts]
                    # TICK | Bal | Equ | DD | Act | Hdg | InR | Clo | RecA | RecC | MTP | RTP
                    last_row = {
                        "tick": tick_str,
                        "act": int(data[4]),
                        "hdg": int(data[5]),
                        "inr": int(data[6]),
                        "clo": int(data[7]),
                        "reca": int(data[8]),
                        "recc": int(data[9])
                    }
            except (ValueError, IndexError):
                continue

if last_row:
    open_parents = last_row["act"] + last_row["hdg"] + last_row["inr"]
    total_parents = open_parents + last_row["clo"]
    pct_closed = (last_row["clo"] / total_parents * 100) if total_parents > 0 else 0
    
    print(f"ANÁLISIS AL TICK: {last_row['tick']}")
    print("-" * 50)
    print(f"Total Parent Cycles Created:  {total_parents}")
    print(f"  - Active (Main C1):       {last_row['act']}")
    print(f"  - Hedged (Main C1):       {last_row['hdg']}")
    print(f"  - In Recovery (Parent):   {last_row['inr']}")
    print(f"  - Closed Parent:          {last_row['clo']}")
    print(f"Efficiency: {pct_closed:.1f}% of parents are closed.")
    print("-" * 50)
    print(f"Total Recovery Cycles (RecA+RecC): {last_row['reca'] + last_row['recc']}")
    print(f"  - Recovery Active:        {last_row['reca']}")
    print(f"  - Recovery Closed:        {last_row['recc']}")
else:
    print("No se encontró la tabla de resumen en el log.")

# Buscar ciclos que han sido "FULLY RESOLVED"
resolved_count = 0
with open(log_file, "r") as f:
    for line in f:
        if "FULLY RESOLVED" in line:
            resolved_count += 1

print(f"\nParent cycles FULLY RESOLVED (Debt paid): {resolved_count}")
if last_row:
    print(f"Parent cycles CLOSED directly (No debt):    {last_row['clo'] - resolved_count}")
