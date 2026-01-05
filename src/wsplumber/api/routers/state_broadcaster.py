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
        Obtiene el estado actual del sistema para el Dashboard.
        
        Returns:
            Diccionario con métricas: equity, exposure, cycles, pips, etc.
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
            
            # 2. Calcular cambio de equity (simplificado)
            equity_change = 0.0
            if balance > 0:
                equity_change = ((equity - balance) / balance) * 100
            
            # 3. Contar ciclos activos
            active_cycles = len(self._orchestrator._active_cycles)
            
            # 4. Contar recoveries (si están en la estructura)
            active_recoveries = 0
            for pair, cycle in self._orchestrator._active_cycles.items():
                if hasattr(cycle, 'recovery_operations'):
                    active_recoveries += len(cycle.recovery_operations)
            
            # 5. Calcular pips del día (placeholder - requiere historial)
            daily_pips = self._last_state.get("daily_pips", 0.0)
            
            # 6. Calcular exposición
            exposure = 0.0
            if equity > 0:
                exposure = (margin / equity) * 100
            
            state = {
                "equity": round(equity, 2),
                "equity_change": round(equity_change, 2),
                "balance": round(balance, 2),
                "margin": round(margin, 2),
                "margin_level": round(margin_level, 1),
                "daily_pips": round(daily_pips, 1),
                "exposure": round(exposure, 1),
                "active_cycles": active_cycles,
                "active_recoveries": active_recoveries,
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
