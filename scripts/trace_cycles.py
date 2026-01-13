import re
import json

LOG_FILE = "audit_logs_2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.log"

def trace_cycles():
    cycles = {} # cycle_id -> {events: []}
    
    print(f"Reading {LOG_FILE}...")
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # New cycle
            if "New dual cycle opened" in line:
                match = re.search(r'cycle_id=([^, ]+)', line)
                if match:
                    cid = match.group(1).strip('"')
                    cycles[cid] = {"status": "OPENED", "events": []}
            
            # Transition to IN_RECOVERY
            if "Cycle transitioned to IN_RECOVERY" in line:
                match = re.search(r'cycle_id=([^, ]+)', line)
                if match:
                    cid = match.group(1).strip('"')
                    if cid not in cycles: cycles[cid] = {"events": []}
                    cycles[cid]["status"] = "IN_RECOVERY"
            
            # Cycle closed
            if "Cycle closed" in line:
                match = re.search(r'cycle_id=([^, ]+)', line)
                if match:
                    cid = match.group(1).strip('"')
                    if cid not in cycles: cycles[cid] = {"events": []}
                    cycles[cid]["status"] = "CLOSED"

    print("\n--- Cycle Summary ---")
    status_counts = {}
    for cid, info in cycles.items():
        status = info.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
        # if status != "CLOSED":
        #    print(f"  {cid}: {status}")

    for status, count in status_counts.items():
        print(f"{status}: {count}")
    
    if "CLOSED" not in status_counts:
        print("\nWARNING: NO CYCLES WERE CLOSED!")

if __name__ == "__main__":
    trace_cycles()
