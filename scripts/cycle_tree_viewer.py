"""
WSPlumber - Cycle Tree Viewer

Visualiza el estado de todos los ciclos en formato arbol con detalles de:
- Estado de cada operacion (Main, Hedge, Recovery)
- Deuda, recuperacion, surplus
- Razon por la que no cerro (si aplica)
- Sincronizacion broker/sistema

Usage: python scripts/cycle_tree_viewer.py [--repo <repo_file>]
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wsplumber.domain.entities.cycle import Cycle, CycleStatus, CycleType
from wsplumber.domain.entities.operations import Operation
from wsplumber.domain.types import OperationStatus


@dataclass
class CycleTreeNode:
    """Nodo del arbol de ciclo."""
    id: str
    label: str
    status: str
    details: Dict[str, Any]
    children: List['CycleTreeNode']
    issues: List[str]  # Problemas detectados


class CycleTreeViewer:
    """Visualizador de ciclos en formato arbol."""
    
    def __init__(self, repo: Any, broker: Any = None):
        self.repo = repo
        self.broker = broker
        self.issues_found: List[str] = []
    
    def build_tree(self) -> List[CycleTreeNode]:
        """Construye el arbol de todos los ciclos."""
        trees = []
        
        # Obtener ciclos ordenados por tipo (main primero, luego recovery)
        main_cycles = [c for c in self.repo.cycles.values() if c.cycle_type == CycleType.MAIN]
        recovery_cycles = [c for c in self.repo.cycles.values() if c.cycle_type == CycleType.RECOVERY]
        
        for cycle in main_cycles:
            tree = self._build_cycle_node(cycle)
            trees.append(tree)
        
        return trees
    
    def _build_cycle_node(self, cycle: Cycle) -> CycleTreeNode:
        """Construye nodo para un ciclo."""
        issues = []
        
        # Info basica
        status_icon = self._get_status_icon(cycle.status)
        
        # Calcular metricas de deuda
        debt_info = self._get_debt_info(cycle)
        
        # Verificar por que no cerro
        if cycle.status != CycleStatus.CLOSED:
            close_issues = self._check_why_not_closed(cycle)
            issues.extend(close_issues)
        
        # Construir nodo
        node = CycleTreeNode(
            id=cycle.id,
            label=f"{status_icon} {cycle.id[:30]}... [{cycle.status.value}]",
            status=cycle.status.value,
            details={
                "type": cycle.cycle_type.value,
                "debt_total": debt_info["total"],
                "debt_recovered": debt_info["recovered"],
                "debt_pending": debt_info["pending"],
                "surplus": debt_info["surplus"],
                "is_fully_recovered": debt_info["is_fully_recovered"],
            },
            children=[],
            issues=issues
        )
        
        # Agregar operaciones como hijos
        ops = [op for op in self.repo.operations.values() if op.cycle_id == cycle.id]
        
        # Agrupar por tipo
        mains = [op for op in ops if op.is_main]
        hedges = [op for op in ops if 'hedge' in op.op_type.value]
        recoveries = [op for op in ops if op.is_recovery]
        
        # Main operations
        for op in mains:
            op_node = self._build_operation_node(op, "MAIN")
            node.children.append(op_node)
        
        # Hedge operations
        if hedges:
            hedge_node = CycleTreeNode(
                id="hedges",
                label=f"Hedges ({len(hedges)})",
                status="",
                details={},
                children=[self._build_operation_node(h, "HEDGE") for h in hedges],
                issues=[]
            )
            node.children.append(hedge_node)
        
        # Recovery operations (buscar ciclos recovery hijos)
        child_recoveries = [c for c in self.repo.cycles.values() 
                          if c.cycle_type == CycleType.RECOVERY 
                          and c.metadata.get("parent_cycle") == cycle.id]
        
        if child_recoveries:
            rec_node = CycleTreeNode(
                id="recoveries",
                label=f"Recoveries ({len(child_recoveries)})",
                status="",
                details={},
                children=[self._build_recovery_summary(r) for r in child_recoveries],
                issues=[]
            )
            node.children.append(rec_node)
        
        return node
    
    def _build_operation_node(self, op: Operation, op_type: str) -> CycleTreeNode:
        """Construye nodo para una operacion."""
        issues = []
        
        status_icon = self._get_op_status_icon(op.status)
        direction = "BUY" if op.is_buy else "SELL"
        
        # Calcular pips flotantes si esta activa
        floating_pips = 0.0
        if hasattr(op, 'metadata') and op.metadata:
            floating_pips = op.metadata.get('floating_pips', 0.0)
        
        # Verificar sincronizacion broker
        if self.broker:
            broker_sync = self._check_broker_sync(op)
            if not broker_sync["synced"]:
                issues.append(f"DESYNC: {broker_sync['reason']}")
        
        details = {
            "direction": direction,
            "entry": str(op.entry_price),
            "tp": str(op.tp_price) if op.tp_price else "N/A",
            "floating_pips": floating_pips,
            "broker_ticket": str(op.broker_ticket) if op.broker_ticket else "N/A",
        }
        
        pips_str = f"{floating_pips:+.1f} pips" if floating_pips != 0 else ""
        
        return CycleTreeNode(
            id=op.id,
            label=f"{status_icon} {op_type} {direction}: {op.entry_price} -> TP {op.tp_price or 'N/A'} [{op.status.value}] {pips_str}",
            status=op.status.value,
            details=details,
            children=[],
            issues=issues
        )
    
    def _build_recovery_summary(self, recovery_cycle: Cycle) -> CycleTreeNode:
        """Construye resumen de un ciclo recovery."""
        status_icon = self._get_status_icon(recovery_cycle.status)
        
        # Obtener operaciones del recovery
        ops = [op for op in self.repo.operations.values() if op.cycle_id == recovery_cycle.id]
        tp_hit = any(op.status == OperationStatus.TP_HIT for op in ops)
        
        result = "[TP +80 pips]" if tp_hit else "[ACTIVE]" if recovery_cycle.status != CycleStatus.CLOSED else "[FAIL]"
        
        return CycleTreeNode(
            id=recovery_cycle.id,
            label=f"{status_icon} {recovery_cycle.id[:20]}... {result}",
            status=recovery_cycle.status.value,
            details={"tier": recovery_cycle.metadata.get("tier", 1)},
            children=[],
            issues=[]
        )
    
    def _get_debt_info(self, cycle: Cycle) -> Dict[str, Any]:
        """Obtiene informacion de deuda del ciclo."""
        if not hasattr(cycle, 'accounting'):
            return {"total": 0, "recovered": 0, "pending": 0, "surplus": 0, "is_fully_recovered": True}
        
        acc = cycle.accounting
        total = float(acc.pips_locked) if hasattr(acc, 'pips_locked') else 0
        recovered = float(acc.pips_recovered) if hasattr(acc, 'pips_recovered') else 0
        pending = total - recovered
        surplus = acc.surplus_pips if hasattr(acc, 'surplus_pips') else 0
        is_fully = acc.is_fully_recovered if hasattr(acc, 'is_fully_recovered') else (pending <= 0)
        
        return {
            "total": total,
            "recovered": recovered,
            "pending": pending,
            "surplus": surplus,
            "is_fully_recovered": is_fully
        }
    
    def _check_why_not_closed(self, cycle: Cycle) -> List[str]:
        """Analiza por que el ciclo no cerro."""
        issues = []
        
        debt_info = self._get_debt_info(cycle)
        
        # Razon 1: Deuda pendiente
        if debt_info["pending"] > 0:
            issues.append(f"DEUDA PENDIENTE: {debt_info['pending']:.1f} pips aun sin pagar")
        
        # Razon 2: Surplus < 20 (la regla antigua)
        if debt_info["is_fully_recovered"] and debt_info["surplus"] < 20:
            issues.append(f"SURPLUS INSUFICIENTE: {debt_info['surplus']:.1f} pips (requiere >= 20)")
        
        # Razon 3: Operaciones aun activas
        ops = [op for op in self.repo.operations.values() if op.cycle_id == cycle.id]
        active_ops = [op for op in ops if op.status in (OperationStatus.ACTIVE, OperationStatus.PENDING)]
        if active_ops:
            issues.append(f"OPERACIONES ACTIVAS: {len(active_ops)} operaciones sin cerrar")
        
        return issues
    
    def _check_broker_sync(self, op: Operation) -> Dict[str, Any]:
        """Verifica sincronizacion con broker."""
        if not self.broker or not op.broker_ticket:
            return {"synced": True, "reason": ""}
        
        ticket = str(op.broker_ticket)
        
        # Verificar en posiciones abiertas
        if ticket in self.broker.open_positions:
            broker_pos = self.broker.open_positions[ticket]
            # Verificar status match
            if op.status == OperationStatus.CLOSED and broker_pos.status != OperationStatus.CLOSED:
                return {"synced": False, "reason": "Sistema=CLOSED, Broker=OPEN"}
            return {"synced": True, "reason": ""}
        
        # Verificar en historial
        if any(h.get("ticket") == ticket for h in self.broker.history):
            if op.status not in (OperationStatus.CLOSED, OperationStatus.TP_HIT):
                return {"synced": False, "reason": f"Sistema={op.status.value}, Broker=CERRADO"}
            return {"synced": True, "reason": ""}
        
        # No encontrado en ningun lado
        if op.status not in (OperationStatus.PENDING, OperationStatus.CANCELLED):
            return {"synced": False, "reason": "No encontrado en broker"}
        
        return {"synced": True, "reason": ""}
    
    def _get_status_icon(self, status: CycleStatus) -> str:
        """Icono para status de ciclo."""
        icons = {
            CycleStatus.ACTIVE: "[ACT]",
            CycleStatus.HEDGED: "[HDG]",
            CycleStatus.IN_RECOVERY: "[REC]",
            CycleStatus.CLOSED: "[OK]",
            CycleStatus.PAUSED: "[PAU]",
        }
        return icons.get(status, "[?]")
    
    def _get_op_status_icon(self, status: OperationStatus) -> str:
        """Icono para status de operacion."""
        icons = {
            OperationStatus.PENDING: "[ ]",
            OperationStatus.ACTIVE: "[A]",
            OperationStatus.TP_HIT: "[T]",
            OperationStatus.SL_HIT: "[S]",
            OperationStatus.CLOSED: "[X]",
            OperationStatus.CANCELLED: "[-]",
            OperationStatus.NEUTRALIZED: "[N]",
        }
        return icons.get(status, "[?]")
    
    def print_tree(self, trees: List[CycleTreeNode] = None, max_cycles: int = 20):
        """Imprime el arbol."""
        if trees is None:
            trees = self.build_tree()
        
        print("\n" + "="*80)
        print("CYCLE TREE VIEWER - Estado de Ciclos")
        print("="*80)
        print(f"Total ciclos: {len(trees)}")
        print(f"Mostrando: {min(len(trees), max_cycles)}")
        print("-"*80)
        
        # Mostrar solo los primeros N y los que tienen problemas
        shown = 0
        for tree in trees:
            if shown >= max_cycles:
                remaining = len(trees) - shown
                if remaining > 0:
                    print(f"\n... y {remaining} ciclos mas")
                break
            
            self._print_node(tree, 0)
            shown += 1
        
        # Resumen de issues
        all_issues = []
        for tree in trees:
            all_issues.extend(tree.issues)
            for child in tree.children:
                all_issues.extend(child.issues)
        
        if all_issues:
            print("\n" + "="*80)
            print("PROBLEMAS DETECTADOS:")
            print("-"*80)
            for issue in all_issues[:20]:
                print(f"  ! {issue}")
            if len(all_issues) > 20:
                print(f"  ... y {len(all_issues) - 20} problemas mas")
        
        print("="*80)
    
    def _print_node(self, node: CycleTreeNode, depth: int):
        """Imprime un nodo del arbol."""
        indent = "  " * depth
        connector = "|-- " if depth > 0 else ""
        
        print(f"{indent}{connector}{node.label}")
        
        # Mostrar detalles si es ciclo principal
        if node.details.get("debt_total"):
            d = node.details
            print(f"{indent}    Debt: {d['debt_total']:.0f} | Recovered: {d['debt_recovered']:.0f} | Pending: {d['debt_pending']:.0f} | Surplus: {d['surplus']:.1f}")
        
        # Mostrar issues
        for issue in node.issues:
            print(f"{indent}    [!] {issue}")
        
        # Hijos
        for child in node.children:
            self._print_node(child, depth + 1)


def run_viewer(repo, broker=None, max_cycles: int = 20):
    """Ejecuta el visualizador."""
    viewer = CycleTreeViewer(repo, broker)
    trees = viewer.build_tree()
    viewer.print_tree(trees, max_cycles)
    return viewer


if __name__ == "__main__":
    print("CycleTreeViewer - Usar desde audit_scenario.py con run_viewer(repo, broker)")
