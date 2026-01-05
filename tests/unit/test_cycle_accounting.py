# tests/unit/test_cycle_accounting.py
import pytest
from decimal import Decimal
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.types import CurrencyPair, Pips, RecoveryId

def test_fifo_recovery_queue():
    """Verifica que la cola de recoveries en el ciclo se comporte como FIFO."""
    cycle = Cycle(id="TEST_CYCLE", pair=CurrencyPair("EURUSD"))
    
    # Simular acumulación de deudas (pips bloqueados/locked)
    # En la implementación real, recovery_queue guarda RecoveryId (que son strings)
    rec1 = RecoveryId("REC_1")
    rec2 = RecoveryId("REC_2")
    
    cycle.add_recovery_to_queue(rec1)
    cycle.add_recovery_to_queue(rec2)
    
    assert len(cycle.accounting.recovery_queue) == 2
    assert cycle.accounting.recovery_queue[0] == "REC_1" # La más antigua primero

def test_neutralization_logic():
    """Verifica que los pips se sumen correctamente en la contabilidad."""
    cycle = Cycle(id="TEST_CYCLE", pair=CurrencyPair("EURUSD"))
    
    # Registrar deudas (neutralización)
    cycle.record_neutralization(Pips(40.0))
    cycle.record_neutralization(Pips(40.0))
    
    assert float(cycle.accounting.pips_locked) == 80.0
    
    # Registrar TP de Recovery
    cycle.record_recovery_tp(Pips(80.0))
    
    assert float(cycle.accounting.pips_recovered) == 80.0
    assert cycle.accounting.is_fully_recovered is True
    assert cycle.accounting.net_pips == 0.0
