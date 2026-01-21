import json
from decimal import Decimal

def analyze_zombie_cycles(filepath='last_positions.json'):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        cycles = data.get('cycles', {})
        if not cycles:
            print("No cycles found in JSON.")
            return

        print(f"Analyzing {len(cycles)} cycles...")
        
        in_recovery = [c for c in cycles.values() if c.get('status') == 'in_recovery']
        print(f"Found {len(in_recovery)} cycles in 'in_recovery' state.")
        
        for c in in_recovery:
            id = c.get('id')
            acc = c.get('accounting', {})
            remaining = acc.get('pips_remaining', 'UNKNOWN')
            debt_units = acc.get('debt_units', [])
            recovered = acc.get('pips_recovered', 0)
            
            print(f"\nCycle: {id}")
            print(f"  Pips Remaining: {remaining}")
            print(f"  Debt Units: {debt_units}")
            print(f"  Pips Recovered: {recovered}")
            
            # Check for operations
            ops = [o for o in data.get('operations', {}).values() if o.get('cycle_id') == id]
            active_ops = [o for o in ops if o.get('status') == 'active' or o.get('status') == 'neutralized']
            print(f"  Open Ops in Broker: {len(active_ops)}")
            for o in active_ops:
                print(f"    - {o.get('id')} ({o.get('op_type')}) Status: {o.get('status')} Ticket: {o.get('broker_ticket')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_zombie_cycles()
