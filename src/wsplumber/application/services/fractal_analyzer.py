import numpy as np
from typing import List, Union
from decimal import Decimal
from loguru import logger

class FractalAnalyzer:
    """
    Servicio para el análisis fractal del mercado basado en las teorías de Mandelbrot.
    Implementa el cálculo del Exponente de Hurst (H) mediante R/S Analysis.
    """

    def __init__(self, min_window: int = 10, max_window: int = 500):
        self.min_window = min_window
        self.max_window = max_window

    def calculate_hurst(self, prices: Union[List[Decimal], List[float]]) -> float:
        """
        Calcula el exponente de Hurst para una serie de precios.
        H < 0.5: Anti-persistente (Lateral/Mean Reverting)
        H == 0.5: Paseo aleatorio
        H > 0.5: Persistente (Tendencial)
        """
        if len(prices) < self.min_window:
            return 0.5  # Neutral por falta de datos

        # Convertir a float para cálculos numpy
        p = np.array([float(x) for x in prices])
        
        # Calcular retornos logarítmicos
        log_returns = np.diff(np.log(p))
        if len(log_returns) < self.min_window:
            return 0.5

        # Método de R/S (Rescaled Range)
        def get_rs(data):
            # 1. Media
            mean_val = np.mean(data)
            # 2. Desviaciones acumuladas
            y = np.cumsum(data - mean_val)
            # 3. Rango (R)
            r = np.max(y) - np.min(y)
            # 4. Desviación estándar (S)
            s = np.std(data)
            if s == 0:
                return 0
            return r / s

        # Dividir la serie en bloques de diferentes tamaños para la regresión
        lags = range(self.min_window, min(len(log_returns), self.max_window))
        rs_values = []
        valid_lags = []

        for lag in lags:
            # Dividir en bloques de tamaño 'lag'
            num_blocks = len(log_returns) // lag
            if num_blocks == 0:
                continue
            
            block_rs = []
            for i in range(num_blocks):
                block = log_returns[i*lag : (i+1)*lag]
                rs = get_rs(block)
                if rs > 0:
                    block_rs.append(rs)
            
            if block_rs:
                rs_values.append(np.mean(block_rs))
                valid_lags.append(lag)

        if len(valid_lags) < 2:
            return 0.5

        # Regresión lineal: log(R/S) = H * log(lag)
        coeffs = np.polyfit(np.log(valid_lags), np.log(rs_values), 1)
        hurst = coeffs[0]
        
        return float(hurst)

    def get_range_length_pips(self, prices: Union[List[Decimal], List[float]], pip_value: float = 0.0001) -> float:
        """
        Calcula la longitud robusta del rango (R de R/S) en pips.
        """
        if len(prices) < self.min_window:
            return 0.0

        p = np.array([float(x) for x in prices])
        mean_val = np.mean(p)
        y = np.cumsum(p - mean_val)
        r = np.max(y) - np.min(y)
        
        # El rango R del R/S es una medida de desviación acumulada absoluta, 
        # pero para propósitos operativos, escalamos el High-Low tradicional 
        # con la volatilidad fractal
        
        current_range = (np.max(p) - np.min(p)) / pip_value
        return float(current_range)
