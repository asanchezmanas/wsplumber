# src/wsplumber/api/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from loguru import logger

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
        self.active_connections.remove(websocket)
        logger.info(f"Dashboard client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

manager = ConnectionManager()

@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """Canal de comunicación en tiempo real para el Dashboard."""
    await manager.connect(websocket)
    try:
        # Enviar estado inicial (Dummy por ahora)
        initial_state = {
            "type": "initial_state",
            "data": {
                "equity": 124592,
                "exposure": 12.4,
                "active_cycles": 4,
                "daily_pips": 8.5
            }
        }
        await websocket.send_text(json.dumps(initial_state))
        
        while True:
            # Mantener conexión y escuchar mensajes del cliente si es necesario
            data = await websocket.receive_text()
            logger.debug(f"Received from client: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
