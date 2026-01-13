import re

LOG_FILE = "audit_logs_2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.log"

def analyze():
    counts = {
        "New Main Cycle": 0,
        "Recovery Cycle Opened": 0,
        "Cycle Closed": 0,
        "Main TP Detected": 0,
        "Recovery TP Detected": 0
    }
    
    examples = []
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if "New dual cycle opened" in line: counts["New Main Cycle"] += 1
            if "Recovery cycle opened" in line: counts["Recovery Cycle Opened"] += 1
            if "Cycle closed" in line: 
                counts["Cycle Closed"] += 1
                if len(examples) < 5: examples.append(line.strip())
            if "Main TP detected" in line: counts["Main TP Detected"] += 1
            if "Recovery TP hit" in line: counts["Recovery TP Detected"] += 1
            
    print("\n--- STATISTICS ---")
    for k, v in counts.items():
        print(f"{k}: {v}")
    
    print("\n--- EXAMPLES OF CLOSED CYCLES ---")
    if not examples:
        print("None found.")
    else:
        for ex in examples:
            print(ex)

if __name__ == "__main__":
    analyze()
