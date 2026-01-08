"""
Análisis WSPlumber - Drawdown Real y Cola FIFO
Mide las deudas activas (Mains/Hedges neutralizados esperando resolución)
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime

audit_file = sys.argv[1] if len(sys.argv) > 1 else 'docs/master_backtest_audit.md'

print(f"📊 ANÁLISIS WSPLUMBER - DRAWDOWN REAL Y COLA FIFO")
print(f"Archivo: {audit_file}")
print("="*60)

# Estado del sistema
balance = 10000.0
open_positions = {}  # op_id -> {type, entry_price, pips_locked, timestamp}
fifo_queue = []  # Lista de deudas pendientes [(debt_id, pips, timestamp)]
closed_with_profit = []  # Lista de cierres exitosos

# Métricas de drawdown
max_floating_loss = 0.0
current_floating_loss = 0.0
max_fifo_size = 0
max_tier = 0

# Contadores
main_tps = 0
recovery_tps = 0
hedges_activated = 0
full_recoveries = 0

# Timeline para gráfico
equity_timeline = []
fifo_timeline = []
timestamps = []

print("Procesando logs...")

with open(audit_file, 'r', encoding='utf-8') as f:
    for line in f:
        # 1. Detectar activación de operaciones
        if 'Operation activated' in line:
            op_match = re.search(r'"op_id":\s*"([^"]+)"', line)
            type_match = re.search(r'"op_type":\s*"([^"]+)"', line)
            price_match = re.search(r'"fill_price":\s*"([^"]+)"', line)
            
            if op_match and type_match:
                op_id = op_match.group(1)
                op_type = type_match.group(1)
                price = float(price_match.group(1)) if price_match else 0
                
                open_positions[op_id] = {
                    'type': op_type,
                    'entry_price': price,
                    'pips_locked': 0
                }
                
                if 'hedge' in op_type:
                    hedges_activated += 1
                    # Un hedge significa que hay una deuda de ~20 pips
                    current_floating_loss += 20.0
                    fifo_queue.append((op_id, 20.0, 'hedge'))
        
        # 2. Detectar TPs de Recovery (resuelven deudas)
        if 'correction TP hit' in line or 'FIFO Summary' in line:
            # Buscar pips usados para cerrar deudas
            used_match = re.search(r'"pips_used":\s*(\d+\.?\d*)', line)
            profit_match = re.search(r'"pips_profit":\s*(\d+\.?\d*)', line)
            recovered_match = re.search(r'"is_fully_recovered":\s*true', line)
            
            if used_match:
                pips_used = float(used_match.group(1))
                # Cada 40 pips usados = 1 deuda cerrada
                debts_closed = int(pips_used / 40) if pips_used >= 40 else (1 if pips_used >= 20 else 0)
                for _ in range(debts_closed):
                    if fifo_queue:
                        closed_debt = fifo_queue.pop(0)
                        current_floating_loss -= closed_debt[1]
            
            if recovered_match:
                full_recoveries += 1
        
        # 3. Detectar TPs de Main
        if 'Main TP detected' in line:
            main_tps += 1
            balance += 1.0  # ~1€ por TP de Main con 0.01 lotes
        
        # 4. Detectar TPs de Recovery
        if 'Position closed' in line and 'recovery' in line.lower():
            pips_match = re.search(r'"profit_pips":\s*(\d+\.?\d*)', line)
            if pips_match:
                pips = float(pips_match.group(1))
                if pips > 50:  # Es un Recovery (TP de 80 pips)
                    recovery_tps += 1
                    balance += 8.0  # ~8€ por Recovery
        
        # 5. Detectar tier máximo
        tier_match = re.search(r'"tier":\s*(\d+)', line)
        if tier_match:
            tier = int(tier_match.group(1))
            if tier > max_tier:
                max_tier = tier
        
        # 6. Actualizar métricas de drawdown
        if current_floating_loss > max_floating_loss:
            max_floating_loss = current_floating_loss
        
        if len(fifo_queue) > max_fifo_size:
            max_fifo_size = len(fifo_queue)

# Calcular equity final
equity = balance - current_floating_loss

print(f"\n{'='*60}")
print("💰 RESULTADOS FINANCIEROS")
print("="*60)
print(f"   Balance:              {balance:,.2f} EUR (ganancias realizadas)")
print(f"   Floating Loss:        {current_floating_loss:,.2f} EUR (deudas activas)")
print(f"   Equity (Neto):        {equity:,.2f} EUR")
print(f"   Profit Realizado:     {balance - 10000:+,.2f} EUR")

print(f"\n{'='*60}")
print("📉 ANÁLISIS DE DRAWDOWN REAL")
print("="*60)
print(f"   Max Floating Loss:    {max_floating_loss:,.2f} EUR")
print(f"   Max Drawdown %:       {(max_floating_loss/10000)*100:.2f}%")
print(f"   Deudas Activas Ahora: {len(fifo_queue)}")
print(f"   Max Cola FIFO:        {max_fifo_size} deudas simultáneas")
print(f"   Max Tier Alcanzado:   {max_tier}")

print(f"\n{'='*60}")
print("🔄 ANÁLISIS DE CICLOS")
print("="*60)
print(f"   Main TPs:             {main_tps} (+{main_tps}€ aprox)")
print(f"   Recovery TPs:         {recovery_tps} (+{recovery_tps * 8}€ aprox)")
print(f"   Hedges Activados:     {hedges_activated}")
print(f"   Recoveries Full:      {full_recoveries}")

print(f"\n{'='*60}")
print("📊 DEUDAS EN COLA FIFO (Actuales)")
print("="*60)
if fifo_queue:
    for i, (debt_id, pips, debt_type) in enumerate(fifo_queue[:10]):
        print(f"   {i+1}. {debt_type:10} | {pips:.0f} pips | {debt_id[:30]}...")
    if len(fifo_queue) > 10:
        print(f"   ... y {len(fifo_queue) - 10} más")
else:
    print("   ✅ Cola vacía - Sin deudas pendientes")

# Calcular ratio de eficiencia
if hedges_activated > 0:
    efficiency = (full_recoveries / hedges_activated) * 100
    print(f"\n{'='*60}")
    print("📈 EFICIENCIA DEL SISTEMA")
    print("="*60)
    print(f"   Ratio Hedge/Recovery: {hedges_activated}:{full_recoveries}")
    print(f"   Tasa Resolución:      {efficiency:.1f}%")
    print(f"   Deudas sin resolver:  {hedges_activated - full_recoveries}")
    
print("="*60)
