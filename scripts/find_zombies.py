import json
import re

LOG_FILE = "audit_logs_2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.log"

def analyze_zombies():
    # Maps cycle_id -> status
    cycles = {}
    # Maps operation_id -> {cycle_id, status, type}
    operations = {}
    # Maps recovery_cycle_id -> parent_cycle_id
    parent_map = {}
    
    # regex for "Cycle transitioned to IN_RECOVERY" with parent info
    # 2026-01-13 10:33:47,060 | INFO | wsplumber ... | Cycle transitioned to IN_RECOVERY {"cycle_id": "...", ...}
    
    print(f"Analyzing {LOG_FILE}...")
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if "Cycle transitioned to IN_RECOVERY" in line:
                 # Extract data
                 try:
                    data_str = line.split("|")[-1].strip()
                    # Some logs are formatted differently, let's try a safer way
                    match = re.search(r'Cycle transitioned to IN_RECOVERY (\{.*\})', line)
                    if match:
                        data = json.loads(match.group(1))
                        cid = data.get("cycle_id")
                        cycles[cid] = "IN_RECOVERY"
                 except: pass

            if "Cycle closed" in line:
                match = re.search(r'Cycle closed .* (\{.*\})', line)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        cid = data.get("cycle_id")
                        cycles[cid] = "CLOSED"
                    except: pass
            
            # Watch for child cycle creation
            # "metadata\": {\"reason\": \"recovery_after_hedge_tp\", \"parent_cycle\": \"..."
            if "recovery_after_hedge_tp" in line:
                match = re.search(r'\"parent_cycle\": \"([^\"]+)\"', line)
                cid_match = re.search(r'\"id\": \"([^\"]+)\"', line) # This might be the child
                if match and cid_match:
                    parent_map[cid_match.group(1)] = match.group(0)

    # Now find CLOSED cycles that have children that are NOT closed
    print("\n--- Potential Zombie Parent Cycles (CLOSED) ---")
    closed_parents = [cid for cid, status in cycles.items() if status == "CLOSED"]
    print(f"Total closed cycles found: {len(closed_parents)}")
    
    # List a few
    for cid in closed_parents[:10]:
        print(f"Closed Cycle: {cid}")

if __name__ == "__main__":
    analyze_zombies()
