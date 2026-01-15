# src/wsplumber/api/routers/backtest.py
"""
Router de FastAPI para ejecutar backtests con streaming de progreso.

Endpoints:
- GET  /api/backtest/scenarios  - Lista escenarios disponibles
- POST /api/backtest/run        - Ejecuta backtest con streaming SSE
- GET  /api/backtest/partitions - Lista particiones por año
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from wsplumber.application.services.backtest_service import backtest_service

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    """Request para iniciar un backtest."""
    csv_path: str
    pair: str = "EURUSD"
    max_ticks: Optional[int] = None
    report_interval: int = 1000  # Normal: cada 1000 ticks
    initial_balance: float = 10000.0
    audit_mode: bool = False  # Si True, report_interval se reduce a 10 para logs detallados


@router.get("/scenarios")
async def list_scenarios():
    """
    Lista todos los escenarios disponibles para backtest.
    
    Incluye:
    - Escenarios de tests/scenarios/
    - Particiones por año en data/partitions/
    - CSVs grandes en el directorio raíz
    """
    scenarios = backtest_service.list_scenarios()
    return {
        "total": len(scenarios),
        "scenarios": scenarios
    }


@router.get("/partitions")
async def list_partitions():
    """Lista particiones de datos por año."""
    partitions_dir = Path("data/partitions")
    
    if not partitions_dir.exists():
        return {
            "message": "No hay particiones. Ejecuta: python scripts/partition_csv_by_year.py <csv>",
            "partitions": {}
        }
    
    # Agrupar por par
    partitions = {}
    for f in sorted(partitions_dir.glob("*.parquet")):
        parts = f.stem.split("_")
        pair = parts[0]
        year = parts[1] if len(parts) > 1 else "unknown"
        
        if pair not in partitions:
            partitions[pair] = []
        
        partitions[pair].append({
            "year": year,
            "path": str(f),
            "size_mb": round(f.stat().st_size / (1024*1024), 2)
        })
    
    return {
        "partitions_dir": str(partitions_dir),
        "pairs": list(partitions.keys()),
        "partitions": partitions
    }


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """
    Ejecuta un backtest y devuelve progreso via Server-Sent Events (SSE).
    
    El stream devuelve líneas JSON con el formato:
    ```
    data: {"tick": 1000, "balance": 10050.5, "equity": 10045.2, ...}
    data: {"tick": 2000, "balance": 10080.1, "equity": 10075.8, ...}
    data: {"status": "complete", "message": "Backtest completado..."}
    ```
    
    Usa curl para probar:
    ```bash
    curl -N -X POST "http://localhost:8000/api/backtest/run" \\
         -H "Content-Type: application/json" \\
         -d '{"csv_path": "tests/scenarios/r01.csv", "max_ticks": 500}'
    ```
    """
    # Validar que el archivo existe
    csv_path = Path(request.csv_path)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {request.csv_path}")
    
    async def generate():
        """Generador SSE."""
        # En audit_mode, reportar cada 10 ticks para logs detallados
        interval = 10 if request.audit_mode else request.report_interval
        try:
            async for progress in backtest_service.run_streaming(
                csv_path=request.csv_path,
                pair=request.pair,
                max_ticks=request.max_ticks,
                report_interval=interval,
                initial_balance=request.initial_balance
            ):
                yield f"data: {json.dumps(progress.to_dict())}\n\n"
        except Exception as e:
            error_data = {
                "status": "error",
                "message": str(e),
                "tick": 0,
                "total_ticks": 0,
                "balance": 0,
                "equity": 0
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Para nginx
        }
    )


@router.post("/run-quick")
async def run_backtest_quick(
    csv_path: str = Query(..., description="Ruta al CSV"),
    pair: str = Query("EURUSD"),
    max_ticks: int = Query(1000, description="Máximo de ticks (default 1000 para test rápido)")
):
    """
    Endpoint simplificado para tests rápidos vía query params.
    
    Ejemplo:
    ```
    curl -N "http://localhost:8000/api/backtest/run-quick?csv_path=tests/scenarios/r01.csv&max_ticks=500"
    ```
    """
    request = BacktestRequest(
        csv_path=csv_path,
        pair=pair,
        max_ticks=max_ticks,
        report_interval=100
    )
    return await run_backtest(request)
