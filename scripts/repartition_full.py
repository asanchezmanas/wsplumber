import pandas as pd
import os

df = pd.read_parquet("data/partitions/EURUSD_2015.parquet")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")

# Standard weeks (starting from first tick)
start_date = df["timestamp"].min()
for i in range(1, 41): # Create up to 40 weeks of 2015
    week_start = start_date + pd.Timedelta(weeks=i-1)
    week_end = start_date + pd.Timedelta(weeks=i)
    mask = (df["timestamp"] >= week_start) & (df["timestamp"] < week_end)
    week_df = df[mask]
    
    if not week_df.empty:
        filename = f"data/partitions/EURUSD_2015_Week{i}.csv"
        # Only create if doesn't exist to save time, or overwrite if we want fresh
        week_df.to_csv(filename, index=False)
        if i > 9: # Only print new ones
            print(f"Created {filename}")
