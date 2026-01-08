import json
import re
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

# Permitir pasar archivo por argumento
audit_file = sys.argv[1] if len(sys.argv) > 1 else 'docs/master_backtest_audit.md'

print(f"📊 ANÁLISIS PROFUNDO DEL BACKTEST")
print(f"Archivo: {audit_file}")
print("="*60)

# Métricas
max_tier = 0
max_lots = 0.0
total_pips = 0.0
main_tp_count = 0
recovery_count = 0
cycles_opened = 0

# Para Drawdown
balance_history = [10000.0]  # Empezamos con 10k
equity_points = []
max_balance = 10000.0
max_drawdown = 0.0
max_drawdown_pct = 0.0

# Operaciones
ops_opened = Counter()
ops_closed = Counter()
open_positions = {}  # ticket -> data

# Timeline
first_date = None
last_date = None

print("Analizando líneas...")
line_count = 0

with open(audit_file, 'r', encoding='utf-8') as f:
    for line in f:
        line_count += 1
        
        # Extraer timestamp de datos simulados
        ts_match = re.search(r'timestamp": "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if ts_match:
            try:
                dt = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
                if first_date is None:
                    first_date = dt
                last_date = dt
            except:
                pass
        
        # Tier y Lotes
        tier_match = re.search(r'"tier":\s*(\d+)', line)
        if tier_match:
            tier = int(tier_match.group(1))
            if tier > max_tier: max_tier = tier
        
        lot_match = re.search(r'"lot":\s*(\d*\.\d+|\d+)', line)
        if lot_match:
            lot = float(lot_match.group(1))
            if lot > max_lots: max_lots = lot

        # Operaciones Abiertas
        if 'Operation activated' in line:
            m = re.search(r'"op_type":\s*"([^"]+)"', line)
            if m:
                ops_opened[m.group(1)] += 1

        # Posiciones Cerradas
        if 'Position closed' in line:
            pips_match = re.search(r'"profit_pips":\s*([-+]?\d*\.\d+|\d+)', line)
            if pips_match:
                pips = float(pips_match.group(1))
                total_pips += pips
                ops_closed['total'] += 1
                
                # Actualizar balance
                # Asumiendo 0.01 lotes = ~0.10 USD/pip para EURUSD micro
                pnl_eur = pips * 0.10  # Aproximación
                new_balance = balance_history[-1] + pnl_eur
                balance_history.append(new_balance)
                
                # Calcular drawdown
                if new_balance > max_balance:
                    max_balance = new_balance
                else:
                    dd = max_balance - new_balance
                    dd_pct = (dd / max_balance) * 100 if max_balance > 0 else 0
                    if dd > max_drawdown:
                        max_drawdown = dd
                        max_drawdown_pct = dd_pct

        # Ciclos
        if 'Main TP detected' in line:
            main_tp_count += 1
        
        if 'is_fully_recovered": true' in line:
            recovery_count += 1

        if 'New dual position_group opened' in line:
            cycles_opened += 1

        # Progreso oficial (Balance real)
        if 'Progreso:' in line:
            m = re.search(r'Balance:\s*(\d+\.\d+)', line)
            e = re.search(r'Equity:\s*(\d+\.\d+)', line)
            if m: 
                balance_final = float(m.group(1))
            if e: 
                equity_final = float(e.group(1))

print(f"Líneas procesadas: {line_count:,}")

# Balance final del último progreso
try:
    balance_final
except:
    balance_final = balance_history[-1] if balance_history else 10000.0
    equity_final = balance_final

print("\n" + "="*60)
print("💰 RESULTADOS FINANCIEROS")
print("="*60)
print(f"   Balance Final:       {balance_final:,.2f} EUR")
print(f"   Equity (Flotante):   {equity_final:,.2f} EUR")
print(f"   Profit Realizado:    {balance_final - 10000:+,.2f} EUR ({(balance_final/100-100):+.1f}%)")
print(f"   Pips Totales:        {total_pips:+,.2f} pips")

print("\n" + "="*60)
print("📉 ANÁLISIS DE RIESGO")
print("="*60)
print(f"   Max Drawdown:        {max_drawdown:,.2f} EUR ({max_drawdown_pct:.2f}%)")
print(f"   Max Balance Peak:    {max_balance:,.2f} EUR")
print(f"   Max Tier Alcanzado:  {max_tier}")
print(f"   Max Lotaje Usado:    {max_lots:.2f}")

print("\n" + "="*60)
print("🔄 ANÁLISIS DE CICLOS")
print("="*60)
print(f"   Ciclos Abiertos:     {cycles_opened}")
print(f"   Main TPs:            {main_tp_count}")
print(f"   Recoveries Full:     {recovery_count}")

print("\n" + "="*60)
print("📊 OPERACIONES POR TIPO")
print("="*60)
for op, count in sorted(ops_opened.items()):
    print(f"   {op:20} {count:,}")
print(f"   {'TOTAL CERRADAS':20} {ops_closed['total']:,}")

print("\n" + "="*60)
print("📅 PERÍODO CUBIERTO")
print("="*60)
if first_date and last_date:
    print(f"   Desde: {first_date}")
    print(f"   Hasta: {last_date}")
    days = (last_date - first_date).days
    print(f"   Días:  {days} (~{days/365:.1f} años)")
else:
    print("   No se pudo determinar el período")

print("\n" + "="*60)
