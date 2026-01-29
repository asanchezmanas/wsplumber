# src/wsplumber/application/services/economic_calendar.py
"""
Servicio de Calendario Económico (Layer 2 - Event Guard).

Este servicio gestiona la detección de eventos macroeconómicos de alto impacto
para proteger el capital durante ventanas de volatilidad extrema.
"""

import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

from wsplumber.domain.types import Timestamp

logger = logging.getLogger(__name__)

class EconomicEvent:
    """Representa un evento del calendario económico."""
    def __init__(self, timestamp: datetime, importance: str, description: str):
        self.timestamp = timestamp
        self.importance = importance.upper()
        self.description = description

    def __repr__(self):
        return f"Event({self.timestamp.isoformat()}, {self.importance}, {self.description})"

class EconomicCalendar:
    """
    Gestión de eventos económicos con soporte híbrido (Local/Live).
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.events: List[EconomicEvent] = []
        self._loaded_years: set = set()

    def load_historical_events(self, year: int) -> bool:
        """
        Carga eventos desde archivos CSV locales (data/events_{year}.csv).
        """
        if year in self._loaded_years:
            return True

        file_path = self.data_dir / f"events_{year}.csv"
        if not file_path.exists():
            logger.warning(f"Calendar file not found: {file_path}")
            return False

        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                new_events = []
                for row in reader:
                    # Skip comments and empty lines
                    if not row or row[0].startswith('#'):
                        continue
                    
                    try:
                        dt = datetime.fromisoformat(row[0].strip())
                        importance = row[1].strip()
                        desc = row[2].strip()
                        
                        # Filter: Only HIGH impact for now
                        if importance.upper() == "HIGH":
                            new_events.append(EconomicEvent(dt, importance, desc))
                    except (ValueError, IndexError) as e:
                        logger.error(f"Error parsing calendar row {row}: {e}")
                        continue
                
                self.events.extend(new_events)
                self.events.sort(key=lambda x: x.timestamp)
                self._loaded_years.add(year)
                logger.info(f"Loaded {len(new_events)} high-impact events for {year}")
                return True

        except Exception as e:
            logger.error(f"Failed to load calendar for {year}: {e}")
            return False

    def is_near_critical_event(self, current_time: datetime, window_minutes: int = 5) -> Optional[EconomicEvent]:
        """
        Verifica si estamos dentro de la ventana de protección de un evento crítico (T-window a T+window).
        """
        # Ensure year is loaded
        self.load_historical_events(current_time.year)

        lower_bound = current_time - timedelta(minutes=window_minutes)
        upper_bound = current_time + timedelta(minutes=window_minutes)

        for event in self.events:
            # Optimize: Events are sorted, so we can break early if we passed the window
            if event.timestamp > upper_bound:
                break
            
            if lower_bound <= event.timestamp <= upper_bound:
                return event

        return None

    def get_next_event(self, current_time: datetime) -> Optional[EconomicEvent]:
        """Retorna el próximo evento cronológico."""
        self.load_historical_events(current_time.year)
        for event in self.events:
            if event.timestamp > current_time:
                return event
        return None
