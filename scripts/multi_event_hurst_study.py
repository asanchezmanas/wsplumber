import pandas as pd
import numpy as np
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer
from datetime import timedelta
import os

def check_hurst_around_event(parquet_path: str, event_date_str: str, event_name: str):
    if not os.path.exists(parquet_path):
        print(f"Skipping {event_name}: {parquet_path} not found")
        return None
        
    df = pd.read_parquet(parquet_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    # Resample to 1H
    resampled = df['mid'].resample('1H').last().dropna()
    
    event_ts = pd.Timestamp(event_date_str)
    
    # We need context (last 100 1h bars)
    analyzer = FractalAnalyzer(min_window=30, max_window=200)
    window_size = 100
    
    # Range: 24h before to 6h after
    start_range = event_ts - timedelta(hours=24)
    end_range = event_ts + timedelta(hours=6)
    
    relevant_timestamps = resampled.loc[start_range:end_range].index.tolist()
    
    print(f"\nInvestigation: {event_name} ({event_date_str})")
    print("-" * 80)
    print(f"{'Time Relative':<15} | {'Timestamp':<25} | {'Hurst':<10} | {'Status'}")
    print("-" * 80)
    
    all_prices = resampled.tolist()
    all_ts = resampled.index.tolist()
    
    for i, ts in enumerate(all_ts):
        if ts in relevant_timestamps:
            if i < window_size: continue
            
            window = all_prices[i-window_size : i]
            h = analyzer.calculate_hurst(window)
            
            diff = (ts - event_ts).total_seconds() / 3600
            rel_str = f"{diff:+.1f}h"
            status = "LOW" if h < 0.45 else "TREND" if h > 0.55 else "NEUTRAL"
            
            # Highlight event moment
            prefix = ">>> " if -1 <= diff <= 0 else "    "
            print(f"{prefix}{rel_str:<11} | {str(ts):<25} | {h:<10.3f} | {status}")

def run_study():
    events = [
        ("data/partitions/EURUSD_2015.parquet", "2015-01-15 09:00:00", "SNB Black Thursday"),
        ("data/partitions/EURUSD_2015.parquet", "2015-01-22 13:00:00", "ECB QE Bazooka"),
        ("data/partitions/EURUSD_2016.parquet", "2016-06-24 00:00:00", "Brexit Vote Result"),
        ("data/partitions/EURUSD_2020.parquet", "2020-03-09 00:00:00", "Covid Flash Crash"),
        ("data/partitions/EURUSD_2022.parquet", "2022-02-24 04:00:00", "Ukraine Invasion Start")
    ]
    
    for path, dt, name in events:
        check_hurst_around_event(path, dt, name)

if __name__ == "__main__":
    run_study()
