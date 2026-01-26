# src/wsplumber/infrastructure/brokers/paper_broker.py
"""
PaperBroker - Linux-native virtual broker for Cloud Paper Trading.

Uses a real-time price provider (Yahoo Finance or similar) and maintains
a virtual account state in memory/Supabase.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import httpx

from wsplumber.domain.interfaces.ports import IBroker
from wsplumber.domain.types import (
    BrokerTicket, CurrencyPair, OperationStatus, OperationType,
    OrderRequest, OrderResult, Price, Result, TickData, Timestamp, Pips, LotSize
)
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)

class PaperBroker(IBroker):
    def __init__(self, initial_balance: float = 10000.0, leverage: int = 100):
        self.balance = Decimal(str(initial_balance))
        self.leverage = leverage
        self._connected = False
        self.open_positions: Dict[BrokerTicket, Dict[str, Any]] = {}
        self.pending_orders: Dict[BrokerTicket, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []
        self.ticket_counter = 5000  # Start high to distinguish from backtest/MT5
        self._price_cache: Dict[str, TickData] = {}
        self._last_poll_time: Optional[datetime] = None

    async def connect(self) -> Result[bool]:
        self._connected = True
        logger.info("PaperBroker connected (Cloud Mode)")
        return Result.ok(True)

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("PaperBroker disconnected")

    async def is_connected(self) -> bool:
        return self._connected

    async def get_account_info(self) -> Result[Dict[str, Any]]:
        # Calculate equity based on current cached prices
        total_pnl = 0.0
        for ticket, pos in self.open_positions.items():
            pair = pos["pair"]
            price_res = await self.get_current_price(pair)
            if price_res.success:
                tick = price_res.value
                mult = 100 if "JPY" in str(pair) else 10000
                if pos["order_type"] == "buy":
                    pips = float((tick.bid - Price(pos["entry_price"])) * mult)
                else:
                    pips = float((Price(pos["entry_price"]) - tick.ask) * mult)
                
                pos["profit_pips"] = pips
                pos["profit_money"] = pips * float(pos["lot_size"]) * 10.0
                total_pnl += pos["profit_money"]

        equity = float(self.balance) + total_pnl
        return Result.ok({
            "balance": float(self.balance),
            "equity": equity,
            "margin": 0.0,  # Simplified for paper trading
            "free_margin": equity,
            "leverage": self.leverage,
            "currency": "EUR"
        })

    async def get_current_price(self, pair: CurrencyPair) -> Result[TickData]:
        """Fetch live price from Yahoo Finance (via HTTP to avoid complex deps)."""
        # Rate limit polling to once every 2 seconds
        now = datetime.now()
        pair_str = str(pair)
        
        if self._last_poll_time and (now - self._last_poll_time).total_seconds() < 2:
            if pair_str in self._price_cache:
                return Result.ok(self._price_cache[pair_str])

        try:
            # Format for Yahoo: EURUSD=X
            symbol = f"{pair_str}=X"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    result = data["chart"]["result"][0]
                    price = result["meta"]["regularMarketPrice"]
                    
                    # Create a dummy spread since YF doesn't give bid/ask easily in charts
                    bid = Price(Decimal(str(price)))
                    ask = Price(Decimal(str(price + 0.0001))) # 1 pip spread dummy
                    
                    tick = TickData(
                        pair=pair,
                        bid=bid,
                        ask=ask,
                        timestamp=Timestamp(now),
                        spread_pips=Pips(1.0)
                    )
                    self._price_cache[pair_str] = tick
                    self._last_poll_time = now
                    return Result.ok(tick)
                
            return Result.fail(f"HTTP Error {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching live price: {e}")
            if pair_str in self._price_cache:
                return Result.ok(self._price_cache[pair_str])
            return Result.fail(str(e))

    async def place_order(self, request: OrderRequest) -> Result[OrderResult]:
        ticket = BrokerTicket(str(self.ticket_counter))
        self.ticket_counter += 1
        
        # In Paper Mode, we activate market orders immediately
        # Pending orders are stored but we lack a background thread to "tick" them
        # (The orchestrator will poll)
        
        self.pending_orders[ticket] = {
            "ticket": ticket,
            "operation_id": request.operation_id,
            "pair": request.pair,
            "order_type": request.order_type.value,
            "entry_price": float(request.entry_price),
            "tp_price": float(request.tp_price),
            "lot_size": float(request.lot_size),
            "status": "pending"
        }
        
        logger.info(f"PaperBroker: Order placed {ticket} for {request.operation_id}")
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=ticket,
            timestamp=Timestamp(datetime.now())
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
        price_res = await self.get_current_price(pos["pair"])
        close_price = price_res.value.bid if pos["order_type"] == "buy" else price_res.value.ask
        
        # Calculate final P&L
        mult = 100 if "JPY" in str(pos["pair"]) else 10000
        if pos["order_type"] == "buy":
            pips = float((close_price - Price(pos["entry_price"])) * mult)
        else:
            pips = float((Price(pos["entry_price"]) - close_price) * mult)
        
        profit_money = pips * float(pos["lot_size"]) * 10.0
        self.balance += Decimal(str(profit_money))
        
        self.history.append({**pos, "close_price": float(close_price), "profit_pips": pips, "profit_money": profit_money, "closed_at": datetime.now()})
        
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=ticket,
            fill_price=close_price,
            timestamp=Timestamp(datetime.now())
        ))

    async def modify_order(self, ticket: BrokerTicket, new_tp: Optional[Price] = None, new_sl: Optional[Price] = None) -> Result[bool]:
        if ticket in self.pending_orders:
            if new_tp: self.pending_orders[ticket]["tp_price"] = float(new_tp)
            return Result.ok(True)
        return Result.fail("Order not found")

    async def modify_position(self, ticket: BrokerTicket, new_tp: Optional[Price] = None, new_sl: Optional[Price] = None) -> Result[bool]:
        if ticket in self.open_positions:
            if new_tp: self.open_positions[ticket]["tp_price"] = float(new_tp)
            return Result.ok(True)
        return Result.fail("Position not found")

    async def update_position_status(self, ticket: BrokerTicket, status: OperationStatus) -> Result[bool]:
        if ticket in self.open_positions:
            self.open_positions[ticket]["status"] = status.value
            return Result.ok(True)
        return Result.fail("Position not found")

    async def get_open_positions(self) -> Result[List[Dict[str, Any]]]:
        # Process executions (Pending -> Open) based on current price
        executed_tickets = []
        for ticket, order in self.pending_orders.items():
            price_res = await self.get_current_price(order["pair"])
            if price_res.success:
                tick = price_res.value
                # Simple stop activation: if we crossed the price
                # For demo, let's just activate immediately if it's a paper market order
                # or if price touched the entry.
                if order["order_type"].endswith("buy") and tick.ask >= Price(order["entry_price"]):
                    executed_tickets.append(ticket)
                elif order["order_type"].endswith("sell") and tick.bid <= Price(order["entry_price"]):
                    executed_tickets.append(ticket)
        
        for ticket in executed_tickets:
            order = self.pending_orders.pop(ticket)
            order["status"] = "active"
            order["open_time"] = datetime.now()
            self.open_positions[ticket] = order
            logger.info(f"PaperBroker: Order {ticket} activated at market")

        # Check TPs
        tp_closed = []
        for ticket, pos in self.open_positions.items():
            price_res = await self.get_current_price(pos["pair"])
            if price_res.success:
                tick = price_res.value
                if pos["order_type"] == "buy" and pos["tp_price"] and tick.bid >= Price(pos["tp_price"]):
                    tp_closed.append(ticket)
                elif pos["order_type"] == "sell" and pos["tp_price"] and tick.ask <= Price(pos["tp_price"]):
                    tp_closed.append(ticket)
        
        for ticket in tp_closed:
            await self.close_position(ticket)
            logger.info(f"PaperBroker: Position {ticket} hit TP")

        return Result.ok(list(self.open_positions.values()))

    async def get_pending_orders(self) -> Result[List[Dict[str, Any]]]:
        return Result.ok(list(self.pending_orders.values()))

    async def get_order_history(self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> Result[List[Dict[str, Any]]]:
        return Result.ok(self.history)

    async def get_historical_rates(self, pair: CurrencyPair, timeframe: str, count: int, from_date: Optional[datetime] = None) -> Result[List[Dict[str, Any]]]:
        return Result.fail("Historical rates not supported in PaperBroker (Mocked)")

    async def get_historical_ticks(self, pair: CurrencyPair, count: int, from_date: Optional[datetime] = None) -> Result[List[TickData]]:
        return Result.fail("Historical ticks not supported in PaperBroker")
