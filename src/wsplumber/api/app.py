# src/wsplumber/api/app.py
"""
Servidor FastAPI - El Fontanero de Wall Street (V2).

Configuración de rutas, plantillas Jinja2 y archivos estáticos.
"""

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from wsplumber.config.settings import get_settings
from wsplumber.api.routers import websocket

# Configuración
settings = get_settings()
app = FastAPI(
    title="WS Plumber API",
    description="Estrategia Algorítmica de Alta Fidelidad",
    version="0.1.0"
)

# Registrar Routers
app.include_router(websocket.router)

# Rutas de Archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(BASE_DIR, "static")
templates_path = os.path.join(BASE_DIR, "templates")

# Montar Archivos Estáticos
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Configurar Jinja2
templates = Jinja2Templates(directory=templates_path)

@app.get("/", response_class=HTMLResponse)
async def read_landing(request: Request):
    """Ruta principal: Landing Page V2."""
    return templates.TemplateResponse(
        "pages/landing.html", 
        {"request": request, "title": "WS Plumber - Inicio"}
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Ruta del Dashboard V2."""
    return templates.TemplateResponse(
        "pages/dashboard.html",
        {"request": request, "title": "WS Plumber - Dashboard"}
    )

@app.get("/health")
async def health_check():
    """Endpoint de salud del sistema."""
    return {"status": "ok", "version": "0.1.0"}
