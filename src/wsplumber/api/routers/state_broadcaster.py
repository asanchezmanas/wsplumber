# src/wsplumber/api/routers/state_broadcaster.py
"""
State Broadcaster: Puente entre el CycleOrchestrator y el WebSocket.

Proporciona funciones para obtener el estado actual del sistema y
emitir actualizaciones periódicas a todos los clientes conectados.
"""

import asyncio
import json
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from loguru import logger

if TYPE_CHECKING:
    from wsplumber.application.use_cases.cycle_orchestrator import CycleOrchestrator


class StateBroadcaster:
    """
    Gestiona el broadcast del estado del sistema al Dashboard.
    
    Se conecta con el CycleOrchestrator para obtener métricas en vivo
    y las envía a todos los clientes WebSocket conectados.
    """
    
    def __init__(self, broadcast_interval: float = 1.0):
        """
        Initialize the state broadcaster.
        
        Args:
            broadcast_interval: Seconds between state broadcasts (default: 1s)
        """
        self._orchestrator: Optional["CycleOrchestrator"] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._broadcast_fn = None  # WebSocket broadcast function
        self._running = False
        self._broadcast_interval = broadcast_interval
        
        # Estado inicial (dummy hasta que haya orquestador conectado)
        self._last_state: Dict[str, Any] = {
            "equity": 124592.00,
            "equity_change": 2.3,
            "daily_pips": 8.5,
            "exposure": 12.4,
            "active_cycles": 0,
            "active_recoveries": 0,
            "margin_level": 520.0,
        }
    
    def connect_orchestrator(self, orchestrator: "CycleOrchestrator"):
        """Conecta el broadcaster con el orquestador de ciclos."""
        self._orchestrator = orchestrator
        logger.info("StateBroadcaster: Conectado con CycleOrchestrator")
    
    def set_broadcast_function(self, broadcast_fn):
        """
        Establece la función de broadcast del WebSocket manager.
        
        Args:
            broadcast_fn: async function(message: str) -> None
        """
        self._broadcast_fn = broadcast_fn
        logger.info("StateBroadcaster: Función de broadcast configurada")
    
    async def start(self):
        """Inicia el bucle de broadcast periódico."""
        if self._running:
            return
        
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("StateBroadcaster: Iniciado")
    
    async def stop(self):
        """Detiene el bucle de broadcast."""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("StateBroadcaster: Detenido")
    
    async def _broadcast_loop(self):
        """Bucle principal de broadcast periódico."""
        while self._running:
            try:
                state = await self.get_dashboard_state()
                if self._broadcast_fn and state:
                    message = json.dumps({
                        "type": "state_update",
                        "data": state,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    await self._broadcast_fn(message)
            except Exception as e:
                logger.error(f"StateBroadcaster: Error en broadcast loop: {e}")
            
            await asyncio.sleep(self._broadcast_interval)
    
    async def get_dashboard_state(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del sistema para el Dashboard V3.
        
        Returns:
            Diccionario con métricas completas para el dashboard.
        """
        if not self._orchestrator:
            # Sin orquestador, devolver último estado conocido
            return self._last_state
        
        try:
            # 1. Obtener info de cuenta del broker
            account_info = {}
            broker = self._orchestrator.trading_service.broker
            acc_result = await broker.get_account_info()
            if acc_result.success:
                account_info = acc_result.value
            
            equity = account_info.get("equity", 0.0)
            balance = account_info.get("balance", 0.0)
            margin = account_info.get("margin", 0.0)
            margin_level = account_info.get("margin_level", 0.0)
            free_margin = account_info.get("free_margin", 0.0)
            
            # 2. Calcular cambio de equity
            equity_change = 0.0
            if balance > 0:
                equity_change = ((equity - balance) / balance) * 100
            
            # 3. Contar ciclos por estado
            active_cycles = 0
            cycles_in_recovery = 0
            total_pips_remaining = 0.0
            total_pips_recovered = 0.0
            
            for pair, cycle in self._orchestrator._active_cycles.items():
                active_cycles += 1
                if hasattr(cycle, 'accounting'):
                    remaining = float(cycle.accounting.pips_remaining or 0)
                    recovered = float(cycle.accounting.pips_recovered or 0)
                    if remaining > 0:
                        cycles_in_recovery += 1
                        total_pips_remaining += remaining
                    total_pips_recovered += recovered
            
            # 4. Obtener operaciones activas
            active_operations = []
            repo = self._orchestrator.repository
            for pair in self._orchestrator._active_cycles.keys():
                ops_result = await repo.get_active_operations_by_pair(pair)
                if ops_result.success:
                    for op in ops_result.value[:10]:  # Limitar a 10
                        active_operations.append({
                            "id": str(op.id)[:8],
                            "pair": str(op.pair),
                            "type": "Buy" if op.is_buy else "Sell",
                            "is_recovery": op.is_recovery,
                            "status": op.status.value,
                            "pnl_pips": float(op.profit_pips or 0),
                            "entry_price": float(op.actual_entry_price or op.entry_price),
                            "ticket": str(op.broker_ticket) if op.broker_ticket else None,
                        })
            
            # 5. Calcular exposición
            exposure_pct = 0.0
            if equity > 0:
                exposure_pct = (margin / equity) * 100
            
            # 6. Calcular lotes totales
            total_lots = 0.0
            positions_result = await broker.get_open_positions()
            if positions_result.success:
                for pos in positions_result.value:
                    total_lots += float(pos.get("volume", 0))
            
            # 7. Estadísticas del día (placeholder - mejorar con historial real)
            daily_pips = self._last_state.get("daily_pips", 0.0)
            main_tps = self._last_state.get("main_tps_today", 0)
            recovery_tps = self._last_state.get("recovery_tps_today", 0)
            
            # 8. Métricas de rendimiento
            win_rate = 87.0  # Placeholder - calcular del historial
            profit_factor = 3.2  # Placeholder
            max_dd = abs(equity_change) if equity_change < 0 else 2.4
            
            state = {
                # Account
                "equity": round(equity, 2),
                "balance": round(balance, 2),
                "equity_change": round(equity_change, 2),
                "margin": round(margin, 2),
                "free_margin": round(free_margin, 2),
                "margin_level": round(margin_level, 1),
                
                # Exposure
                "exposure_pct": round(exposure_pct, 1),
                "total_lots": round(total_lots, 2),
                
                # Cycles
                "active_cycles": active_cycles,
                "cycles_in_recovery": cycles_in_recovery,
                
                # Recovery/Debt
                "pips_remaining": round(total_pips_remaining, 1),
                "pips_recovered": round(total_pips_recovered, 1),
                
                # Daily stats
                "daily_pips": round(daily_pips, 1),
                "main_tps_today": main_tps,
                "recovery_tps_today": recovery_tps,
                
                # Performance
                "win_rate": round(win_rate, 1),
                "profit_factor": round(profit_factor, 1),
                "max_dd_today": round(max_dd, 1),
                
                # Operations list
                "operations": active_operations[:10],
                
                # Timestamp
                "server_time": datetime.utcnow().isoformat(),
            }
            
            self._last_state = state
            return state
            
        except Exception as e:
            logger.error(f"StateBroadcaster: Error obteniendo estado: {e}")
            return self._last_state
    
    async def emit_ticker_event(self, pair: str, message: str):
        """
        Emite un evento al ticker del Dashboard.
        
        Args:
            pair: Par de divisas (ej: "EURUSD")
            message: Mensaje a mostrar (ej: "TP Hit @ 1.08450 (+10.4 pips)")
        """
        if self._broadcast_fn:
            event = json.dumps({
                "type": "ticker_event",
                "data": {
                    "pair": pair,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            await self._broadcast_fn(event)
    
    async def emit_cycle_update(self, cycle_data: Dict[str, Any]):
        """
        Emite una actualización de ciclo específico.
        
        Args:
            cycle_data: Datos del ciclo (id, pair, status, pnl, level, etc.)
        """
        if self._broadcast_fn:
            update = json.dumps({
                "type": "cycle_update",
                "data": cycle_data
            })
            await self._broadcast_fn(update)


# Instancia global del broadcaster
state_broadcaster = StateBroadcaster(broadcast_interval=2.0)
