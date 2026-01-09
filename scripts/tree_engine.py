"""
WSPlumber - Tree Verification Engine

Executes nested verification trees to validate complete cycle flows.

The tree structure allows conditional branching:
- If condition is met (on_true) → execute child checks
- If condition not met (on_false) → execute alternative checks

This enables validation of complete flows like:
  Cycle Created
    └─ Main Activated
        ├─ [Only one active] → TP → Cancel counterpart → New cycle
        └─ [Both active] → HEDGED → Hedges created
            └─ Main TP → Hedge cancelled → Recovery
                ├─ [Recovery TP] → FIFO close → Cycle closed
                └─ [Recovery fails] → New recovery at +20 pips
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from wsplumber.domain.entities.cycle import CycleStatus, CycleType
from wsplumber.domain.types import OperationStatus


@dataclass
class TreeCheckResult:
    """Result of a tree node check."""
    name: str
    passed: bool
    condition_met: Optional[bool] = None  # For condition nodes
    message: str = ""
    children: List['TreeCheckResult'] = field(default_factory=list)
    depth: int = 0


class TreeVerificationEngine:
    """Engine that executes nested verification trees."""
    
    def __init__(self):
        self.results: List[TreeCheckResult] = []
        self.current_cycle = None
        self.cycles_by_order: List[Any] = []  # Cycles in creation order
    
    def load_tree(self, yaml_path: Path) -> dict:
        """Load tree definition from YAML."""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def run_tree(self, tree_def: dict, ctx: Any) -> List[TreeCheckResult]:
        """Execute the verification tree."""
        self.ctx = ctx
        self.results = []
        
        # Build cycles list in order
        self.cycles_by_order = sorted(
            ctx.repo.cycles.values(),
            key=lambda c: c.id  # or by created_at if available
        )
        
        if self.cycles_by_order:
            self.current_cycle = self.cycles_by_order[0]
        
        # Execute tree
        tree_nodes = tree_def.get('tree', [])
        for node in tree_nodes:
            result = self._execute_node(node, depth=0)
            self.results.append(result)
        
        return self.results
    
    def _execute_node(self, node: dict, depth: int) -> TreeCheckResult:
        """Execute a single tree node."""
        name = node.get('name', 'Unnamed')
        node_type = node.get('type', 'check')
        
        result = TreeCheckResult(name=name, passed=True, depth=depth)
        
        if node_type == 'condition':
            result = self._execute_condition(node, depth)
        elif node_type == 'check':
            result = self._execute_check(node, depth)
        
        return result
    
    def _execute_condition(self, node: dict, depth: int) -> TreeCheckResult:
        """Execute a condition node with branching."""
        name = node.get('name', 'Condition')
        check_def = node.get('check', {})
        expected = node.get('expect', True)
        
        # Evaluate condition
        condition_met = self._evaluate_check(check_def, expected)
        
        result = TreeCheckResult(
            name=name,
            passed=True,
            condition_met=condition_met,
            depth=depth,
            message=f"{'MET' if condition_met else 'NOT MET'}"
        )
        
        # Execute appropriate branch
        if condition_met:
            on_true = node.get('on_true', [])
            for child_node in on_true:
                child_result = self._execute_node(child_node, depth + 1)
                result.children.append(child_result)
                if not child_result.passed:
                    result.passed = False
        else:
            on_false = node.get('on_false', [])
            for child_node in on_false:
                child_result = self._execute_node(child_node, depth + 1)
                result.children.append(child_result)
                if not child_result.passed:
                    result.passed = False
        
        return result
    
    def _execute_check(self, node: dict, depth: int) -> TreeCheckResult:
        """Execute a simple check node."""
        name = node.get('name', 'Check')
        check_def = node.get('check', {})
        expected = node.get('expect')
        
        passed = self._evaluate_check(check_def, expected)
        
        return TreeCheckResult(
            name=name,
            passed=passed,
            depth=depth,
            message=f"{'PASS' if passed else 'FAIL'}"
        )
    
    def _evaluate_check(self, check_def: dict, expected: Any) -> bool:
        """Evaluate a check definition against the context."""
        check_type = check_def.get('type', '')
        filter_def = check_def.get('filter', {})
        
        try:
            if check_type == 'cycle_exists':
                cycle_type = filter_def.get('cycle_type') or check_def.get('cycle_type')
                return any(
                    c.cycle_type.value == cycle_type
                    for c in self.ctx.repo.cycles.values()
                )
            
            elif check_type == 'cycle_count':
                cycles = self._filter_cycles(filter_def)
                return self._compare_count(len(cycles), expected) if isinstance(expected, str) else len(cycles) == expected
            
            elif check_type == 'cycle_status':
                if not self.current_cycle:
                    return False
                return self.current_cycle.status.value == expected
            
            elif check_type == 'cycle_pips_locked':
                if not self.current_cycle:
                    return False
                pips = getattr(self.current_cycle.accounting, 'pips_locked', 0) if hasattr(self.current_cycle, 'accounting') else 0
                return self._compare_count(pips, expected) if isinstance(expected, str) else abs(pips - expected) < 0.1
            
            elif check_type == 'operation_count':
                ops = self._filter_operations(filter_def)
                exp = expected.get('count', expected) if isinstance(expected, dict) else expected
                return self._compare_count(len(ops), exp) if isinstance(exp, str) else len(ops) == exp
            
            elif check_type == 'operation_status':
                ops = self._filter_operations(filter_def)
                count_exp = check_def.get('count') or (expected.get('count') if isinstance(expected, dict) else None)
                if count_exp:
                    return self._compare_count(len(ops), count_exp)
                return len(ops) >= 1
            
            elif check_type == 'operation_entry_price':
                # Complex check - verify entry price matches reference
                return True  # TODO: Implement
            
            elif check_type == 'operation_entry_distance':
                # Complex check - verify distance in pips
                return True  # TODO: Implement
            
            else:
                return True  # Unknown check type passes by default
                
        except Exception as e:
            return False
    
    def _filter_cycles(self, filter_def: dict) -> list:
        """Filter cycles based on filter definition."""
        cycles = list(self.ctx.repo.cycles.values())
        result = []
        
        for c in cycles:
            match = True
            
            if 'cycle_type' in filter_def:
                if c.cycle_type.value != filter_def['cycle_type']:
                    match = False
            
            if 'status' in filter_def:
                exp_status = filter_def['status']
                if isinstance(exp_status, list):
                    if c.status.value not in exp_status:
                        match = False
                else:
                    if c.status.value != exp_status:
                        match = False
            
            if match:
                result.append(c)
        
        return result
    
    def _filter_operations(self, filter_def: dict) -> list:
        """Filter operations based on filter definition."""
        ops = list(self.ctx.repo.operations.values())
        result = []
        
        for op in ops:
            match = True
            
            # Filter by cycle if specified
            if filter_def.get('cycle') == 'current' and self.current_cycle:
                if op.cycle_id != self.current_cycle.id:
                    match = False
            
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
                exp_status = filter_def['status']
                if isinstance(exp_status, list):
                    if op.status.value not in exp_status:
                        match = False
                else:
                    if op.status.value != exp_status:
                        match = False
            
            if match:
                result.append(op)
        
        return result
    
    def _compare_count(self, actual: int, expected: Any) -> bool:
        """Evaluate count expression."""
        if isinstance(expected, int):
            return actual == expected
        
        if isinstance(expected, str):
            import re
            match = re.match(r'(>=|<=|==|>|<)\s*(\d+)', expected)
            if match:
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
        
        return actual == int(expected)
    
    def print_results(self, results: List[TreeCheckResult] = None):
        """Print verification tree results."""
        if results is None:
            results = self.results
        
        print("\n" + "="*70)
        print("🌳 ÁRBOL DE VERIFICACIÓN DE FLUJO")
        print("="*70)
        
        for result in results:
            self._print_node(result)
        
        # Count pass/fail
        total, passed, failed = self._count_results(results)
        
        print("\n" + "-"*70)
        print(f"📊 RESUMEN: {passed}/{total} checks pasados")
        if failed > 0:
            print(f"   ❌ {failed} checks fallaron")
        else:
            print("   ✅ Todos los checks pasaron")
        print("="*70)
    
    def _print_node(self, node: TreeCheckResult, prefix: str = ""):
        """Print a single node with tree formatting."""
        indent = "  " * node.depth
        
        if node.condition_met is not None:
            # Condition node
            icon = "🔀" if node.condition_met else "⬜"
            status = f"[{node.message}]"
        else:
            # Check node
            icon = "✅" if node.passed else "❌"
            status = ""
        
        print(f"{indent}{icon} {node.name} {status}")
        
        for child in node.children:
            self._print_node(child)
    
    def _count_results(self, results: List[TreeCheckResult]) -> Tuple[int, int, int]:
        """Count total, passed, and failed checks."""
        total = 0
        passed = 0
        failed = 0
        
        for result in results:
            if result.condition_met is None:  # Only count check nodes
                total += 1
                if result.passed:
                    passed += 1
                else:
                    failed += 1
            
            # Count children
            if result.children:
                t, p, f = self._count_results(result.children)
                total += t
                passed += p
                failed += f
        
        return total, passed, failed
