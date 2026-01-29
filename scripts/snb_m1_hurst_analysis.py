import pandas as pd
import numpy as np
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer
from datetime import timedelta

def analyze_m1_hurst_snb(parquet_path: str):
    df = pd.read_parquet(parquet_path)
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    # SNB Event: 2015-01-15 09:30 (approx)
    event_start = pd.Timestamp('2015-01-15 08:00')
    event_end = pd.Timestamp('2015-01-15 11:00')
    
    # We need M1 data. The parquet already seems to have it.
    # Just filter the window we need + context
    analysis_window = df.loc['2015-01-15 06:00':'2015-01-15 12:00']
    
    analyzer = FractalAnalyzer(min_window=30, max_window=200)
    window_calc = 60 # 60 minutes window
    
    print(f"{'Time':<20} | {'Price':<10} | {'Change (pips)':<15} | {'Hurst (H)':<10} | {'Status'}")
    print("-" * 75)
    
    prices = analysis_window['mid'].tolist()
    ts = analysis_window.index.tolist()
    
    for i in range(len(prices)):
        curr_ts = ts[i]
        if curr_ts < event_start or curr_ts > event_end:
            continue
            
        if i < window_calc:
            continue
            
        window = prices[i-window_calc : i]
        h = analyzer.calculate_hurst(window)
        
        price_change = (prices[i] - prices[i-1]) / 0.0001 if i > 0 else 0
        
        status = "CRASH/BOUNCE" if abs(price_change) > 20 else "LOW" if h < 0.45 else "NEUTRAL"
        
        # We only print the most interesting parts around the jump
        # or every 5 mins to not flood
        if abs(price_change) > 5 or i % 5 == 0:
            marker = "!!! EVENT !!!" if abs(price_change) > 50 else ""
            print(f"{str(curr_ts.time()):<20} | {prices[i]:<10.5f} | {price_change:<15.2f} | {h:<10.3f} | {status} {marker}")

if __name__ == "__main__":
    analyze_m1_hurst_snb("data/partitions/EURUSD_2015.parquet")
