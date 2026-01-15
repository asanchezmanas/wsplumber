# src/wsplumber/api/schemas/backtest_schemas.py
"""
Schemas Pydantic para la API de Backtesting.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BacktestConfig(BaseModel):
    """Configuración para ejecutar un backtest."""
    csv_path: str = Field(..., description="Ruta al archivo CSV o Parquet")
    pair: str = Field(default="EURUSD", description="Par de divisas")
    max_ticks: Optional[int] = Field(default=None, description="Límite de ticks a procesar")
    report_interval: int = Field(default=1000, description="Cada cuántos ticks enviar progreso")
    initial_balance: float = Field(default=10000.0, description="Balance inicial en EUR")


class BacktestProgress(BaseModel):
    """Progreso de un backtest en ejecución."""
    tick: int = Field(..., description="Tick actual")
    total_ticks: int = Field(..., description="Total de ticks")
    progress_pct: float = Field(..., description="Porcentaje completado")
    balance: float = Field(..., description="Balance actual")
    equity: float = Field(..., description="Equity actual")
    drawdown_pct: float = Field(..., description="Drawdown actual en %")
    active_cycles: int = Field(default=0, description="Ciclos activos")
    hedged_cycles: int = Field(default=0, description="Ciclos en hedge")
    in_recovery_cycles: int = Field(default=0, description="Ciclos en recovery")
    closed_cycles: int = Field(default=0, description="Ciclos cerrados")
    main_tps: int = Field(default=0, description="TPs de operaciones main")
    recovery_tps: int = Field(default=0, description="TPs de recovery")
    status: str = Field(default="running", description="running | complete | error")
    message: Optional[str] = Field(default=None, description="Mensaje adicional")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BacktestResult(BaseModel):
    """Resultado final de un backtest."""
    job_id: str
    csv_path: str
    pair: str
    total_ticks: int
    duration_seconds: float
    initial_balance: float
    final_balance: float
    final_equity: float
    profit_loss: float
    profit_pct: float
    max_drawdown_pct: float
    total_cycles: int
    closed_cycles: int
    max_recovery_level: int
    main_tps: int
    recovery_tps: int
    status: str = "complete"
    metrics_csv_path: Optional[str] = None
    log_path: Optional[str] = None


class ScenarioInfo(BaseModel):
    """Información de un escenario disponible."""
    name: str
    path: str
    size_mb: float
    rows: Optional[int] = None
    year: Optional[int] = None
    pair: str = "EURUSD"
