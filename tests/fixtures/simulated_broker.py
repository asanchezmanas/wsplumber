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

logger = logging.getLogger(__name__)

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

@dataclass
class SimulatedOrder:
    ticket: BrokerTicket
    operation_id: str
    pair: CurrencyPair
    order_type: OperationType
    entry_price: Price
    tp_price: Price
    lot_size: LotSize
    status: OperationStatus = OperationStatus.PENDING

class SimulatedBroker(IBroker):
    """
    Broker simulado que lee datos de un CSV para testing determinístico.
    """

    def __init__(self, initial_balance: float = 10000.0, leverage: int = 100):
        self.balance = Decimal(str(initial_balance))
        self.leverage = leverage
        self.ticks: List[TickData] = []
        self.current_tick_index = -1
        
        self.open_positions: Dict[BrokerTicket, SimulatedPosition] = {}
        self.pending_orders: Dict[BrokerTicket, SimulatedOrder] = {}
        self.history: List[SimulatedPosition] = []
        
        self.ticket_counter = 1000
        self._connected = False

    def load_csv(self, csv_path: str):
        """Carga ticks desde un archivo CSV."""
        self.ticks = []
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pair = CurrencyPair(row['pair'])
                bid = Price(Decimal(row['bid']))
                ask = Price(Decimal(row['ask']))
                dt = datetime.fromisoformat(row['timestamp'])
                
                # Calcular spread
                mult = 100 if "JPY" in pair else 10000
                spread = float((ask - bid) * mult)
                
                self.ticks.append(TickData(
                    pair=pair,
                    bid=bid,
                    ask=ask,
                    timestamp=Timestamp(dt),
                    spread_pips=Pips(spread)
                ))
        self.current_tick_index = 0
        logger.info(f"Loaded {len(self.ticks)} ticks from {csv_path}")

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
            # Margen simple: lot * contract_size / leverage
            # Asumimos contract_size = 100,000
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
            # En un entorno real buscaríamos el tick más reciente de ese par.
            # Para los escenarios de testing, solemos usar 1 solo par por CSV.
            return Result.fail(f"Current tick is for {tick.pair}, not {pair}")
            
        return Result.ok(tick)

    async def place_order(self, request: OrderRequest) -> Result[OrderResult]:
        ticket = BrokerTicket(str(self.ticket_counter))
        self.ticket_counter += 1
        
        order = SimulatedOrder(
            ticket=ticket,
            operation_id=request.operation_id,
            pair=request.pair,
            order_type=request.order_type,
            entry_price=request.entry_price,
            tp_price=request.tp_price,
            lot_size=request.lot_size
        )
        self.pending_orders[ticket] = order
        
        logger.info("Broker: Order placed", ticket=ticket, operation_id=request.operation_id, price=request.entry_price)
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=ticket,
            timestamp=self.ticks[self.current_tick_index].timestamp if self.ticks and self.current_tick_index >= 0 else None
        ))

    async def cancel_order(self, ticket: BrokerTicket) -> Result[bool]:
        if ticket in self.pending_orders:
            del self.pending_orders[ticket]
            return Result.ok(True)
        return Result.fail("Order not found")

    async def close_position(self, ticket: BrokerTicket) -> Result[OrderResult]:
        if ticket not in self.open_positions:
            return Result.fail("Position not found")
        
        pos = self.open_positions.pop(ticket)
        current_tick = self.ticks[self.current_tick_index]
        
        # Realizar el cierre
        self.balance += Decimal(str(pos.current_pnl_money))
        pos.status = OperationStatus.CLOSED
        self.history.append(pos)
        
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=ticket,
            fill_price=current_tick.bid if pos.order_type.is_buy else current_tick.ask,
            timestamp=current_tick.timestamp
        ))

    async def modify_order(
        self,
        ticket: BrokerTicket,
        new_tp: Optional[Price] = None,
        new_sl: Optional[Price] = None,
    ) -> Result[bool]:
        if ticket in self.pending_orders:
            if new_tp: self.pending_orders[ticket].tp_price = new_tp
            return Result.ok(True)
        if ticket in self.open_positions:
            if new_tp: self.open_positions[ticket].tp_price = new_tp
            return Result.ok(True)
        return Result.fail("Order/Position not found")

    async def get_open_positions(self) -> Result[List[Dict[str, Any]]]:
        print(f">>> Broker[{id(self)}]: get_open_positions called. Count: {len(self.open_positions)}")
        for t, p in self.open_positions.items():
            print(f">>>   Broker[{id(self)}] has pos {t} for {p.operation_id}")
        return Result.ok([vars(p) for p in self.open_positions.values()])

    async def get_pending_orders(self) -> Result[List[Dict[str, Any]]]:
        return Result.ok([vars(o) for o in self.pending_orders.values()])

    async def get_order_history(self, from_date=None, to_date=None) -> Result[List[Dict[str, Any]]]:
        return Result.ok([vars(p) for p in self.history])

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
        """Verifica órdenes pendientes y TPs."""
        # 1. Procesar Órdenes Pendientes (STOP orders)
        tickets_to_activate = []
        for ticket, order in self.pending_orders.items():
            # Buy Stop: precio Ask toca o supera Entry
            if order.order_type.is_buy and tick.ask >= order.entry_price:
                tickets_to_activate.append(ticket)
            # Sell Stop: precio Bid toca o cae por debajo de Entry
            elif order.order_type.is_sell and tick.bid <= order.entry_price:
                tickets_to_activate.append(ticket)
        
        for t in tickets_to_activate:
            order = self.pending_orders.pop(t)
            pos = SimulatedPosition(
                ticket=order.ticket,
                operation_id=order.operation_id,
                pair=order.pair,
                order_type=order.order_type,
                entry_price=order.entry_price, # Slippage 0 en simulación simple
                tp_price=order.tp_price,
                lot_size=order.lot_size,
                open_time=tick.timestamp
            )
            self.open_positions[t] = pos
            logger.info(f"Order {t} activated at {tick.timestamp}")

        # 2. Actualizar P&L y procesar TPs
        tickets_to_close = []
        for ticket, pos in self.open_positions.items():
            # Calcular Pips
            mult = 100 if "JPY" in pos.pair else 10000
            if pos.order_type.is_buy:
                pips = float((tick.bid - pos.entry_price) * mult)
            else:
                pips = float((pos.entry_price - tick.ask) * mult)
            
            pos.current_pnl_pips = pips
            # P&L Money: pips * lot * pip_value
            # Simplificación: pip_value = 10 USD por lote estándar (1.0) en pares USD
            # 0.01 lote -> 0.1 USD por pip
            pip_value_per_lot = 10.0 
            pos.current_pnl_money = pips * float(pos.lot_size) * pip_value_per_lot
            
            # Verificar TP
            if pos.order_type.is_buy and tick.bid >= pos.tp_price:
                tickets_to_close.append(ticket)
            elif pos.order_type.is_sell and tick.ask <= pos.tp_price:
                tickets_to_close.append(ticket)
                
        for t in tickets_to_close:
            await self.close_position(t)
            logger.info(f"Position {t} closed by TP at {tick.timestamp}")
