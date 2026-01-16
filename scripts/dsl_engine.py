"""
WSPlumber - DSL Engine for Scenario Checks

Parses YAML check definitions and executes them against scenario results.
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from wsplumber.domain.entities.cycle import CycleStatus, CycleType


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    passed: bool
    message: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class ScenarioResult:
    """Result of scenario verification."""
    scenario: str
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    invariants: List[CheckResult] = field(default_factory=list)
    error: Optional[str] = None


class DSLEngine:
    """Engine that interprets YAML DSL checks and executes them."""
    
    def __init__(self, checks_dir: Path = None):
        self.checks_dir = checks_dir or Path(__file__).parent.parent / "tests" / "scenarios" / "checks"
    
    def load_checks(self, scenario_name: str) -> Optional[dict]:
        """Load YAML checks for a scenario."""
        name = scenario_name.replace(".csv", "")
        check_file = self.checks_dir / f"{name}.yaml"
        
        if not check_file.exists():
            return None
        
        with open(check_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def run_checks(self, scenario_name: str, ctx: Any) -> ScenarioResult:
        """Run all checks for a scenario."""
        checks_def = self.load_checks(scenario_name)
        
        if not checks_def:
            # Return basic checks if no YAML defined
            return self._run_basic_checks(scenario_name, ctx)
        
        result = ScenarioResult(
            scenario=scenario_name,
            passed=True
        )
        
        # Run each defined check
        for check_def in checks_def.get('checks', []):
            check_result = self._execute_check(check_def, ctx)
            result.checks.append(check_result)
            if not check_result.passed:
                result.passed = False
        
        # Run invariants
        for inv_result in self._run_invariants(ctx):
            result.invariants.append(inv_result)
            if not inv_result.passed:
                result.passed = False
        
        return result
    
    def _execute_check(self, check_def: dict, ctx: Any) -> CheckResult:
        """Execute a single check based on its type."""
        check_type = check_def.get('type', 'unknown')
        name = check_def.get('name', 'Unnamed check')
        
        try:
            if check_type == 'operation_status':
                return self._check_operation_status(name, check_def, ctx)
            elif check_type == 'operation_metadata':
                return self._check_operation_metadata(name, check_def, ctx)
            elif check_type == 'cycle_count':
                return self._check_cycle_count(name, check_def, ctx)
            elif check_type == 'balance':
                return self._check_balance(name, check_def, ctx)
            elif check_type == 'invariant':
                return self._check_invariant(name, check_def, ctx)
            else:
                return CheckResult(name, False, f"Unknown check type: {check_type}")
        except Exception as e:
            return CheckResult(name, False, f"Error: {e}")
    
    def _filter_operations(self, filter_def: dict, ctx: Any) -> list:
        """Filter operations based on filter definition."""
        ops = list(ctx.repo.operations.values())
        result = []
        
        for op in ops:
            match = True
            
            if 'is_main' in filter_def:
                if op.is_main != filter_def['is_main']:
                    match = False
            
            if 'is_hedge' in filter_def:
                is_hedge = 'hedge' in op.op_type.value
                if is_hedge != filter_def['is_hedge']:
                    match = False
            
            if 'is_recovery' in filter_def:
                is_recovery = 'recovery' in op.op_type.value
                if is_recovery != filter_def['is_recovery']:
                    match = False
            
            if 'op_type' in filter_def:
                if filter_def['op_type'] not in op.op_type.value:
                    match = False
            
            if 'status' in filter_def:
                if op.status.value != filter_def['status']:
                    match = False
            
            if match:
                result.append(op)
        
        return result
    
    def _filter_cycles(self, filter_def: dict, ctx: Any) -> list:
        """Filter cycles based on filter definition."""
        cycles = list(ctx.repo.cycles.values())
        result = []
        
        for c in cycles:
            match = True
            
            if 'cycle_type' in filter_def:
                expected = filter_def['cycle_type']
                if expected == 'main' and c.cycle_type != CycleType.MAIN:
                    match = False
                elif expected == 'recovery' and c.cycle_type != CycleType.RECOVERY:
                    match = False
            
            if 'status' in filter_def:
                status_list = filter_def['status']
                if isinstance(status_list, str):
                    status_list = [status_list]
                if c.status.value not in status_list:
                    match = False
            
            if match:
                result.append(c)
        
        return result
    
    def _evaluate_count(self, actual: int, expected: str) -> bool:
        """Evaluate count expression like '>= 2'."""
        if isinstance(expected, int):
            return actual == expected
        
        match = re.match(r'(>=|<=|==|>|<)\s*(\d+)', str(expected))
        if not match:
            return actual == int(expected)
        
        op, val = match.groups()
        val = int(val)
        
        if op == '>=':
            return actual >= val
        elif op == '<=':
            return actual <= val
        elif op == '==':
            return actual == val
        elif op == '>':
            return actual > val
        elif op == '<':
            return actual < val
        
        return False
    
    def _check_operation_status(self, name: str, check_def: dict, ctx: Any) -> CheckResult:
        """Check operation status."""
        filter_def = check_def.get('filter', {})
        expect = check_def.get('expect', {})
        
        ops = self._filter_operations(filter_def, ctx)
        
        # Filter by expected status
        if 'status' in expect:
            ops = [op for op in ops if op.status.value == expect['status']]
        
        # Check count
        if 'count' in expect:
            passed = self._evaluate_count(len(ops), expect['count'])
            return CheckResult(
                name, passed,
                expected=f"count {expect['count']}",
                actual=f"count {len(ops)}"
            )
        
        # Default: at least 1
        passed = len(ops) >= 1
        return CheckResult(name, passed, expected="count >= 1", actual=f"count {len(ops)}")
    
    def _check_operation_metadata(self, name: str, check_def: dict, ctx: Any) -> CheckResult:
        """Check operation metadata."""
        filter_def = check_def.get('filter', {})
        expect = check_def.get('expect', {})
        
        ops = self._filter_operations(filter_def, ctx)
        
        if not ops:
            return CheckResult(name, False, expected="operations with metadata", actual="no matching operations")
        
        metadata_expect = expect.get('metadata', {})
        for key, expected_val in metadata_expect.items():
            for op in ops:
                actual_val = op.metadata.get(key)
                if actual_val == expected_val:
                    return CheckResult(name, True, expected=f"{key}={expected_val}", actual=f"{key}={actual_val}")
        
        return CheckResult(name, False, expected=str(metadata_expect), actual="no match found")
    
    def _check_cycle_count(self, name: str, check_def: dict, ctx: Any) -> CheckResult:
        """Check cycle count."""
        filter_def = check_def.get('filter', {})
        expect = check_def.get('expect', {})
        
        cycles = self._filter_cycles(filter_def, ctx)
        
        if 'count' in expect:
            passed = self._evaluate_count(len(cycles), expect['count'])
            return CheckResult(name, passed, expected=f"count {expect['count']}", actual=f"count {len(cycles)}")
        
        return CheckResult(name, len(cycles) >= 1, expected="count >= 1", actual=f"count {len(cycles)}")
    
    def _check_balance(self, name: str, check_def: dict, ctx: Any) -> CheckResult:
        """Check balance changes."""
        expect = check_def.get('expect', {})
        
        if 'final' in expect:
            expr = expect['final']
            if expr == '> initial':
                passed = ctx.final_balance > ctx.initial_balance
            elif expr == '== initial':
                passed = abs(ctx.final_balance - ctx.initial_balance) < 0.01
            elif expr == '< initial':
                passed = ctx.final_balance < ctx.initial_balance
            else:
                passed = ctx.final_balance >= float(expr)
            
            return CheckResult(
                name, passed,
                expected=f"balance {expr}",
                actual=f"initial={ctx.initial_balance:.2f}, final={ctx.final_balance:.2f}"
            )
        
        return CheckResult(name, True, message="No balance expectation defined")
    
    def _check_invariant(self, name: str, check_def: dict, ctx: Any) -> CheckResult:
        """Check system invariants."""
        rule = check_def.get('rule', '')
        expect = check_def.get('expect', {})
        
        if rule == 'mains_per_cycle':
            expected_count = expect.get('count', 2)
            main_cycles = [c for c in ctx.repo.cycles.values() if c.cycle_type == CycleType.MAIN]
            
            for c in main_cycles:
                mains = [op for op in ctx.repo.operations.values() 
                        if op.cycle_id == c.id and op.is_main]
                if len(mains) != expected_count:
                    return CheckResult(
                        name, False,
                        expected=f"{expected_count} mains per cycle",
                        actual=f"Cycle {c.id[:20]} has {len(mains)} mains"
                    )
            
            return CheckResult(name, True, expected=f"{expected_count} mains per cycle", actual="all cycles OK")
        
        elif rule == 'no_orphans':
            cycle_ids = {c.id for c in ctx.repo.cycles.values()}
            for op in ctx.repo.operations.values():
                if op.cycle_id not in cycle_ids:
                    return CheckResult(name, False, expected="no orphans", actual=f"Op {op.id} orphaned")
            return CheckResult(name, True, expected="no orphans", actual="all ops have cycles")
        
        return CheckResult(name, True, message=f"Unknown invariant rule: {rule}")
    
    def _run_invariants(self, ctx: Any) -> List[CheckResult]:
        """Run default invariants on every scenario."""
        results = []
        
        # Invariant 1: Every main cycle has exactly 2 mains
        main_cycles = [c for c in ctx.repo.cycles.values() if c.cycle_type == CycleType.MAIN]
        all_ok = True
        problem = ""
        for c in main_cycles:
            mains = [op for op in ctx.repo.operations.values() if op.cycle_id == c.id and op.is_main]
            if len(mains) != 2:
                all_ok = False
                problem = f"Cycle {c.id[:20]} has {len(mains)} mains"
                break
        
        results.append(CheckResult(
            "[INV] Every main cycle has 2 mains",
            all_ok,
            expected="2 mains per cycle",
            actual="OK" if all_ok else problem
        ))
        
        # Invariant 2: No orphaned operations
        cycle_ids = {c.id for c in ctx.repo.cycles.values()}
        orphans = [op for op in ctx.repo.operations.values() if op.cycle_id not in cycle_ids]
        results.append(CheckResult(
            "[INV] No orphaned operations",
            len(orphans) == 0,
            expected="0 orphans",
            actual=f"{len(orphans)} orphans"
        ))
        
        return results
    
    def _run_basic_checks(self, scenario_name: str, ctx: Any) -> ScenarioResult:
        """Run basic checks when no YAML is defined."""
        result = ScenarioResult(scenario=scenario_name, passed=True)
        
        # Basic check: at least 1 cycle
        has_cycles = len(ctx.repo.cycles) >= 1
        result.checks.append(CheckResult(
            "At least 1 cycle created",
            has_cycles,
            expected=">= 1 cycle",
            actual=f"{len(ctx.repo.cycles)} cycles"
        ))
        if not has_cycles:
            result.passed = False
        
        # Basic check: operations exist
        has_ops = len(ctx.repo.operations) >= 1
        result.checks.append(CheckResult(
            "Operations exist",
            has_ops,
            expected=">= 1 operation",
            actual=f"{len(ctx.repo.operations)} operations"
        ))
        if not has_ops:
            result.passed = False
        
        # Run invariants
        for inv in self._run_invariants(ctx):
            result.invariants.append(inv)
            if not inv.passed:
                result.passed = False
        
        return result
    
    def print_result(self, result: ScenarioResult):
        """Print verification result in readable format."""
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        print(f"\n{'='*60}")
        print(f"Scenario: {result.scenario}")
        print(f"Result: {status}")
        print(f"{'='*60}")
        
        if result.checks:
            print("\nCHECKS:")
            for check in result.checks:
                icon = "[OK]" if check.passed else "[FAIL]"
                print(f"  {icon} {check.name}")
                if not check.passed:
                    print(f"      Expected: {check.expected}")
                    print(f"      Actual:   {check.actual}")
        
        if result.invariants:
            print("\nINVARIANTS:")
            for inv in result.invariants:
                icon = "[OK]" if inv.passed else "[FAIL]"
                print(f"  {icon} {inv.name}")
                if not inv.passed:
                    print(f"      Expected: {inv.expected}")
                    print(f"      Actual:   {inv.actual}")
        
        print(f"\n{'='*60}")
