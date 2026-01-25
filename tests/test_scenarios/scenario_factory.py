import csv
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple, Dict, Any

class ScenarioFactory:
    """
    Factoría Factorial Avanzada para WSPlumber.
    Genera un 'Bosque de Escenarios' cubriendo todas las ramificaciones de la estrategia.
    """
    
    def __init__(self, output_dir: str = "tests/scenarios/factorial"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.base_time = datetime(2024, 1, 1, 10, 0, 0)
        self.spread = Decimal("0.0002") # 2 pips
        self.pip_value = Decimal("0.0001")
        self.start_price = Decimal("1.1000")
        
    def _write_header(self, f, description: str, expected_resolution: str):
        """Escribe un encabezado descriptivo en el CSV para auditoría humana."""
        f.write(f"# ESCENARIO: {description}\n")
        f.write(f"# RESOLUCIÓN ESPERADA: {expected_resolution}\n")
        f.write("# Lógica Maya-Zonza 2.0: FIFO con Arrastre de Excedentes\n")
        f.write("# --------------------------------------------------\n")

    def _generate_csv(self, filename: str, ticks: List[Tuple[float, str]], desc: str = "", res: str = ""):
        full_path = os.path.join(self.output_dir, filename)
        with open(full_path, mode='w', newline='', encoding='utf-8') as f:
            if desc:
                self._write_header(f, desc, res)
                
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
            
            curr_price = self.start_price
            for i, (price_change_pips, event) in enumerate(ticks):
                curr_price += Decimal(str(price_change_pips)) * self.pip_value
                ts = (self.base_time + timedelta(seconds=i)).isoformat()
                writer.writerow([ts, "EURUSD", curr_price, curr_price + self.spread])
        return full_path

    def build_forest(self):
        """Genera el bosque completo de escenarios factoriales y stress tests."""
        scenarios = []
        
        # 1. ESCENARIOS FACTORIALES (Base)
        for dir_first in ["buy_first", "sell_first"]:
            for path in ["direct_tp", "hedge_tp", "recovery_tp", "recovery_fail", "cascade_n2", "overlap_ofensivo"]:
                for mode in ["clean", "overlap"]:
                    if path == "direct_tp" and mode == "overlap": continue
                    for condition in ["smooth", "gap"]:
                        for greed_pips in [0, 10, 20]:
                            if "recovery" not in path and greed_pips > 0: continue
                            
                            filename = f"{dir_first}_{path}_{mode}_{condition}_g{greed_pips}.csv"
                            description = f"Test de ruta {path} con {dir_first} y modo {mode}"
                            resolution = "Cierre del ciclo con beneficio" if "tp" in path or "overlap" in path else "Ciclo abierto o fallido"
                            
                            ticks = self.create_ticks(dir_first, path, mode, condition, greed_pips)
                            path_out = self._generate_csv(filename, ticks, description, resolution)
                            scenarios.append(path_out)
        
        # 2. STRESS TESTS (Deep Cascade & Surplus Carryover)
        for n_levels in [5, 20, 50]:
            filename = f"stress_cascade_{n_levels}_levels.csv"
            description = f"Stress Test de Cascada Profunda: {n_levels} niveles de recovery fallido"
            resolution = f"Liquidación FIFO secuencial tras TP final. Debe terminar en positivo por arrastre de excedentes."
            
            ticks = self.create_stress_ticks(n_levels)
            path_out = self._generate_csv(filename, ticks, description, resolution)
            scenarios.append(path_out)
            
        print(f"Forest expanded: {len(scenarios)} scenarios generated (Factorial + Stress).")
        return scenarios

    def create_ticks(self, dir_first: str, path: str, mode: str, condition: str, greed: int) -> List[Tuple[float, str]]:
        """Calcula ticks con precisión para cubrir flags dinámicos."""
        ticks = [(0.0, "Start at 1.1000")]
        mult = 1 if dir_first == "buy_first" else -1
        
        # 1. Activation sequence
        ticks.append((6.0 * mult, "Initial Activation")) 
        
        if path != "direct_tp":
            if mode == "overlap":
                ticks.append((-12.0 * mult, "Fast Reversal (Overlap)")) 
            else:
                ticks.append((-15.0 * mult, "Normal Hedge Activation"))
                ticks.append((5.0 * mult, "Wait in Hedge")) 

        # 2. To the outcome
        if path == "direct_tp":
            ticks.append((10.0 * mult, "Direct move to TP"))
            
        elif path == "hedge_tp":
            target_hit = 15.0 + greed
            ticks.append((target_hit * mult, f"Trying to hit TP (greed={greed})"))
            if condition == "gap":
                ticks.append((10.0 * mult, "Sudden Gap Forward"))
            ticks.append((1.0 * mult, "Closure attempt"))
            
        elif "recovery" in path or "cascade" in path or "overlap" in path:
            ticks.append((25.0 * mult, "Hit Main TP -> Start Recovery")) 
            ticks.append((20.0 * mult, "Enter REC zone")) 
            
            target_move = 80.0 + greed
            ticks.append((target_move * mult, f"Move to REC TP (target={target_move})"))
            
            if path == "recovery_fail":
                ticks.append((-150.0 * mult, "Greed trap: Market collapses!"))
            elif path == "cascade_n2":
                ticks.append((-150.0 * mult, "Fail N1 -> Move to N2"))
                ticks.append((-50.0 * mult, "Activate N2 Order"))
            elif path == "overlap_ofensivo":
                ticks.append((35.0 * mult, "Hit Main TP -> Start Recovery")) 
                ticks.append((20.0 * mult, "Enter REC zone (L1B activation)")) 
                ticks.append((20.0 * mult, "Move even higher (Trail Sell)")) 
                ticks.append((-10.0 * mult, "Reversal: Activate Counter Sell in Profit")) 
                ticks.append((1.0 * mult, "Trigger Overlap Logic"))

        return ticks

    def create_stress_ticks(self, levels: int) -> List[Tuple[float, str]]:
        """Genera una cascada de N niveles seguida de una resolución por TP."""
        ticks = [(0.0, "Stress Start @ 1.1000")]
        
        # 1. Activar Mains y entrar en Hedge
        ticks.append((6.0, "M_B Active"))
        ticks.append((-12.0, "M_S Active (HEDGED)"))
        ticks.append((25.0, "M_B TP Hit -> REC1 Opens"))
        
        # 2. Bucle de Fallos de Recovery (Cascada)
        # Cada fallo añade 40 pips de deuda
        for i in range(1, levels):
            ticks.append((25.0, f"REC{i}_B Active"))
            ticks.append((-65.0, f"REC{i}_S Active (BLOQUEO {i}) -> REC{i+1} Opens"))
            ticks.append((20.0, "Stabilizing..."))
            
        # 3. Resolución Final
        # El último recovery toca TP (+80 pips)
        # Necesitamos un movimiento más largo para recuperar todo el drawdown acumulado
        ticks.append((120.0, f"Final REC{levels} TP Hit! Starting FIFO massive liquidation"))
        ticks.append((1.0, "Processing Arrastre..."))
        
        return ticks
        
    def create_be_ticks(self) -> List[Tuple[float, str]]:
        """
        Escenario E01: Break Even Protection (con GAP)
        """
        ticks = [(0.0, "Start @ 1.1000")]
        ticks.append((6.0, "M_B Active @ 1.1006"))
        ticks.append((5.0, "Position in Profit (+5 pips)"))
        ticks.append((0.0, "Waiting..."))
        ticks.append((0.0, "Waiting..."))
        ticks.append((0.0, "EVENT START: Shield Activates BE"))
        ticks.append((-15.0, "Market Reversal (GAP): Hitting BE Stop Loss"))
        ticks.append((5.0, "Stabilizing..."))
        return ticks

    def create_be_no_gap_ticks(self) -> List[Tuple[float, str]]:
        """
        Escenario E02: Break Even sin Gap (Validación Limpia)
        Misma lógica que E01 pero sin el gap final para ver el cierre al precio BE.
        """
        ticks = [(0.0, "Start @ 1.1000")]
        ticks.append((6.0, "M_B Active @ 1.1006"))
        ticks.append((5.0, "Position in Profit (+5 pips) @ 1.1011"))
        ticks.append((0.0, "Waiting..."))
        ticks.append((0.0, "Waiting..."))
        ticks.append((0.0, "EVENT START: Shield Activates BE @ 1.1011"))
        # Caída suave hasta el BE (1.10061)
        # Entry (1.1006) + Buffer (0.00001) = 1.10061
        # 1.1011 -> 1.10061 = -4.9 pips
        ticks.append((-4.9, "Falling slowly to BE level")) 
        ticks.append((0.0, "Hitting BE level exactly 1.10061"))
        ticks.append((-5.0, "Dropping below BE"))
        return ticks

    def create_event_resume_ticks(self) -> List[Tuple[float, str]]:
        """
        Escenario E03: Resumen tras Escudo (Normalización)
        1. Se activa un Main.
        2. El Escudo cancela la contra-orden.
        3. Al terminar el evento (T+11), la contra-orden se restaura.
        """
        ticks = [(0.0, "Start @ 1.1000")] # T+0: 11:51
        ticks.append((6.0, "M_B Active @ 1.1006")) # T+1: 11:52
        ticks.append((0.0, "Waiting...")) # T+2: 11:53
        ticks.append((0.0, "Waiting...")) # T+3: 11:54
        ticks.append((0.0, "Waiting... (Shield Start)")) # T+4: 11:55 (WINDOW START)
        ticks.append((0.0, "Waiting...")) # T+5: 11:56
        ticks.append((0.0, "Waiting...")) # T+6: 11:57
        ticks.append((0.0, "Waiting...")) # T+7: 11:58
        ticks.append((0.0, "Waiting...")) # T+8: 11:59
        ticks.append((0.0, "EVENT PEAK")) # T+9: 12:00
        ticks.append((0.0, "Waiting...")) # T+10: 12:01
        ticks.append((0.0, "Waiting...")) # T+11: 12:02
        ticks.append((0.0, "Waiting...")) # T+12: 12:03
        ticks.append((0.0, "Waiting...")) # T+13: 12:04
        ticks.append((0.0, "Waiting... (Shield End Soon)")) # T+14: 12:05 (WINDOW END)
        ticks.append((0.0, "EVENT OVER: Normalization begins")) # T+15: 12:06
        ticks.append((0.0, "Normalization completes: Order restored")) # T+16: 12:07
        return ticks

    def create_event_tp_hit_ticks(self) -> List[Tuple[float, str]]:
        """
        Escenario E04: TP durante evento + Recovery post-evento.
        Flujo completo:
        1. Iniciar Main @ 1.1000.
        2. T+1: Activar ambos mains (Hedged).
        3. T+2: TP Main Buy @ 1.1010 -> Recovery Open.
        4. T+4: NEWS START (Shield Active).
        5. T+5: Spike +80 pips (TP Recovery).
        6. T+15: EVENT OVER. Resumption opens next node.
        """
        ticks = [(0.0, "Start @ 1.1000")] # T+0: 11:51
        ticks.append((10.0, "Hedge! (Ambas activas) @ 1.1010")) # T+1: 11:52
        ticks.append((0.0, "Main Buy TP Hit -> Recovery opens")) # T+2: 11:53 
        ticks.append((0.0, "Waiting...")) # T+3: 11:54
        ticks.append((0.0, "EVENT START: Shield Active")) # T+4: 11:55
        ticks.append((80.0, "News Spike! Recovery TP Hit @ 1.1090")) # T+5: 11:56
        for _ in range(9): # T+6..14
            ticks.append((0.0, "Waiting..."))
        ticks.append((0.0, "EVENT OVER: Normalization begins")) # T+15: 12:06
        ticks.append((0.0, "Decision: Open next node due to debt")) # T+16: 12:07
        return ticks

    def save_to_csv(self, ticks: List[Tuple[float, str]], filename: str, start_time: str = None):
        """Guarda ticks en CSV con soporte para timestamp personalizado."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        base_ts = datetime.fromisoformat(start_time) if start_time else self.base_time
        
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'pair', 'bid', 'ask'])
            
            curr_price = self.start_price
            for i, (price_change_pips, event) in enumerate(ticks):
                curr_price += Decimal(str(price_change_pips)) * self.pip_value
                # Usamos intervalos de 1 minuto para coincidir con la ventana de 5 min del escudo
                ts = (base_ts + timedelta(minutes=i)).isoformat() 
                writer.writerow([ts, "EURUSD", curr_price, curr_price + self.spread])
        return filename

if __name__ == "__main__":
    factory = ScenarioFactory()
    factory.build_forest()
    
    # 3. Escenarios de Inmunidad (Checks)
    # E01: Gap reversal
    be_ticks = factory.create_be_ticks()
    factory.save_to_csv(be_ticks, "tests/scenarios/checks/e01_event_shield_be.csv", 
                         start_time="2026-01-16T11:51:00")
                         
    # E02: Smooth reversal (Perfect BE)
    be_no_gap_ticks = factory.create_be_no_gap_ticks()
    factory.save_to_csv(be_no_gap_ticks, "tests/scenarios/checks/e02_break_even_no_gap.csv",
                         start_time="2026-01-16T11:51:00")

    # E03: Event Resume (Normalization)
    resume_ticks = factory.create_event_resume_ticks()
    factory.save_to_csv(resume_ticks, "tests/scenarios/checks/e03_event_resume.csv",
                         start_time="2026-01-16T11:51:00")

    # E04: TP Hit during News
    tp_hit_ticks = factory.create_event_tp_hit_ticks()
    factory.save_to_csv(tp_hit_ticks, "tests/scenarios/checks/e04_event_tp_hit.csv",
                         start_time="2026-01-16T11:51:00")
