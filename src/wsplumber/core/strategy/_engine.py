# src/wsplumber/core/strategy/_engine.py
"""
Motor Principal del Core Secreto - El Fontanero.

Implementa IStrategy. Coordina la generación de señales 
principales y de recuperación basadas en las fórmulas y parámetros.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from wsplumber.domain.interfaces.ports import IStrategy
from wsplumber.domain.entities.cycle import Cycle
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.types import (
    StrategySignal, 
    SignalType, 
    TickData, 
    CurrencyPair,
    OperationId,
    OperationStatus,
    Result,
    Pips,
    Price,
    Timestamp
)
from wsplumber.infrastructure.logging.safe_logger import get_logger

from ._params import (
    MAX_SPREAD_PIPS, 
    RECOVERY_DISTANCE_PIPS, 
    RECOVERY_LEVEL_STEP,
    MAX_RECOVERY_LEVELS
)
from ._formulas import calculate_main_tp, calculate_recovery_setup

logger = get_logger(__name__)


def _pips_between(price1: Decimal, price2: Decimal, pair: str) -> float:
    """Calcula la distancia en pips entre dos precios."""
    multiplier = Decimal("100") if "JPY" in pair else Decimal("10000")
    return float(abs(price1 - price2) * multiplier)


class WallStreetPlumberStrategy(IStrategy):
    """
    Estrategia "El Fontanero de Wall Street".
    
    Se basa en ciclos duales continuos y un sistema de recuperación 
    matemática FIFO.
    
    Reglas de decisión:
    1. Si no hay ciclo activo para el par → OPEN_CYCLE
    2. Si el ciclo está en cobertura (hedged) y no tiene recovery → OPEN_RECOVERY
    3. Si el ciclo tiene recovery pero el precio se ha movido 40+ pips
       desde el último nivel de recovery → OPEN_RECOVERY (siguiente nivel)
    """
    
    def __init__(self):
        self._active_cycles: Dict[str, Cycle] = {}
        self._state: Dict[str, Any] = {}

    # ============================================
    # MÉTODOS ABSTRACTOS DE ISTRATEGY
    # ============================================

    def process_tick(
        self,
        pair: CurrencyPair,
        bid: float,
        ask: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """
        Procesa un tick y retorna señal.
        """
        spread_pips = _pips_between(Decimal(str(bid)), Decimal(str(ask)), str(pair))
        
        # Validar spread
        if spread_pips > MAX_SPREAD_PIPS:
            return StrategySignal(
                signal_type=SignalType.NO_ACTION,
                pair=pair,
                metadata={"reason": "high_spread", "spread": spread_pips}
            )

        # Verificar si hay ciclo activo
        if str(pair) not in self._active_cycles:
            return StrategySignal(
                signal_type=SignalType.OPEN_CYCLE,
                pair=pair,
                entry_price=Price(Decimal(str(ask))),
                metadata={"reason": "no_active_cycle", "spread": spread_pips}
            )

        # Analizar ciclo existente para detectar necesidad de recovery
        cycle = self._active_cycles[str(pair)]
        signal = self._analyze_cycle_for_recovery(cycle, Decimal(str(ask)), pair)
        
        if signal:
            if not signal.metadata: signal.metadata = {}
            signal.metadata["spread"] = spread_pips
            return signal
            
        return StrategySignal(
            signal_type=SignalType.NO_ACTION,
            pair=pair,
            metadata={"reason": "logic_not_met", "spread": spread_pips}
        )

    def process_order_fill(
        self,
        operation_id: OperationId,
        fill_price: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """Procesa ejecución de orden."""
        logger.info("Order filled", operation_id=operation_id, fill_price=fill_price)
        # El orquestador se encarga de actualizar el estado
        return StrategySignal(
            signal_type=SignalType.NO_ACTION,
            pair=CurrencyPair(""),  # Se llenará por el orquestador
            metadata={"filled_operation": operation_id}
        )

    def process_tp_hit(
        self,
        operation_id: OperationId,
        profit_pips: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """Procesa take profit alcanzado."""
        logger.info("TP hit", operation_id=operation_id, profit_pips=profit_pips)
        
        # Según Documento Madre: al tocar TP de una main, se renueva ciclo
        return StrategySignal(
            signal_type=SignalType.OPEN_CYCLE, # Provoca renovación
            pair=CurrencyPair(""),
            metadata={"tp_operation": operation_id, "profit_pips": profit_pips, "reason": "tp_renewal"}
        )

    def get_current_state(self) -> Dict[str, Any]:
        """Estado actual (SANITIZADO)."""
        return {
            "active_pairs": list(self._active_cycles.keys()),
            "total_cycles": len(self._active_cycles),
            "timestamp": datetime.now().isoformat()
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Carga estado desde checkpoint."""
        self._state = state
        logger.info("State loaded", state_keys=list(state.keys()))

    def reset(self) -> None:
        """Reinicia el estado de la estrategia."""
        self._active_cycles.clear()
        self._state.clear()
        logger.info("Strategy state reset")

    # ============================================
    # LÓGICA INTERNA DE DECISIÓN
    # ============================================

    async def generate_signals(self, tick: TickData, active_cycles: List[Cycle]) -> List[StrategySignal]:
        """
        Analiza el mercado y el estado actual para generar señales.
        (Versión asíncrona para uso interno)
        """
        signals: List[StrategySignal] = []
        pair = tick.pair
        current_price = Decimal(str(tick.ask))

        if float(tick.spread_pips) > MAX_SPREAD_PIPS:
            return signals

        pair_cycles = [c for c in active_cycles if c.pair == pair]
        
        if not pair_cycles:
            signals.append(StrategySignal(
                pair=pair,
                signal_type=SignalType.OPEN_CYCLE,
                entry_price=current_price,
                timestamp=datetime.now(),
                metadata={"reason": "no_active_cycle"}
            ))
            return signals

        for cycle in pair_cycles:
            signal = self._analyze_cycle_for_recovery(cycle, current_price, pair)
            if signal:
                signals.append(signal)

        return signals

    def _analyze_cycle_for_recovery(
        self, 
        cycle: Cycle, 
        current_price: Decimal, 
        pair: CurrencyPair
    ) -> Optional[StrategySignal]:
        """Analiza un ciclo para determinar si necesita apertura de Recovery."""
        if not cycle.needs_recovery and not cycle.is_hedged:
            return None
            
        current_recovery_level = len(cycle.accounting.recovery_queue)
        # Limite removido por petición del usuario: "cero limites"

        reference_price = self._get_reference_price(cycle)
        if reference_price is None:
            return None

        distance_pips = _pips_between(current_price, reference_price, str(pair))
        is_price_up = current_price > reference_price
        recovery_is_buy = not is_price_up

        required_distance = RECOVERY_DISTANCE_PIPS if current_recovery_level == 0 else RECOVERY_LEVEL_STEP
        
        if distance_pips >= required_distance:
            entry, tp = calculate_recovery_setup(current_price, recovery_is_buy, pair)
            
            return StrategySignal(
                pair=pair,
                signal_type=SignalType.OPEN_RECOVERY,
                entry_price=entry,
                tp_price=tp,
                timestamp=datetime.now(),
                metadata={
                    "reason": "distance_threshold_met",
                    "cycle_id": cycle.id,
                    "recovery_level": current_recovery_level + 1,
                    "distance_pips": distance_pips,
                    "is_buy": recovery_is_buy
                }
            )
        
        return None

    def _get_reference_price(self, cycle: Cycle) -> Optional[Decimal]:
        """Obtiene el precio de referencia para calcular la distancia."""
        if cycle.recovery_operations:
            last_recovery = cycle.recovery_operations[-1]
            return Decimal(str(last_recovery.entry_price))
        
        for op in cycle.neutralized_operations:
            if op.entry_price:
                return Decimal(str(op.entry_price))
        
        for op in cycle.main_operations:
            if op.entry_price:
                return Decimal(str(op.entry_price))
                
        return None

    async def calculate_levels(self, pair: CurrencyPair, current_price: float) -> Result[dict]:
        """Calcula niveles de TP/SL para nuevas operaciones."""
        price = Price(Decimal(str(current_price)))
        
        tp_buy = calculate_main_tp(price, is_buy=True, pair=pair)
        tp_sell = calculate_main_tp(price, is_buy=False, pair=pair)
        
        return Result.ok({
            "buy": {"entry": float(price), "tp": float(tp_buy)},
            "sell": {"entry": float(price), "tp": float(tp_sell)}
        })

    def register_cycle(self, cycle: Cycle) -> None:
        """Registra un ciclo activo en el estado interno."""
        self._active_cycles[str(cycle.pair)] = cycle

    def unregister_cycle(self, pair: CurrencyPair) -> None:
        """Elimina un ciclo del estado interno."""
        self._active_cycles.pop(str(pair), None)
