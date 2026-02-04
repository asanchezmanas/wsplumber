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
from wsplumber.core.strategy._params import (
    LAYER1_MODE, TRAILING_LEVELS, TRAILING_MIN_LOCK
)

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
    sl_price: Optional[Price] = None
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

    def __init__(self, initial_balance: float = 10000.0, leverage: int = 100, repository=None):
        self.balance = Decimal(str(initial_balance))
        self.leverage = leverage
        self.ticks: List[TickData] = []
        self.current_tick_index = -1
        self.current_tick: Optional[TickData] = None  # FIX: Initialize for get_current_price
        
        self.open_positions: Dict[BrokerTicket, SimulatedPosition] = {}
        self.pending_orders: Dict[BrokerTicket, SimulatedOrder] = {}
        self.history: List[Dict[str, Any]] = []  # FIX: Ahora guarda dicts con más info
        self.history_dict: Dict[BrokerTicket, Dict[str, Any]] = {}  # Optimization for sync
        
        self.ticket_counter = 1000
        self._connected = False
        
        # Referencia al repositorio para sincronizar status de operaciones
        self._repository = repository



    @property
    def equity(self) -> Decimal:
        """Calcula el equity actual (balance + P&L flotante)."""
        floating_pnl = sum(Decimal(str(pos.current_pnl_money)) for pos in self.open_positions.values())
        return self.balance + floating_pnl

    def load_csv(self, csv_path: str, default_pair: Optional[str] = None, start_date=None, end_date=None):
        """Carga ticks desde un archivo CSV (Formato TickData) o Parquet.
        
        Usa carga en memoria para archivos < 50MB, streaming para mayores.
        """
        import os
        self.csv_path = csv_path
        self.default_pair = default_pair
        self.ticks = []
        
        # Check extension
        if str(csv_path).endswith('.parquet'):
            self._load_parquet(csv_path, default_pair, start_date, end_date)
            return
            
        file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
        
        if file_size_mb < 5000:
            # In-memory loading for smaller files
            self._load_csv_to_memory(csv_path, default_pair)
        else:
            # Streaming for massive files
            self._tick_generator = self._create_tick_generator()
            self.current_tick_index = 0
            logger.info(f"Broker prepared for streaming ticks from {csv_path}")

    def _load_parquet(self, parquet_path: str, default_pair: Optional[str] = None, start_date=None, end_date=None):
        """Carga ticks desde un archivo Parquet usando Pandas (OPTIMIZADO)."""
        import pandas as pd
        import numpy as np
        logger.info(f"Loading ticks from Parquet: {parquet_path}")
        df = pd.read_parquet(parquet_path)
        
        # Normalize column names
        df.columns = [c.lower() for c in df.columns]
        
        # Determine column names
        ts_col = 'timestamp' if 'timestamp' in df.columns else ('datetime' if 'datetime' in df.columns else None)
        bid_col = 'bid'
        ask_col = 'ask'
        
        if not ts_col or bid_col not in df.columns or ask_col not in df.columns:
            logger.error(f"Parquet file {parquet_path} missing required columns")
            return

        # Filtering
        df['timestamp_dt'] = pd.to_datetime(df[ts_col], format='mixed')
        if start_date:
            df = df[df['timestamp_dt'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp_dt'] <= pd.to_datetime(end_date)]

        logger.info(f"Ingesting {len(df)} ticks from Parquet...")

        # Convert to TickData objects - Vectorized approach
        p_vals = df['pair'] if 'pair' in df.columns else [default_pair or "EURUSD"] * len(df)
        
        for ts, bid_val, ask_val, p_val in zip(df['timestamp_dt'], df[bid_col], df[ask_col], p_vals):
            pair = CurrencyPair(p_val)
            dt = ts.to_pydatetime()
            bid = Price(Decimal(str(bid_val)))
            ask = Price(Decimal(str(ask_val)))
            
            pips_mult = 100 if "JPY" in str(pair) else 10000
            # Spread check (optional column)
            spread = float((ask - bid) * pips_mult)
            
            self.ticks.append(TickData(
                pair=pair,
                bid=bid,
                ask=ask,
                timestamp=Timestamp(dt),
                spread_pips=Pips(spread)
            ))
            
        self.current_tick_index = -1
        logger.info(f"Loaded {len(self.ticks)} ticks from Parquet")
    
    def _load_csv_to_memory(self, csv_path: str, default_pair: Optional[str] = None):
        """Carga ticks en memoria (para archivos < 50MB)."""
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            # Skip comment lines
            lines = [line for line in f if not line.startswith('#')]
            reader = csv.DictReader(lines)
            for row in reader:
                # Normalizar keys: quitar espacios y pasar a minúsculas. Manejar claves None.
                row = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
                
                pair_val = row.get('pair', default_pair)
                if not pair_val:
                    pair_val = "EURUSD"
                
                pair = CurrencyPair(pair_val)
                bid_key = 'bid'
                ask_key = 'ask'
                ts_key = 'timestamp' if 'timestamp' in row else ('datetime' if 'datetime' in row else None)
                
                # PHASE 14: Auto-detect OHLC / Black Swan format
                if not ts_key:
                    if 'date' in row and 'time' in row:
                        row['timestamp'] = f"{row['date']} {row['time']}"
                        ts_key = 'timestamp'
                    elif 'date' in row:
                        ts_key = 'date'
                
                if bid_key not in row or ask_key not in row:
                    # Try OHLC fallback (Close as Bid, Close + small spread as Ask)
                    if 'close' in row:
                        row['bid'] = row['close']
                        # Assume 1.0 pip spread if not present
                        mult = 0.01 if "JPY" in str(pair) else 0.0001
                        row['ask'] = str(float(row['close']) + mult)
                        bid_key = 'bid'
                        ask_key = 'ask'
                
                if not ts_key or bid_key not in row or ask_key not in row:
                    continue

                if row[bid_key] is None or row[ask_key] is None or row[ts_key] is None:
                    continue
                
                # Saltar filas donde bid/ask estén vacíos
                if not str(row[bid_key]).strip() or not str(row[ask_key]).strip():
                    continue

                bid_val = str(row[bid_key]).strip()
                ask_val = str(row[ask_key]).strip()
                bid = Price(Decimal(bid_val))
                ask = Price(Decimal(ask_val))
                
                raw_ts = row[ts_key]
                ts_clean = raw_ts.replace(".", "-")
                try:
                    dt = datetime.fromisoformat(ts_clean)
                except ValueError:
                    try:
                        # Try common formats like "2015.01.01 00:00"
                        dt = datetime.strptime(raw_ts, "%Y.%m.%d %H:%M")
                    except ValueError:
                        try:
                            dt = datetime.strptime(raw_ts, "%Y%m%d %H:%M:%S.%f")
                        except ValueError:
                            try:
                                # Black Swan format: 20220221 00:00:00
                                dt = datetime.strptime(raw_ts, "%Y%m%d %H:%M:%S")
                            except ValueError:
                                dt = datetime.now()
                
                pips_mult = 100 if "JPY" in str(pair) else 10000
                spread_val = row.get('spread_pips')
                if spread_val is not None:
                    spread = float(spread_val)
                else:
                    spread = float((ask - bid) * pips_mult)
                
                self.ticks.append(TickData(
                    pair=pair,
                    bid=bid,
                    ask=ask,
                    timestamp=Timestamp(dt),
                    spread_pips=Pips(spread)
                ))
        self.current_tick_index = -1
        logger.info(f"Loaded {len(self.ticks)} ticks from {csv_path} (in-memory)")

    def _create_tick_generator(self):
        """Generador de ticks para evitar cargar todo el CSV en RAM."""
        print(f"[DEBUG] Opening CSV: {self.csv_path}")
        with open(self.csv_path, mode='r', encoding='utf-8-sig') as f:
            # Create a generator that skips comment lines
            clean_lines = (line for line in f if not line.startswith('#'))
            reader = csv.DictReader(clean_lines)
            row_count = 0
            for row in reader:
                row_count += 1
                # if row_count == 1:
                #     print(f"[DEBUG] First row keys: {list(row.keys())}")
                
                # Detect column names (handle case-insensitive and different formats)
                col_map = {k.lower(): k for k in row.keys()}
                
                pair_val = row.get(col_map.get('pair', 'NOSUCHCOLUMN'), self.default_pair)
                if not pair_val:
                    pair_val = "EURUSD"
                
                pair = CurrencyPair(pair_val)
                bid_key = col_map.get('bid', 'bid')
                ask_key = col_map.get('ask', 'ask')
                ts_key = col_map.get('timestamp', col_map.get('datetime', 'timestamp'))
                
                try:
                    bid = Price(Decimal(row[bid_key]))
                    ask = Price(Decimal(row[ask_key]))
                    
                    raw_ts = row[ts_key]
                    try:
                        # Handle formats like "2015.01.01 00:00" or ISO
                        ts_clean = raw_ts.replace(".", "-")
                        try:
                            dt = datetime.fromisoformat(ts_clean)
                        except ValueError:
                            try:
                                # Try common formats
                                dt = datetime.strptime(raw_ts, "%Y.%m.%d %H:%M")
                            except ValueError:
                                try:
                                    dt = datetime.strptime(raw_ts, "%Y%m%d %H:%M:%S.%f")
                                except ValueError:
                                    dt = datetime.now()
                    except Exception:
                        dt = datetime.now()
                    
                    pips_mult = 100 if "JPY" in str(pair) else 10000
                    spread_val = row.get(col_map.get('spread_pips', 'NOSUCHCOLUMN'))
                    if spread_val is not None:
                        spread = float(spread_val)
                    else:
                        spread = float((ask - bid) * pips_mult)
                    
                    yield TickData(
                        pair=pair,
                        bid=bid,
                        ask=ask,
                        timestamp=Timestamp(dt),
                        spread_pips=Pips(spread)
                    )
                except Exception as e:
                    # print(f"[DEBUG] Error processing row {row_count}: {e}")
                    continue
            
            # print(f"[DEBUG] Generator finished after {row_count} rows")

    def peek_next_tick(self) -> Optional[TickData]:
        """Peeks at the next tick without consuming it or processing executions."""
        next_idx = self.current_tick_index + 1
        if self.ticks:
            if next_idx < len(self.ticks):
                return self.ticks[next_idx]
        elif hasattr(self, '_tick_generator'):
            # This is harder for generators, but in our audit we usually use in-memory for small/medium files
            # For now, only support in-memory peeking for deterministic gap detection in tests
            if next_idx < len(self.ticks): # Fallback if list was partially populated
                return self.ticks[next_idx]
        return None

    async def advance_tick(self, is_allowed: bool = True) -> Optional[TickData]:
        """Consume el siguiente tick y procesa ejecuciones.
        
        Args:
            is_allowed: If False, skips all executions (activations/TPs/SLs) for this tick.
        """
        tick = None
        
        # Modo in-memory (archivos < 50MB)
        if self.ticks:
            self.current_tick_index += 1
            if self.current_tick_index >= len(self.ticks):
                return None
            tick = self.ticks[self.current_tick_index]
        # Modo streaming (archivos >= 50MB)
        elif hasattr(self, '_tick_generator'):
            try:
                tick = next(self._tick_generator)
                self.current_tick_index += 1
            except StopIteration:
                return None
        else:
            return None
        
        self.current_tick = tick
        
        # FIX-GAP-STOP: Procesa activaciones solo si el tick es válido (no es gap ciego)
        if is_allowed:
            await self._process_executions(tick)
        else:
            logger.warning("Broker: Skipping executions for gap tick", price=float(tick.mid))
            
        return tick

    async def process_tick_manual(self, tick: TickData, is_allowed: bool = True) -> None:
        """Procesa un tick inyectado manualmente (útil para tests de matriz)."""
        self.current_tick = tick
        if is_allowed:
            await self._process_executions(tick)
        else:
            await self.update_pnl_only()

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
        # Primero verificar si hay un tick actual establecido directamente
        if self.current_tick is not None:
            if self.current_tick.pair != pair:
                return Result.fail(f"Current tick is for {self.current_tick.pair}, not {pair}")
            return Result.ok(self.current_tick)
        
        # Fallback al array de ticks (modo in-memory)
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
        
        pos = self.open_positions[ticket]
        # DEBUG: Log what's being closed and its P&L
        import traceback
        caller = traceback.format_stack()[-3]  # Get the caller's line
        # print(f"[DEBUG CLOSE] ticket={ticket} op_id={pos.operation_id} type={pos.order_type.value} entry={float(pos.entry_price):.5f} pnl={pos.current_pnl_pips:.1f} pips, status={pos.status.value}")
        # print(f"[DEBUG CALLER] {caller.strip()}")
        
        pos = self.open_positions.pop(ticket)
        # Usar current_tick si está disponible (manual en tests o automático en avance)
        current_tick = self.current_tick
        if not current_tick and self.ticks and self.current_tick_index >= 0:
            current_tick = self.ticks[self.current_tick_index]
        
        if not current_tick:
             return Result.fail("No current tick available for closing")
             
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
        h_entry = {
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
        }
        self.history.append(h_entry)
        self.history_dict[pos.ticket] = h_entry
        
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

    async def close_debt_unit(self, main_ticket: BrokerTicket, hedge_ticket: BrokerTicket) -> Result[Dict]:
        """
        Close a debt unit (Main + Hedge) atomically with correct net P&L.
        
        The net P&L is calculated from the fixed entry price difference,
        not from the individual frozen P&Ls which may be inconsistent.
        
        Returns:
            Result with details including the fixed net P&L
        """
        if main_ticket not in self.open_positions:
            return Result.fail(f"Main position {main_ticket} not found")
        if hedge_ticket not in self.open_positions:
            return Result.fail(f"Hedge position {hedge_ticket} not found")
        
        main_pos = self.open_positions.pop(main_ticket)
        hedge_pos = self.open_positions.pop(hedge_ticket)
        current_tick = self.ticks[self.current_tick_index]
        
        # Calculate the FIXED net P&L from entry difference
        # This is always exactly -20 pips for Main+Hedge (10 pip separation + 10 pip to TP)
        multiplier = 100 if "JPY" in str(main_pos.pair) else 10000
        entry_diff_pips = abs(float(main_pos.entry_price) - float(hedge_pos.entry_price)) * multiplier
        
        # The debt is always the entry difference (negative because it's a loss)
        net_pips = -entry_diff_pips
        pip_value_per_lot = 10.0
        net_money = net_pips * float(main_pos.lot_size) * pip_value_per_lot
        
        # Apply to balance
        self.balance += Decimal(str(net_money))
        
        # Save to history
        for pos, ticket in [(main_pos, main_ticket), (hedge_pos, hedge_ticket)]:
            h_entry = {
                "ticket": ticket,
                "operation_id": pos.operation_id,
                "pair": pos.pair,
                "order_type": pos.order_type.value,
                "entry_price": float(pos.entry_price),
                "close_price": float(current_tick.mid),
                "lot_size": float(pos.lot_size),
                "profit_pips": net_pips / 2,  # Split for record keeping
                "profit_money": net_money / 2,
                "closed_at": current_tick.timestamp,
                "status": "debt_unit_closed"
            }
            self.history.append(h_entry)
            self.history_dict[ticket] = h_entry
        
        logger.info("Broker: Debt unit closed atomically",
                   main_ticket=main_ticket,
                   hedge_ticket=hedge_ticket,
                   net_pips=net_pips,
                   net_money=net_money)
        
        return Result.ok({
            "main_ticket": main_ticket,
            "hedge_ticket": hedge_ticket,
            "net_pips": net_pips,
            "net_money": net_money
        })

    async def modify_order(
        self,
        ticket: BrokerTicket,
        new_tp: Optional[Price] = None,
        new_sl: Optional[Price] = None,
    ) -> Result[bool]:
        """Modifica una orden pendiente."""
        if ticket in self.pending_orders:
            if new_tp is not None:
                self.pending_orders[ticket].tp_price = new_tp
            if new_sl is not None:
                # Opcional: añadir sl_price a SimulatedOrder si es necesario
                pass
            logger.info(f"Broker: Modified pending order {ticket}", new_tp=float(new_tp) if new_tp else "REMOVED")
            return Result.ok(True)
        return Result.fail("Pending order not found")

    async def modify_pending_order(
        self,
        ticket: BrokerTicket,
        new_entry_price: Optional[Price] = None,
        new_tp_price: Optional[Price] = None,
    ) -> Result[bool]:
        """
        Modifica el precio de entrada de una orden pendiente (Layer 1B).
        Equivalente a OrderModify() en MT4/MT5.
        """
        if ticket not in self.pending_orders:
            return Result.fail("Pending order not found")
        
        order = self.pending_orders[ticket]
        
        if new_entry_price is not None:
            old_entry = order.entry_price
            order.entry_price = new_entry_price
            # Also update reference price to the current mid to maintain correct direction logic
            if self.current_tick:
                order.reference_price = self.current_tick.mid
            
            logger.debug(
                "Broker: Modified pending order entry",
                ticket=ticket,
                old_entry=float(old_entry),
                new_entry=float(new_entry_price)
            )
        
        if new_tp_price is not None:
            order.tp_price = new_tp_price
        
        return Result.ok(True)

    async def modify_position(
        self,
        ticket: BrokerTicket,
        new_tp: Optional[Price] = None,
        new_sl: Optional[Price] = None,
    ) -> Result[bool]:
        """Modifica una posición abierta. Si se pasa None, se elimina el TP/SL."""
        if ticket in self.open_positions:
            # FIX: No filtrar por 'is not None' para permitir el borrado de TPs (stripping)
            self.open_positions[ticket].tp_price = new_tp
            self.open_positions[ticket].sl_price = new_sl
            
            logger.info(f"Broker: Modified position {ticket}", 
                       new_tp=float(new_tp) if new_tp is not None else "NONE",
                       new_sl=float(new_sl) if new_sl is not None else "NONE")
            return Result.ok(True)
        return Result.fail("Position not found")


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
                "fill_price": float(pos.entry_price),
                "tp": float(pos.tp_price) if pos.tp_price else 0.0,
                "profit": pos.current_pnl_money,
                "profit_pips": pos.current_pnl_pips,
                "open_time": pos.open_time,
                "bid": float(self.current_tick.bid) if self.current_tick else float(pos.entry_price),
                "ask": float(self.current_tick.ask) if self.current_tick else float(pos.entry_price),
                "current_price": float(self.current_tick.bid) if self.current_tick else float(pos.entry_price),
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


    async def update_pnl_only(self) -> None:
        """
        PHASE 1: Update P&L for all open positions WITHOUT checking TPs.
        
        This allows the orchestrator to run Layer 1 trailing stops
        before TPs are evaluated and marked.
        """
        if not self.current_tick:
            return
        
        tick = self.current_tick
        
        for ticket, pos in self.open_positions.items():
            # Sync status from repository
            if self._repository and pos.operation_id:
                op_res = self._repository.operations.get(pos.operation_id)
                if op_res and op_res.status != pos.status:
                    pos.status = op_res.status
            
            # Skip frozen positions
            if pos.status in (OperationStatus.TP_HIT, OperationStatus.NEUTRALIZED):
                continue
            
            # Calculate P&L
            mult = 100 if "JPY" in pos.pair else 10000
            if pos.order_type.is_buy:
                pips = float((tick.bid - pos.entry_price) * mult)
            else:
                pips = float((pos.entry_price - tick.ask) * mult)
            
            pos.current_pnl_pips = pips
            pip_value_per_lot = 10.0
            pos.current_pnl_money = pips * float(pos.lot_size) * pip_value_per_lot

    async def check_and_mark_tps(self) -> None:
        """
        PHASE 2: Check and mark TPs for positions that weren't closed by Layer 1.
        
        Only call this AFTER orchestrator has run Layer 1 trailing stops.
        """
        if not self.current_tick:
            return
        
        tick = self.current_tick
        tp_closures = []
        
        for ticket, pos in self.open_positions.items():
            if pos.status == OperationStatus.ACTIVE and pos.tp_price is not None:
                tp_hit = False
                close_price = None
                
                if pos.tp_price and float(pos.tp_price) > 0:
                    if pos.order_type.is_buy and tick.bid >= pos.tp_price:
                        tp_hit = True
                        close_price = tick.bid
                    elif pos.order_type.is_sell and tick.ask <= pos.tp_price:
                        tp_hit = True
                        close_price = tick.ask
                
                if tp_hit:
                    tp_closures.append({
                        "ticket": ticket,
                        "pos": pos,
                        "close_price": close_price,
                        "pnl_pips": pos.current_pnl_pips,
                        "pnl_money": pos.current_pnl_money,
                        "timestamp": tick.timestamp
                    })
        
        for closure in tp_closures:
            ticket = closure["ticket"]
            pos = closure["pos"]
            
            if pos.status != OperationStatus.TP_HIT:
                pos.status = OperationStatus.TP_HIT
                pos.actual_close_price = closure["close_price"]
                pos.close_time = closure["timestamp"]
                
                logger.info(f"Broker: Position {ticket} marked as TP_HIT",
                           operation_id=pos.operation_id,
                           close_price=float(closure["close_price"]),
                           profit_pips=closure["pnl_pips"])

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
                    # print(f"[DEBUG PK] TICKET {ticket} BUY entry={order.entry_price} ask={tick.ask} above={entry_above}")
                    if tick.ask >= order.entry_price:
                        tickets_to_activate.append(ticket)
                else:  # SELL con entry arriba (como HEDGE_SELL)
                    if tick.bid >= order.entry_price:
                        tickets_to_activate.append(ticket)
            else:
                # Entry está ABAJO → activa cuando precio BAJA hasta entry
                if order.order_type.is_sell:
                    # print(f"[DEBUG PK] TICKET {ticket} SELL entry={order.entry_price} bid={tick.bid} below={entry_below}")
                    if tick.bid <= order.entry_price:
                        tickets_to_activate.append(ticket)
                else:  # BUY con entry abajo (como HEDGE_BUY)
                    if tick.ask <= order.entry_price:
                        tickets_to_activate.append(ticket)
        
        for t in tickets_to_activate:
            order = self.pending_orders.pop(t)
            # Determine fill price (handle slippage/gaps)
            # In a real market, a STOP order fills at the first available price better than or equal to entry
            if order.order_type.is_buy:
                fill_price = Price(max(Decimal(str(order.entry_price)), Decimal(str(tick.ask))))
            else:
                fill_price = Price(min(Decimal(str(order.entry_price)), Decimal(str(tick.bid))))
                
            pos = SimulatedPosition(
                ticket=order.ticket,
                operation_id=order.operation_id,
                pair=order.pair,
                order_type=order.order_type,
                entry_price=fill_price,  # Fills at actual tick price (slippage)
                tp_price=order.tp_price,
                lot_size=order.lot_size,
                open_time=tick.timestamp
            )
            self.open_positions[t] = pos
            
            # PHASE 11: Absolute Forensic Gap Tracking
            gap_pips = 0.0
            if abs(float(fill_price) - float(order.entry_price)) > 1e-7:
                 mult = 100 if "JPY" in str(order.pair) else 10000
                 gap_pips = (float(fill_price) - float(order.entry_price)) * mult if order.order_type.is_buy else (float(order.entry_price) - float(fill_price)) * mult
                 logger.warning(f"Broker: GAP ACTIVATION detected for {t}", 
                              op_id=order.operation_id, entry=float(order.entry_price), 
                              fill=float(fill_price), gap_pips=f"{gap_pips:+.1f}")
            else:
                 logger.info(f"Broker: Order {t} activated", 
                            operation_id=order.operation_id,
                            entry_price=float(order.entry_price),
                            timestamp=tick.timestamp)

        # 2. Actualizar P&L y MARCAR TPs
        # Recolectar tickets a cerrar para no modificar dict durante iteración
        tp_closures = []

        for ticket, pos in self.open_positions.items():
            # FIX-SB-05: Sync status from repository before P&L calculation
            # This ensures NEUTRALIZED status set by orchestrator is respected immediately
            if self._repository and pos.operation_id:
                op_res = self._repository.operations.get(pos.operation_id)
                if op_res and op_res.status != pos.status:
                    pos.status = op_res.status
                    logger.debug(f"Broker: Synced status from repo for {ticket}: {pos.status.value}")
            
            # FIX-SB-04: Skip P&L recalculation for TP_HIT and NEUTRALIZED positions
            # NEUTRALIZED = hedged pairs that should have frozen P&L
            # Their P&L should be frozen at the entry price difference, not recalculated
            if pos.status in (OperationStatus.TP_HIT, OperationStatus.NEUTRALIZED):
                # P&L is already frozen, skip recalculation
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
            # FIX-TP-NULL: Skip TP check if tp_price is None (neutralized)
            if pos.status == OperationStatus.ACTIVE:
                # 1. Check Take Profit
                if pos.tp_price and float(pos.tp_price) > 0:
                    tp_hit = False
                    close_price = None
                    if pos.order_type.is_buy and tick.bid >= pos.tp_price:
                        tp_hit = True
                        close_price = tick.bid
                    elif pos.order_type.is_sell and tick.ask <= pos.tp_price:
                        tp_hit = True
                        close_price = tick.ask
                    
                    if tp_hit:
                        tp_closures.append({
                            "ticket": ticket,
                            "pos": pos,
                            "close_price": close_price,
                            "pnl_pips": pos.current_pnl_pips,
                            "pnl_money": pos.current_pnl_money,
                            "timestamp": tick.timestamp
                        })
                        continue # If TP hit, no need to check SL

                # 2. Check Stop Loss (PHASE 6)
                if pos.sl_price and float(pos.sl_price) > 0:
                    sl_hit = False
                    close_price = None
                    # Sl hit for BUY when bid drops to sl
                    if pos.order_type.is_buy and tick.bid <= pos.sl_price:
                        sl_hit = True
                        close_price = tick.bid
                    # Sl hit for SELL when ask rises to sl
                    elif pos.order_type.is_sell and tick.ask >= pos.sl_price:
                        sl_hit = True
                        close_price = tick.ask
                    
                    if sl_hit:
                        logger.warning(f"Broker: SL hit for {ticket}", 
                                      sl=float(pos.sl_price), current=float(tick.bid if pos.order_type.is_buy else tick.ask))
                        # SL should close the position immediately to simulate broker behavior
                        # But for consistency with SB-01, we mark as CLOSED here (same as orchestrated close)
                        tp_closures.append({
                            "ticket": ticket,
                            "pos": pos,
                            "close_price": close_price,
                            "pnl_pips": pos.current_pnl_pips,
                            "pnl_money": pos.current_pnl_money,
                            "timestamp": tick.timestamp,
                            "reason": "sl_hit"
                        })

        # 3. Procesar TPs marcados
        for closure in tp_closures:
            ticket = closure["ticket"]
            pos = closure["pos"]
            
            # FIX-SB-01: NO cerrar inmediatamente. Solo marcar como TP_HIT.
            # El orquestador detectará este status y llamará a close_position().
            if pos.status != OperationStatus.TP_HIT:
                pos.status = OperationStatus.TP_HIT
                pos.actual_close_price = closure["close_price"]
                pos.close_time = closure["timestamp"]
                
                logger.info(f"Broker: Position {ticket} marked as TP_HIT",
                           operation_id=pos.operation_id,
                           close_price=float(closure["close_price"]),
                           profit_pips=closure["pnl_pips"])
