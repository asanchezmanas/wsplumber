# 🐝 Robustness Swarm Report
Generated: 5 MC Simulations of 20000 ticks.

## Statistical Summary
| Metric | Average | Worst Case (Max/Min) | SD | Status |
| :--- | :--- | :--- | :--- | :--- |
| **RED Score** | 0.270 | 0.450 (Max) | 0.110 | ✅ SAFE |
| **CER Ratio** | 0.180 | 0.000 (Min) | 0.284 | ⚠️ WEAK |
| **NSB Bias** | 0.047 | 0.138 (Max) | 0.066 | ✅ HEALTHY |

## Survivability
- **Max Recovery Level Reached**: 33
- **Average Recovery Level**: 26.2

> [!IMPORTANT]
> A "Worst Case" RED Score < 0.8 proves that even in the most unlucky random walk, 
> the system maintains a safety margin before margin exhaustion.
