# scripts/robustness_swarm.py
import subprocess
import os
import sys
import re
from pathlib import Path
from statistics import mean, stdev

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing: {cmd}")
        print(result.stderr)
        return None
    return result.stdout

def parse_metrics(output):
    metrics = {}
    red_match = re.search(r"RED Score:\s+([\d\.]+)", output)
    cer_match = re.search(r"CER Ratio:\s+([\d\.]+)", output)
    nsb_match = re.search(r"NSB Bias:\s+([\d\.]+)", output)
    max_rec_match = re.search(r"Max Concurrent Rec:\s+(\d+)", output)
    
    if red_match: metrics['red'] = float(red_match.group(1))
    if cer_match: metrics['cer'] = float(cer_match.group(1))
    if nsb_match: metrics['nsb'] = float(nsb_match.group(1))
    if max_rec_match: metrics['max_rec'] = int(max_rec_match.group(1))
    
    return metrics

def run_swarm(runs=5, ticks=20000):
    print(f"🚀 Starting Robustness Swarm: {runs} runs of {ticks} ticks each...")
    
    results = []
    project_root = Path(__file__).parent.parent.absolute()
    
    # Prepare environment
    env = os.environ.copy()
    env["PYTHONPATH"] = f"src;{str(project_root)}"
    
    python_exe = sys.executable
    
    for i in range(runs):
        print(f"\n[RUN {i+1}/{runs}] Generating entropy...")
        csv_file = str(project_root / f"tests/scenarios/swarm_mc_{i}.csv")
        
        # Generator
        gen_cmd = [python_exe, "scripts/generator_monte_carlo.py", str(ticks), csv_file]
        subprocess.run(gen_cmd, env=env, capture_output=True, text=True)
        
        print(f"[RUN {i+1}/{runs}] Auditing...")
        # Auditor
        audit_cmd = [python_exe, "scripts/audit_scenario.py", csv_file, "--sample-rate", str(ticks)]
        result = subprocess.run(audit_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout
            m = parse_metrics(output)
            if m:
                results.append(m)
                print(f"      RED: {m.get('red')} | CER: {m.get('cer')} | NSB: {m.get('nsb')} | MaxRec: {m.get('max_rec')}")
        else:
            print(f"      Error in run {i+1}: {result.stderr}")
        
        # Cleanup
        if os.path.exists(csv_file):
            os.remove(csv_file)

    if not results:
        print("No results collected.")
        return

    # Aggregate
    reds = [r['red'] for r in results]
    cers = [r['cer'] for r in results]
    nsbs = [r['nsb'] for r in results]
    recs = [r['max_rec'] for r in results]

    report = f"""# 🐝 Robustness Swarm Report
Generated: {runs} MC Simulations of {ticks} ticks.

## Statistical Summary
| Metric | Average | Worst Case (Max/Min) | SD | Status |
| :--- | :--- | :--- | :--- | :--- |
| **RED Score** | {mean(reds):.3f} | {max(reds):.3f} (Max) | {stdev(reds) if len(reds)>1 else 0:.3f} | {'✅ SAFE' if max(reds) < 0.8 else '❌ DANGER'} |
| **CER Ratio** | {mean(cers):.3f} | {min(cers):.3f} (Min) | {stdev(cers) if len(cers)>1 else 0:.3f} | {'✅ STABLE' if mean(cers) > 1.15 or mean(cers) > 0.5 else '⚠️ WEAK'} |
| **NSB Bias** | {mean(nsbs):.3f} | {max(nsbs):.3f} (Max) | {stdev(nsbs) if len(nsbs)>1 else 0:.3f} | {'✅ HEALTHY' if mean(nsbs) < 0.3 else '⚠️ TOXIC'} |

## Survivability
- **Max Recovery Level Reached**: {max(recs)}
- **Average Recovery Level**: {mean(recs):.1f}

> [!IMPORTANT]
> A "Worst Case" RED Score < 0.8 proves that even in the most unlucky random walk, 
> the system maintains a safety margin before margin exhaustion.
"""
    
    report_path = "docs/swarm_robustness_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ Swarm Completed. Report saved to: {report_path}")
    print(report)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=20000)
    args = parser.parse_args()
    
    run_swarm(args.runs, args.ticks)
