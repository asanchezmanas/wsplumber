# src/wsplumber/api/app.py
"""
Servidor FastAPI - El Fontanero de Wall Street (V2).

Configuración de rutas, plantillas Jinja2 y archivos estáticos.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from wsplumber.config.settings import get_settings
from wsplumber.api.routers import websocket
from wsplumber.api.routers.traceability import router as traceability_router
from wsplumber.api.routers.backtest import router as backtest_router
from wsplumber.api.routers.state_broadcaster import state_broadcaster
from fastapi.middleware.cors import CORSMiddleware


# Lifespan handler para startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    # Startup
    await state_broadcaster.start()
    yield
    # Shutdown
    await state_broadcaster.stop()


# Configuración
settings = get_settings()
app = FastAPI(
    title="WS Plumber API",
    description="Estrategia Algorítmica de Alta Fidelidad",
    version="0.1.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Routers
app.include_router(websocket.router)
app.include_router(traceability_router)
app.include_router(backtest_router)

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
    """Ruta del Dashboard V3."""
    return templates.TemplateResponse(
        "pages/dashboard_v3.html",
        {"request": request, "title": "WS Plumber - Dashboard"}
    )

@app.get("/dashboard/legacy", response_class=HTMLResponse)
async def read_dashboard_legacy(request: Request):
    """Ruta del Dashboard antiguo (fallback)."""
    return templates.TemplateResponse(
        "pages/dashboard.html",
        {"request": request, "title": "WS Plumber - Dashboard Legacy"}
    )

@app.get("/traceability", response_class=HTMLResponse)
async def read_traceability(request: Request):
    """Página de Trazabilidad de Flujos."""
    return templates.TemplateResponse(
        "pages/traceability.html",
        {"request": request, "title": "WS Plumber - Trazabilidad"}
    )

@app.get("/health")
async def health_check():
    """Endpoint de salud del sistema."""
    return {"status": "ok", "version": "0.1.0"}

