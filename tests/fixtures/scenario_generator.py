"""
Generador automático de CSVs para los 62 escenarios de auditoría.

Uso:
    python tests/fixtures/scenario_generator.py

Genera:
    tests/scenarios/*.csv (62 archivos)
"""

import csv
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple, Any
import yaml


class ScenarioCSVGenerator:
    """Genera CSVs de prueba desde especificaciones YAML."""

    def __init__(self, specs_path: str, output_dir: str):
        self.specs_path = Path(specs_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(specs_path, 'r', encoding='utf-8') as f:
            self.specs = yaml.safe_load(f)
    
    def generate_all(self) -> None:
        """Genera todos los CSVs de todas las categorías."""
        categories = [
            'core', 'cycles', 'hedged', 'recovery', 
            'fifo', 'risk_management', 'money_management',
            'edge_cases', 'multi_pair', 'jpy_pairs'
        ]
        
        total_generated = 0
        
        for category in categories:
            if category not in self.specs:
                continue
            
            print(f"\n📂 Generando categoría: {category.upper()}")
            
            for scenario_id, spec in self.specs[category].items():
                csv_path = self.output_dir / f"{scenario_id}.csv"
                
                try:
                    if spec.get('pair') == 'MULTI':
                        self._generate_multi_pair_csv(scenario_id, spec, csv_path)
                    else:
                        self._generate_single_pair_csv(scenario_id, spec, csv_path)
                    
                    total_generated += 1
                    print(f"  ✓ {scenario_id}.csv")
                    
                except Exception as e:
                    print(f"  ✗ {scenario_id}.csv - Error: {e}")
        
        print(f"\n✅ Total generado: {total_generated} archivos")
    
    def _generate_single_pair_csv(
        self, 
        scenario_id: str, 
        spec: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Genera CSV para escenario de un solo par."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
            
            pair = spec['pair']
            sequence = spec['sequence']
            
            base_time = datetime(2024, 1, 1, 10, 0, 0)
            
            for i, tick_spec in enumerate(sequence):
                timestamp = base_time + timedelta(seconds=tick_spec['time'])
                bid = Decimal(str(tick_spec['bid']))
                ask = Decimal(str(tick_spec['ask']))
                
                writer.writerow([
                    timestamp.isoformat(),
                    pair,
                    str(bid),
                    str(ask)
                ])
                
                # Interpolar ticks intermedios si hay gran salto
                if i < len(sequence) - 1:
                    next_tick = sequence[i + 1]
                    self._add_interpolated_ticks(
                        writer, pair, base_time,
                        tick_spec, next_tick
                    )
    
    def _add_interpolated_ticks(
        self,
        writer: csv.writer,
        pair: str,
        base_time: datetime,
        current: Dict[str, Any],
        next_tick: Dict[str, Any]
    ) -> None:
        """Añade ticks intermedios para transiciones suaves."""
        time_diff = next_tick['time'] - current['time']
        
        # Si hay más de 1 segundo, interpolar
        if time_diff > 1:
            bid_start = Decimal(str(current['bid']))
            bid_end = Decimal(str(next_tick['bid']))
            ask_start = Decimal(str(current['ask']))
            ask_end = Decimal(str(next_tick['ask']))
            
            # Interpolar linealmente
            steps = min(time_diff - 1, 5)  # Máximo 5 ticks intermedios
            
            for step in range(1, steps + 1):
                ratio = Decimal(step) / Decimal(steps + 1)
                
                interp_bid = bid_start + (bid_end - bid_start) * ratio
                interp_ask = ask_start + (ask_end - ask_start) * ratio
                
                interp_time = base_time + timedelta(
                    seconds=current['time'] + step
                )
                
                writer.writerow([
                    interp_time.isoformat(),
                    pair,
                    str(interp_bid),
                    str(interp_ask)
                ])
    
    def _generate_multi_pair_csv(
        self,
        scenario_id: str,
        spec: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Genera CSV para escenarios multi-pair."""
        # Para multi-pair, crear archivos separados por par
        pairs = spec.get('pairs', [])
        
        for pair in pairs:
            pair_output = output_path.parent / f"{scenario_id}_{pair.lower()}.csv"
            
            with open(pair_output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
                
                # Filtrar sequence por par
                pair_sequence = [
                    tick for tick in spec['sequence']
                    if tick.get('pair', pair) == pair
                ]
                
                base_time = datetime(2024, 1, 1, 10, 0, 0)
                
                for tick_spec in pair_sequence:
                    timestamp = base_time + timedelta(seconds=tick_spec['time'])
                    writer.writerow([
                        timestamp.isoformat(),
                        pair,
                        str(tick_spec['bid']),
                        str(tick_spec['ask'])
                    ])
    
    def generate_scenario(self, scenario_id: str) -> None:
        """Genera un solo escenario específico."""
        for category in self.specs:
            if category == 'metadata':
                continue
            
            if scenario_id in self.specs[category]:
                spec = self.specs[category][scenario_id]
                csv_path = self.output_dir / f"{scenario_id}.csv"
                
                if spec.get('pair') == 'MULTI':
                    self._generate_multi_pair_csv(scenario_id, spec, csv_path)
                else:
                    self._generate_single_pair_csv(scenario_id, spec, csv_path)
                
                print(f"✓ Generado: {scenario_id}.csv")
                return
        
        print(f"✗ Escenario no encontrado: {scenario_id}")


def main():
    """Punto de entrada principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Genera CSVs de test desde especificaciones YAML'
    )
    parser.add_argument(
        '--specs',
        default='tests/fixtures/scenario_specs.yaml',
        help='Ruta al archivo YAML de especificaciones'
    )
    parser.add_argument(
        '--output',
        default='tests/scenarios',
        help='Directorio de salida para CSVs'
    )
    parser.add_argument(
        '--scenario',
        help='Generar solo un escenario específico'
    )
    
    args = parser.parse_args()
    
    generator = ScenarioCSVGenerator(args.specs, args.output)
    
    if args.scenario:
        generator.generate_scenario(args.scenario)
    else:
        generator.generate_all()


if __name__ == '__main__':
    main()
