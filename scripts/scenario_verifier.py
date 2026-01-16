"""
WSPlumber - Scenario Verifier

Runs CSV scenarios and validates behavior using YAML DSL checks.

Usage:
    python scripts/scenario_verifier.py <scenario.csv>
    python scripts/scenario_verifier.py --all
    python scripts/scenario_verifier.py --category hedge
"""

import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator
from wsplumber.application.services.trading_service import TradingService
from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.core.risk.risk_manager import RiskManager
from wsplumber.domain.types import CurrencyPair
from wsplumber.infrastructure.persistence.in_memory_repo import InMemoryRepository
from tests.fixtures.simulated_broker import SimulatedBroker
from scripts.dsl_engine import DSLEngine, ScenarioResult
from scripts.audit_by_cycle import CycleAuditor
from scripts.tree_engine import TreeVerificationEngine


@dataclass
class VerificationContext:
    """Context passed to DSL engine checks."""
    repo: any
    broker: any
    cycles: List[any]
    initial_balance: float
    final_balance: float
    tick_count: int


class ScenarioVerifier:
    """Runs scenarios and validates with YAML DSL checks."""
    
    def __init__(self):
        self.scenarios_dir = Path(__file__).parent.parent / "tests" / "scenarios"
        self.dsl_engine = DSLEngine(self.scenarios_dir / "checks")
        
    async def run_scenario(self, scenario_path: Path, verbose: bool = True) -> ScenarioResult:
        """Run a single scenario and validate."""
        scenario_name = scenario_path.stem
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"RUNNING: {scenario_name}")
            print(f"{'='*60}")
        
        # Setup
        # import logging
        # logging.disable(logging.CRITICAL)
        
        broker = SimulatedBroker(initial_balance=10000.0)
        repo = InMemoryRepository()
        trading_service = TradingService(broker, repo)
        risk_manager = RiskManager()
        strategy = WallStreetPlumberStrategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        pair = CurrencyPair("EURUSD")
        initial_balance = 10000.0
        
        # Load scenario CSV
        broker.load_csv(str(scenario_path))
        await broker.connect()
        
        # Run simulation
        auditor = CycleAuditor()
        tick_count = 0
        
        while True:
            tick = await broker.advance_tick()
            if not tick:
                break
            
            await orchestrator.process_tick(tick)
            tick_count += 1
            
            acc = await broker.get_account_info()
            balance = float(acc.value["balance"])
            auditor.check(tick_count, repo, broker, balance)
        
        # Get final state
        acc = await broker.get_account_info()
        final_balance = float(acc.value["balance"])
        
        if verbose:
            print(f"\n📊 Simulation complete: {tick_count} ticks")
            print(f"   Cycles: {len(repo.cycles)}")
            print(f"   Operations: {len(repo.operations)}")
            print(f"   Balance: {initial_balance:.2f} → {final_balance:.2f}")
        
        # Create context for checks
        ctx = VerificationContext(
            repo=repo,
            broker=broker,
            cycles=list(auditor.cycles.values()),
            initial_balance=initial_balance,
            final_balance=final_balance,
            tick_count=tick_count
        )
        
        # Run DSL checks
        result = self.dsl_engine.run_checks(scenario_name, ctx)
        
        if verbose:
            self.dsl_engine.print_result(result)
            
            # Print audit by cycle
            if auditor.cycles:
                print("\n📋 CYCLE AUDIT:")
                for audit in sorted(auditor.cycles.values(), key=lambda c: c.created_tick):
                    print(f"\n  {audit.name} ({audit.cycle_type})")
                    print(f"    Created: tick #{audit.created_tick}")
                    print(f"    Status: {audit.status}")
                    print(f"    Mains: {len(audit.mains)} | Hedges: {len(audit.hedges)}")
                    print(f"    Events: {len(audit.events)}")
                    for e in audit.events[:10]:  # Show first 10
                        print(f"      #{e.tick:4} | {e.event_type}: {e.description}")
                    if len(audit.events) > 10:
                        print(f"      ... +{len(audit.events)-10} more events")
        
        return result
    
    async def run_all(self, category: Optional[str] = None) -> dict:
        """Run all scenarios or by category."""
        results = {"passed": 0, "failed": 0, "scenarios": []}
        
        # Find all CSV files
        pattern = f"{category}*.csv" if category else "*.csv"
        scenarios = sorted(self.scenarios_dir.glob(pattern))
        
        print(f"\n{'='*70}")
        print(f"🔬 WSPlumber Scenario Verification")
        print(f"{'='*70}")
        print(f"Scenarios found: {len(scenarios)}")
        if category:
            print(f"Category filter: {category}")
        print(f"{'='*70}")
        
        for scenario_path in scenarios:
            result = await self.run_scenario(scenario_path, verbose=False)
            
            icon = "✅" if result.passed else "❌"
            passed_checks = sum(1 for c in result.checks if c.passed)
            total_checks = len(result.checks)
            passed_inv = sum(1 for i in result.invariants if i.passed)
            total_inv = len(result.invariants)
            
            print(f"  {icon} {result.scenario:40} checks: {passed_checks}/{total_checks} inv: {passed_inv}/{total_inv}")
            
            if result.passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
                # Show failures
                for c in result.checks:
                    if not c.passed:
                        print(f"      ↳ FAIL: {c.name}")
                        print(f"         Expected: {c.expected}, Actual: {c.actual}")
            
            results["scenarios"].append({
                "name": result.scenario,
                "passed": result.passed,
                "checks": total_checks,
                "checks_passed": passed_checks
            })
        
        # Summary
        print(f"\n{'='*70}")
        print(f"📊 SUMMARY")
        print(f"{'='*70}")
        print(f"   Total: {len(scenarios)}")
        print(f"   Passed: {results['passed']} ✅")
        print(f"   Failed: {results['failed']} ❌")
        print(f"   Pass rate: {100*results['passed']/max(len(scenarios),1):.1f}%")
        print(f"{'='*70}")
        
        return results
    
    async def run_tree(self, bars: int = 500):
        """Run tree-based flow verification on backtest data."""
        
        print(f"\n{'='*70}")
        print(f"🌳 Tree-Based Flow Verification ({bars} bars)")
        print(f"{'='*70}")
        
        # Setup
        import logging
        logging.disable(logging.CRITICAL)
        
        broker = SimulatedBroker(initial_balance=10000.0)
        repo = InMemoryRepository()
        trading_service = TradingService(broker, repo)
        risk_manager = RiskManager()
        strategy = WallStreetPlumberStrategy()
        
        orchestrator = CycleOrchestrator(
            trading_service=trading_service,
            strategy=strategy,
            risk_manager=risk_manager,
            repository=repo
        )
        
        # Load M1 data
        data_path = Path(__file__).parent.parent / "2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv"
        
        if not data_path.exists():
            print(f"❌ Data file not found: {data_path}")
            return
        
        broker.load_m1_csv(str(data_path), max_bars=bars)
        await broker.connect()
        
        initial_balance = 10000.0
        tick_count = 0
        
        # Run simulation
        while True:
            tick = await broker.advance_tick()
            if not tick:
                break
            await orchestrator.process_tick(tick)
            tick_count += 1
        
        # Get final state
        acc = await broker.get_account_info()
        final_balance = float(acc.value["balance"])
        
        print(f"\n📊 Simulation complete: {tick_count} ticks")
        print(f"   Cycles: {len(repo.cycles)}")
        print(f"   Operations: {len(repo.operations)}")
        print(f"   Balance: {initial_balance:.2f} → {final_balance:.2f}")
        
        # Create context
        ctx = VerificationContext(
            repo=repo,
            broker=broker,
            cycles=[],
            initial_balance=initial_balance,
            final_balance=final_balance,
            tick_count=tick_count
        )
        
        # Run tree verification
        tree_engine = TreeVerificationEngine()
        tree_path = self.scenarios_dir / "checks" / "_tree_schema.yaml"
        
        if tree_path.exists():
            tree_def = tree_engine.load_tree(tree_path)
            results = tree_engine.run_tree(tree_def, ctx)
            tree_engine.print_results(results)
        else:
            print(f"❌ Tree schema not found: {tree_path}")


async def main():
    verifier = ScenarioVerifier()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/scenario_verifier.py <scenario.csv>")
        print("  python scripts/scenario_verifier.py --all")
        print("  python scripts/scenario_verifier.py --category hedge")
        print("  python scripts/scenario_verifier.py --tree [bars]")
        return
    
    arg = sys.argv[1]
    
    if arg == "--all":
        await verifier.run_all()
    elif arg == "--category":
        if len(sys.argv) < 3:
            print("Error: specify category (e.g., --category hedge)")
            return
        await verifier.run_all(category=sys.argv[2])
    elif arg == "--tree":
        bars = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        await verifier.run_tree(bars)
    else:
        # Single scenario
        path = Path(arg)
        if not path.exists():
            path = verifier.scenarios_dir / arg
        if not path.exists():
            print(f"Error: scenario not found: {arg}")
            return
        await verifier.run_scenario(path)


if __name__ == "__main__":
    asyncio.run(main())

