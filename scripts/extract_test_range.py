"""
Extract a specific tick range from 2015 data for Layer 1B testing.
This was identified as the problematic period with the 93.5 pip gap.
"""
import pandas as pd
from pathlib import Path

# Load 2015 data
data_path = Path("data/partitions/EURUSD_2015.parquet")
df = pd.read_parquet(data_path)

print(f"Total ticks: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Extract ticks 60000 to 80000
subset = df.iloc[60000:80000].copy()
print(f"\nExtracted subset: {len(subset)} ticks")
print(f"Subset date range: {subset['timestamp'].min()} to {subset['timestamp'].max()}")

# Save as CSV for scenario testing
output_path = Path("tests/scenarios/eurusd_2015_60k_80k.csv")
subset.to_csv(output_path, index=False)
print(f"\nSaved to: {output_path}")

# Find the biggest gaps in this subset
subset['mid'] = (subset['bid'] + subset['ask']) / 2
subset['gap_pips'] = abs(subset['mid'].diff()) / 0.0001

print("\nTop 10 gaps in this period:")
top_gaps = subset.nlargest(10, 'gap_pips')[['timestamp', 'bid', 'ask', 'gap_pips']]
print(top_gaps.to_string())
