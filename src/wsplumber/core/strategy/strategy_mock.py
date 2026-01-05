# src/wsplumber/core/strategy/strategy_mock.py
"""
Mock del Motor de Estrategia (Secreto).

Simula el comportamiento del core secreto para pruebas de integración.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from wsplumber.domain.interfaces.ports import IStrategy
from wsplumber.domain.types import (
    CurrencyPair,
    OperationId,
    SignalType,
    StrategySignal,
    Timestamp,
)

class StrategyMock(IStrategy):
    """
    Simulación de estrategia para testing.
    """

    def __init__(self):
        self._cycle_open = False

    def process_tick(
        self,
        pair: CurrencyPair,
        bid: float,
        ask: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """
        Lógica de simulación simple: abre un ciclo si no hay uno activo.
        """
        if not self._cycle_open:
            self._cycle_open = True
            return StrategySignal(
                signal_type=SignalType.OPEN_CYCLE,
                pair=pair,
                metadata={"op_type": "main_buy", "reason": "mock_trigger"}
            )
        
        return StrategySignal(signal_type=SignalType.NO_ACTION, pair=pair)

    def process_order_fill(
        self,
        operation_id: OperationId,
        fill_price: float,
        timestamp: datetime,
    ) -> StrategySignal:
        return StrategySignal(signal_type=SignalType.NO_ACTION, pair=CurrencyPair(""))

    def process_tp_hit(
        self,
        operation_id: OperationId,
        profit_pips: float,
        timestamp: datetime,
    ) -> StrategySignal:
        self._cycle_open = False
        return StrategySignal(signal_type=SignalType.CLOSE_OPERATIONS, pair=CurrencyPair(""))

    def get_current_state(self) -> Dict[str, Any]:
        return {"cycle_open": self._cycle_open}

    def load_state(self, state: Dict[str, Any]) -> None:
        self._cycle_open = state.get("cycle_open", False)

    def reset(self) -> None:
        self._cycle_open = False
