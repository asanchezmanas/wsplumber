import os
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def convert_csv_to_parquet(csv_path: Path):
    parquet_path = csv_path.with_suffix('.parquet')
    try:
        logging.info(f"Converting {csv_path.name} to Parquet...")
        # Read CSV with flexible settings
        df = pd.read_csv(csv_path, comment='#')
        
        # Ensure timestamp is string or datetime (for consistency)
        # Parquet loves datetime64[ns]
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'].str.replace('.', '-'), errors='ignore')
        elif 'datetime' in df.columns:
             df['datetime'] = pd.to_datetime(df['datetime'].str.replace('.', '-'), errors='ignore')
             
        df.to_parquet(parquet_path, index=False)
        logging.info(f"Saved: {parquet_path.name}")
        
        # Optional: verify sizes
        csv_size = os.path.getsize(csv_path) / (1024 * 1024)
        parquet_size = os.path.getsize(parquet_path) / (1024 * 1024)
        logging.info(f"Size: {csv_size:.2f}MB -> {parquet_size:.2f}MB (Reduction: {(1 - parquet_size/csv_size)*100:.1f}%)")
        
        return True
    except Exception as e:
        logging.error(f"Failed to convert {csv_path.name}: {e}")
        return False

def main():
    base_dir = Path("tests/scenarios")
    
    # Target files: factorial folder and large CSVs in root scenarios
    files_to_convert = list(base_dir.glob("**/*.csv"))
    
    success_count = 0
    for csv_file in files_to_convert:
        if convert_csv_to_parquet(csv_file):
            success_count += 1
            # Explicitly NOT deleting CSV yet until user approves broker update
            
    logging.info(f"Finished. Total converted: {success_count}/{len(files_to_convert)}")

if __name__ == "__main__":
    main()
