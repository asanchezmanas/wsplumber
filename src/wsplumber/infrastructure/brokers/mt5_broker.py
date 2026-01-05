# src/wsplumber/infrastructure/brokers/mt5_broker.py
"""
Adaptador para MetaTrader 5.

Implementa IBroker usando la librería oficial MetaTrader5 de MetaQuotes.
Maneja conexión, ejecución de órdenes y obtención de datos de mercado.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5

from wsplumber.domain.interfaces.ports import IBroker
from wsplumber.domain.types import (
    BrokerTicket,
    CurrencyPair,
    Direction,
    LotSize,
    Money,
    OperationId,
    OperationStatus,
    OperationType,
    OrderRequest,
    OrderResult,
    Pips,
    Price,
    Result,
    TickData,
    Timestamp,
)
from wsplumber.infrastructure.logging.safe_logger import get_logger

logger = get_logger(__name__)


class MT5Broker(IBroker):
    """
    Implementación de IBroker para MetaTrader 5.
    
    Requiere que la terminal de MT5 esté instalada y accesible.
    """

    def __init__(self, login: int, password: str, server: str, path: Optional[str] = None):
        """
        Inicializa el adaptador.

        Args:
            login: Número de cuenta
            password: Contraseña
            server: Servidor del broker
            path: Ruta al terminal MT5 (opcional)
        """
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self._connected = False

    async def connect(self) -> Result[bool]:
        """Establece conexión con la terminal y loguea la cuenta."""
        try:
            # Inicializar terminal
            init_params = {
                "login": self.login,
                "password": self.password,
                "server": self.server,
            }
            if self.path:
                init_params["path"] = self.path

            if not mt5.initialize(**init_params):
                err = mt5.last_error()
                logger.error("Failed to initialize MT5", error=err)
                return Result.fail(f"MT5 initialize failed: {err}", "MT5_INIT_ERROR")

            self._connected = True
            logger.info("MT5 connected and logged in", login=self.login, server=self.server)
            return Result.ok(True)

        except Exception as e:
            logger.error("Exception during MT5 connection", exception=e)
            return Result.fail(str(e), "CONNECTION_ERROR")

    async def disconnect(self) -> None:
        """Cierra la conexión con la terminal."""
        mt5.shutdown()
        self._connected = False
        logger.info("MT5 connection closed")

    async def is_connected(self) -> bool:
        """Verifica si la terminal está conectada y logueada."""
        if not self._connected:
            return False
        
        # Verificar estado real de la cuenta
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            self._connected = False
            return False
        
        return terminal_info.connected

    async def get_account_info(self) -> Result[Dict[str, Any]]:
        """Obtiene información financiera de la cuenta."""
        acc = mt5.account_info()
        if acc is None:
            return Result.fail("Could not get account info", "MT5_ERROR")
        
        return Result.ok({
            "login": acc.login,
            "balance": acc.balance,
            "equity": acc.equity,
            "margin": acc.margin,
            "margin_free": acc.margin_free,
            "currency": acc.currency,
            "leverage": acc.leverage,
        })

    async def get_current_price(self, pair: CurrencyPair) -> Result[TickData]:
        """Obtiene el último tick de un símbolo."""
        tick = mt5.symbol_info_tick(str(pair))
        if tick is None:
            return Result.fail(f"Could not get tick for {pair}", "SYMBOL_NOT_FOUND")
        
        spread = (tick.ask - tick.bid)
        # Ajustar para pips (suponiendo 4/5 decimales o 2/3 para JPY)
        multiplier = 100 if "JPY" in str(pair) else 10000
        spread_pips = Pips(float(spread * multiplier))

        data = TickData(
            pair=pair,
            bid=Price(Decimal(str(tick.bid))),
            ask=Price(Decimal(str(tick.ask))),
            timestamp=Timestamp(datetime.fromtimestamp(tick.time)),
            spread_pips=spread_pips
        )
        return Result.ok(data)

    async def place_order(self, request: OrderRequest) -> Result[OrderResult]:
        """Envía una orden al mercado o pendiente."""
        # Mapear tipo de orden
        mt5_order_type = self._map_order_type(request.order_type)
        if mt5_order_type is None:
            return Result.fail(f"Unsupported order type: {request.order_type}", "INVALID_TYPE")

        # Preparar request para MT5
        # NOTA: En este sistema usamos principalmente ordenes a mercado por la naturaleza del core
        # Pero se puede extender para ordenes pendientes (STOP/LIMIT)
        action = mt5.TRADE_ACTION_DEAL # Por defecto a mercado
        
        trade_request = {
            "action": action,
            "symbol": str(request.pair),
            "volume": float(request.lot_size),
            "type": mt5_order_type,
            "price": float(request.entry_price),
            "tp": float(request.tp_price),
            "magic": 123456, # Magic number configurable
            "comment": request.comment or f"wsplumber {request.operation_id}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC, # Puede variar por broker
        }

        # Ejecutar orden
        result = mt5.order_send(trade_request)
        
        if result is None:
            return Result.fail("MT5 order_send returned None", "MT5_CRITICAL_ERROR")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Order failed", retcode=result.retcode, comment=result.comment)
            return Result.fail(f"Order failed: {result.comment} ({result.retcode})", "ORDER_REJECTED")

        logger.info("Order placed successfully", ticket=result.order, pair=request.pair)
        
        return Result.ok(OrderResult(
            success=True,
            broker_ticket=BrokerTicket(str(result.order)),
            fill_price=Price(Decimal(str(result.price))),
            timestamp=Timestamp(datetime.now())
        ))

    async def cancel_order(self, ticket: BrokerTicket) -> Result[bool]:
        """Cancela una orden pendiente."""
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(str(ticket)),
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return Result.ok(True)
        return Result.fail(f"Cancel failed: {result.comment}", "CANCEL_ERROR")

    async def close_position(self, ticket: BrokerTicket) -> Result[OrderResult]:
        """Cierra una posición abierta mediante una operación contraria."""
        # Obtener info de la posición
        position = mt5.positions_get(ticket=int(str(ticket)))
        if not position:
            return Result.fail(f"Position {ticket} not found", "NOT_FOUND")
        
        pos = position[0]
        symbol = pos.symbol
        volume = pos.volume
        pos_type = pos.type
        
        # Tipo opuesto
        type_close = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if type_close == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": type_close,
            "position": int(str(ticket)),
            "price": price,
            "magic": 123456,
            "comment": "Close by wsplumber",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return Result.ok(OrderResult(
                success=True,
                broker_ticket=BrokerTicket(str(result.order)),
                fill_price=Price(Decimal(str(result.price))),
                timestamp=Timestamp(datetime.now())
            ))
        
        return Result.fail(f"Close failed: {result.comment}", "CLOSE_ERROR")

    async def modify_order(
        self,
        ticket: BrokerTicket,
        new_tp: Optional[Price] = None,
        new_sl: Optional[Price] = None,
    ) -> Result[bool]:
        """Modifica SL/TP de una posición u orden."""
        # Determinar si es posición u orden
        position = mt5.positions_get(ticket=int(str(ticket)))
        if position:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": int(str(ticket)),
                "tp": float(new_tp) if new_tp else 0.0,
                "sl": float(new_sl) if new_sl else 0.0,
            }
        else:
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": int(str(ticket)),
                "tp": float(new_tp) if new_tp else 0.0,
                "sl": float(new_sl) if new_sl else 0.0,
            }
            
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return Result.ok(True)
        return Result.fail(f"Modify failed: {result.comment}", "MODIFY_ERROR")

    async def get_open_positions(self) -> Result[List[Dict[str, Any]]]:
        """Lista todas las posiciones abiertas."""
        positions = mt5.positions_get()
        if positions is None:
            return Result.fail("Could not get positions", "MT5_ERROR")
        
        res = []
        for p in positions:
            res.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "volume": p.volume,
                "type": "buy" if p.type == mt5.POSITION_TYPE_BUY else "sell",
                "price_open": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "magic": p.magic,
            })
        return Result.ok(res)

    async def get_pending_orders(self) -> Result[List[Dict[str, Any]]]:
        """Lista todas las órdenes pendientes."""
        orders = mt5.orders_get()
        if orders is None:
            return Result.fail("Could not get orders", "MT5_ERROR")
        
        res = []
        for o in orders:
            res.append({
                "ticket": o.ticket,
                "symbol": o.symbol,
                "volume": o.volume_initial,
                "type": o.type,
                "price_open": o.price_open,
                "sl": o.sl,
                "tp": o.tp,
            })
        return Result.ok(res)

    async def get_order_history(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Result[List[Dict[str, Any]]]:
        """Obtiene historial de trades finalizados."""
        if from_date is None:
            from_date = datetime(2020, 1, 1)
        if to_date is None:
            to_date = datetime.now()
            
        history = mt5.history_deals_get(from_date, to_date)
        if history is None:
            return Result.fail("Could not get history", "MT5_ERROR")
        
        res = []
        for h in history:
            res.append({
                "ticket": h.ticket,
                "order": h.order,
                "symbol": h.symbol,
                "volume": h.volume,
                "type": h.type,
                "price": h.price,
                "profit": h.profit,
                "commission": h.commission,
                "swap": h.swap,
                "time": datetime.fromtimestamp(h.time),
            })
        return Result.ok(res)

    # --- Privados ---

    def _map_order_type(self, op_type: OperationType) -> Optional[int]:
        """Mapea OperationType de dominio a ORDER_TYPE de MT5."""
        mapping = {
            OperationType.MAIN_BUY: mt5.ORDER_TYPE_BUY,
            OperationType.MAIN_SELL: mt5.ORDER_TYPE_SELL,
            OperationType.HEDGE_BUY: mt5.ORDER_TYPE_BUY,
            OperationType.HEDGE_SELL: mt5.ORDER_TYPE_SELL,
            OperationType.RECOVERY_BUY: mt5.ORDER_TYPE_BUY,
            OperationType.RECOVERY_SELL: mt5.ORDER_TYPE_SELL,
        }
        return mapping.get(op_type)
