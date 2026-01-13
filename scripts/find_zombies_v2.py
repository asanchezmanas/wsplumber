import json
import re
from datetime import datetime

LOG_FILE = "audit_logs_2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.log"

def analyze_zombies():
    # cycle_id -> status
    cycle_statuses = {}
    # cycle_id -> close_timestamp
    cycle_close_times = {}
    # child_cycle_id -> parent_cycle_id
    child_to_parent = {}
    
    print(f"Reading {LOG_FILE} (this might take a while)...")
    
    # regexes
    # I'll use simple search for speed, then regex for extraction
    count = 0
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            count += 1
            if count % 100000 == 0:
                print(f"Processed {count} lines...")
                
            # Track parent-child relationships
            if "recovery_after_hedge_tp" in line or "recovery_after_hedge_tp" in line:
                # "id": "...", "metadata": {"parent_cycle": "..."}
                try:
                    match_id = re.search(r'"id": "([^"]+)"', line)
                    match_parent = re.search(r'"parent_cycle": "([^"]+)"', line)
                    if match_id and match_parent:
                        child_to_parent[match_id.group(1)] = match_parent.group(1)
                except: pass

            # Track cycle closures
            if "Cycle closed" in line:
                try:
                    ts_str = line.split(" | ")[0]
                    match_id = re.search(r'"cycle_id": "([^"]+)"', line)
                    if match_id:
                        cid = match_id.group(1)
                        cycle_statuses[cid] = "CLOSED"
                        cycle_close_times[cid] = ts_str
                except: pass

            # Track active operations in broker dumps
            # The broker dumps periodic state like: {"ticket": "4412", "status": "active", "pips": -17.0}
            if '"status": "active"' in line and "Broker Open Positions" in line:
                # We need to know which cycle this operation belongs to.
                # Unfortunately the broker dump doesn't always have cycle_id.
                # But the operation activation log does.
                pass
            
            # Better approach: Look for "Operation activated" logs to map ops to cycles
            if "Operation activated" in line:
                try:
                    match_id = re.search(r'op_id=([^, ]+)', line)
                    match_cycle = re.search(r'cycle_id=([^, ]+)', line) # Wait, is it there?
                    # Let's check the log format
                except: pass

    # Let's simplify: Find any CLOSED parent whose ID is STILL being mentioned in the parent_map
    # of open positions if we find them.
    
    print("\n--- Summary ---")
    closed = [cid for cid, status in cycle_statuses.items() if status == "CLOSED"]
    print(f"Total Cycles marked CLOSED: {len(closed)}")
    
    zombies_found = 0
    for cid in closed:
        # Are there any children for this closed parent?
        children = [child for child, parent in child_to_parent.items() if parent == cid]
        if children:
            print(f"\nParent {cid} is CLOSED at {cycle_close_times[cid]}")
            print(f"  It has {len(children)} child recovery cycles: {children}")
            # Now we'd need to check if these children ever closed. 
            # If they don't appear in cycle_statuses as CLOSED, they are STILL OPEN (Zombies).
            for child in children:
                if cycle_statuses.get(child) != "CLOSED":
                    print(f"  -> CHILD {child} IS STILL OPEN (ZOMBIE)")
                    zombies_found += 1
    
    print(f"\nTotal Zombie Child Cycles Identified: {zombies_found}")

if __name__ == "__main__":
    analyze_zombies()
