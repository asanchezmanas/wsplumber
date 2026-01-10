# scripts/data_slicer.py
"""
Data Slicer - Utility to extract date ranges from large CSV files.
Optimized for 3GB+ files (line-by-line processing).

Usage:
    python scripts/data_slicer.py --start 20080915 --end 20081015 --output lehman_2008.csv
"""

import argparse
import os

def slice_csv(input_path, output_path, start_date, end_date):
    """
    Extracts lines where the date is between start_date and end_date.
    Format of date in CSV is assumed to be YYYYMMDD at the start of the line.
    """
    print(f"Slicing {input_path} from {start_date} to {end_date}...")
    
    count = 0
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        
        # Write header
        header = f_in.readline()
        f_out.write(header)
        
        for line in f_in:
            if not line.strip(): continue
            # First 8 chars are YYYYMMDD
            line_date = line[:8]
            
            if start_date <= line_date <= end_date:
                f_out.write(line)
                count += 1
                if count <= 5:
                    print(f"Sample match: {line.strip()}")
            
    print(f"Extraction complete! Saved {count} ticks to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slice large CSV by date range.")
    parser.add_argument("--input", default="2026.1.5EURUSD(3)_TICK_UTCPlus02-TICK-No Session.csv", help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--start", required=True, help="Start date YYYYMMDD")
    parser.add_argument("--end", required=True, help="End date YYYYMMDD")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
    else:
        slice_csv(args.input, args.output, args.start, args.end)
