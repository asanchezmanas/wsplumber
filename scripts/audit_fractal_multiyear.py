import pandas as pd
import numpy as np
from pathlib import Path
from wsplumber.application.services.fractal_analyzer import FractalAnalyzer
from datetime import timedelta
import sys
import glob

def analyze_file(parquet_path: str, timeframe: str = '1H', threshold: float = 0.45):
    year = Path(parquet_path).stem.split('_')[-1]
    
    # Cargar datos
    df = pd.read_parquet(parquet_path)
    if df.empty:
        return None
        
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
    df.set_index('timestamp', inplace=True)
    
    # Resamplear
    df['mid'] = (df['bid'] + df['ask']) / 2
    resampled = df['mid'].resample(timeframe).last().dropna()
    
    if len(resampled) < 110:
        return None
        
    analyzer = FractalAnalyzer(min_window=30, max_window=200)
    prices = resampled.tolist()
    window_size = 100
    
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
    
    # Episodios y Breakouts
    analysis_df['episode_id'] = (analysis_df['is_low'] != analysis_df['is_low'].shift()).cumsum()
    episodes = analysis_df[analysis_df['is_low']].groupby('episode_id').agg({
        'price': ['count', 'min', 'max'],
        'hurst': 'mean'
    })
    
    breakouts = 0
    valid_episodes = 0
    for episode_id, data in episodes.iterrows():
        last_time = analysis_df[analysis_df['episode_id'] == episode_id].index[-1]
        future_window = analysis_df.loc[last_time : last_time + timedelta(hours=24)]
        if len(future_window) > 1:
            future_move = (future_window['price'].max() - future_window['price'].min()) / 0.0001
            if future_move > 50:
                breakouts += 1
            valid_episodes += 1
            
    stats = {
        'year': year,
        'timeframe': timeframe,
        'percent_low': analysis_df['is_low'].mean() * 100,
        'episodes_per_week': len(episodes) / max(1, analysis_df.index.isocalendar().week.nunique()),
        'avg_range_pips': ((episodes[('price', 'max')] - episodes[('price', 'min')]) / 0.0001).mean(),
        'breakout_prob': (breakouts / valid_episodes * 100) if valid_episodes > 0 else 0
    }
    return stats

def main():
    target_dir = "data/partitions"
    files = glob.glob(f"{target_dir}/*.parquet")
    files.sort()
    
    timeframes = ['15m', '30m', '1H', '4H', '1D']
    
    for tf in timeframes:
        all_stats = []
        print(f"\nAUDITING TIMEFRAME: {tf}")
        print("="*30)
        
        for f in files:
            print(f"Processing {Path(f).name}...")
            res = analyze_file(f, tf)
            if res:
                all_stats.append(res)
                print(f"  Result: {res['percent_low']:.1f}% low | {res['breakout_prob']:.1f}% breakout")
                
        if not all_stats:
            continue
            
        summary_df = pd.DataFrame(all_stats)
        print("\n" + "="*50)
        print(f"GLOBAL FRACTAL AUDIT REPORT ({tf})")
        print("="*50)
        print(summary_df.to_string(index=False))
        
        print("\nAVERAGE STATISTICS:")
        print(f"- Time Below 0.45: {summary_df['percent_low'].mean():.2f}%")
        print(f"- Episodes per Week: {summary_df['episodes_per_week'].mean():.2f}")
        print(f"- Breakout Probability (>50p): {summary_df['breakout_prob'].mean():.2f}%")
        print(f"- Avg Range in 'Trigger Trap': {summary_df['avg_range_pips'].mean():.2f} pips")

if __name__ == "__main__":
    main()
