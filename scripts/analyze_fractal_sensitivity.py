import pandas as pd
import numpy as np
from pathlib import Path
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer
from datetime import timedelta
import sys

def analyze_sensitivity(parquet_path: str, timeframe: str = '1H', threshold: float = 0.45):
    print(f"--- Analyzing Sensitivity for {timeframe} (Hurst < {threshold}) ---")
    
    # Cargar datos
    df = pd.read_parquet(parquet_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Resamplear para obtener OHLC (usamos el mid price)
    df['mid'] = (df['bid'] + df['ask']) / 2
    resampled = df['mid'].resample(timeframe).last().dropna()
    
    analyzer = FractalAnalyzer(min_window=30, max_window=200)
    
    results = []
    prices = resampled.tolist()
    
    # Ventana deslizante para Hurst
    window_size = 100 # Revisamos los últimos 100 periodos del timeframe
    
    hurst_values = []
    for i in range(len(prices)):
        if i < window_size:
            hurst_values.append(0.5)
            continue
            
        window = prices[i-window_size : i]
        h = analyzer.calculate_hurst(window)
        hurst_values.append(h)
        
    analysis_df = pd.DataFrame({
        'price': prices,
        'hurst': hurst_values
    }, index=resampled.index)
    
    analysis_df['is_low'] = analysis_df['hurst'] < threshold
    
    # Análisis por semana
    analysis_df['week'] = analysis_df.index.isocalendar().week
    weekly_stats = analysis_df.groupby('week')['is_low'].mean() * 100 # % tiempo congelado
    
    # Detectar episodios de bajo Hurst
    analysis_df['episode_id'] = (analysis_df['is_low'] != analysis_df['is_low'].shift()).cumsum()
    episodes = analysis_df[analysis_df['is_low']].groupby('episode_id').agg({
        'price': ['count', 'min', 'max'],
        'hurst': 'mean'
    })
    
    # Calcular movimientos posteriores (Breakouts)
    # ¿Hay un movimiento de mas de 50 pips en las 24h siguientes al fin de un episodio?
    breakouts = 0
    valid_episodes = 0
    
    for episode_id, data in episodes.iterrows():
        # Encontrar el tiempo de fin del episodio
        last_time = analysis_df[analysis_df['episode_id'] == episode_id].index[-1]
        
        # Mirar ventana futura (24h)
        future_window = analysis_df.loc[last_time : last_time + timedelta(hours=24)]
        if len(future_window) > 1:
            future_move = (future_window['price'].max() - future_window['price'].min()) / 0.0001
            if future_move > 50:
                breakouts += 1
            valid_episodes += 1
    
    print(f"Estadísticas Generales ({timeframe}):")
    print(f"- % Tiempo por debajo de {threshold}: {analysis_df['is_low'].mean()*100:.2f}%")
    print(f"- Media de episodios por semana: {len(episodes) / analysis_df.index.isocalendar().week.nunique():.2f}")
    print(f"- Rango medio durante episodios (pips): {((episodes[('price', 'max')] - episodes[('price', 'min')]) / 0.0001).mean():.2f}")
    print(f"- Probabilidad de Breakout (>50p) tras el episodio: {(breakouts / valid_episodes)*100:.2f}%" if valid_episodes > 0 else "")
    
    print("\nDetalle Semanal (% Tiempo Congelado):")
    print(weekly_stats.head(10))
    
    return analysis_df

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/analyze_fractal_sensitivity.py [path_to_parquet]")
        sys.exit(1)
        
    path = sys.argv[1]
    # Analizamos H1 y H4 para comparar
    analyze_sensitivity(path, '1H')
    print("-" * 50)
    analyze_sensitivity(path, '4H')
