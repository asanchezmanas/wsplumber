# tests/unit/test_strategy_core.py
import pytest
from decimal import Decimal
from wsplumber.domain.types import Price, CurrencyPair
from wsplumber.core.strategy._formulas import calculate_main_tp, calculate_recovery_setup

def test_calculate_main_tp_standard():
    """Verifica el cálculo de TP de 10 pips para pares estándar (EURUSD)."""
    entry = Price(Decimal("1.1000"))
    pair = CurrencyPair("EURUSD")
    
    # Buy: 1.1000 + 0.0010 = 1.1010
    tp_buy = calculate_main_tp(entry, is_buy=True, pair=pair)
    assert tp_buy == Price(Decimal("1.1010"))
    
    # Sell: 1.1000 - 0.0010 = 1.0990
    tp_sell = calculate_main_tp(entry, is_buy=False, pair=pair)
    assert tp_sell == Price(Decimal("1.0990"))

def test_calculate_main_tp_jpy():
    """Verifica el cálculo de TP de 10 pips para pares JPY."""
    entry = Price(Decimal("150.00"))
    pair = CurrencyPair("USDJPY")
    
    # Buy: 150.00 + 0.10 = 150.10
    tp_buy = calculate_main_tp(entry, is_buy=True, pair=pair)
    assert tp_buy == Price(Decimal("150.10"))
    
    # Sell: 150.00 - 0.10 = 149.90
    tp_sell = calculate_main_tp(entry, is_buy=False, pair=pair)
    assert tp_sell == Price(Decimal("149.90"))

def test_calculate_recovery_setup():
    """Verifica que el recovery se posicione a 20 pips y TP a 80 pips."""
    price = Price(Decimal("1.1000"))
    pair = CurrencyPair("EURUSD")
    
    # BUY Recovery
    # Entry: 1.1000 + 20 pips (0.0020) = 1.1020
    # TP: 1.1020 + 80 pips (0.0080) = 1.1100
    entry, tp = calculate_recovery_setup(price, is_buy=True, pair=pair)
    assert entry == Price(Decimal("1.1020"))
    assert tp == Price(Decimal("1.1100"))
    
    # SELL Recovery
    # Entry: 1.1000 - 20 pips (0.0020) = 1.0980
    # TP: 1.0980 - 80 pips (0.0080) = 1.0900
    entry, tp = calculate_recovery_setup(price, is_buy=False, pair=pair)
    assert entry == Price(Decimal("1.0980"))
    assert tp == Price(Decimal("1.0900"))
