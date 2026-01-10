# src/wsplumber/application/services/pruning_service.py
"""
Servicio de Poda (Pruning Service) - Sistema Inmune Layer 4.

Este servicio permite utilizar el excedente de pips (surplus) generado por ciclos 
exitosos para liquidar unidades de deuda de otros ciclos "enfermos" o estancados.
"""

from typing import List
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.interfaces.ports import IRepository
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)

class PruningService:
    def __init__(self, repository: IRepository):
        self.repository = repository

    async def execute_pruning(self, all_active_cycles: List[Cycle]) -> int:
        """
        Ejecuta la lógica de poda cruzada entre ciclos.
        
        Args:
            all_active_cycles: Lista de todos los ciclos activos de todos los pares.
            
        Returns:
            int: Número de unidades de deuda podadas.
        """
        # 1. Calcular el surplus global disponible
        global_surplus = sum(c.accounting.surplus_pips for c in all_active_cycles)
        
        if global_surplus < 20.0:
            return 0
            
        logger.info(f"Pruning: Global surplus available: {global_surplus:.1f} pips")
        
        # 2. Identificar ciclos con deuda (ordenados por antigüedad)
        cycles_with_debt = [c for c in all_active_cycles if c.accounting.pips_locked > 0]
        cycles_with_debt.sort(key=lambda x: x.created_at)
        
        pruned_count = 0
        
        for victim_cycle in cycles_with_debt:
            # Intentar liquidar la unidad más antigua de este ciclo
            if not victim_cycle.accounting.debt_units:
                continue
                
            unit_cost = victim_cycle.accounting.debt_units[0]
            
            if global_surplus >= unit_cost:
                # ¡PODA POSIBLE!
                logger.warning(
                    f"IMMMUNE SYSTEM: Pruning debt unit of {unit_cost} pips from cycle {victim_cycle.id}"
                )
                
                # Descontar del surplus global (distribuido proporcionalmente o FIFO de surplus)
                temp_cost = unit_cost
                for donor_cycle in all_active_cycles:
                    if donor_cycle.accounting.surplus_pips > 0:
                        take = min(donor_cycle.accounting.surplus_pips, temp_cost)
                        donor_cycle.accounting.surplus_pips -= take
                        temp_cost -= take
                        await self.repository.save_cycle(donor_cycle)
                        
                        if temp_cost <= 0:
                            break
                            
                # Liquidar en la victima
                victim_cycle.accounting.debt_units.pop(0)
                victim_cycle.accounting.pips_locked = sum(victim_cycle.accounting.debt_units)
                victim_cycle.metadata["pruned_units"] = victim_cycle.metadata.get("pruned_units", 0) + 1
                
                await self.repository.save_cycle(victim_cycle)
                pruned_count += 1
                global_surplus -= unit_cost
                
                # Nota: En una implementación real, aquí cerraríamos las operaciones 
                # neutralizadas físicas asociadas a esta deuda.
                
            if global_surplus < 20.0:
                break
                
        if pruned_count > 0:
            logger.info(f"Pruning complete: {pruned_count} units liquidated.")
            
        return pruned_count
