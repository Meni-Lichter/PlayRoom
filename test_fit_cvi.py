"""Test script for FIT_CVI reading functionality"""

from src.utils import load_config
from src.infrastructure import read_file
from tkinter import Tk, filedialog
from pathlib import Path


def main():
    print("=" * 80)
    print("FIT_CVI Reader Test")
    print("=" * 80)

    # Load configuration
    config = load_config("config/config.json")
    print("\nConfiguration loaded successfully")
    print("\nFIT_CVI Settings:")
    fit_cvi_config = config.get("fit_cvi", {})
    for key, value in fit_cvi_config.items():
        print(f"  {key}: {value}")

    # Initialize file picker
    root = Tk()
    root.withdraw()

    print("\n" + "-" * 80)
    print("Please select a FIT_CVI Excel file...")
    fit_cvi_path = filedialog.askopenfilename(
        title="Select FIT_CVI Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
    )

    if not fit_cvi_path:
        print("No file selected. Exiting.")
        return

    print(f"\nReading file: {fit_cvi_path}")
    print("-" * 80)

    if isinstance(fit_cvi_path, str):
        fit_cvi_path = Path(fit_cvi_path)

    # Process FIT_CVI file
    df = read_file(fit_cvi_path, file_type="fit_cvi", header=0)

    if df is not None:
        print(f"\n[OK] Successfully read file")
        print(f"  Shape: {df.shape} (rows: {df.shape[0]}, columns: {df.shape[1]})")
        print(f"  Columns: {list(df.columns)}")

        print("\n--- First 5 Rows ---")
        print(df.head())

        print("\n--- Data Types ---")
        print(df.dtypes)

        print("\n--- Sample Statistics ---")
        numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
        if len(numeric_cols) > 0:
            print(f"Numeric columns found: {list(numeric_cols)}")
            print(df[numeric_cols].describe())

        # Check for expected FIT_CVI columns
        print("\n--- Column Validation ---")
        expected_cols = fit_cvi_config.get("columns", {})
        if expected_cols:
            print("Expected columns from config:")
            for key, col_name in expected_cols.items():
                exists = col_name in df.columns
                status = "[OK]" if exists else "[MISSING]"
                print(f"  {status} {key}: '{col_name}'")

        # Show how date column is being read
        print("\n" + "=" * 80)
        print("--- DATE COLUMN ANALYSIS ---")
        print("=" * 80)
        date_col_name = fit_cvi_config.get("columns", {}).get("date", "")
        if date_col_name and date_col_name in df.columns:
            print(f"\nDate Column: '{date_col_name}'")
            print(f"Data Type: {df[date_col_name].dtype}")
            print(f"Total rows: {len(df[date_col_name])}")
            print(f"Non-null rows: {df[date_col_name].notna().sum()}")
            print(f"Null rows: {df[date_col_name].isna().sum()}")
            
            print("\n--- First 10 Date Values (as read from file) ---")
            for idx, val in enumerate(df[date_col_name].head(10), 1):
                print(f"  {idx}. {repr(val)} (type: {type(val).__name__})")
            
            print("\n--- Last 5 Date Values (as read from file) ---")
            for idx, val in enumerate(df[date_col_name].tail(5), len(df) - 4):
                print(f"  {idx}. {repr(val)} (type: {type(val).__name__})")
            
            # Show unique date formats/patterns
            print("\n--- Sample of Unique Date Values (first 15) ---")
            unique_dates = df[date_col_name].dropna().unique()[:15]
            for i, date_val in enumerate(unique_dates, 1):
                print(f"  {i}. {repr(date_val)}")
            
            print(f"\nTotal unique date values: {len(df[date_col_name].dropna().unique())}")
            
            # Check if values are strings
            sample_non_null = df[date_col_name].dropna().iloc[0] if len(df[date_col_name].dropna()) > 0 else None
            if sample_non_null is not None:
                print(f"\nSample value details:")
                print(f"  Value: {repr(sample_non_null)}")
                print(f"  Type: {type(sample_non_null)}")
                if hasattr(sample_non_null, '__len__'):
                    print(f"  Length: {len(str(sample_non_null))}")
                print(f"  String representation: '{str(sample_non_null)}'")
        else:
            print(f"\n[WARNING] Date column '{date_col_name}' not found in DataFrame")
        
        print("\n" + "=" * 80)
        print("\n[OK] Test completed successfully!")
    else:
        print("\n[ERROR] Failed to read file")

    # Test with header=None (no headers)
    print("\n" + "=" * 80)
    print("--- Test 2: Reading with header=None (no column names) ---")
    df_no_header = read_file(fit_cvi_path, file_type="fit_cvi", header=None)

    if df_no_header is not None:
        print(f"[OK] Successfully read file without headers")
        print(f"  Shape: {df_no_header.shape}")
        print(f"  Columns: {list(df_no_header.columns)}")
        print("\n--- First 3 Rows ---")
        print(df_no_header.head(3))


if __name__ == "__main__":
    main()
