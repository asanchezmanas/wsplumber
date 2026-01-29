import pytest
import numpy as np
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer

def test_hurst_trend():
    analyzer = FractalAnalyzer(min_window=10, max_window=100)
    # Generar una tendencia clara (Persistent)
    prices = np.cumsum(np.random.normal(0.5, 0.1, 200)) # Tendencia alcista con ruido
    h = analyzer.calculate_hurst(list(prices))
    print(f"Trend Hurst: {h}")
    assert h > 0.5

def test_hurst_random_walk():
    analyzer = FractalAnalyzer(min_window=10, max_window=100)
    # Paseo aleatorio puro
    prices = np.cumsum(np.random.normal(0, 1, 200))
    h = analyzer.calculate_hurst(list(prices))
    print(f"Random Hurst: {h}")
    # H debería estar cerca de 0.5 (permitimos margen)
    assert 0.4 < h < 0.6

def test_hurst_mean_reverting():
    analyzer = FractalAnalyzer(min_window=10, max_window=100)
    # Serie que vuelve a la media (Anti-persistent)
    prices = []
    curr = 1.0
    for _ in range(200):
        curr += -0.5 * (curr - 1.0) + np.random.normal(0, 0.1)
        prices.append(curr)
    
    h = analyzer.calculate_hurst(prices)
    print(f"Mean Reverting Hurst: {h}")
    assert h < 0.5

def test_range_length():
    analyzer = FractalAnalyzer(min_window=2) # Adjust for small test sample
    # Rango de 50 pips exactos
    prices = [1.0000, 1.0050]
    range_pips = analyzer.get_range_length_pips(prices, pip_value=0.0001)
    assert range_pips == 50.0
