# src/wsplumber/core/strategy/_engine.py
"""
Motor Principal del Core Secreto - El Fontanero - VERSIÓN CORREGIDA.

Fixes aplicados:
- FIX-EN-01: process_tp_hit retorna NO_ACTION (orquestador maneja renovación)
- FIX-EN-02: _analyze_cycle_for_recovery verifica status del ciclo
- FIX-EN-03: Uso consistente de CurrencyPair (sin str())
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from wsplumber.domain.interfaces.ports import IStrategy
from wsplumber.domain.entities.cycle import Cycle, CycleStatus
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
    MAX_RECOVERY_LEVELS,
    MIN_ATR_PIPS,
    ATR_WINDOW_SIZE
)
from ._formulas import calculate_main_tp, calculate_recovery_setup

logger = get_logger(__name__)


def _pips_between(price1: Decimal, price2: Decimal, pair: CurrencyPair) -> float:
    """Calcula la distancia en pips entre dos precios."""
    # FIX-EN-03: Usar pair directamente, no str(pair)
    multiplier = Decimal("100") if "JPY" in pair else Decimal("10000")
    return float(abs(price1 - price2) * multiplier)


class WallStreetPlumberStrategy(IStrategy):
    """
    Estrategia "El Fontanero de Wall Street".
    
    VERSIÓN CORREGIDA con mejor manejo de señales y estados.
    """
    
    def __init__(self):
        self._active_cycles: Dict[CurrencyPair, Cycle] = {}
        self._state: Dict[str, Any] = {}
        # Sistema Inmune Layer 2: ATR Tracking
        # {pair: {"current_hour": YYYYMMDDHH, "high": X, "low": Y, "history": [range1, range2, ...]}}
        self._atr_data: Dict[CurrencyPair, Dict[str, Any]] = {}

    def _update_atr(self, pair: CurrencyPair, price: float, timestamp: datetime):
        """Actualiza la data de ATR para el par."""
        if pair not in self._atr_data:
            self._atr_data[pair] = {
                "current_hour": timestamp.strftime("%Y%m%d%H"),
                "high": price,
                "low": price,
                "history": []
            }
            return

        data = self._atr_data[pair]
        hour_key = timestamp.strftime("%Y%m%d%H")

        if hour_key != data["current_hour"]:
            # Nueva hora - Guardar rango de la anterior
            hour_range = data["high"] - data["low"]
            data["history"].append(hour_range)
            if len(data["history"]) > ATR_WINDOW_SIZE:
                data["history"].pop(0)
            
            # Reset para nueva hora
            data["current_hour"] = hour_key
            data["high"] = price
            data["low"] = price
        else:
            # Misma hora - Actualizar High/Low
            data["high"] = max(data["high"], price)
            data["low"] = min(data["low"], price)

    def _get_current_atr(self, pair: CurrencyPair) -> float:
        """Calcula el ATR actual en pips."""
        if pair not in self._atr_data or not self._atr_data[pair]["history"]:
            return 999.0 # Valor por defecto alto para no bloquear si no hay historial
            
        avg_range = sum(self._atr_data[pair]["history"]) / len(self._atr_data[pair]["history"])
        multiplier = 100 if "JPY" in pair else 10000
        return avg_range * multiplier

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
        # Actualizar ATR (Layer 2)
        self._update_atr(pair, ask, timestamp)
        
        spread_pips = _pips_between(Decimal(str(bid)), Decimal(str(ask)), pair)
        
        # Validar spread
        if spread_pips > MAX_SPREAD_PIPS:
            return StrategySignal(
                signal_type=SignalType.NO_ACTION,
                pair=pair,
                metadata={"reason": "high_spread", "spread": spread_pips}
            )

        # Verificar si hay ciclo activo
        if pair not in self._active_cycles:
            # --- IMMUNE SYSTEM: Layer 2 - ATR Filter ---
            atr_pips = self._get_current_atr(pair)
            if atr_pips < MIN_ATR_PIPS:
                return StrategySignal(
                    signal_type=SignalType.NO_ACTION,
                    pair=pair,
                    metadata={
                        "reason": "low_volatility", 
                        "atr_pips": round(atr_pips, 1),
                        "min_required": MIN_ATR_PIPS
                    }
                )
            # --- END IMMUNE SYSTEM ---

            return StrategySignal(
                signal_type=SignalType.OPEN_CYCLE,
                pair=pair,
                entry_price=Price(Decimal(str(ask))),
                metadata={"reason": "no_active_cycle", "spread": spread_pips, "atr": round(atr_pips, 1)}
            )

        # Analizar ciclo existente para detectar necesidad de recovery
        cycle = self._active_cycles[pair]
        signal = self._analyze_cycle_for_recovery(cycle, Decimal(str(ask)), pair)
        
        if signal:
            if not signal.metadata: 
                signal.metadata = {}
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
        return StrategySignal(
            signal_type=SignalType.NO_ACTION,
            pair=CurrencyPair(""),
            metadata={"filled_operation": operation_id}
        )

    def process_tp_hit(
        self,
        operation_id: OperationId,
        profit_pips: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """
        Procesa take profit alcanzado.
        
        FIX-EN-01: Retorna NO_ACTION porque el orquestador ya tiene 
        _renew_main_operations() que maneja la renovación directamente.
        
        Antes retornaba OPEN_CYCLE con pair="" lo cual causaba comportamiento indefinido.
        """
        logger.info("TP hit processed by strategy", 
                   operation_id=operation_id, 
                   profit_pips=profit_pips)
        
        # FIX-EN-01: NO generar señal de apertura aquí
        # El orquestador detecta el TP en _check_operations_status() y 
        # llama a _renew_main_operations() directamente
        return StrategySignal(
            signal_type=SignalType.NO_ACTION,
            pair=CurrencyPair(""),  # OK porque es NO_ACTION
            metadata={
                "event": "tp_acknowledged",
                "tp_operation": operation_id, 
                "profit_pips": profit_pips,
                "note": "Renewal handled by orchestrator"
            }
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
        """
        Analiza un ciclo para determinar si necesita apertura de Recovery.
        
        FIX-EN-02: Verifica el status del ciclo antes de generar señales.
        """
        # FIX-EN-02: No generar recovery para ciclos cerrados o pausados
        if cycle.status in (CycleStatus.CLOSED, CycleStatus.PAUSED):
            return None
        
        # Solo generar recovery si está en estado HEDGED o necesita recovery
        if not cycle.needs_recovery and not cycle.is_hedged:
            return None
        
        if cycle.status not in (CycleStatus.HEDGED, CycleStatus.IN_RECOVERY, CycleStatus.ACTIVE):
            logger.debug("Cycle not in valid state for recovery", 
                        cycle_id=cycle.id, 
                        status=cycle.status.value)
            return None
            
        # GUARD-FIX-001: No generar más señales si ya hay un recovery pendiente
        # Esto previene la "cascada de señales" durante el tiempo de apertura
        if any(op.status == OperationStatus.PENDING for op in cycle.recovery_operations):
            logger.debug("Recovery already pending, skipping signal generation", cycle_id=cycle.id)
            return None

        current_recovery_level = len(cycle.accounting.recovery_queue)


        reference_price = self._get_reference_price(cycle)
        if reference_price is None:
            return None

        distance_pips = _pips_between(current_price, reference_price, pair)
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
                    "cycle_status": cycle.status.value,
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
        # FIX-EN-03: Usar CurrencyPair directamente como key
        self._active_cycles[cycle.pair] = cycle

    def unregister_cycle(self, pair: CurrencyPair) -> None:
        """Elimina un ciclo del estado interno."""
        # FIX-EN-03: Usar pair directamente
        self._active_cycles.pop(pair, None)