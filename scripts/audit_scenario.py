"""
WSPlumber - Enhanced Scenario Auditor with Charts
Usage: python scripts/audit_scenario.py tests/scenarios/r07_cascade_n1_n2_n3.csv

Features:
- Detailed live metrics (cycles, recoveries, mains hit, hedged, etc.)
- Time-series data collection for charting
- Matplotlib chart generation (equity/balance + drawdown)
"""
import asyncio
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair, CycleStatus
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from scripts.audit_by_cycle import CycleAuditor


@dataclass
class AuditMetrics:
    """Collects detailed metrics for analysis and charting."""
    
    # Time-series data (sampled every N ticks)
    ticks: List[int] = field(default_factory=list)
    balances: List[float] = field(default_factory=list)
    equities: List[float] = field(default_factory=list)
    drawdowns: List[float] = field(default_factory=list)
    pips: List[float] = field(default_factory=list)
    
    # Peak tracking for drawdown calculation
    peak_equity: float = 10000.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Cumulative stats
    total_cycles_created: int = 0
    total_cycles_closed: int = 0
    total_mains_hit: int = 0
    total_recovery_tps: int = 0
    max_recoveries_per_cycle: int = 0
    max_concurrent_cycles: int = 0
    max_concurrent_recoveries: int = 0
    
    def update(self, tick: int, balance: float, equity: float, pips: float,
               cycles_open: int, cycles_closed: int, recoveries: int, 
               mains_hit: int = 0, max_rec: int = 0):
        """Update metrics with new data point."""
        self.ticks.append(tick)
        self.balances.append(balance)
        self.equities.append(equity)
        self.pips.append(pips)
        
        # Update peak and drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        current_dd = self.peak_equity - equity
        current_dd_pct = (current_dd / self.peak_equity) * 100 if self.peak_equity > 0 else 0
        self.drawdowns.append(current_dd)
        
        if current_dd > self.max_drawdown:
            self.max_drawdown = current_dd
            self.max_drawdown_pct = current_dd_pct
        
        # Update maximums
        self.total_cycles_closed = cycles_closed
        self.total_mains_hit = mains_hit
        self.max_recoveries_per_cycle = max(self.max_recoveries_per_cycle, max_rec)
        self.max_concurrent_cycles = max(self.max_concurrent_cycles, cycles_open)
        self.max_concurrent_recoveries = max(self.max_concurrent_recoveries, recoveries)
    
    def generate_chart(self, output_path: str = "audit_chart.png"):
        """Generate equity/balance chart with drawdown bars."""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            from matplotlib.ticker import FuncFormatter
            import numpy as np
        except ImportError:
            print("[WARN] matplotlib not installed. Skipping chart generation.")
            print("       Install with: pip install matplotlib")
            return False
        
        if len(self.ticks) < 2:
            print("[WARN] Not enough data points for chart.")
            return False
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1], sharex=True)
        fig.suptitle('WSPlumber Stress Test Results', fontsize=14, fontweight='bold')
        
        # Top chart: Equity and Balance
        ax1.plot(self.ticks, self.equities, label='Equity', color='#2196F3', linewidth=1.5, alpha=0.9)
        ax1.plot(self.ticks, self.balances, label='Balance', color='#4CAF50', linewidth=1.5, alpha=0.9)
        ax1.fill_between(self.ticks, self.equities, self.balances, 
                         where=[e < b for e, b in zip(self.equities, self.balances)],
                         alpha=0.3, color='red', label='Floating Loss')
        ax1.fill_between(self.ticks, self.equities, self.balances,
                         where=[e >= b for e, b in zip(self.equities, self.balances)],
                         alpha=0.3, color='green', label='Floating Profit')
        
        ax1.set_ylabel('EUR', fontsize=10)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(left=0)
        
        # Format y-axis as currency
        ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        
        # Bottom chart: Drawdown bars
        ax2.bar(self.ticks, self.drawdowns, color='#f44336', alpha=0.7, width=max(1, len(self.ticks)//200))
        ax2.axhline(y=self.max_drawdown, color='darkred', linestyle='--', 
                    label=f'Max DD: {self.max_drawdown:,.0f} EUR ({self.max_drawdown_pct:.1f}%)')
        ax2.set_xlabel('Tick', fontsize=10)
        ax2.set_ylabel('Drawdown (EUR)', fontsize=10)
        ax2.legend(loc='upper right', fontsize=9)
        ax2.grid(True, alpha=0.3)
        ax2.invert_yaxis()  # Drawdown is negative conceptually
        
        # Add stats annotation
        final_balance = self.balances[-1] if self.balances else 0
        final_pips = self.pips[-1] if self.pips else 0
        stats_text = (
            f"Final: {final_balance:,.0f} EUR | "
            f"Pips: +{final_pips:,.0f} | "
            f"Max DD: {self.max_drawdown_pct:.1f}%"
        )
        fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10, 
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"[OK] Chart saved to: {output_path}")
        return True


async def audit_scenario(csv_path_str: str, log_level: str = "INFO", sample_rate: int = 500):
    import logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    logging.basicConfig(level=numeric_level, format='%(message)s')
    
    # SILENCE INTERNAL LOGGERS
    logging.getLogger("wsplumber").setLevel(logging.CRITICAL)
    logging.getLogger("wsplumber.core").setLevel(logging.CRITICAL)
    logging.getLogger("wsplumber.application").setLevel(logging.CRITICAL)
    logging.getLogger("tests.fixtures.simulated_broker").setLevel(logging.CRITICAL)
    
    csv_path = Path(csv_path_str)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return

    # Detect pair
    pair_str = "EURUSD"
    if "JPY" in csv_path_str.upper(): pair_str = "USDJPY"
    if "GBP" in csv_path_str.upper(): pair_str = "GBPUSD"
    pair = CurrencyPair(pair_str)

    # Setup
    broker = SimulatedBroker(initial_balance=10000.0)
    broker.load_csv(str(csv_path))
    await broker.connect()

    repo = InMemoryRepository()
    trading_service = TradingService(broker, repo)
    risk_manager = RiskManager()
    strategy = WallStreetPlumberStrategy()
    
    # Mock settings for risk manager/strategy
    from unittest.mock import MagicMock, patch
    mock = MagicMock()
    mock.trading.default_lot_size = 0.01
    mock.trading.max_lot_size = 1.0
    mock.strategy.main_tp_pips = 10
    mock.strategy.main_step_pips = 10
    mock.strategy.recovery_tp_pips = 80
    mock.strategy.recovery_step_pips = 40
    mock.risk.max_exposure_per_pair = 1000.0
    
    with patch('wsplumber.core.risk.risk_manager.get_settings', return_value=mock):
        risk_manager.settings = mock
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )

        auditor = CycleAuditor()
        metrics = AuditMetrics()
        tick_count = 0
        
        print(f"\n{'═'*115}")
        print(f" WSPlumber Stress Test - {csv_path.name}")
        print(f"{'═'*115}")
        print(f" {'TICK':>8} | {'BALANCE':>10} | {'EQUITY':>10} | {'PIPS':>9} | {'CYC(O/C)':>9} | {'REC(A/MX)':>9} | {'MAINS':>5} | {'DD%':>6}")
        print(f"{'─'*115}")
        
        while True:
            tick = await broker.advance_tick()
            if not tick:
                break
            
            await orchestrator._process_tick_for_pair(pair)
            tick_count += 1
            
            acc = await broker.get_account_info()
            balance = float(acc.value["balance"])
            equity = float(acc.value["equity"])
            auditor.check(tick_count, repo, broker, balance)
            
            # Calculate fast stats every tick
            total_pips = sum(c.total_pips for c in auditor.cycles.values())
            
            # Heavy calculations ONLY when sampling for charts
            if tick_count % sample_rate == 0:
                all_cycles = list(repo.cycles.values())
                open_cycles = sum(1 for c in all_cycles if c.status != CycleStatus.CLOSED)
                closed_cycles = sum(1 for c in all_cycles if c.status == CycleStatus.CLOSED)
                active_rec = sum(1 for c in all_cycles if c.cycle_type.value == "recovery" and c.status != CycleStatus.CLOSED)
                
                max_rec_now = 0
                if any(c.status != CycleStatus.CLOSED for c in all_cycles):
                    max_rec_now = max((len(c.accounting.recovery_queue) for c in all_cycles if c.status != CycleStatus.CLOSED), default=0)
                
                total_mains_hit = 0
                for c_audit in auditor.cycles.values():
                    total_mains_hit += sum(1 for e in c_audit.events if e.event_type == "TP_HIT" and "M_" in e.description)

                metrics.update(
                    tick=tick_count,
                    balance=balance,
                    equity=equity,
                    pips=total_pips,
                    cycles_open=open_cycles,
                    cycles_closed=closed_cycles,
                    recoveries=active_rec,
                    mains_hit=total_mains_hit,
                    max_rec=max_rec_now
                )
            
            # PROGRESS LOGGING (every 1000 ticks)
            if tick_count % 1000 == 0:
                # If we haven't already calculated detailed stats for this tick (due to sample_rate)
                if tick_count % sample_rate != 0:
                    all_cycles = list(repo.cycles.values())
                    open_cycles = sum(1 for c in all_cycles if c.status != CycleStatus.CLOSED)
                    closed_cycles = sum(1 for c in all_cycles if c.status == CycleStatus.CLOSED)
                    active_rec = sum(1 for c in all_cycles if c.cycle_type.value == "recovery" and c.status != CycleStatus.CLOSED)
                    max_rec_now = max((len(c.accounting.recovery_queue) for c in all_cycles if c.status != CycleStatus.CLOSED), default=0)
                    total_mains_hit = 0
                    for c_audit in auditor.cycles.values():
                        total_mains_hit += sum(1 for e in c_audit.events if e.event_type == "TP_HIT" and "M_" in e.description)

                dd_pct = ((metrics.peak_equity - equity) / metrics.peak_equity * 100) if metrics.peak_equity > 0 else 0
                print(f" {tick_count:>8,} | {balance:>10,.2f} | {equity:>10,.2f} | +{total_pips:>8,.1f} | {open_cycles:>4}/{closed_cycles:<4} | {active_rec:>4}/{max_rec_now:<4} | {total_mains_hit:>5} | {dd_pct:>5.1f}%", flush=True)

        # Final stats
        acc = await broker.get_account_info()
        final_balance = float(acc.value["balance"])
        final_equity = float(acc.value["equity"])
        
        print(f"{'─'*90}")
        print(f"\n{'═'*90}")
        print(f" FINAL RESULTS")
        print(f"{'═'*90}")
        print(f" Total Ticks:            {tick_count:,}")
        print(f" Final Balance:          {final_balance:,.2f} EUR")
        print(f" Final Equity:           {final_equity:,.2f} EUR")
        print(f" Profit:                 {final_balance - 10000:+,.2f} EUR ({(final_balance/10000-1)*100:+.2f}%)")
        print(f" Max Concurrent Cycles:  {metrics.max_concurrent_cycles}")
        print(f" Max Concurrent Rec:     {metrics.max_concurrent_recoveries}")
        print(f" Max Drawdown:           {metrics.max_drawdown:,.2f} EUR ({metrics.max_drawdown_pct:.2f}%)")
        print(f"{'═'*90}\n")
        
        # Generate chart
        chart_path = f"audit_chart_{csv_path.stem}.png"
        metrics.generate_chart(chart_path)
        
        # Determine output file
        report_name = f"audit_report_{csv_path.stem}.txt"
        print(f"[INFO] Saving audit report to: {report_name}")
        
        # Redirect stdout to file for the report
        with open(report_name, 'w', encoding='utf-8') as f:
            original_stdout = sys.stdout
            sys.stdout = f
            try:
                auditor.print_report(repo, final_balance, final_equity, repo)
            finally:
                sys.stdout = original_stdout
        
        print(f"[OK] Audit completed for {tick_count:,} ticks.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WSPlumber Enhanced Scenario Auditor")
    parser.add_argument("csv_path", help="Path to scenario CSV")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--sample-rate", type=int, default=500, help="Sample rate for chart data (default: 500)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(audit_scenario(args.csv_path, args.log_level, args.sample_rate))
    except KeyboardInterrupt:
        print("\n[INFO] Audit interrupted by user.")
        sys.exit(0)
