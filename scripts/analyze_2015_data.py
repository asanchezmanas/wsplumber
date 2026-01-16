import pandas as pd
import numpy as np

def analyze_parquet(path, start_idx, end_idx):
    df = pd.read_parquet(path)
    subset = df.iloc[start_idx:end_idx].copy()
    
    # Check for gaps in timestamps
    subset['timestamp'] = pd.to_datetime(subset['timestamp'])
    subset['time_diff'] = subset['timestamp'].diff()
    max_gap = subset['time_diff'].max()
    
    # Check for price jumps (volatility)
    subset['bid_change'] = subset['bid'].diff()
    max_jump = subset['bid_change'].abs().max()
    
    print(f"Analysis for indices {start_idx} to {end_idx}:")
    print(f"Max time gap: {max_gap}")
    print(f"Max price jump (bid): {max_jump:.5f}")
    
    # Find the exact index of max jump
    jump_idx = subset['bid_change'].abs().idxmax()
    print(f"Max jump at index {jump_idx}:")
    print(subset.loc[jump_idx-1:jump_idx+1])

if __name__ == "__main__":
    path = "data/partitions/EURUSD_2015.parquet"
    analyze_parquet(path, 60000, 80000)
