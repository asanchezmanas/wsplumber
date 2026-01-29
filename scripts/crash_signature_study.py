import pandas as pd
import numpy as np
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer
from datetime import timedelta
import os

def get_pre_event_hurst(parquet_path, event_ts_str, window_mins=60, pre_offset_mins=15):
    if not os.path.exists(parquet_path): return None
    
    df = pd.read_parquet(parquet_path)
    df['ts'] = pd.to_datetime(df['timestamp'])
    df.set_index('ts', inplace=True)
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    event_ts = pd.Timestamp(event_ts_str)
    # Target: Hurst at (Event - pre_offset_mins)
    target_ts = event_ts - timedelta(minutes=pre_offset_mins)
    
    # Needs a window of data ending at target_ts
    window_start = target_ts - timedelta(minutes=window_mins)
    data = df.loc[window_start : target_ts]['mid']
    
    if len(data) < 30: return None
    
    analyzer = FractalAnalyzer()
    h = analyzer.calculate_hurst(data.tolist())
    return h

def run_signature_study():
    events = [
        # Crashes / Structural Breaks
        ("data/partitions/EURUSD_2015.parquet", "2015-01-15 11:30:00", "SNB Black Thursday", "CRASH"),
        ("data/partitions/EURUSD_2022.parquet", "2022-02-24 04:00:00", "Ukraine Invasion", "CRASH"),
        
        # Volatile Trends (News)
        ("data/partitions/EURUSD_2015.parquet", "2015-01-22 13:00:00", "ECB QE (Bazooka)", "TREND"),
        ("data/partitions/EURUSD_2015.parquet", "2015-02-06 13:30:00", "NFP February", "TREND"),
        ("data/partitions/EURUSD_2016.parquet", "2016-06-24 00:00:00", "Brexit Vote Result", "TREND")
    ]
    
    print(f"{'Event':<25} | {'Type':<10} | {'Hurst (15m before)':<20} | {'Verdict'}")
    print("-" * 80)
    
    for path, ts, name, etype in events:
        h = get_pre_event_hurst(path, ts)
        if h is not None:
            verdict = "BLOCK (Safe)" if h < 0.45 else "ALLOW (Risk)"
            print(f"{name:<25} | {etype:<10} | {h:<20.3f} | {verdict}")

if __name__ == "__main__":
    run_signature_study()
