# tests/unit/test_engine_signals.py
"""Tests para la lógica de decisión del engine."""
import pytest
from decimal import Decimal
from datetime import datetime

from wsplumber.core.strategy._engine import WallStreetPlumberStrategy
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.types import (
    TickData, 
    CurrencyPair, 
    Price, 
    Pips, 
    Timestamp, 
    SignalType,
    CycleStatus
)


@pytest.fixture
def strategy():
    return WallStreetPlumberStrategy()


@pytest.fixture
def basic_tick():
    """Tick básico de EURUSD con spread bajo."""
    return TickData(
        pair=CurrencyPair("EURUSD"),
        bid=Price(Decimal("1.09990")),
        ask=Price(Decimal("1.10000")),
        timestamp=Timestamp(datetime.now()),
        spread_pips=Pips(1.0)
    )


@pytest.mark.asyncio
async def test_open_cycle_when_no_active(strategy, basic_tick):
    """Verifica que se genere OPEN_CYCLE cuando no hay ciclos activos."""
    signals = await strategy.generate_signals(basic_tick, active_cycles=[])
    
    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.OPEN_CYCLE
    assert signals[0].pair == "EURUSD"


@pytest.mark.asyncio
async def test_no_signal_when_cycle_active_and_ok(strategy, basic_tick):
    """Verifica que no se generen señales cuando el ciclo está activo y OK."""
    cycle = Cycle(id="EURUSD_001", pair=CurrencyPair("EURUSD"))
    # Ciclo activo sin necesidad de recovery
    
    signals = await strategy.generate_signals(basic_tick, active_cycles=[cycle])
    
    # No debería generar signals para abrir ciclo ni para recovery
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_skip_signal_on_high_spread(strategy):
    """Verifica que se omitan señales cuando el spread es alto."""
    high_spread_tick = TickData(
        pair=CurrencyPair("EURUSD"),
        bid=Price(Decimal("1.09950")),
        ask=Price(Decimal("1.10000")),
        timestamp=Timestamp(datetime.now()),
        spread_pips=Pips(5.0)  # > MAX_SPREAD_PIPS (3.0)
    )
    
    signals = await strategy.generate_signals(high_spread_tick, active_cycles=[])
    
    assert len(signals) == 0  # No signal debido a spread alto
