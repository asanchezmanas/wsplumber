# src/wsplumber/application/services/robustness_service.py
"""
Servicio de Robustez - Calcula métricas avanzadas de supervivencia y eficiencia.
Versión V4.1 (Standards Compliance)
"""

import math
from typing import List, Dict, Any
from decimal import Decimal
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation

class RobustnessService:
    @staticmethod
    def calculate_red_score(max_level: int, capacity_level: int = 20) -> float:
        """
        RED Score (Recovery Exhaustion Depth).
        0.0 = Safe, 1.0 = Exhausted (Margin Call likely).
        """
        if capacity_level <= 0:
            return 1.0
        score = max_level / capacity_level
        return round(float(score), 3)

    @staticmethod
    def calculate_cer(cycles: List[Cycle]) -> float:
        """
        CER (Cycle Efficiency Ratio).
        Realized Pips / Incurred Debt.
        Must be > 1.15 to be sustainable.
        """
        total_pips_recovered = sum(float(c.accounting.pips_recovered) for c in cycles)
        total_debt_incurred = sum(float(c.accounting.total_debt_incurred) for c in cycles)
        
        if total_debt_incurred == 0:
            return 2.0  # Perfect efficiency if no debt
            
        cer = total_pips_recovered / total_debt_incurred
        return round(float(cer), 3)

    @staticmethod
    def _correlation(x: List[float], y: List[float]) -> float:
        """Calculates Pearson correlation coefficient."""
        n = len(x)
        if n < 2: return 0.0
        
        mu_x = sum(x) / n
        mu_y = sum(y) / n
        
        std_x = math.sqrt(sum((xi - mu_x)**2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mu_y)**2 for yi in y) / n)
        
        if std_x == 0 or std_y == 0:
            return 0.0
            
        covariance = sum((x[i] - mu_x) * (y[i] - mu_y) for i in range(n)) / n
        return covariance / (std_x * std_y)

    @staticmethod
    def calculate_nsb(cycles: List[Cycle]) -> float:
        """
        NSB (Negative Selection Bias).
        Correlation between cycle duration (age) and total debt.
        Positive correlation = High NSB (bad, zombie cycles accumulating).
        """
        if len(cycles) < 5:
            return 0.0

        durations = []
        debts = []
        
        for c in cycles:
            if c.created_at and c.closed_at:
                age = (c.closed_at - c.created_at).total_seconds()
            else:
                age = 0
            
            durations.append(float(age))
            debts.append(float(c.accounting.total_debt_incurred))

        corr = RobustnessService._correlation(durations, debts)
        return round(float(corr), 3)

    @staticmethod
    def generate_certificate(metrics: Dict[str, Any]) -> str:
        """Genera el contenido Markdown para el Certificado de Robustez."""
        cer = metrics.get("cer", 0.0)
        red = metrics.get("red_score", 0.0)
        nsb = metrics.get("nsb", 0.0)
        
        cer_status = "✅ STABLE" if cer > 1.15 else "⚠️ WEAK"
        red_status = "✅ SAFE" if red < 0.6 else "❌ DANGEROUS"
        nsb_status = "✅ HEALTHY" if nsb < 0.3 else "⚠️ DEBT_ACCUMULATION"
        
        return f"""# 🛡️ WSPlumber Robustness Certificate
Generated: {metrics.get('timestamp', 'N/A')}

## Executive Summary
| Metric | Value | Status |
|--------|-------|--------|
| **RED Score** | {red} | {red_status} |
| **CER Ratio** | {cer} | {cer_status} |
| **NSB Bias** | {nsb} | {nsb_status} |

## Technical Breakdown
- **Survivability**: System handled max level {metrics.get('max_level', 0)}.
- **Edge Persistence**: Mathematical edge remains {round((cer-1)*100, 1)}% above overhead.
- **Resolution Entropy**: {metrics.get('resolved_percent', 0.0)}% of cycles resolved correctly.

> [!IMPORTANT]
> This certificate validates the mathematical integrity of the Recovery Cascade logic 
> under current simulation parameters.
"""
