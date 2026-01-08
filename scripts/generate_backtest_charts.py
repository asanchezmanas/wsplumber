import json
import re
import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict

# Archivo de logs
audit_file = sys.argv[1] if len(sys.argv) > 1 else 'docs/master_backtest_audit.md'

print(f"📈 Generando gráficos del backtest...")
print(f"Archivo: {audit_file}")

# Datos para gráficos
timestamps = []
balance_curve = []
equity_curve = []
pips_per_trade = []
tier_history = []

current_balance = 10000.0
current_equity = 10000.0

with open(audit_file, 'r', encoding='utf-8') as f:
    for line in f:
        # Balance oficial de progreso
        if 'Progreso:' in line:
            m = re.search(r'Balance:\s*(\d+\.\d+)', line)
            e = re.search(r'Equity:\s*(\d+\.\d+)', line)
            if m:
                current_balance = float(m.group(1))
            if e:
                current_equity = float(e.group(1))
        
        # Cerrar posición -> actualizar curva
        if 'Position closed' in line:
            pips_match = re.search(r'"profit_pips":\s*([-+]?\d*\.\d+|\d+)', line)
            ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            
            if pips_match:
                pips = float(pips_match.group(1))
                pips_per_trade.append(pips)
                
                # Actualizar balance con pips (aprox 0.10 EUR/pip para 0.01 lots)
                current_balance += pips * 0.10
                balance_curve.append(current_balance)
                
                if ts_match:
                    try:
                        dt = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
                        timestamps.append(dt)
                    except:
                        pass
        
        # Tier history
        tier_match = re.search(r'"tier":\s*(\d+)', line)
        if tier_match:
            tier_history.append(int(tier_match.group(1)))

print(f"Trades analizados: {len(pips_per_trade)}")

# Crear figura con subplots
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('📊 WSPlumber Backtest Analysis (Dic 2014 - Ene 2015)', fontsize=14, fontweight='bold')

# 1. Equity Curve
ax1 = axes[0, 0]
if timestamps and len(timestamps) == len(balance_curve):
    ax1.plot(timestamps, balance_curve, 'g-', linewidth=1.5, label='Balance')
    ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Inicio')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
else:
    ax1.plot(balance_curve, 'g-', linewidth=1.5)
    ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5)
ax1.set_title('💰 Equity Curve')
ax1.set_ylabel('Balance (EUR)')
ax1.grid(True, alpha=0.3)
ax1.legend()

# 2. Distribución de Pips por Trade
ax2 = axes[0, 1]
if pips_per_trade:
    colors = ['green' if p > 0 else 'red' for p in pips_per_trade]
    ax2.hist(pips_per_trade, bins=50, color='steelblue', edgecolor='white', alpha=0.7)
    ax2.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    avg_pips = sum(pips_per_trade) / len(pips_per_trade)
    ax2.axvline(x=avg_pips, color='green', linestyle='-', label=f'Media: {avg_pips:.1f} pips')
ax2.set_title('📊 Distribución de Pips por Trade')
ax2.set_xlabel('Pips')
ax2.set_ylabel('Frecuencia')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Tier Usage
ax3 = axes[1, 0]
if tier_history:
    tier_counts = defaultdict(int)
    for t in tier_history:
        tier_counts[t] += 1
    tiers = sorted(tier_counts.keys())
    counts = [tier_counts[t] for t in tiers]
    ax3.bar(tiers, counts, color='orange', edgecolor='white')
    ax3.set_title('⚠️ Niveles de Recovery Usados')
    ax3.set_xlabel('Tier')
    ax3.set_ylabel('Frecuencia')
    ax3.grid(True, alpha=0.3, axis='y')

# 4. Cumulative Pips
ax4 = axes[1, 1]
if pips_per_trade:
    cumulative = []
    total = 0
    for p in pips_per_trade:
        total += p
        cumulative.append(total)
    ax4.plot(cumulative, 'b-', linewidth=1)
    ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax4.fill_between(range(len(cumulative)), cumulative, 0, 
                     where=[c > 0 for c in cumulative], color='green', alpha=0.3)
    ax4.fill_between(range(len(cumulative)), cumulative, 0, 
                     where=[c <= 0 for c in cumulative], color='red', alpha=0.3)
ax4.set_title('📈 Pips Acumulados')
ax4.set_xlabel('# Trade')
ax4.set_ylabel('Pips Acumulados')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
output_path = 'docs/backtest_analysis_charts.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✅ Gráfico guardado en: {output_path}")

# Mostrar resumen
print("\n" + "="*50)
print("📊 RESUMEN ESTADÍSTICO")
print("="*50)
if pips_per_trade:
    wins = [p for p in pips_per_trade if p > 0]
    losses = [p for p in pips_per_trade if p < 0]
    print(f"   Total Trades: {len(pips_per_trade)}")
    print(f"   Ganadores:    {len(wins)} ({100*len(wins)/len(pips_per_trade):.1f}%)")
    print(f"   Perdedores:   {len(losses)} ({100*len(losses)/len(pips_per_trade):.1f}%)")
    print(f"   Media Pips:   {sum(pips_per_trade)/len(pips_per_trade):+.2f}")
    print(f"   Max Win:      {max(pips_per_trade):+.2f} pips")
    print(f"   Max Loss:     {min(pips_per_trade):+.2f} pips")
if tier_history:
    print(f"   Max Tier:     {max(tier_history)}")
print("="*50)

plt.show()
