import pandas as pd
import numpy as np
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer
from datetime import datetime

def investigate_snb_hurst(parquet_path: str):
    df = pd.read_parquet(parquet_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    # SNB Day: 2015-01-15
    start_date = '2015-01-12'
    end_date = '2015-01-18'
    
    # Resample to 1H for reliable Hurst
    resampled = df['mid'].resample('1H').last().dropna()
    prices = resampled.loc[start_date:end_date].tolist()
    timestamps = resampled.loc[start_date:end_date].index.tolist()
    
    analyzer = FractalAnalyzer(min_window=30, max_window=200)
    window_size = 100
    
    print(f"{'Timestamp':<25} | {'Price':<10} | {'Hurst':<10} | {'Status'}")
    print("-" * 60)
    
    # We need historical context for the first Hurst values in our range
    full_prices = resampled.tolist()
    full_timestamps = resampled.index.tolist()
    
    for i in range(len(full_prices)):
        ts = full_timestamps[i]
        if ts < pd.Timestamp(start_date) or ts > pd.Timestamp(end_date):
            continue
            
        if i < window_size:
            continue
            
        window = full_prices[i-window_size : i]
        h = analyzer.calculate_hurst(window)
        status = "LOW" if h < 0.45 else "TREND" if h > 0.55 else "NEUTRAL"
        print(f"{str(ts):<25} | {full_prices[i]:<10.5f} | {h:<10.3f} | {status}")

if __name__ == "__main__":
    investigate_snb_hurst("data/partitions/EURUSD_2015.parquet")
