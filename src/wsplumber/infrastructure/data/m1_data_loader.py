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

    def parse_m1_csv(self, csv_path: str, max_bars: int = None) -> Generator[TickData, None, None]:
        """
        Lee un CSV M1 y emite 4 ticks por vela (Open, Low, High, Close).
        Soporta formatos con/sin cabecera y diferentes formatos de fecha.
        """
        with open(csv_path, mode='r', encoding='utf-8') as f:
            # Soportar formatos con y sin BOM
            content = f.read(1)
            if content != '\ufeff':
                f.seek(0)
            
            # Detectar si hay cabecera analizando la primera línea
            first_line = f.readline().strip()
            f.seek(0)
            has_header = "date" in first_line.lower() or "time" in first_line.lower()
            
            if has_header:
                reader = csv.DictReader(f)
            else:
                reader = csv.reader(f)

            bar_count = 0
            for row_raw in reader:
                if max_bars is not None and bar_count >= max_bars:
                    break
                
                try:
                    if has_header:
                        row = row_raw
                        date_str = row['Date']
                        time_str = row['Time']
                        o_val, h_val, l_val, c_val = row['Open'], row['High'], row['Low'], row['Close']
                    else:
                        row = row_raw
                        if len(row) < 6: continue
                        date_str = row[0]
                        time_str = row[1]
                        o_val, h_val, l_val, c_val = row[2], row[3], row[4], row[5]

                    # Normalizar formato de fecha
                    date_str = date_str.replace('.', '').replace('-', '')
                    if time_str.count(':') == 1:
                        time_str += ":00"
                    
                    dt = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H:%M:%S")
                    
                    o = Price(Decimal(o_val))
                    h = Price(Decimal(h_val))
                    l = Price(Decimal(l_val))
                    c = Price(Decimal(c_val))
                    
                    prices = [o, l, h, c]
                    for i, p in enumerate(prices):
                        spread_pips = 1.0 
                        bid = p
                        ask = Price(p + Decimal("0.00010"))
                        
                        yield TickData(
                            pair=self.pair,
                            bid=bid,
                            ask=ask,
                            timestamp=Timestamp(dt.replace(microsecond=i)),
                            spread_pips=Pips(spread_pips)
                        )
                    bar_count += 1
                except Exception as e:
                    logger.error(f"Error parsing M1 row: {row_raw}. Error: {e}")
                    continue

    @staticmethod
    def detect_pair_from_filename(filename: str) -> CurrencyPair:
        """Detecta el par de divisas desde el nombre del archivo."""
        if "EURUSD" in filename.upper():
            return CurrencyPair("EURUSD")
        if "GBPUSD" in filename.upper():
            return CurrencyPair("GBPUSD")
        return CurrencyPair("UNKNOWN")
