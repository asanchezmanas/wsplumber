# src/wsplumber/config/settings.py
"""
Sistema de Configuración.

Usa Pydantic Settings para validación y carga desde .env.
Todas las configuraciones están tipadas y validadas.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================
# CONFIGURACIÓN BASE
# ============================================


class BaseConfig(BaseSettings):
    """Configuración base con carga desde .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# ============================================
# CONFIGURACIÓN DEL ENTORNO
# ============================================


class EnvironmentConfig(BaseConfig):
    """Configuración del entorno de ejecución."""

    environment: str = Field(default="development", description="Entorno de ejecución")
    debug: bool = Field(default=False, description="Modo debug")
    log_level: str = Field(default="INFO", description="Nivel de logging")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v_upper


# ============================================
# CONFIGURACIÓN DE SUPABASE
# ============================================


class SupabaseConfig(BaseConfig):
    """Configuración de Supabase."""

    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=".env",
        extra="ignore",
    )

    url: str = Field(default="", description="URL de Supabase")
    key: str = Field(default="", description="Anon key de Supabase")
    service_key: Optional[str] = Field(None, description="Service role key (admin)")

    @property
    def is_configured(self) -> bool:
        """True si Supabase está configurado."""
        return bool(self.url and self.key)


# ============================================
# CONFIGURACIÓN DE BROKERS
# ============================================


class MT5Config(BaseConfig):
    """Configuración de MetaTrader 5."""

    model_config = SettingsConfigDict(
        env_prefix="MT5_",
        env_file=".env",
        extra="ignore",
    )

    login: Optional[int] = Field(None, description="Número de cuenta")
    password: Optional[str] = Field(None, description="Contraseña")
    server: Optional[str] = Field(None, description="Servidor del broker")
    path: Optional[str] = Field(None, description="Ruta al ejecutable de MT5")

    @property
    def is_configured(self) -> bool:
        """True si MT5 está configurado."""
        return all([self.login, self.password, self.server])


class DarwinexConfig(BaseConfig):
    """Configuración de Darwinex."""

    model_config = SettingsConfigDict(
        env_prefix="DARWINEX_",
        env_file=".env",
        extra="ignore",
    )

    api_key: Optional[str] = Field(None, description="API key")
    account_id: Optional[str] = Field(None, description="ID de cuenta")
    environment: str = Field(default="demo", description="Entorno (demo/live)")

    @property
    def is_configured(self) -> bool:
        """True si Darwinex está configurado."""
        return all([self.api_key, self.account_id])

    @property
    def is_live(self) -> bool:
        """True si es cuenta real."""
        return self.environment == "live"


# ============================================
# CONFIGURACIÓN DE TRADING
# ============================================


class TradingConfig(BaseConfig):
    """Configuración de parámetros de trading."""

    # Tamaños
    default_lot_size: float = Field(default=0.01, ge=0.01, le=100.0)
    max_lot_size: float = Field(default=1.0, ge=0.01, le=100.0)

    # Spreads y filtros
    max_spread_pips: float = Field(default=2.0, ge=0.1, le=10.0)
    min_volatility_pips: float = Field(default=10.0, ge=0.0)

    # Límites operacionales
    max_operations_per_pair: int = Field(default=50, ge=1, le=500)
    max_total_operations: int = Field(default=200, ge=1, le=1000)
    max_cycles_per_pair: int = Field(default=10, ge=1, le=100)

    # Exposición
    max_exposure_percent: float = Field(default=30.0, ge=1.0, le=100.0)

    # Fondo de reserva
    reserve_fund_percent: float = Field(default=20.0, ge=0.0, le=50.0)

    # Pares permitidos
    allowed_pairs: List[str] = Field(
        default=["EURUSD", "GBPUSD", "USDJPY"],
        description="Pares permitidos para trading",
    )


# ============================================
# CONFIGURACIÓN DE RIESGO
# ============================================


class RiskConfig(BaseConfig):
    """Configuración de gestión de riesgo."""

    # Paradas de emergencia
    emergency_stop_drawdown_pips: float = Field(default=500.0, ge=100.0)
    max_daily_loss_pips: float = Field(default=100.0, ge=10.0)
    max_weekly_loss_pips: float = Field(default=300.0, ge=50.0)
    max_monthly_loss_pips: float = Field(default=500.0, ge=100.0)

    # Límites de recovery
    max_concurrent_recovery: int = Field(default=20, ge=1, le=100)
    max_recovery_level: int = Field(default=5, ge=1, le=10)

    # Alertas
    warning_drawdown_pips: float = Field(default=200.0, ge=50.0)
    critical_drawdown_pips: float = Field(default=400.0, ge=100.0)

    # Pausa automática
    pause_on_consecutive_losses: int = Field(default=5, ge=2, le=20)


# ============================================
# CONFIGURACIÓN POR PAR
# ============================================


class PairConfig(BaseConfig):
    """Configuración específica por par de divisas."""

    pair: str
    tp_main_pips: float = Field(default=10.0, ge=1.0)
    tp_recovery_pips: float = Field(default=80.0, ge=10.0)
    separation_pips: float = Field(default=5.0, ge=1.0)
    recovery_distance_pips: float = Field(default=20.0, ge=5.0)
    max_spread_pips: float = Field(default=2.0, ge=0.1)
    min_volatility_pips: float = Field(default=10.0, ge=0.0)
    sessions: List[str] = Field(default=["London", "NewYork"])

    @property
    def pip_multiplier(self) -> float:
        """Multiplicador para convertir precio a pips."""
        return 100.0 if "JPY" in self.pair else 10000.0


# Configuraciones predefinidas por par
DEFAULT_PAIR_CONFIGS: Dict[str, Dict[str, Any]] = {
    "EURUSD": {
        "tp_main_pips": 10.0,
        "tp_recovery_pips": 80.0,
        "separation_pips": 5.0,
        "recovery_distance_pips": 20.0,
        "max_spread_pips": 1.5,
        "min_volatility_pips": 10.0,
        "sessions": ["London", "NewYork"],
    },
    "GBPUSD": {
        "tp_main_pips": 12.0,
        "tp_recovery_pips": 85.0,
        "separation_pips": 6.0,
        "recovery_distance_pips": 25.0,
        "max_spread_pips": 2.0,
        "min_volatility_pips": 15.0,
        "sessions": ["London", "NewYork"],
    },
    "USDJPY": {
        "tp_main_pips": 8.0,
        "tp_recovery_pips": 70.0,
        "separation_pips": 5.0,
        "recovery_distance_pips": 20.0,
        "max_spread_pips": 1.5,
        "min_volatility_pips": 8.0,
        "sessions": ["Tokyo", "London", "NewYork"],
    },
}


def get_pair_config(pair: str) -> PairConfig:
    """Obtiene configuración para un par específico."""
    defaults = DEFAULT_PAIR_CONFIGS.get(pair, DEFAULT_PAIR_CONFIGS["EURUSD"])
    return PairConfig(pair=pair, **defaults)


# ============================================
# CONFIGURACIÓN DE API
# ============================================


class APIConfig(BaseConfig):
    """Configuración del API FastAPI."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)
    workers: int = Field(default=1, ge=1, le=10)


# ============================================
# CONFIGURACIÓN DE PATHS
# ============================================


class PathsConfig(BaseConfig):
    """Configuración de rutas de archivos."""

    quantdata_path: Path = Field(default=Path("/data/quantdata"))
    backtest_results_path: Path = Field(default=Path("./backtest_results"))
    logs_path: Path = Field(default=Path("./logs"))

    def ensure_directories(self) -> None:
        """Crea directorios si no existen."""
        self.backtest_results_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)


# ============================================
# CONFIGURACIÓN DE ALERTAS
# ============================================


class AlertsConfig(BaseConfig):
    """Configuración de sistema de alertas."""

    # Telegram
    telegram_bot_token: Optional[str] = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, alias="TELEGRAM_CHAT_ID")

    # Email
    email_smtp_host: Optional[str] = Field(None, alias="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, alias="EMAIL_SMTP_PORT")
    email_username: Optional[str] = Field(None, alias="EMAIL_USERNAME")
    email_password: Optional[str] = Field(None, alias="EMAIL_PASSWORD")
    email_to: Optional[str] = Field(None, alias="EMAIL_TO")

    @property
    def telegram_enabled(self) -> bool:
        """True si Telegram está configurado."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def email_enabled(self) -> bool:
        """True si email está configurado."""
        return bool(self.email_smtp_host and self.email_username)


# ============================================
# CONFIGURACIÓN DE FEATURE FLAGS
# ============================================


class FeatureFlags(BaseConfig):
    """Feature flags para habilitar/deshabilitar funcionalidades."""

    enable_paper_trading: bool = Field(default=True, alias="ENABLE_PAPER_TRADING")
    enable_live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")
    enable_backtesting: bool = Field(default=True, alias="ENABLE_BACKTESTING")
    enable_api: bool = Field(default=True, alias="ENABLE_API")


# ============================================
# CONFIGURACIÓN PRINCIPAL (AGREGADA)
# ============================================


class Settings(BaseSettings):
    """
    Configuración principal que agrega todas las configuraciones.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-configuraciones
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)
    mt5: MT5Config = Field(default_factory=MT5Config)
    darwinex: DarwinexConfig = Field(default_factory=DarwinexConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    def __init__(self, **data):
        super().__init__(**data)
        # Inicializar sub-configuraciones
        self.environment = EnvironmentConfig()
        self.supabase = SupabaseConfig()
        self.mt5 = MT5Config()
        self.darwinex = DarwinexConfig()
        self.trading = TradingConfig()
        self.risk = RiskConfig()
        self.api = APIConfig()
        self.paths = PathsConfig()
        self.alerts = AlertsConfig()
        self.features = FeatureFlags()

    @property
    def is_production(self) -> bool:
        """True si estamos en producción."""
        return self.environment.environment == "production"

    @property
    def is_development(self) -> bool:
        """True si estamos en desarrollo."""
        return self.environment.environment == "development"

    def get_pair_config(self, pair: str) -> PairConfig:
        """Obtiene configuración para un par."""
        return get_pair_config(pair)


# ============================================
# SINGLETON
# ============================================


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene instancia singleton de Settings.
    """
    return Settings()


# ============================================
# VALIDACIÓN DE CONFIGURACIÓN
# ============================================


def validate_configuration() -> Dict[str, Any]:
    """
    Valida la configuración y retorna estado.
    """
    settings = get_settings()

    return {
        "environment": settings.environment.environment,
        "supabase_configured": settings.supabase.is_configured,
        "mt5_configured": settings.mt5.is_configured,
        "darwinex_configured": settings.darwinex.is_configured,
        "telegram_enabled": settings.alerts.telegram_enabled,
        "email_enabled": settings.alerts.email_enabled,
        "live_trading_enabled": settings.features.enable_live_trading,
        "paper_trading_enabled": settings.features.enable_paper_trading,
    }
