
import re

log_file = "audit_logs_2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc_ticks.log"

pattern = re.compile(r"^\s*(\d+,?\d*)\s*\|\s*[\d\.]+\s*\|\s*[\d\.]+\s*\|\s*[\d\.-]+%\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|")

print(f"{'TICK':>10} | {'Act':>4} | {'Hdg':>4} | {'Total':>5}")
print("-" * 35)

with open(log_file, "r") as f:
    for line in f:
        match = pattern.match(line)
        if match:
            tick = match.group(1).replace(",", "")
            act = int(match.group(2))
            hdg = int(match.group(3))
            total = act + hdg
            if total > 1:
                print(f"{tick:>10} | {act:>4} | {hdg:>4} | {total:>5}")
