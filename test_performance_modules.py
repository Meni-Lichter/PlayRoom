"""
Comprehensive test suite for PerformanceCenter, PerformanceAnalyzer, and Predictor
Tests include file loading, data transformation, and integration with all modules
"""

from typing import List

import pytest
import pandas as pd
import os
from pathlib import Path
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from src.models import SalesRecord
from src.analysis import PerformanceAnalyzer, Predictor
from src.services import PerformanceCenter
from src.infrastructure import load_cbom, read_file
from src.infrastructure.data_transformer import transform_cbom_data
from src.utils import load_config, normalize_identifier


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create a temporary directory for test data files"""
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture(scope="session")
def config():
    """Load the actual configuration"""
    return load_config("config/config.json")


# ============================================================================
# Interactive Demo Main Function
# ============================================================================


def parse_ymbd_to_sales_records(ymbd_df) -> List[SalesRecord]:
    """Parse YMBD DataFrame to SalesRecord objects"""
    sales_records = []

    # Debug: Check for the specific 12NC
    target_12nc = "989606130501"
    print(f"\n[YMBD DEBUG] Looking for 12NC {target_12nc} in YMBD data...")
    print(f"[YMBD DEBUG] Total rows in YMBD: {len(ymbd_df)}")
    print(f"[YMBD DEBUG] Component column dtype: {ymbd_df['Component'].dtype}")
    print(f"[YMBD DEBUG] First 5 Component values: {ymbd_df['Component'].head().tolist()}")

    # Check if target exists in raw data
    raw_match = ymbd_df["Component"].astype(str).str.contains(target_12nc, na=False).any()
    print(f"[YMBD DEBUG] Target {target_12nc} found in raw Component column: {raw_match}")

    # Try multiple date formats
    date_formats = [
        "%Y-%m-%d %H:%M:%S",  # 2025-02-28 00:00:00
        "%Y-%m-%d",  # 2025-02-28
        "%m-%d-%Y",  # 02-28-2025
        "%d-%b-%Y",  # 28-Feb-2025
    ]

    matching_count = 0
    for _, row in ymbd_df.iterrows():
        try:
            date_str = str(row["Confirmed Delivery Date"]).strip()
            sales_date = None

            # Try each date format
            for fmt in date_formats:
                try:
                    sales_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

            if sales_date is None:
                print(f"Warning: Could not parse date '{date_str}', skipping row")
                continue

            # Handle Component value - ensure it's properly formatted as a 12-digit string
            component_value = row["Component"]
            if pd.isna(component_value):
                print(f"Warning: Empty Component value, skipping row")
                continue

            # Use normalize_identifier to remove hyphens, decimals, etc.
            twelve_nc = normalize_identifier(component_value)

            # Validate it's 12 digits after normalization
            if not twelve_nc or len(twelve_nc) != 12 or not twelve_nc.isdigit():
                # Pad with zeros if needed
                twelve_nc = twelve_nc.zfill(12)

            # DEBUG: Show normalization for first row
            if matching_count == 0:
                print(
                    f"[YMBD DEBUG] First 12NC normalization: '{component_value}' -> '{twelve_nc}'"
                )
                matching_count = -1  # Mark that we printed first one

            # Debug: Check if this is our target 12NC
            if twelve_nc == target_12nc:
                if matching_count == -1:
                    matching_count = 1
                else:
                    matching_count += 1
                if matching_count <= 3:  # Only print first few matches
                    print(
                        f"[YMBD DEBUG] ✓✓✓ Found {target_12nc}: date={sales_date}, qty={row['Component Quantity']}, raw='{component_value}'"
                    )

            quantity = int(row["Component Quantity"])
            sales_record = SalesRecord(
                twelve_nc=twelve_nc, room="UNKNOWN", quantity=quantity, date=sales_date
            )
            # We'll need room mapping from CBOM
            sales_records.append(sales_record)
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue

    print(f"[DEBUG] Total records found for {target_12nc}: {matching_count}")

    # Additional debug: Show summary of quantities found
    if matching_count > 0:
        target_quantities = [r.quantity for r in sales_records if r.twelve_nc == target_12nc]
        print(f"[YMBD DEBUG] Total quantity sum for {target_12nc}: {sum(target_quantities)}")
        print(f"[YMBD DEBUG] Number of records: {len(target_quantities)}")
        print(
            f"[YMBD DEBUG] Min qty: {min(target_quantities)}, Max qty: {max(target_quantities)}, Avg: {sum(target_quantities)/len(target_quantities):.1f}"
        )

    return sales_records


def parse_fit_cvi_to_sales_records(fit_cvi_df) -> List[SalesRecord]:
    """Parse FIT_CVI DataFrame to SalesRecord objects"""
    sales_records = []

    # Try multiple date formats
    date_formats = [
        "%Y-%m-%d %H:%M:%S",  # 2025-02-28 00:00:00
        "%Y-%m-%d",  # 2025-02-28
        "%d-%b-%Y",  # 28-Feb-2025
        "%m-%d-%Y",  # 02-28-2025
    ]

    for _, row in fit_cvi_df.iterrows():
        try:
            date_str = str(row["SD Item\nFSD"]).strip()
            sales_date = None

            # Try each date format
            for fmt in date_formats:
                try:
                    sales_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

            if sales_date is None:
                print(f"Warning: Could not parse date '{date_str}', skipping row")
                continue

            room = str(row["Characteristic\nCharacteristic Name"]).strip()
            quantity = int(row["(Self)\nValue from"])

            sales_record = SalesRecord(
                twelve_nc="ROOM_LEVEL_DATA", room=room, quantity=quantity, date=sales_date
            )
            sales_records.append(sales_record)
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue

    return sales_records


def merge_sales_data(
    ymbd_records, fit_cvi_records, room_mappings, nc12_mappings
) -> List[SalesRecord]:
    """Merge YMBD and FIT_CVI data into complete SalesRecord objects

    Important:
    - YMBD records are for 12NC sales (keep 12NC, lookup room from CBOM)
    - FIT_CVI records are for Room sales (keep Room, set 12NC to placeholder)
    - These are separate data sources and should not be mixed
    """
    sales_records = []

    # Debug: Check for specific 12NC
    target_12nc = "989606130501"
    print(f"\n[DEBUG] Checking if {target_12nc} exists in CBOM mappings...")

    # Create lookup dictionaries
    nc_to_rooms = {}
    for mapping in nc12_mappings:
        nc_to_rooms[mapping.twelve_nc] = list(mapping.rooms.keys())
        if mapping.twelve_nc == target_12nc:
            print(f"[DEBUG] Found {target_12nc} in CBOM! Rooms: {list(mapping.rooms.keys())}")

    if target_12nc not in nc_to_rooms:
        print(f"[DEBUG] WARNING: {target_12nc} NOT found in CBOM mappings!")
        print(f"[DEBUG] Available 12NCs in CBOM (first 10): {list(nc_to_rooms.keys())[:10]}")

    # Process YMBD records (12NC sales data)
    # These represent actual 12NC sales, so keep the 12NC
    ymbd_count_for_target = 0
    for record in ymbd_records:
        twelve_nc = record["twelve_nc"]

        # Debug: Count records for target 12NC
        if twelve_nc == target_12nc:
            ymbd_count_for_target += 1

        # Lookup room from CBOM for context (or use first room if 12NC used in multiple rooms)
        room = nc_to_rooms.get(twelve_nc, ["UNKNOWN"])[0]

        sales_records.append(
            SalesRecord(
                twelve_nc=twelve_nc, room=room, quantity=record["quantity"], date=record["date"]
            )
        )

    # Process FIT_CVI records (Room sales data)
    # These represent room sales, NOT 12NC sales, so keep room and use placeholder for 12NC
    for record in fit_cvi_records:
        room = record["room"]
        # Use placeholder 12NC since this is room-level data, not 12NC-level
        twelve_nc = "ROOM_LEVEL_DATA"

        sales_records.append(
            SalesRecord(
                twelve_nc=twelve_nc, room=room, quantity=record["quantity"], date=record["date"]
            )
        )

    print(f"[DEBUG] Created {ymbd_count_for_target} sales records for {target_12nc} from YMBD data")
    print(f"[DEBUG] Total sales records created: {len(sales_records)}")

    # Additional debug: Check dates for target
    if ymbd_count_for_target > 0:
        target_sales = [sr for sr in sales_records if sr.twelve_nc == target_12nc]
        target_dates = [sr.date for sr in target_sales]
        target_qtys = [sr.quantity for sr in target_sales]
        print(
            f"[MERGE DEBUG] Date range for {target_12nc}: {min(target_dates)} to {max(target_dates)}"
        )
        print(f"[MERGE DEBUG] Total quantity: {sum(target_qtys)}")
        print(f"[MERGE DEBUG] Sample records (first 5):")
        for sr in target_sales[:5]:
            print(f"  - {sr.date}: {sr.quantity} units (Room: {sr.room})")

    return sales_records


def interactive_demo():
    """Interactive demo to upload files and see the system in action"""
    from tkinter import Tk, filedialog

    print("=" * 80)
    print("🚀 Room-12NC Performance Center - Interactive Demo")
    print("=" * 80)

    # Load configuration
    print("\n[1/5] Loading configuration...")
    try:
        config = load_config("config/config.json")
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        return

    # Initialize file picker
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()

    # Upload CBOM file
    print("\n[2/5] Please select a CBOM Excel file...")
    cbom_path = filedialog.askopenfilename(
        title="Select CBOM Excel File",
        filetypes=[("Excel files", "*.xlsx *.xls *.xlsm"), ("All files", "*.*")],
    )

    if not cbom_path:
        print("✗ No CBOM file selected. Exiting.")
        root.destroy()
        return

    print(f"✓ Selected: {Path(cbom_path).name}")

    # Upload YMBD file
    print("\n[3/5] Please select a YMBD file (12NC sales data)...")
    ymbd_path = filedialog.askopenfilename(
        title="Select YMBD File",
        filetypes=[("CSV/Excel files", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
    )

    if not ymbd_path:
        print("✗ No YMBD file selected. Exiting.")
        root.destroy()
        return

    print(f"✓ Selected: {Path(ymbd_path).name}")

    # Upload FIT_CVI file
    print("\n[4/5] Please select a FIT_CVI file (Room sales data)...")
    fit_cvi_path = filedialog.askopenfilename(
        title="Select FIT_CVI File",
        filetypes=[("CSV/Excel files", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
    )

    if not fit_cvi_path:
        print("✗ No FIT_CVI file selected. Exiting.")
        root.destroy()
        return

    print(f"✓ Selected: {Path(fit_cvi_path).name}")

    root.destroy()

    # Process files
    print("\n[5/5] Processing files...")
    print("-" * 80)

    try:
        # Load CBOM
        print("\n📂 Loading CBOM data...")
        room_data, data_12nc = load_cbom(cbom_path, config)

        if room_data is None or data_12nc is None:
            print("✗ Failed to load CBOM data")
            return

        room_mappings, nc12_mappings = transform_cbom_data(room_data, data_12nc, config)
        print(f"✓ Loaded {len(room_mappings)} room and {len(nc12_mappings)} 12NC MAPPINGS!!!!")

        # Load YMBD
        print("\n📂 Loading YMBD data...")
        ymbd_df = read_file(Path(ymbd_path), "ymbd", header=0)
        if ymbd_df is None:
            print("✗ Failed to load YMBD file")
            return

        ymbd_records = parse_ymbd_to_sales_records(ymbd_df)
        print(f"✓ Loaded {len(ymbd_records)} YMBD records")

        # Load FIT_CVI
        print("\n📂 Loading FIT_CVI data...")
        fit_cvi_df = read_file(Path(fit_cvi_path), "fit_cvi", header=0)
        if fit_cvi_df is None:
            print("✗ Failed to load FIT_CVI file")
            return

        fit_cvi_records = parse_fit_cvi_to_sales_records(fit_cvi_df)
        print(f"✓ Loaded {len(fit_cvi_records)} FIT_CVI records")

        # Merge sales data
        print("\n🔄 Merging sales data...")
        sales_records = merge_sales_data(
            ymbd_records, fit_cvi_records, room_mappings, nc12_mappings
        )
        print(f"✓ Created {len(sales_records)} total sales records")

        # Initialize Performance Center
        print("\n🏢 Initializing Performance Center...")
        pc = PerformanceCenter(
            sales_data=sales_records, room_mappings=room_mappings, nc12_mappings=nc12_mappings
        )

        # Display summary
        stats = pc.get_summary_stats()
        print("\n" + "=" * 80)
        print("📊 SYSTEM SUMMARY")
        print("=" * 80)
        print(f"Total Sales Records:  {stats['total_sales_records']}")
        print(f"Total Rooms in CBOM:  {stats['total_rooms_in_cbom']}")
        print(f"Total 12NCs in CBOM:  {stats['total_12ncs_in_cbom']}")
        print(
            f"Date Range:           {stats['date_range']['earliest']} to {stats['date_range']['latest']}"
        )

        # Demo: Analyze a 12NC
        print("\n" + "=" * 80)
        print("📈 DEMO: ANALYZING 12NC PERFORMANCE")
        print("=" * 80)

        # Get first 12NC
        if len(nc12_mappings) > 0:
            demo_12nc = str(989606130501)
            print(f"\nAnalyzing 12NC: {demo_12nc}")

            # DEBUG: Check how many sales records exist for this 12NC
            target_records = [sr for sr in sales_records if sr.twelve_nc == demo_12nc]
            print(f"[ANALYSIS DEBUG] Found {len(target_records)} sales records for {demo_12nc}")
            if len(target_records) > 0:
                print(f"[ANALYSIS DEBUG] First 3 records:")
                for sr in target_records[:3]:
                    print(f"  - Date: {sr.date}, Qty: {sr.quantity}, Room: {sr.room}")
            else:
                print(
                    f"[ANALYSIS DEBUG] Available 12NCs in sales records (first 10): {list(set([sr.twelve_nc for sr in sales_records]))[:10]}"
                )

            performance = pc.analyze_12nc_performance(
                twelve_nc=demo_12nc, lookback_years=10, granularity="monthly"
            )

            print(f"\n  Total Quantity (10 years): {performance.total}")
            print(f"  Average per Period:       {performance.average:.2f}")
            print(f"  Number of Periods:        {performance.period_count}")

            if len(performance.periods) > 0:
                print(f"\n  Recent Periods:")
                for period in performance.periods[-6:]:  # Last 6 periods
                    print(f"    {period.label}: {period.quantity}")

            # Demo: Predictions with all three methods
            print("\n" + "=" * 80)
            print("🔮 DEMO: PREDICTION METHODS COMPARISON")
            print("=" * 80)

            methods = [
                ("avg_same_period_previous_years", "Average of Same Period in Previous Years"),
                ("avg_last_n_periods", "Average of Last 11 Periods"),
                ("same_period_last_year", "Same Period from Last Year"),
            ]

            print(f"\nPredictions for 12NC: {demo_12nc}")
            print(f"Buffer: 10%\n")

            for method_name, method_desc in methods:
                prediction = pc.predict_12nc_demand(
                    twelve_nc=demo_12nc, method=method_name, buffer_percentage=10.0
                )

                print(f"\n📌 {method_desc}")
                print(f"   Period:               {prediction.period_label}")
                print(f"   Baseline Prediction:  {prediction.baseline:.2f}")
                print(f"   With Buffer (10%):    {prediction.predicted_quantity:.2f}")
                print(f"   Buffer Amount:        {prediction.buffer_amount:.2f}")

        # Demo: Analyze a Room
        print("\n" + "=" * 80)
        print("🏠 DEMO: ANALYZING ROOM PERFORMANCE")
        print("=" * 80)

        if len(room_mappings) > 0:
            demo_room = room_mappings[0].room
            print(f"\nAnalyzing Room: {demo_room}")

            # Show components
            room_components = pc.get_room_components(demo_room)
            if room_components:
                print(f"\n  Components in this room:")
                for nc, qty in room_components.twelve_ncs.items():
                    print(f"    {nc}: {qty} units")

            room_performance = pc.analyze_room_performance(
                room=demo_room, lookback_years=10, granularity="monthly"
            )

            print(f"\n  Total Quantity (10 years): {room_performance.total}")
            print(f"  Average per Period:       {room_performance.average:.2f}")
            print(f"  Number of Periods:        {room_performance.period_count}")

            # Predict room demand
            room_prediction = pc.predict_room_demand(
                room=demo_room, method="avg_same_period_previous_years", buffer_percentage=10.0
            )

            print(f"\n  🔮 Prediction for next period ({room_prediction.period_label}):")
            print(f"     Baseline:    {room_prediction.baseline:.2f}")
            print(f"     With Buffer: {room_prediction.predicted_quantity:.2f}")

        print("\n" + "=" * 80)
        print("✅ Demo completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        import traceback

        traceback.print_exc()


# ============================================================================
# Run Interactive Demo
# ============================================================================

if __name__ == "__main__":
    interactive_demo()
