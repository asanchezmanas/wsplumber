import json
import re
import os
from collections import Counter

max_tier = 0
max_lots = 0.0
recovery_count = 0
total_pips = 0.0
main_tp_count = 0

# Operation counters
ops_opened = Counter() # Type -> Count
ops_closed = Counter() # Type -> Count

# Cycle counters
cycles_opened = 0
active_cycles = set()

import sys

# Permitir pasar archivo por argumento
audit_file = sys.argv[1] if len(sys.argv) > 1 else 'docs/audit_backtest_output.md'
if not os.path.exists(audit_file):
    if os.path.exists('docs/master_backtest_audit.md'):
        audit_file = 'docs/master_backtest_audit.md'

print(f"Analizando logs: {audit_file}...")

with open(audit_file, 'r', encoding='utf-8') as f:
    for line in f:
        # 1. Tier y Lotes
        tier_match = re.search(r'\"tier\":\s*(\d+)', line)
        if tier_match:
            tier = int(tier_match.group(1))
            if tier > max_tier: max_tier = tier
        
        lot_match = re.search(r'\"lot\":\s*(\d*\.\d+|\d+)', line)
        if lot_match:
            lot = float(lot_match.group(1))
            if lot > max_lots: max_lots = lot

        # 2. Operaciones Abiertas
        if 'Operation activated' in line:
            m = re.search(r'\"op_type\":\s*\"([^\"]+)\"', line)
            if m:
                op_type = m.group(1)
                ops_opened[op_type] += 1

        # 3. Operaciones Cerradas (Profit Pips)
        if 'profit_pips\":' in line and ('Position closed' in line or 'marked as TP_HIT' in line):
            # Intentar capturar el tipo de operacion desde el ID si es posible o simplemente contar
            pips_match = re.search(r'\"profit_pips\":\s*([-+]?\d*\.\d+|\d+)', line)
            if pips_match:
                total_pips += float(pips_match.group(1))
                ops_closed['total'] += 1

        # 4. Ciclos y Recuperaciones
        if 'Main TP detected' in line:
            main_tp_count += 1
        
        if 'is_fully_recovered\": true' in line:
            recovery_count += 1

        if '*** INICIANDO NUEVO CICLO ***' in line or 'New cycle initialized' in line or 'New dual position_group opened' in line:
            cycles_opened += 1
        
        # Si no hay "iniciando nuevo ciclo", contar por el ID del primer main si es posible
        # Pero mejor buscar esta cadena que es estandar en nuestros logs

# Intentar extraer Balance final del ultimo progreso
balance_final = 0
equity_final = 0
with open(audit_file, 'r', encoding='utf-8') as f:
    for line in reversed(list(f)):
        if 'Progreso:' in line:
            m = re.search(r'Balance:\s*(\d+\.\d+)', line)
            e = re.search(r'Equity:\s*(\d+\.\d+)', line)
            if m: balance_final = float(m.group(1))
            if e: equity_final = float(e.group(1))
            break

print(f"\n" + "="*40)
print(f"RESUMEN DETALLADO DEL BACKTEST")
print(f"="*40)
print(f"💰 RESULTADOS FINANCIEROS (al 70%):")
print(f"   Balance Final: {balance_final:.2f} EUR")
print(f"   Equity (Neto): {equity_final:.2f} EUR")
print(f"   Profit Acumulado: {balance_final - 10000:.2f} EUR (+{(balance_final/100 - 100):.1f}%)")
print(f"   Total Pips Realizados: {total_pips:,.2f} pips")

print(f"\n🔄 ANÁLISIS DE CICLOS:")
print(f"   Ciclos Main Abiertos: {cycles_opened}")
print(f"   Ciclos Main en TP: {main_tp_count}")
print(f"   Ciclos de Recovery Full: {recovery_count}")
print(f"   Ciclos que requirieron Recovery: {cycles_opened - main_tp_count}")

print(f"\n📊 OPERACIONES POR TIPO (Activadas):")
for op, count in ops_opened.items():
    print(f"   - {op}: {count}")

print(f"\n⚠️ RIESGO Y LÍMITES:")
print(f"   Tier Máximo alcanzado: {max_tier}")
print(f"   Lotaje Máximo usado: {max_lots:.2f}")
print(f"="*40 + "\n")
