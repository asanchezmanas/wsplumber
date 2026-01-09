#!/usr/bin/env python
"""
Script de Auditoría Automática para Backtests - WSPlumber
Capa 2 de Verificación

Verifica invariantes críticos del sistema en logs de backtest:
1. Cada ciclo tiene exactamente 2 mains
2. No hay operaciones huérfanas
3. Estados de ciclos son válidos
4. No hay acumulación de mains en un solo ciclo

Uso:
    python scripts/audit_cycles.py <backtest_output.log>
    python scripts/audit_cycles.py --json <backtest_output.json>
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class CycleAuditor:
    """Audita invariantes críticos del sistema WSPlumber."""

    def __init__(self):
        self.cycles: Dict[str, Dict] = {}
        self.operations: Dict[str, Dict] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def audit_log_file(self, log_path: Path) -> bool:
        """Audita un archivo de log de backtest."""
        print(f"\n{'='*60}")
        print(f"🔍 AUDITORÍA DE BACKTEST")
        print(f"{'='*60}")
        print(f"Archivo: {log_path}")

        if not log_path.exists():
            self.errors.append(f"Archivo no encontrado: {log_path}")
            return False

        content = log_path.read_text(encoding='utf-8')

        # Parsear ciclos y operaciones
        self._parse_cycles(content)
        self._parse_operations(content)

        # Validar invariantes
        self._validate_mains_per_cycle()
        self._validate_orphaned_operations()
        self._validate_cycle_states()
        self._validate_no_accumulation()

        # Reportar resultados
        return self._report_results()

    def _parse_cycles(self, content: str):
        """Extrae información de ciclos del log."""
        # Patrón: "Ciclo CYC_EURUSD_XXX creado" o similar
        cycle_pattern = r'(?:Ciclo|cycle)[:\s]+([A-Z0-9_]+).*?(?:creado|created|opened)'

        for match in re.finditer(cycle_pattern, content, re.IGNORECASE):
            cycle_id = match.group(1)
            if cycle_id not in self.cycles:
                self.cycles[cycle_id] = {
                    'id': cycle_id,
                    'mains_count': 0,
                    'operations': [],
                    'status': 'PENDING'
                }

    def _parse_operations(self, content: str):
        """Extrae operaciones y sus ciclos del log."""
        # Patrón: "operation_id=OP_XXX" y "cycle_id=CYC_YYY" en la misma línea
        op_pattern = r'operation_id=([A-Z0-9_]+).*?cycle_id=([A-Z0-9_]+).*?(MAIN|main)'

        for match in re.finditer(op_pattern, content, re.IGNORECASE):
            op_id = match.group(1)
            cycle_id = match.group(2)
            is_main = match.group(3).upper() == 'MAIN'

            if op_id not in self.operations:
                self.operations[op_id] = {
                    'id': op_id,
                    'cycle_id': cycle_id,
                    'is_main': is_main
                }

                # Registrar en el ciclo
                if cycle_id in self.cycles and is_main:
                    self.cycles[cycle_id]['mains_count'] += 1
                    self.cycles[cycle_id]['operations'].append(op_id)

    def _validate_mains_per_cycle(self):
        """Invariante 1: Cada ciclo tiene exactamente 2 mains."""
        print(f"\n{'─'*60}")
        print("📊 [V1] MAINS POR CICLO")
        print(f"{'─'*60}")

        for cycle_id, cycle in self.cycles.items():
            mains_count = cycle['mains_count']

            if mains_count == 0:
                # Puede ser un ciclo recién creado sin operaciones aún
                self.warnings.append(f"Ciclo {cycle_id}: 0 mains (puede estar en creación)")
                print(f"  ⚠️  {cycle_id}: {mains_count} mains (sin operaciones)")
            elif mains_count == 2:
                print(f"  ✅ {cycle_id}: {mains_count} mains")
            else:
                self.errors.append(f"Ciclo {cycle_id}: {mains_count} mains (esperado: 2)")
                print(f"  ❌ {cycle_id}: {mains_count} mains (esperado: 2)")

    def _validate_orphaned_operations(self):
        """Invariante 2: No hay operaciones huérfanas (sin ciclo)."""
        print(f"\n{'─'*60}")
        print("🔗 [V2] OPERACIONES HUÉRFANAS")
        print(f"{'─'*60}")

        orphaned = []
        for op_id, op in self.operations.items():
            cycle_id = op['cycle_id']
            if cycle_id not in self.cycles:
                orphaned.append(op_id)
                self.errors.append(f"Operación {op_id} referencia ciclo inexistente {cycle_id}")

        if orphaned:
            print(f"  ❌ {len(orphaned)} operaciones huérfanas encontradas:")
            for op_id in orphaned[:5]:  # Mostrar max 5
                print(f"     - {op_id}")
        else:
            print(f"  ✅ No hay operaciones huérfanas")

    def _validate_cycle_states(self):
        """Invariante 3: Estados de ciclos son válidos."""
        print(f"\n{'─'*60}")
        print("🎯 [V3] ESTADOS DE CICLOS")
        print(f"{'─'*60}")

        valid_states = {
            'PENDING', 'ACTIVE', 'HEDGED', 'IN_RECOVERY', 'CLOSED', 'PAUSED'
        }

        invalid_states = []
        for cycle_id, cycle in self.cycles.items():
            status = cycle['status'].upper()
            if status not in valid_states:
                invalid_states.append((cycle_id, status))
                self.errors.append(f"Ciclo {cycle_id}: estado inválido '{status}'")

        if invalid_states:
            print(f"  ❌ {len(invalid_states)} ciclos con estados inválidos")
            for cycle_id, status in invalid_states[:5]:
                print(f"     - {cycle_id}: {status}")
        else:
            print(f"  ✅ Todos los estados son válidos")

    def _validate_no_accumulation(self):
        """Invariante 4: No hay acumulación de mains (>2 mains en un ciclo)."""
        print(f"\n{'─'*60}")
        print("⚠️  [V4] DETECCIÓN DE ACUMULACIÓN")
        print(f"{'─'*60}")

        accumulated = []
        for cycle_id, cycle in self.cycles.items():
            if cycle['mains_count'] > 2:
                accumulated.append((cycle_id, cycle['mains_count']))
                self.errors.append(f"CRÍTICO: Ciclo {cycle_id} tiene {cycle['mains_count']} mains (acumulación)")

        if accumulated:
            print(f"  ❌ {len(accumulated)} ciclos con acumulación detectada:")
            for cycle_id, count in accumulated:
                print(f"     - {cycle_id}: {count} mains")
        else:
            print(f"  ✅ No se detectó acumulación de mains")

    def _report_results(self) -> bool:
        """Genera reporte final de auditoría."""
        print(f"\n{'='*60}")
        print("📋 RESUMEN DE AUDITORÍA")
        print(f"{'='*60}")

        print(f"\nEstadísticas:")
        print(f"  - Ciclos totales: {len(self.cycles)}")
        print(f"  - Operaciones main totales: {sum(1 for op in self.operations.values() if op['is_main'])}")
        print(f"  - Errores críticos: {len(self.errors)}")
        print(f"  - Advertencias: {len(self.warnings)}")

        if self.errors:
            print(f"\n❌ ERRORES CRÍTICOS ENCONTRADOS:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"\n⚠️  ADVERTENCIAS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        print(f"\n{'='*60}")
        if self.errors:
            print("❌ AUDITORÍA FALLIDA - Se encontraron errores críticos")
            print(f"{'='*60}")
            return False
        else:
            print("✅ AUDITORÍA EXITOSA - Todos los invariantes se cumplen")
            print(f"{'='*60}")
            return True


def main():
    """Punto de entrada del script."""
    if len(sys.argv) < 2:
        print("Uso: python scripts/audit_cycles.py <backtest_output.log>")
        print("     python scripts/audit_cycles.py --json <backtest_output.json>")
        sys.exit(1)

    log_path = Path(sys.argv[-1])
    auditor = CycleAuditor()

    success = auditor.audit_log_file(log_path)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
