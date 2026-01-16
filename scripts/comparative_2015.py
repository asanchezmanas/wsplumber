import asyncio
import os
import json
import sys
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(root_path / "src"))

from wsplumber.application.services.backtest_service import backtest_service
from wsplumber.core.strategy import _params

async def run_2015_test(mode: str):
    print(f"\n🚀 STARTING 2015 BACKTEST | Mode: {mode}")
    
    # 1. Update params dynamically
    _params.LAYER1_MODE = mode
    
    csv_path = "data/partitions/EURUSD_2015.parquet"
    
    results = []
    async for progress in backtest_service.run_streaming(
        csv_path=csv_path,
        pair="EURUSD",
        report_interval=20000
    ):
        if progress.status == "running":
            print(f"  [Progress] Tick: {progress.tick:,} | Balance: {progress.balance:.2f} | Eq: {progress.equity:.2f} | DD: {progress.drawdown_pct:.1f}%")
        results.append(progress.to_dict())
        
    final = results[-1]
    
    # Extract cycle stats from final record
    stats = {
        "final_balance": final["balance"],
        "final_equity": final["equity"],
        "net_profit": round(final["balance"] - 10000.0, 2),
        "max_drawdown": final["drawdown_pct"],
        "main_cycles_closed": final["closed_cycles"],
        "main_tps": final["main_tps"],
        "recovery_tps": final["recovery_tps"]
    }
    
    output_path = f"results_2015_{mode.lower()}.json"
    with open(output_path, "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"✅ FINISHED {mode} | Results saved to {output_path}")
    return stats

async def main():
    # Run Baseline (OFF)
    baseline_stats = await run_2015_test("OFF")
    
    # Run Layer 1 (ADAPTIVE_TRAILING)
    layer1_stats = await run_2015_test("ADAPTIVE_TRAILING")
    
    print("\n" + "="*60)
    print("📋 COMPARATIVE SUMMARY: EURUSD 2015")
    print("="*60)
    print(f"{'Metric':<25} | {'Baseline (OFF)':<15} | {'Layer 1 (L1)':<15}")
    print("-" * 60)
    
    metrics = [
        ("Final Balance", "final_balance"),
        ("Final Equity", "final_equity"),
        ("Net Profit", "net_profit"),
        ("Max Drawdown %", "max_drawdown"),
        ("Main Cycles Closed", "main_cycles_closed"),
        ("Main TPs", "main_tps"),
        ("Recovery TPs", "recovery_tps")
    ]
    
    for label, key in metrics:
        v1 = baseline_stats[key]
        v2 = layer1_stats[key]
        print(f"{label:<25} | {v1:<15} | {v2:<15}")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
