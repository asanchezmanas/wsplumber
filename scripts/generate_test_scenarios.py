"""
WSPlumber - Generador de Escenarios de Test

Genera CSVs de test basados en el catálogo completo de escenarios.
Cada escenario verifica un comportamiento específico del sistema.
"""

import csv
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple


class ScenarioGenerator:
    """Genera CSVs de test para todos los escenarios documentados."""

    def __init__(self, output_dir: str = "tests/test_scenarios"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.base_time = datetime(2024, 1, 1, 10, 0, 0)
        self.scenarios_generated = []

    def generate_csv(
        self,
        filename: str,
        pair: str,
        movements: List[Tuple[float, str]],
        start_price: Decimal = None
    ) -> str:
        """
        Genera CSV a partir de lista de movimientos.

        Args:
            filename: Nombre del archivo CSV
            pair: Par de divisas (EURUSD, USDJPY, etc.)
            movements: Lista de (delta_pips, descripción)
            start_price: Precio inicial (opcional)

        Returns:
            Ruta completa del archivo generado
        """
        filepath = os.path.join(self.output_dir, filename)

        is_jpy = "JPY" in pair
        multiplier = 100 if is_jpy else 10000
        pip_value = Decimal("0.01") if is_jpy else Decimal("0.0001")
        spread = Decimal("0.02") if is_jpy else Decimal("0.0002")

        # Precio inicial por defecto
        if start_price is None:
            start_price = Decimal("150.000") if is_jpy else Decimal("1.10000")

        current_price = start_price

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask', 'spread_pips'])

            for i, (delta_pips, desc) in enumerate(movements):
                ts = (self.base_time + timedelta(seconds=i)).isoformat()
                current_price += Decimal(str(delta_pips)) * pip_value
                bid = current_price
                ask = current_price + spread
                spread_pips = float(spread * multiplier)

                # Formatear precios según el par
                if is_jpy:
                    bid_str = f"{bid:.3f}"
                    ask_str = f"{ask:.3f}"
                else:
                    bid_str = f"{bid:.5f}"
                    ask_str = f"{ask:.5f}"

                writer.writerow([ts, pair, bid_str, ask_str, spread_pips])

        self.scenarios_generated.append({
            'filename': filename,
            'pair': pair,
            'ticks': len(movements),
            'description': movements[-1][1] if movements else ''
        })

        print(f"[OK] Generado: {filepath} ({len(movements)} ticks)")
        return filepath

    def generate_critical_scenarios(self):
        """Genera los escenarios críticos (P0) que DEBEN pasar antes de producción."""

        print("\n=== GENERANDO ESCENARIOS CRÍTICOS ===\n")

        # ===============================================
        # 1.1 TP Simple BUY
        # ===============================================
        self.generate_csv(
            "scenario_1_1_tp_buy.csv",
            "EURUSD",
            [
                (0, "Inicio en 1.10000"),
                (6, "↑6 pips → Activa BUY en 1.10050"),
                (5, "↑5 pips → BUY floating +5 pips"),
                (5, "↑5 pips → BUY TP HIT en 1.10150"),
                (1, "↑1 pip → Final, balance +10 pips"),
            ]
        )

        # ===============================================
        # 1.2 TP Simple SELL
        # ===============================================
        self.generate_csv(
            "scenario_1_2_tp_sell.csv",
            "EURUSD",
            [
                (0, "Inicio en 1.10000"),
                (-6, "↓6 pips → Activa SELL en 1.09950"),
                (-5, "↓5 pips → SELL floating +5 pips"),
                (-5, "↓5 pips → SELL TP HIT en 1.09850"),
                (-1, "↓1 pip → Final, balance +10 pips"),
            ]
        )

        # ===============================================
        # 2.1 Ambas activas → HEDGED
        # ===============================================
        self.generate_csv(
            "scenario_2_1_both_active_hedged.csv",
            "EURUSD",
            [
                (0, "Inicio en 1.10000"),
                (6, "↑6 pips → Activa BUY en 1.10050"),
                (-12, "↓12 pips → Activa SELL en 1.09950 → HEDGED"),
                (-2, "↓2 pips → Estado HEDGED confirmado, pips_locked=20"),
            ]
        )

        # ===============================================
        # 3.1 BUY TP → Hedge SELL se activa
        # ===============================================
        self.generate_csv(
            "scenario_3_1_buy_tp_hedge_sell_activates.csv",
            "EURUSD",
            [
                (0, "Inicio en 1.10000"),
                (6, "↑6 pips → Activa BUY@1.10050"),
                (-12, "↓12 pips → Activa SELL@1.09950 → HEDGED"),
                (6, "↑6 pips → Precio vuelve a subir"),
                (10, "↑10 pips → BUY floating +6 pips"),
                (6, "↑6 pips → BUY TP HIT@1.10150, HEDGE_SELL activa"),
                (2, "↑2 pips → Recovery N1 creado"),
            ]
        )

        # ===============================================
        # 5.1 Recovery N1 TP exitoso
        # ===============================================
        self.generate_csv(
            "scenario_5_1_recovery_n1_tp.csv",
            "EURUSD",
            [
                (0, "Inicio en 1.10000"),
                (6, "↑6 pips → Activa BUY@1.10050"),
                (-12, "↓12 pips → Activa SELL@1.09950 → HEDGED"),
                (10, "↑10 pips → Precio sube"),
                (6, "↑6 pips → BUY TP HIT → IN_RECOVERY"),
                (4, "↑4 pips → Recovery N1 creado"),
                (10, "↑10 pips → Subiendo hacia Recovery"),
                (20, "↑20 pips → Recovery BUY activado"),
                (20, "↑20 pips → Hacia TP de Recovery"),
                (30, "↑30 pips → Más hacia TP"),
                (30, "↑30 pips → Recovery TP HIT (+80 pips)"),
                (5, "↑5 pips → FIFO cierra deuda, neto +60 pips"),
            ]
        )

        # ===============================================
        # 8.1 FIFO múltiple cierre
        # ===============================================
        self.generate_csv(
            "scenario_8_1_fifo_multiple_close.csv",
            "EURUSD",
            [
                (0, "Inicio en 1.10000"),
                (6, "↑6 pips → BUY activa"),
                (-12, "↓12 pips → SELL activa → HEDGED"),
                (10, "↑10 pips → Subida"),
                (6, "↑6 pips → BUY TP → Recovery N1 creado"),
                (25, "↑25 pips → Recovery N1 BUY activa"),
                (-50, "↓50 pips → Recovery N1 SELL activa → N2"),
                (10, "↑10 pips → Recovery N2 creado"),
                (-30, "↓30 pips → Bajada fuerte"),
                (-20, "↓20 pips → Más bajada"),
                (-50, "↓50 pips → Recovery N2 TP HIT"),
                (5, "↓5 pips → FIFO cierra Main(-20) y N1(-40), neto +20"),
            ]
        )

    def generate_high_priority_scenarios(self):
        """Genera escenarios de alta prioridad."""

        print("\n=== GENERANDO ESCENARIOS ALTA PRIORIDAD ===\n")

        # ===============================================
        # 1.3 BUY activa sin TP (retrocede)
        # ===============================================
        self.generate_csv(
            "scenario_1_3_buy_no_tp.csv",
            "EURUSD",
            [
                (0, "Inicio"),
                (6, "↑6 pips → BUY activa"),
                (3, "↑3 pips → BUY floating +4 pips"),
                (-5, "↓5 pips → BUY floating -1 pip"),
                (-8, "↓8 pips → SELL activa → HEDGED"),
                (-2, "↓2 pips → pips_locked=20"),
            ]
        )

        # ===============================================
        # 1.4 SELL activa sin TP (retrocede)
        # ===============================================
        self.generate_csv(
            "scenario_1_4_sell_no_tp.csv",
            "EURUSD",
            [
                (0, "Inicio"),
                (-6, "↓6 pips → SELL activa"),
                (-3, "↓3 pips → SELL floating +3 pips"),
                (5, "↑5 pips → SELL floating -1 pip"),
                (8, "↑8 pips → BUY activa → HEDGED"),
                (2, "↑2 pips → pips_locked=20"),
            ]
        )

        # ===============================================
        # 6.1 Recovery N1 falla → N2
        # ===============================================
        self.generate_csv(
            "scenario_6_1_recovery_n1_fails.csv",
            "EURUSD",
            [
                (0, "Inicio"),
                (6, "BUY activa"),
                (-12, "SELL activa → HEDGED"),
                (10, "Subida"),
                (6, "BUY TP → IN_RECOVERY"),
                (4, "Recovery N1 creado"),
                (25, "Recovery N1 BUY activa"),
                (-15, "Precio baja"),
                (-20, "Más baja"),
                (-15, "Recovery N1 SELL activa → N2 creado"),
                (-5, "Deuda acumulada: -60 pips"),
            ]
        )

        # ===============================================
        # 11.1 USDJPY TP
        # ===============================================
        self.generate_csv(
            "scenario_11_1_usdjpy_tp.csv",
            "USDJPY",
            [
                (0, "Inicio en 150.000"),
                (6, "↑6 pips → BUY activa@150.050"),
                (5, "↑5 pips → Floating +5 pips"),
                (5, "↑5 pips → TP HIT@150.150"),
                (1, "↑1 pip → Balance +10 pips"),
            ]
        )

    def generate_edge_cases(self):
        """Genera casos extremos."""

        print("\n=== GENERANDO EDGE CASES ===\n")

        # ===============================================
        # 10.1 Spread alto → No operar
        # ===============================================
        # Este requiere modificación manual del spread
        filepath = os.path.join(self.output_dir, "scenario_10_1_high_spread.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask', 'spread_pips'])

            base_time = self.base_time
            # Spread alto (5 pips)
            writer.writerow([
                base_time.isoformat(),
                "EURUSD",
                "1.10000",
                "1.10050",
                "5.0"
            ])
            # Spread medio (4 pips)
            writer.writerow([
                (base_time + timedelta(seconds=1)).isoformat(),
                "EURUSD",
                "1.10000",
                "1.10040",
                "4.0"
            ])
            # Spread normal (2 pips)
            writer.writerow([
                (base_time + timedelta(seconds=2)).isoformat(),
                "EURUSD",
                "1.10000",
                "1.10020",
                "2.0"
            ])

        print(f"[OK] Generado: {filepath} (spread variable)")

        # ===============================================
        # 10.2 Gap de fin de semana
        # ===============================================
        filepath = os.path.join(self.output_dir, "scenario_10_2_weekend_gap.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask', 'spread_pips'])

            # Viernes antes del cierre
            writer.writerow([
                "2024-01-05T21:59:00",
                "EURUSD",
                "1.10000",
                "1.10020",
                "2.0"
            ])
            # Lunes apertura con gap de 500 pips
            writer.writerow([
                "2024-01-08T00:01:00",
                "EURUSD",
                "1.10500",
                "1.10520",
                "2.0"
            ])
            writer.writerow([
                "2024-01-08T00:02:00",
                "EURUSD",
                "1.10510",
                "1.10530",
                "2.0"
            ])

        print(f"[OK] Generado: {filepath} (gap 500 pips)")

    def generate_all(self):
        """Genera todos los escenarios."""
        self.generate_critical_scenarios()
        self.generate_high_priority_scenarios()
        self.generate_edge_cases()

        print(f"\n[SUCCESS] {len(self.scenarios_generated)} escenarios generados!")
        print(f"[DIR] Directorio: {os.path.abspath(self.output_dir)}")

        # Generar README
        self._generate_readme()

    def _generate_readme(self):
        """Genera README con índice de escenarios."""
        readme_path = os.path.join(self.output_dir, "README.md")

        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("# WSPlumber - Test Scenarios\n\n")
            f.write("Escenarios de test generados automáticamente.\n\n")
            f.write(f"**Generado:** {datetime.now().isoformat()}\n\n")
            f.write("## Índice de Escenarios\n\n")
            f.write("| Archivo | Par | Ticks | Descripción |\n")
            f.write("|---------|-----|-------|-------------|\n")

            for scenario in self.scenarios_generated:
                f.write(f"| {scenario['filename']} | {scenario['pair']} | "
                       f"{scenario['ticks']} | {scenario['description']} |\n")

            f.write("\n## Cómo Usar\n\n")
            f.write("```python\n")
            f.write("from tests.fixtures.simulated_broker import SimulatedBroker\n\n")
            f.write("broker = SimulatedBroker()\n")
            f.write("broker.load_csv('tests/test_scenarios/scenario_1_1_tp_buy.csv')\n")
            f.write("```\n")

        print(f"[OK] README generado: {readme_path}")


def main():
    """Ejecuta el generador."""
    print("=" * 60)
    print("WSPlumber - Generador de Escenarios de Test")
    print("=" * 60)

    generator = ScenarioGenerator()
    generator.generate_all()

    print("\n" + "=" * 60)
    print("[DONE] Generación completada exitosamente")
    print("=" * 60)


if __name__ == "__main__":
    main()
