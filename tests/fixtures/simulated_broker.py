# tests/fixtures/simulated_broker.py
"""
SimulatedBroker - VERSIÓN CORREGIDA

Fixes aplicados:
- FIX-SB-01: No cerrar TPs internamente, solo marcar
- FIX-SB-02: get_open_positions incluye posiciones TP_HIT
- FIX-SB-03: Cálculo de P&L considera spread
"""

import csv
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from wsplumber.domain.interfaces.ports import IBroker
from wsplumber.domain.types import (
    CurrencyPair, TickData, OrderRequest, OrderResult,
    Result, BrokerTicket, Price, LotSize, OperationType,
    OperationStatus, Timestamp, Pips, Direction
)
from wsplumber.infrastructure.data.m1_data_loader import M1DataLoader
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__, environment="development")


@dataclass
class SimulatedPosition:
    ticket: BrokerTicket
    operation_id: str
    pair: CurrencyPair
    order_type: OperationType
    entry_price: Price
    tp_price: Price
    lot_size: LotSize
    open_time: datetime
    current_pnl_pips: float = 0.0
    current_pnl_money: float = 0.0
    status: OperationStatus = OperationStatus.ACTIVE
    # FIX-SB-01: Campos para tracking de cierre
    actual_close_price: Optional[Price] = None
    close_time: Optional[datetime] = None


@dataclass
class SimulatedOrder:
    ticket: BrokerTicket
    operation_id: str
    pair: CurrencyPair
    order_type: OperationType
    entry_price: Price
    tp_price: Price
    lot_size: LotSize
    reference_price: Optional[Price] = None  # Price when order was created (to determine stop direction)
    status: OperationStatus = OperationStatus.PENDING


class SimulatedBroker(IBroker):
    """
    Broker simulado que lee datos de un CSV para testing determinístico.
    
    VERSIÓN CORREGIDA: Los TPs se marcan pero NO se cierran internamente.
    El orquestador debe detectar el TP via sync y luego llamar a close_position().
    """

    def __init__(self, initial_balance: float = 10000.0, leverage: int = 100):
        self.balance = Decimal(str(initial_balance))
        self.leverage = leverage
        self.ticks: List[TickData] = []
        self.current_tick_index = -1
        
        self.open_positions: Dict[BrokerTicket, SimulatedPosition] = {}
        self.pending_orders: Dict[BrokerTicket, SimulatedOrder] = {}
        self.history: List[Dict[str, Any]] = []  # FIX: Ahora guarda dicts con más info
        
        self.ticket_counter = 1000
        self._connected = False

    def load_csv(self, csv_path: str):
        """Carga ticks desde un archivo CSV (Formato TickData)."""
        self.ticks = []
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pair = CurrencyPair(row['pair'])
                bid = Price(Decimal(row['bid']))
                ask = Price(Decimal(row['ask']))
                dt = datetime.fromisoformat(row['timestamp'])
                
                pips_mult = 100 if "JPY" in pair else 10000
                spread = row.get('spread_pips', float((ask - bid) * pips_mult))
                
                self.ticks.append(TickData(
                    pair=pair,
                    bid=bid,
                    ask=ask,
                    timestamp=Timestamp(dt),
                    spread_pips=Pips(float(spread))
                ))
        self.current_tick_index = -1
        logger.info(f"Loaded {len(self.ticks)} ticks from {csv_path}")

    def load_m1_csv(self, csv_path: str, pair: Optional[CurrencyPair] = None, max_bars: int = None):
        """Carga ticks desde un archivo CSV M1 (Formato OHLC)."""
        if not pair:
            pair = M1DataLoader.detect_pair_from_filename(csv_path)
        
        loader = M1DataLoader(pair)
        self.ticks = list(loader.parse_m1_csv(csv_path, max_bars=max_bars))
        for tick in self.ticks:
            if tick.spread_pips <= 0:
                tick.spread_pips = Pips(1.0)
                tick.ask = Price(tick.bid + Decimal("0.00010"))
                
        self.current_tick_index = -1

        if self.ticks:
            logger.info("Loaded synthetic ticks from M1 CSV", 
                        max_bars=max_bars, 
                        total_ticks=len(self.ticks), 
                        file=csv_path)

    async def connect(self) -> Result[bool]:
        self._connected = True
        return Result.ok(True)

    async def disconnect(self) -> None:
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def get_account_info(self) -> Result[Dict[str, Any]]:
        equity = self.balance
        margin_used = Decimal("0")
        
        for pos in self.open_positions.values():
            equity += Decimal(str(pos.current_pnl_money))
            margin_used += Decimal(str(pos.lot_size)) * 100000 / self.leverage
            
        return Result.ok({
            "balance": float(self.balance),
            "equity": float(equity),
            "margin": float(margin_used),
            "free_margin": float(equity - margin_used),
            "leverage": self.leverage,
            "currency": "EUR"
        })

    async def get_current_price(self, pair: CurrencyPair) -> Result[TickData]:
        if self.current_tick_index < 0 or self.current_tick_index >= len(self.ticks):
            return Result.fail("No tick data available")
        
        tick = self.ticks[self.current_tick_index]
        if tick.pair != pair:
            return Result.fail(f"Current tick is for {tick.pair}, not {pair}")
            
        return Result.ok(tick)

    def should_process_tick(self, tick: TickData) -> bool:
        """
        OPTIMIZATION: Check if this tick can trigger any event.
        
        NOTE: This optimization is currently DISABLED because the broker
        needs to process every tick to detect order activations and TP hits.
        The skip logic was causing orders to never activate.
        
        Future optimization should be done at the orchestrator level, not here.
        """
        # DISABLED: Always process every tick for now
        # The broker's _process_executions() needs to run on every tick
        return True

    async def place_order(self, request: OrderRequest) -> Result[OrderResult]:
        ticket = BrokerTicket(str(self.ticket_counter))
        self.ticket_counter += 1
        
        # Obtener precio de referencia actual para determinar dirección del stop
        current_ref_price = None
        if self.ticks and self.current_tick_index >= 0:
            current_tick = self.ticks[self.current_tick_index]
            current_ref_price = current_tick.mid  # Precio medio actual
        
        order = SimulatedOrder(
            ticket=ticket,
            operation_id=request.operation_id,
            pair=request.pair,
            order_type=request.order_type,
            entry_price=request.entry_price,
            tp_price=request.tp_price,
            lot_size=request.lot_size,
            reference_price=current_ref_price  # Para saber si entry está arriba o abajo
        )
        self.pending_orders[ticket] = order
        
        logger.info("Broker: Order placed", 
                    ticket=ticket, 
                    operation_id=request.operation_id, 
                    price=float(request.entry_price),
                    lots=float(request.lot_size),
                    tp=float(request.tp_price))
        
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=ticket,
            timestamp=self.ticks[self.current_tick_index].timestamp if self.ticks and self.current_tick_index >= 0 else None
        ))

    async def cancel_order(self, ticket: BrokerTicket) -> Result[bool]:
        if ticket in self.pending_orders:
            del self.pending_orders[ticket]
            logger.info("Broker: Order cancelled", ticket=ticket)
            return Result.ok(True)
        return Result.fail("Order not found")

    async def update_position_status(self, ticket: BrokerTicket, new_status: OperationStatus) -> Result[bool]:
        """
        Update the status of an open position.
        
        Used when operations are neutralized (HEDGED state) to prevent
        them from hitting TP in the broker simulation.
        """
        if ticket in self.open_positions:
            self.open_positions[ticket].status = new_status
            logger.info(f"Broker: Position {ticket} status updated to {new_status.value}")
            return Result.ok(True)
        return Result.fail("Position not found")

    async def close_position(self, ticket: BrokerTicket) -> Result[OrderResult]:
        """
        Cierra una posición abierta.
        
        FIX-SB-01: Este método ahora es el ÚNICO lugar donde se cierra una posición.
        El broker NO cierra posiciones automáticamente en _process_executions().
        """
        if ticket not in self.open_positions:
            return Result.fail("Position not found")
        
        pos = self.open_positions.pop(ticket)
        current_tick = self.ticks[self.current_tick_index]
        
        # Determinar precio de cierre
        if pos.actual_close_price:
            # Ya fue marcado como TP_HIT, usar ese precio
            close_price = pos.actual_close_price
        else:
            # Cierre manual, usar precio actual
            close_price = current_tick.bid if pos.order_type.is_buy else current_tick.ask
        
        # Realizar el cierre
        self.balance += Decimal(str(pos.current_pnl_money))
        
        # Guardar en historial con información completa
        self.history.append({
            "ticket": pos.ticket,
            "operation_id": pos.operation_id,
            "pair": pos.pair,
            "order_type": pos.order_type.value,
            "entry_price": float(pos.entry_price),
            "close_price": float(close_price),
            "actual_close_price": float(close_price),
            "lot_size": float(pos.lot_size),
            "profit_pips": pos.current_pnl_pips,
            "profit_money": pos.current_pnl_money,
            "open_time": pos.open_time,
            "close_time": pos.close_time or current_tick.timestamp,
            "closed_at": pos.close_time or current_tick.timestamp,
            "status": pos.status.value
        })
        
        logger.info("Broker: Position closed", 
                    ticket=ticket, 
                    profit_pips=pos.current_pnl_pips,
                    close_price=float(close_price))
        
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=ticket,
            fill_price=close_price,
            timestamp=current_tick.timestamp
        ))

    async def modify_order(
        self,
        ticket: BrokerTicket,
        new_tp: Optional[Price] = None,
        new_sl: Optional[Price] = None,
    ) -> Result[bool]:
        if ticket in self.pending_orders:
            if new_tp: 
                self.pending_orders[ticket].tp_price = new_tp
            return Result.ok(True)
        if ticket in self.open_positions:
            if new_tp: 
                self.open_positions[ticket].tp_price = new_tp
            return Result.ok(True)
        return Result.fail("Order/Position not found")

    async def get_open_positions(self) -> Result[List[Dict[str, Any]]]:
        """
        FIX-SB-02: Incluye posiciones marcadas como TP_HIT.
        
        El orquestador necesita ver estas posiciones para:
        1. Detectar que el TP fue alcanzado
        2. Ejecutar la lógica de renovación
        3. Luego llamar a close_position()
        """
        result = []
        for pos in self.open_positions.values():
            result.append({
                "ticket": pos.ticket,
                "operation_id": pos.operation_id,
                "symbol": pos.pair,
                "pair": pos.pair,
                "volume": float(pos.lot_size),
                "type": "buy" if pos.order_type.is_buy else "sell",
                "order_type": pos.order_type.value,
                "entry_price": float(pos.entry_price),
                "fill_price": float(pos.entry_price),  # Para compatibilidad
                "tp": float(pos.tp_price),
                "profit": pos.current_pnl_money,
                "profit_pips": pos.current_pnl_pips,
                "open_time": pos.open_time,
                # FIX-SB-02: Incluir status y datos de cierre si es TP_HIT
                "status": pos.status.value,
                "actual_close_price": float(pos.actual_close_price) if pos.actual_close_price else None,
                "close_price": float(pos.actual_close_price) if pos.actual_close_price else None,
                "close_time": pos.close_time,
                "closed_at": pos.close_time,
            })
        
        if result:
            logger.debug("Broker Open Positions", 
                         count=len(result),
                         positions=[{
                             "ticket": p["ticket"],
                             "status": p["status"],
                             "pips": p["profit_pips"]
                         } for p in result])
        
        return Result.ok(result)

    async def get_pending_orders(self) -> Result[List[Dict[str, Any]]]:
        return Result.ok([{
            "ticket": o.ticket,
            "operation_id": o.operation_id,
            "symbol": o.pair,
            "volume": float(o.lot_size),
            "type": o.order_type.value,
            "entry_price": float(o.entry_price),
            "tp": float(o.tp_price),
            "status": o.status.value
        } for o in self.pending_orders.values()])

    async def get_order_history(self, from_date=None, to_date=None) -> Result[List[Dict[str, Any]]]:
        """Retorna historial de posiciones cerradas."""
        return Result.ok(self.history)

    async def get_historical_rates(self, pair, timeframe, count, from_date=None) -> Result[List[Dict[str, Any]]]:
        return Result.fail("Not implemented in SimulatedBroker")

    async def get_historical_ticks(self, pair, count, from_date=None) -> Result[List[TickData]]:
        return Result.ok(self.ticks[:self.current_tick_index+1][-count:])

    # --- Lógica de Simulación ---

    async def advance_tick(self) -> Optional[TickData]:
        """Avanza al siguiente tick y procesa ejecuciones."""
        self.current_tick_index += 1
        if self.current_tick_index >= len(self.ticks):
            return None
        
        tick = self.ticks[self.current_tick_index]
        await self._process_executions(tick)
        return tick

    async def _process_executions(self, tick: TickData):
        """
        Verifica órdenes pendientes y TPs.
        
        FIX-SB-01: Los TPs se MARCAN pero NO se cierran.
        El orquestador debe detectarlos y llamar a close_position().
        """
        # 1. Procesar Órdenes Pendientes (activación)
        # NOTA: En WSPlumber todas las órdenes son STOP orders:
        # - BUY_STOP: El entry está POR ENCIMA del precio actual → activa cuando ask >= entry
        # - SELL_STOP: El entry está POR DEBAJO del precio actual → activa cuando bid <= entry
        # 
        # IMPORTANTE para hedges:
        # - HEDGE_SELL entry está al TP del MAIN_BUY (arriba) → activa cuando bid >= entry
        # - HEDGE_BUY entry está al TP del MAIN_SELL (abajo) → activa cuando ask <= entry
        #
        # La lógica correcta es verificar si el precio CRUZÓ el nivel de entry:
        # - Para BUY: ask cruza entry desde abajo (ask >= entry Y entry estaba arriba)
        # - Para SELL: bid cruza entry desde arriba (bid <= entry Y entry estaba abajo)
        
        tickets_to_activate = []
        for ticket, order in self.pending_orders.items():
            ref_price = order.reference_price
            
            # Determinar si es un STOP arriba o abajo del precio de referencia
            if ref_price:
                entry_above = order.entry_price > ref_price
                entry_below = order.entry_price < ref_price
            else:
                # Sin referencia, asumir comportamiento por tipo
                entry_above = order.order_type.is_buy  # BUY_STOP normalmente arriba
                entry_below = order.order_type.is_sell  # SELL_STOP normalmente abajo
            
            if entry_above:
                # Entry está ARRIBA → activa cuando precio SUBE hasta entry
                # Usa ask para BUY, bid para SELL
                if order.order_type.is_buy:
                    if tick.ask >= order.entry_price:
                        tickets_to_activate.append(ticket)
                else:  # SELL con entry arriba (como HEDGE_SELL)
                    if tick.bid >= order.entry_price:
                        tickets_to_activate.append(ticket)
            else:
                # Entry está ABAJO → activa cuando precio BAJA hasta entry
                if order.order_type.is_sell:
                    if tick.bid <= order.entry_price:
                        tickets_to_activate.append(ticket)
                else:  # BUY con entry abajo (como HEDGE_BUY)
                    if tick.ask <= order.entry_price:
                        tickets_to_activate.append(ticket)
        
        for t in tickets_to_activate:
            order = self.pending_orders.pop(t)
            pos = SimulatedPosition(
                ticket=order.ticket,
                operation_id=order.operation_id,
                pair=order.pair,
                order_type=order.order_type,
                entry_price=order.entry_price,
                tp_price=order.tp_price,
                lot_size=order.lot_size,
                open_time=tick.timestamp
            )
            self.open_positions[t] = pos
            logger.info(f"Broker: Order {t} activated", 
                       operation_id=order.operation_id,
                       entry_price=float(order.entry_price),
                       timestamp=tick.timestamp)

        # 2. Actualizar P&L y MARCAR TPs (NO cerrar)
        for ticket, pos in self.open_positions.items():
            # FIX-SB-04: Skip P&L recalculation for TP_HIT positions
            # Their P&L should be frozen at the TP price, not recalculated
            if pos.status == OperationStatus.TP_HIT:
                # P&L is already frozen at close price, skip recalculation
                continue
            
            # FIX-SB-03: Considerar spread en calculo de P&L
            mult = 100 if "JPY" in pos.pair else 10000
            
            if pos.order_type.is_buy:
                # Buy: ganamos cuando bid sube (vendemos al bid)
                # Spread ya fue pagado al abrir (compramos al ask)
                pips = float((tick.bid - pos.entry_price) * mult)
            else:
                # Sell: ganamos cuando ask baja (compramos al ask)
                # Spread ya fue pagado al abrir (vendimos al bid)
                pips = float((pos.entry_price - tick.ask) * mult)
            
            pos.current_pnl_pips = pips
            pip_value_per_lot = 10.0 
            pos.current_pnl_money = pips * float(pos.lot_size) * pip_value_per_lot

            
            # FIX-SB-01: Solo MARCAR TP, NO cerrar
            if pos.status == OperationStatus.ACTIVE:  # Solo si no está ya marcado
                tp_hit = False
                close_price = None
                
                if pos.order_type.is_buy and tick.bid >= pos.tp_price:
                    tp_hit = True
                    close_price = tick.bid
                elif pos.order_type.is_sell and tick.ask <= pos.tp_price:
                    tp_hit = True
                    close_price = tick.ask
                    
                if tp_hit:
                    pos.status = OperationStatus.TP_HIT
                    pos.actual_close_price = close_price
                    pos.close_time = tick.timestamp
                    logger.info(f"Broker: Position {ticket} marked as TP_HIT",
                               operation_id=pos.operation_id,
                               close_price=float(close_price),
                               profit_pips=pos.current_pnl_pips)
                    # NO llamar a close_position() aquí
                    # El orquestador lo hará después de procesar
