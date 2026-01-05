# src/wsplumber/api/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from loguru import logger

from wsplumber.api.routers.state_broadcaster import state_broadcaster

router = APIRouter()

class ConnectionManager:
    """Gestiona conexiones activas de WebSockets."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dashboard client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Dashboard client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Envía un mensaje a todos los clientes conectados."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones muertas
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Conectar el broadcaster con la función de broadcast del manager
state_broadcaster.set_broadcast_function(manager.broadcast)


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """Canal de comunicación en tiempo real para el Dashboard."""
    await manager.connect(websocket)
    try:
        # Enviar estado inicial
        initial_state = await state_broadcaster.get_dashboard_state()
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "data": initial_state
        }))
        
        while True:
            # Mantener conexión y escuchar mensajes del cliente si es necesario
            data = await websocket.receive_text()
            logger.debug(f"Received from client: {data}")
            
            # Manejar comandos del cliente si es necesario
            try:
                cmd = json.loads(data)
                if cmd.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif cmd.get("type") == "request_state":
                    state = await state_broadcaster.get_dashboard_state()
                    await websocket.send_text(json.dumps({
                        "type": "state_update",
                        "data": state
                    }))
            except json.JSONDecodeError:
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

