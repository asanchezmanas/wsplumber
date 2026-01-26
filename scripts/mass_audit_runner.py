
import asyncio
import sys
import os
import csv
from pathlib import Path
import logging
import time

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from audit_by_cycle import run_audit

async def batch_audit():
    input_dirs = [
        "tests/scenarios/factorial",
        "tests/scenarios/truth",
        "tests/scenarios" # Root scenarios like f01, h01, r01, j01
    ]
    
    output_dir = Path("reports/mass_audit")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary_file = output_dir / "mass_audit_summary.csv"
    
    # Priority patterns (as requested by user)
    priority_patterns = ["f0", "h0", "r0", "j0", "factorial"]
    
    files_to_process = []
    for d in input_dirs:
        dir_path = Path(d)
        if not dir_path.exists():
            continue
            
        # Get only immediate files if it's the root scenarios dir, or recursive if specifically requested
        patterns = ["*.csv", "*.parquet"]
        for p in patterns:
            if d == "tests/scenarios":
                # Only direct children for the root scenarios dir to avoid re-processing subdirs
                files_to_process.extend(list(dir_path.glob(p)))
            else:
                files_to_process.extend(list(dir_path.rglob(p)))

    # Filter out large files and duplicates
    # SCENARIO LIMIT: 1MB (enough for thousands of ticks, excludes GB production data)
    MAX_SIZE = 1024 * 1024 
    
    files_to_process = [f for f in files_to_process if f.stat().st_size < MAX_SIZE]
    
    # Remove duplicates by absolute path
    seen_paths = set()
    unique_files = []
    for f in files_to_process:
        abs_p = str(f.absolute())
        if abs_p not in seen_paths:
            seen_paths.add(abs_p)
            unique_files.append(f)
    
    files_to_process = unique_files
    print(f"Found {len(files_to_process)} scenarios to audit.")

    results = []
    start_time = time.time()

    for i, file_path in enumerate(files_to_process):
        rel_path = file_path.relative_to(Path().absolute().parent if "Artur" in str(Path()) else Path())
        print(f"[{i+1}/{len(files_to_process)}] Auditing {file_path.name}...", end="\r")
        
        try:
            # We run run_audit which already saves audit_report_{stem}.txt in CWD
            # We want them in reports/mass_audit/
            audit_res = await run_audit(500, str(file_path), quiet=True)
            
            # Move the generated report
            report_name = f"audit_report_{file_path.stem}.txt"
            generated_report = Path(report_name)
            target_report = output_dir / report_name
            
            if generated_report.exists():
                if target_report.exists():
                    target_report.unlink()
                generated_report.rename(target_report)

            results.append({
                "scenario": file_path.name,
                "folder": file_path.parent.name,
                "pnl": audit_res.get("pnl", 0.0),
                "status": "OK",
                "report": str(target_report)
            })
        except Exception as e:
            results.append({
                "scenario": file_path.name,
                "folder": file_path.parent.name,
                "pnl": 0.0,
                "status": f"ERROR: {str(e)}",
                "report": ""
            })

    print(f"\nAudit complete in {time.time() - start_time:.2f} seconds.")

    # Write summary
    with open(summary_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "folder", "pnl", "status", "report"])
        writer.writeheader()
        writer.writerows(results)

    print(f"Summary saved to {summary_file}")
    
    # Print statistics
    success_count = sum(1 for r in results if r["status"] == "OK")
    error_count = len(results) - success_count
    total_pnl = sum(r["pnl"] for r in results)
    
    print(f"\nSTATISTICS:")
    print(f"- Total Scenarios: {len(results)}")
    print(f"- Success: {success_count}")
    print(f"- Errors: {error_count}")
    print(f"- Accumulated PnL: {total_pnl:+.2f} EUR")

if __name__ == "__main__":
    asyncio.run(batch_audit())
