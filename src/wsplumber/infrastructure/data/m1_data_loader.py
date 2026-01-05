import csv
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Generator

from wsplumber.domain.types import (
    TickData, CurrencyPair, Price, Timestamp, Pips
)

logger = logging.getLogger(__name__)

class M1DataLoader:
    """
    Cargador de datos históricos M1 que expande velas en ticks sintéticos.
    """

    def __init__(self, pair: CurrencyPair):
        self.pair = pair

    def parse_m1_csv(self, csv_path: str) -> Generator[TickData, None, None]:
        """
        Lee un CSV M1 y emite 4 ticks por vela (Open, Low, High, Close).
        """
        with open(csv_path, mode='r', encoding='utf-8') as f:
            # Soportar formatos con y sin BOM
            content = f.read(1)
            if content != '\ufeff':
                f.seek(0)
            
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Parsear timestamp: 20141201,02:00:00
                    date_str = row['Date']
                    time_str = row['Time']
                    dt = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H:%M:%S")
                    
                    o = Price(Decimal(row['Open']))
                    h = Price(Decimal(row['High']))
                    l = Price(Decimal(row['Low']))
                    c = Price(Decimal(row['Close']))
                    
                    # Generar 4 ticks sintéticos
                    # Secuencia: O -> L -> H -> C (Pessimistic approach)
                    # Añadimos micro-segundos para mantener orden cronológico
                    prices = [o, l, h, c]
                    for i, p in enumerate(prices):
                        # Asumimos spread de 0.5 pips si no viene en el CSV
                        # O usamos un spread fijo conservador
                        spread_pips = 1.0 
                        bid = p
                        ask = Price(p + Decimal("0.00010")) # 1.0 pips spread
                        
                        yield TickData(
                            pair=self.pair,
                            bid=bid,
                            ask=ask,
                            timestamp=Timestamp(dt.replace(microsecond=i)),
                            spread_pips=Pips(spread_pips)
                        )
                except Exception as e:
                    logger.error(f"Error parsing M1 row: {row}. Error: {e}")
                    continue

    @staticmethod
    def detect_pair_from_filename(filename: str) -> CurrencyPair:
        """Detecta el par de divisas desde el nombre del archivo."""
        if "EURUSD" in filename.upper():
            return CurrencyPair("EURUSD")
        if "GBPUSD" in filename.upper():
            return CurrencyPair("GBPUSD")
        return CurrencyPair("UNKNOWN")
