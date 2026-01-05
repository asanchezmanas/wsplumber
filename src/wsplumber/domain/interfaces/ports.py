# src/wsplumber/domain/interfaces/ports.py
"""
Interfaces del dominio (Ports).

Estas interfaces definen los contratos que deben implementar
los adaptadores de infraestructura. Siguiendo Clean Architecture,
el dominio no conoce las implementaciones concretas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from wsplumber.domain.types import (
    BrokerTicket,
    CurrencyPair,
    CycleId,
    Direction,
    LotSize,
    Money,
    OperationId,
    OperationStatus,
    OrderRequest,
    OrderResult,
    Pips,
    Price,
    Result,
    StrategySignal,
    TickData,
    Timestamp,
)
from wsplumber.domain.entities.operation import Operation
from wsplumber.domain.entities.cycle import Cycle


# ============================================
# BROKER INTERFACE
# ============================================


class IBroker(ABC):
    """
    Interface para comunicación con el broker.

    Los adaptadores concretos (MT5, Darwinex) implementan esta interface.
    El dominio y aplicación solo conocen esta abstracción.
    """

    @abstractmethod
    async def connect(self) -> Result[bool]:
        """
        Establece conexión con el broker.

        Returns:
            Result indicando éxito o error de conexión.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Cierra conexión con el broker."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Verifica si hay conexión activa.

        Returns:
            True si está conectado.
        """
        pass

    @abstractmethod
    async def get_account_info(self) -> Result[Dict[str, Any]]:
        """
        Obtiene información de la cuenta.

        Returns:
            Dict con balance, equity, margin, etc.
        """
        pass

    @abstractmethod
    async def get_current_price(self, pair: CurrencyPair) -> Result[TickData]:
        """
        Obtiene precio actual de un par.

        Args:
            pair: Par de divisas

        Returns:
            TickData con bid, ask, spread.
        """
        pass

    @abstractmethod
    async def place_order(self, request: OrderRequest) -> Result[OrderResult]:
        """
        Coloca una orden en el broker.

        Args:
            request: Solicitud de orden con todos los parámetros

        Returns:
            OrderResult con ticket si éxito, error si no.
        """
        pass

    @abstractmethod
    async def cancel_order(self, ticket: BrokerTicket) -> Result[bool]:
        """
        Cancela una orden pendiente.

        Args:
            ticket: Ticket de la orden

        Returns:
            True si se canceló exitosamente.
        """
        pass

    @abstractmethod
    async def close_position(self, ticket: BrokerTicket) -> Result[OrderResult]:
        """
        Cierra una posición abierta.

        Args:
            ticket: Ticket de la posición

        Returns:
            OrderResult con precio de cierre.
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        ticket: BrokerTicket,
        new_tp: Optional[Price] = None,
        new_sl: Optional[Price] = None,
    ) -> Result[bool]:
        """
        Modifica una orden existente.

        Args:
            ticket: Ticket de la orden
            new_tp: Nuevo take profit (opcional)
            new_sl: Nuevo stop loss (opcional)

        Returns:
            True si se modificó exitosamente.
        """
        pass

    @abstractmethod
    async def get_open_positions(self) -> Result[List[Dict[str, Any]]]:
        """
        Obtiene todas las posiciones abiertas.

        Returns:
            Lista de posiciones con detalles.
        """
        pass

    @abstractmethod
    async def get_pending_orders(self) -> Result[List[Dict[str, Any]]]:
        """
        Obtiene todas las órdenes pendientes.

        Returns:
            Lista de órdenes pendientes.
        """
        pass

    @abstractmethod
    async def get_order_history(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Result[List[Dict[str, Any]]]:
        """
        Obtiene historial de órdenes.

        Args:
            from_date: Fecha inicio (opcional)
            to_date: Fecha fin (opcional)

        Returns:
            Lista de órdenes históricas.
        """
        pass

    @abstractmethod
    async def get_historical_rates(
        self,
        pair: CurrencyPair,
        timeframe: str,
        count: int,
        from_date: Optional[datetime] = None,
    ) -> Result[List[Dict[str, Any]]]:
        """
        Obtiene datos históricos de velas (OHLC).

        Args:
            pair: Par de divisas.
            timeframe: Temporalidad (M1, H1, etc.)
            count: Cantidad de velas.
            from_date: Fecha inicio (opcional).

        Returns:
            Result con lista de velas.
        """
        pass

    @abstractmethod
    async def get_historical_ticks(
        self,
        pair: CurrencyPair,
        count: int,
        from_date: Optional[datetime] = None,
    ) -> Result[List[TickData]]:
        """
        Obtiene historial de ticks.

        Args:
            pair: Par de divisas.
            count: Cantidad de ticks.
            from_date: Fecha inicio (opcional).

        Returns:
            Result con lista de TickData.
        """
        pass


# ============================================
# REPOSITORY INTERFACE
# ============================================


class IRepository(ABC):
    """
    Interface para persistencia de datos.

    Los adaptadores concretos (Supabase, SQLite) implementan esta interface.
    """

    # ============================================
    # CYCLES
    # ============================================

    @abstractmethod
    async def save_cycle(self, cycle: Cycle) -> Result[CycleId]:
        """
        Guarda o actualiza un ciclo.

        Args:
            cycle: Ciclo a guardar

        Returns:
            ID del ciclo guardado.
        """
        pass

    @abstractmethod
    async def get_cycle(self, cycle_id: CycleId) -> Result[Optional[Cycle]]:
        """
        Obtiene un ciclo por ID.

        Args:
            cycle_id: ID del ciclo

        Returns:
            Cycle si existe, None si no.
        """
        pass

    @abstractmethod
    async def get_active_cycles(
        self, pair: Optional[CurrencyPair] = None
    ) -> Result[List[Cycle]]:
        """
        Obtiene ciclos activos.

        Args:
            pair: Filtrar por par (opcional)

        Returns:
            Lista de ciclos activos.
        """
        pass

    @abstractmethod
    async def get_cycles_by_status(
        self,
        statuses: List[str],
        pair: Optional[CurrencyPair] = None,
    ) -> Result[List[Cycle]]:
        """
        Obtiene ciclos por estado.

        Args:
            statuses: Lista de estados
            pair: Filtrar por par (opcional)

        Returns:
            Lista de ciclos.
        """
        pass

    # ============================================
    # OPERATIONS
    # ============================================

    @abstractmethod
    async def save_operation(self, operation: Operation) -> Result[OperationId]:
        """
        Guarda o actualiza una operación.

        Args:
            operation: Operación a guardar

        Returns:
            ID de la operación.
        """
        pass

    @abstractmethod
    async def get_operation(
        self, operation_id: OperationId
    ) -> Result[Optional[Operation]]:
        """
        Obtiene una operación por ID.

        Args:
            operation_id: ID de la operación

        Returns:
            Operation si existe, None si no.
        """
        pass

    @abstractmethod
    async def get_active_operations(
        self, pair: Optional[CurrencyPair] = None
    ) -> Result[List[Operation]]:
        """
        Obtiene operaciones activas.

        Args:
            pair: Filtrar por par (opcional)

        Returns:
            Lista de operaciones activas.
        """
        pass

    @abstractmethod
    async def get_pending_operations(
        self, pair: Optional[CurrencyPair] = None
    ) -> Result[List[Operation]]:
        """
        Obtiene operaciones pendientes.

        Args:
            pair: Filtrar por par (opcional)

        Returns:
            Lista de operaciones pendientes.
        """
        pass

    @abstractmethod
    async def get_operation_by_ticket(
        self, ticket: BrokerTicket
    ) -> Result[Optional[Operation]]:
        """
        Obtiene operación por ticket del broker.

        Args:
            ticket: Ticket del broker

        Returns:
            Operation si existe.
        """
        pass

    # ============================================
    # CHECKPOINTS
    # ============================================

    @abstractmethod
    async def save_checkpoint(self, state: Dict[str, Any]) -> Result[str]:
        """
        Guarda checkpoint del estado.

        Args:
            state: Estado completo a guardar

        Returns:
            ID del checkpoint.
        """
        pass

    @abstractmethod
    async def get_latest_checkpoint(self) -> Result[Optional[Dict[str, Any]]]:
        """
        Obtiene el checkpoint más reciente.

        Returns:
            Estado del checkpoint o None.
        """
        pass

    # ============================================
    # OUTBOX
    # ============================================

    @abstractmethod
    async def add_to_outbox(
        self,
        operation_type: str,
        payload: Dict[str, Any],
        idempotency_key: str,
    ) -> Result[str]:
        """
        Añade operación al outbox.

        Args:
            operation_type: Tipo de operación
            payload: Datos de la operación
            idempotency_key: Clave de idempotencia

        Returns:
            ID de la entrada en outbox.
        """
        pass

    @abstractmethod
    async def get_pending_outbox_entries(
        self, limit: int = 10
    ) -> Result[List[Dict[str, Any]]]:
        """
        Obtiene entradas pendientes del outbox.

        Args:
            limit: Máximo de entradas

        Returns:
            Lista de entradas pendientes.
        """
        pass

    @abstractmethod
    async def update_outbox_status(
        self,
        entry_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Result[bool]:
        """
        Actualiza estado de entrada en outbox.

        Args:
            entry_id: ID de la entrada
            status: Nuevo estado
            error_message: Mensaje de error (opcional)

        Returns:
            True si se actualizó.
        """
        pass

    # ============================================
    # METRICS
    # ============================================

    @abstractmethod
    async def save_daily_metrics(self, metrics: Dict[str, Any]) -> Result[bool]:
        """
        Guarda métricas diarias.

        Args:
            metrics: Métricas a guardar

        Returns:
            True si se guardó.
        """
        pass

    @abstractmethod
    async def get_daily_metrics(
        self, days: int = 30
    ) -> Result[List[Dict[str, Any]]]:
        """
        Obtiene métricas de los últimos N días.

        Args:
            days: Número de días

        Returns:
            Lista de métricas diarias.
        """
        pass

    # ============================================
    # ALERTS
    # ============================================

    @abstractmethod
    async def create_alert(
        self,
        severity: str,
        alert_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[str]:
        """
        Crea una alerta.

        Args:
            severity: Severidad (info, warning, error, critical)
            alert_type: Tipo de alerta
            message: Mensaje
            metadata: Datos adicionales

        Returns:
            ID de la alerta.
        """
        pass

    # ============================================
    # HEALTH
    # ============================================

    @abstractmethod
    async def health_check(self) -> Result[str]:
        """
        Verifica salud de la conexión.

        Returns:
            Mensaje de estado.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cierra conexión con la base de datos."""
        pass

    # ============================================
    # HISTORICAL DATA
    # ============================================

    @abstractmethod
    async def save_historical_rates(
        self,
        pair: CurrencyPair,
        timeframe: str,
        rates: List[Dict[str, Any]]
    ) -> Result[int]:
        """
        Persiste datos históricos de velas.

        Args:
            pair: Par de divisas.
            timeframe: Temporalidad.
            rates: Lista de diccionarios con datos de velas.

        Returns:
            Result con cantidad de registros guardados.
        """
        pass

    @abstractmethod
    async def save_historical_ticks(
        self,
        pair: CurrencyPair,
        ticks: List[TickData]
    ) -> Result[int]:
        """
        Persiste datos históricos de ticks.

        Args:
            pair: Par de divisas.
            ticks: Lista de TickData.

        Returns:
            Result con cantidad de registros guardados.
        """
        pass


# ============================================
# STRATEGY INTERFACE
# ============================================


class IStrategy(ABC):
    """
    Interface del motor de estrategia (CORE SECRETO).

    El código externo solo ve estos métodos.
    La implementación real está en el core protegido.
    """

    @abstractmethod
    def process_tick(
        self,
        pair: CurrencyPair,
        bid: float,
        ask: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """
        Procesa un tick y retorna señal.

        Args:
            pair: Par de divisas
            bid: Precio bid
            ask: Precio ask
            timestamp: Momento del tick

        Returns:
            Señal de la estrategia (NO revela lógica interna).
        """
        pass

    @abstractmethod
    def process_order_fill(
        self,
        operation_id: OperationId,
        fill_price: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """
        Procesa ejecución de orden.

        Args:
            operation_id: ID de la operación
            fill_price: Precio de ejecución
            timestamp: Momento de ejecución

        Returns:
            Señal de la estrategia.
        """
        pass

    @abstractmethod
    def process_tp_hit(
        self,
        operation_id: OperationId,
        profit_pips: float,
        timestamp: datetime,
    ) -> StrategySignal:
        """
        Procesa take profit alcanzado.

        Args:
            operation_id: ID de la operación
            profit_pips: Pips ganados
            timestamp: Momento del TP

        Returns:
            Señal de la estrategia.
        """
        pass

    @abstractmethod
    def get_current_state(self) -> Dict[str, Any]:
        """
        Estado actual (SANITIZADO).

        Solo expone lo necesario para monitoreo.
        NO incluye parámetros ni lógica interna.

        Returns:
            Estado sanitizado.
        """
        pass

    @abstractmethod
    def load_state(self, state: Dict[str, Any]) -> None:
        """
        Carga estado desde checkpoint.

        Args:
            state: Estado a cargar.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reinicia el estado de la estrategia."""
        pass


# ============================================
# RISK MANAGER INTERFACE
# ============================================


class IRiskManager(ABC):
    """Interface del gestor de riesgo."""

    @abstractmethod
    def can_open_position(
        self,
        pair: CurrencyPair,
        current_exposure: float,
    ) -> Result[bool]:
        """
        Verifica si se puede abrir posición.

        Args:
            pair: Par de divisas
            current_exposure: Exposición actual

        Returns:
            Result con True si se puede, False si no (con razón).
        """
        pass

    @abstractmethod
    def calculate_lot_size(
        self,
        pair: CurrencyPair,
        account_balance: float,
    ) -> LotSize:
        """
        Calcula tamaño de posición.

        Args:
            pair: Par de divisas
            account_balance: Balance de cuenta

        Returns:
            Tamaño de lote calculado.
        """
        pass

    @abstractmethod
    def check_daily_limits(self) -> Result[bool]:
        """
        Verifica límites diarios.

        Returns:
            True si no se han excedido, False con razón si sí.
        """
        pass

    @abstractmethod
    def check_emergency_stop(self) -> bool:
        """
        Verifica si se debe activar parada de emergencia.

        Returns:
            True si hay que parar.
        """
        pass


# ============================================
# DATA PROVIDER INTERFACE
# ============================================


class IDataProvider(ABC):
    """Interface para proveedores de datos históricos."""

    @abstractmethod
    async def load_historical_data(
        self,
        pair: CurrencyPair,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Result[Any]:  # DataFrame
        """
        Carga datos históricos.

        Args:
            pair: Par de divisas
            timeframe: Temporalidad (M1, M5, H1, etc)
            start_date: Fecha inicio
            end_date: Fecha fin

        Returns:
            DataFrame con datos OHLC.
        """
        pass

    @abstractmethod
    async def get_available_pairs(self) -> Result[List[CurrencyPair]]:
        """
        Lista pares disponibles.

        Returns:
            Lista de pares.
        """
        pass

    @abstractmethod
    async def get_data_range(
        self, pair: CurrencyPair
    ) -> Result[Dict[str, datetime]]:
        """
        Obtiene rango de datos disponibles.

        Args:
            pair: Par de divisas

        Returns:
            Dict con 'start' y 'end'.
        """
        pass
