import pandas as pd
from pathlib import Path
from datetime import datetime

# Load 2015 data
data_path = Path("data/partitions/EURUSD_2015.parquet")
df = pd.read_parquet(data_path)

# Convert timestamp to datetime if needed
if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# FOMC Event: 2015-01-28 19:00:00
target_time = datetime(2015, 1, 28, 19, 0, 0)
start_time = datetime(2015, 1, 28, 18, 55, 0)

# Find index closest to start_time
idx = (df['timestamp'] - start_time).abs().idxmin()

# Extract 1000 ticks from there
subset = df.iloc[idx:idx+1000].copy()

print(f"Total ticks in 2015: {len(df)}")
print(f"Extracted {len(subset)} ticks starting at {subset['timestamp'].iloc[0]}")

# Save as CSV
output_path = Path("tests/scenarios/eurusd_2015_fomc_1000.csv")
subset.to_csv(output_path, index=False)
print(f"Saved to {output_path}")
