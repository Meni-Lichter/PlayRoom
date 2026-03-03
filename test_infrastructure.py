"""
Infrastructure Test Suite for Room_12NC_PerformanceCenter
Tests data loading and transformation performance and accuracy.
"""

import pytest
import pandas as pd
import time
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Optional, Tuple

# Import infrastructure modules
from src.infrastructure.data_loaders import load_cbom, read_file
from src.infrastructure.data_transformer import (
    transform_cbom_data,
    parse_ymbd_to_sales_records,
    parse_fit_cvi_to_sales_records,
)
from src.models.mapping import Room, TwelveNC
from src.models.sales_record import SalesRecord
from src.utils.config_util import load_config


# ============================================================================
# FILE PICKER UTILITIES
# ============================================================================


def pick_file(title: str, filetypes: list) -> Optional[str]:
    """Open file picker dialog"""
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()

    return file_path if file_path else None


def get_test_files() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Interactive file selection for test files"""
    print("\n" + "=" * 80)
    print("📂 FILE SELECTION FOR INFRASTRUCTURE TESTS")
    print("=" * 80)

    print("\n1️⃣  Select CBOM file (Excel)...")
    cbom_file = pick_file(
        "Select CBOM File", [("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
    )
    if cbom_file:
        print(f"   ✓ Selected: {Path(cbom_file).name}")
    else:
        print("   ⚠ Skipped")

    print("\n2️⃣  Select YMBD file (Excel)...")
    ymbd_file = pick_file(
        "Select YMBD File", [("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
    )
    if ymbd_file:
        print(f"   ✓ Selected: {Path(ymbd_file).name}")
    else:
        print("   ⚠ Skipped")

    print("\n3️⃣  Select FIT/CVI file (Excel)...")
    fit_file = pick_file(
        "Select FIT/CVI File", [("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
    )
    if fit_file:
        print(f"   ✓ Selected: {Path(fit_file).name}")
    else:
        print("   ⚠ Skipped")

    print("\n" + "=" * 80 + "\n")

    return cbom_file, ymbd_file, fit_file


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def test_files():
    """Session-scoped fixture for test files"""
    return get_test_files()


@pytest.fixture
def cbom_file(test_files):
    """CBOM file path fixture"""
    return test_files[0]


@pytest.fixture
def ymbd_file(test_files):
    """YMBD file path fixture"""
    return test_files[1]


@pytest.fixture
def fit_file(test_files):
    """FIT/CVI file path fixture"""
    return test_files[2]


@pytest.fixture(scope="session")
def config():
    """Load configuration"""
    return load_config()


# ============================================================================
# DATA LOADER TESTS
# ============================================================================


class TestDataLoaders:
    """Test suite for data loading functions"""

    def test_load_cbom(self, cbom_file, config):
        """Test CBOM file loading performance and structure"""
        if not cbom_file:
            pytest.skip("No CBOM file provided")

        print("\n" + "=" * 80)
        print("🧪 TEST: CBOM File Loading")
        print("=" * 80)

        start_time = time.perf_counter()

        # Load CBOM file
        room_data, data_12nc = load_cbom(cbom_file, config)

        end_time = time.perf_counter()
        load_time = (end_time - start_time) * 1000  # ms

        # Assertions
        assert room_data is not None, "room_data should not be None"
        assert data_12nc is not None, "data_12nc should not be None"
        assert isinstance(room_data, dict), "room_data should be a dictionary"
        assert isinstance(data_12nc, dict), "data_12nc should be a dictionary"
        assert len(room_data) > 0, "Should load at least one room"
        assert len(data_12nc) > 0, "Should load at least one 12NC"

        # Performance metrics
        total_items = len(room_data) + len(data_12nc)
        throughput = total_items / (load_time / 1000) if load_time > 0 else 0

        print(f"\n✓ CBOM file loaded successfully")
        print(f"  - File: {Path(cbom_file).name}")
        print(f"  - Load time: {load_time:.2f} ms")
        print(f"  - Rooms loaded: {len(room_data):,}")
        print(f"  - 12NCs loaded: {len(data_12nc):,}")
        print(f"  - Throughput: {throughput:.2f} items/sec")

        # Data structure validation
        print(f"\n📊 Data Structure:")
        # Check first room
        first_room_key = next(iter(room_data.keys()))
        first_room_data = room_data[first_room_key]
        print(f"  - Sample room: {first_room_key}")
        print(f"    Type: {type(first_room_data)}")
        print(f"    12NCs in room: {len(first_room_data)}")

        # Check first 12NC
        first_12nc_key = next(iter(data_12nc.keys()))
        first_12nc_data = data_12nc[first_12nc_key]
        print(f"  - Sample 12NC: {first_12nc_key}")
        print(f"    Type: {type(first_12nc_data)}")
        print(f"    Rooms with 12NC: {len(first_12nc_data)}")

        print("\n" + "=" * 80)

    def test_load_ymbd(self, ymbd_file):
        """Test YMBD file loading performance"""
        if not ymbd_file:
            pytest.skip("No YMBD file provided")

        print("\n" + "=" * 80)
        print("🧪 TEST: YMBD File Loading")
        print("=" * 80)

        start_time = time.perf_counter()

        # Load YMBD file
        ymbd_df = read_file(ymbd_file, "ymbd", header=0)

        end_time = time.perf_counter()
        load_time = (end_time - start_time) * 1000

        # Assertions
        assert ymbd_df is not None, "DataFrame should not be None"
        assert isinstance(ymbd_df, pd.DataFrame), "Should return pandas DataFrame"
        assert len(ymbd_df) > 0, "DataFrame should not be empty"

        # Performance metrics
        rows = len(ymbd_df)
        throughput = rows / (load_time / 1000) if load_time > 0 else 0

        print(f"\n✓ YMBD file loaded successfully")
        print(f"  - File: {Path(ymbd_file).name}")
        print(f"  - Load time: {load_time:.2f} ms")
        print(f"  - Rows loaded: {rows:,}")
        print(f"  - Columns: {len(ymbd_df.columns)}")
        print(f"  - Throughput: {throughput:.2f} rows/sec")

        print(f"\n📊 Data Quality:")
        print(f"  - Null values: {ymbd_df.isnull().sum().sum()}")
        print(f"  - Duplicate rows: {ymbd_df.duplicated().sum()}")
        print(f"  - Column names: {list(ymbd_df.columns[:5])}")

        print("\n" + "=" * 80)

    def test_load_fit_cvi(self, fit_file):
        """Test FIT/CVI file loading performance"""
        if not fit_file:
            pytest.skip("No FIT/CVI file provided")

        print("\n" + "=" * 80)
        print("🧪 TEST: FIT/CVI File Loading")
        print("=" * 80)

        start_time = time.perf_counter()

        # Load FIT/CVI file
        fit_df = read_file(fit_file, "fit_cvi", header=0)

        end_time = time.perf_counter()
        load_time = (end_time - start_time) * 1000

        # Assertions
        assert fit_df is not None, "DataFrame should not be None"
        assert isinstance(fit_df, pd.DataFrame), "Should return pandas DataFrame"
        assert len(fit_df) > 0, "DataFrame should not be empty"

        # Performance metrics
        rows = len(fit_df)
        throughput = rows / (load_time / 1000) if load_time > 0 else 0

        print(f"\n✓ FIT/CVI file loaded successfully")
        print(f"  - File: {Path(fit_file).name}")
        print(f"  - Load time: {load_time:.2f} ms")
        print(f"  - Rows loaded: {rows:,}")
        print(f"  - Columns: {len(fit_df.columns)}")
        print(f"  - Throughput: {throughput:.2f} rows/sec")

        print(f"\n📊 Data Quality:")
        print(f"  - Null values: {fit_df.isnull().sum().sum()}")
        print(f"  - Duplicate rows: {fit_df.duplicated().sum()}")
        print(f"  - Column names: {list(fit_df.columns[:5])}")

        print("\n" + "=" * 80)


# ============================================================================
# DATA TRANSFORMER TESTS
# ============================================================================


class TestDataTransformers:
    """Test suite for data transformation functions"""

    def test_transform_cbom_data(self, cbom_file, config):
        """Test CBOM data transformation to Room and TwelveNC objects"""
        if not cbom_file:
            pytest.skip("No CBOM file provided")

        print("\n" + "=" * 80)
        print("🧪 TEST: CBOM Data Transformation")
        print("=" * 80)

        # Load and transform CBOM
        print("\n📥 Loading CBOM...")
        room_data, data_12nc = load_cbom(cbom_file, config)
        print(f"  ✓ Loaded {len(room_data)} rooms, {len(data_12nc)} 12NCs")

        print("\n🔄 Transforming data...")
        start_time = time.perf_counter()
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        transform_time = (time.perf_counter() - start_time) * 1000

        # Validation
        assert rooms and nc12s, "Should create rooms and 12NCs"
        assert all(isinstance(r, Room) for r in rooms), "All should be Room objects"
        assert all(isinstance(nc, TwelveNC) for nc in nc12s), "All should be TwelveNC objects"
        assert all(r.id for r in rooms), "All rooms should have IDs"
        assert all(
            nc.id and len(nc.id) == 12 for nc in nc12s
        ), "All 12NCs should have valid 12-digit IDs"

        # Metrics
        print(f"\n✓ CBOM data transformed successfully")
        print(f"  - Transform time: {transform_time:.2f} ms")
        print(f"  - Room objects created: {len(rooms)}")
        print(f"  - TwelveNC objects created: {len(nc12s)}")
        print(
            f"  - Throughput: {(len(rooms) + len(nc12s)) / (transform_time / 1000):.2f} objects/sec"
        )

        # Sample data
        print(f"\n📦 Sample Room Object:")
        r = rooms[0]
        print(f"  - Room ID: {r.id}")
        print(
            f"  - Description: {r.description[:50]}..."
            if len(r.description) > 50
            else f"  - Description: {r.description}"
        )
        print(f"  - Components: {len(r.twelve_ncs)}")
        print(f"  - Total items: {r.total_items}")

        print(f"\n🔢 Sample 12NC Object:")
        nc = nc12s[0]
        print(f"  - 12NC ID: {nc.id}")
        print(
            f"  - Description: {nc.description[:50]}..."
            if len(nc.description) > 50
            else f"  - Description: {nc.description}"
        )
        print(f"  - IGT: {nc.igt}")
        print(f"  - Rooms: {len(nc.rooms)}")
        print(f"  - Total items: {nc.total_items}")

        print(f"\n🔍 Validation:")
        print(f"  ✓ Rooms with valid IDs: {len(rooms)}/{len(rooms)}")
        print(f"  ✓ 12NCs with valid IDs: {len(nc12s)}/{len(nc12s)}")

        print("\n" + "=" * 80)

    def test_parse_ymbd_to_sales_records(self, cbom_file, ymbd_file, config):
        """Test YMBD parsing and linking to TwelveNC objects"""
        if not cbom_file or not ymbd_file:
            pytest.skip("Need both CBOM and YMBD files")

        print("\n" + "=" * 80)
        print("🧪 TEST: YMBD Sales Record Parsing")
        print("=" * 80)

        # Setup: Load and transform CBOM
        print("\n📥 Setup: Loading CBOM...")
        room_data, data_12nc = load_cbom(cbom_file, config)
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        print(f"  ✓ Created {len(nc12s)} 12NC objects")

        # Load and parse YMBD data
        print("\n📥 Loading YMBD...")
        ymbd_df = read_file(ymbd_file, "ymbd", header=0)
        print(f"  ✓ Loaded {len(pd.DataFrame(ymbd_df))} YMBD rows")

        print("\n🔄 Parsing YMBD to sales records...")
        start_time = time.perf_counter()
        updated_nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)
        parse_time = (time.perf_counter() - start_time) * 1000

        # Assertions
        assert updated_nc12s is not None, "Should not return None"
        assert len(updated_nc12s) == len(nc12s), "Should return same number of 12NCs"

        # Metrics
        nc12s_with_sales = [nc for nc in updated_nc12s if len(nc.sales_history) > 0]
        total_sales = sum(len(nc.sales_history) for nc in updated_nc12s)

        print(f"\n✓ YMBD data parsed successfully")
        print(f"  - Parse time: {parse_time:.2f} ms")
        print(f"  - 12NCs updated: {len(nc12s_with_sales)}/{len(nc12s)}")
        print(f"  - Total sales records: {total_sales:,}")
        if nc12s_with_sales:
            print(f"  - Avg records per 12NC: {total_sales/len(nc12s_with_sales):.1f}")
        print(f"  - Throughput: {len(pd.DataFrame(ymbd_df)) / (parse_time / 1000):.2f} rows/sec")

        # Coverage
        coverage = (len(nc12s_with_sales) / len(nc12s) * 100) if nc12s else 0
        print(f"\n📊 Coverage Analysis:")
        print(f"  - Match rate: {coverage:.1f}%")
        print(f"  - Matched: {len(nc12s_with_sales)}")
        print(f"  - Unmatched: {len(nc12s) - len(nc12s_with_sales)}")

        # Validation
        if nc12s_with_sales:
            sample = nc12s_with_sales[0]
            print(f"\n💰 Sample Sales Data:")
            print(f"  - 12NC: {sample.id}")
            print(f"  - Sales records: {len(sample.sales_history)}")
            if sample.sales_history:
                sr = sample.sales_history[0]
                print(f"    └─ Date: {sr.date}, Qty: {sr.quantity}")

            # Validate first 5
            for nc in nc12s_with_sales[:5]:
                for record in nc.sales_history:
                    assert isinstance(record, SalesRecord), "Should be SalesRecord object"
                    assert hasattr(record, "date") and record.date, "Should have date"
                    assert (
                        hasattr(record, "quantity") and record.quantity > 0
                    ), "Should have positive quantity"

        print("\n" + "=" * 80)

    def test_parse_fit_cvi_to_sales_records(self, cbom_file, fit_file, config):
        """Test FIT/CVI parsing and linking to Room objects"""
        if not cbom_file or not fit_file:
            pytest.skip("Need both CBOM and FIT/CVI files")

        print("\n" + "=" * 80)
        print("🧪 TEST: FIT/CVI Sales Record Parsing")
        print("=" * 80)

        # Setup: Load and transform CBOM first
        print("\n📥 Setup: Loading CBOM...")
        room_data, data_12nc = load_cbom(cbom_file, config)
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        print(f"  ✓ Created {len(rooms)} room objects")

        # Load and parse FIT/CVI data
        print("\n📥 Loading FIT/CVI...")
        fit_df = read_file(fit_file, "fit_cvi", header=0)
        print(f"  ✓ Loaded {len(pd.DataFrame(fit_df))} FIT/CVI rows")

        print("\n🔄 Parsing FIT/CVI to sales records...")
        start_time = time.perf_counter()
        updated_rooms = parse_fit_cvi_to_sales_records(rooms, fit_df)
        end_time = time.perf_counter()
        parse_time = (end_time - start_time) * 1000

        # Assertions
        assert updated_rooms is not None, "Should not return None"
        assert len(updated_rooms) == len(rooms), "Should return same number of rooms"
        assert all(
            isinstance(room, Room) for room in updated_rooms
        ), "All items should be Room objects"

        # Extract all sales records from rooms
        all_sales_records = []
        for room in updated_rooms:
            all_sales_records.extend(room.sales_history)

        # Metrics
        rooms_with_sales = [r for r in updated_rooms if len(r.sales_history) > 0]
        throughput = len(pd.DataFrame(fit_df)) / (parse_time / 1000) if parse_time > 0 else 0

        print(f"\n✓ FIT/CVI data parsed successfully")
        print(f"  - Parse time: {parse_time:.2f} ms")
        print(f"  - Rooms updated: {len(rooms_with_sales)}/{len(updated_rooms)}")
        print(f"  - Total sales records: {len(all_sales_records):,}")
        print(f"  - Throughput: {throughput:.2f} rows/sec")

        # Validation
        if all_sales_records:
            assert all(
                isinstance(sr, SalesRecord) for sr in all_sales_records
            ), "All should be SalesRecord objects"
            assert all(
                hasattr(sr, "date") and sr.date for sr in all_sales_records[:10]
            ), "Records should have dates"
            assert all(
                sr.quantity > 0 for sr in all_sales_records[:10]
            ), "Quantities should be positive"

            print(f"\n📊 Validation:")
            print(f"  ✓ All sales records valid")
            print(f"  ✓ Avg records/room: {len(all_sales_records)/len(rooms_with_sales):.1f}")

        print("\n" + "=" * 80)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """End-to-end integration tests"""

    def test_complete_pipeline(self, cbom_file, ymbd_file, fit_file, config):
        """Test complete data loading and transformation pipeline"""
        if not cbom_file:
            pytest.skip("Need CBOM file for integration test")

        print("\n" + "=" * 80)
        print("🧪 INTEGRATION TEST: Complete Data Pipeline")
        print("=" * 80)

        start_time = time.perf_counter()

        # Step 1: Load and transform CBOM
        print("\n1️⃣  Loading and transforming CBOM...")
        room_data, data_12nc = load_cbom(cbom_file, config)
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        print(f"   ✓ Created {len(rooms)} rooms and {len(nc12s)} 12NCs")

        # Validate CBOM objects
        assert all(isinstance(r, Room) for r in rooms), "All rooms should be Room objects"
        assert all(isinstance(nc, TwelveNC) for nc in nc12s), "All 12NCs should be TwelveNC objects"
        assert all(r.id for r in rooms), "All rooms should have IDs"
        assert all(
            len(r.componenets) > 0 for r in rooms if not r.id.startswith("FITxxxx")
        ), "Rooms should have components"

        # Step 2: Load and process YMBD (if available)
        ymbd_coverage = 0
        if ymbd_file:
            print("\n2️⃣  Loading and processing YMBD...")
            ymbd_df = read_file(ymbd_file, "ymbd", header=0)
            nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)
            ymbd_coverage = sum(1 for nc in nc12s if len(nc.sales_history) > 0)
            print(f"   ✓ Updated {ymbd_coverage}/{len(nc12s)} 12NCs with sales data")

            # Validate YMBD data
            if ymbd_coverage > 0:
                all_ymbd_records = [sr for nc in nc12s for sr in nc.sales_history]
                assert all(
                    isinstance(sr, SalesRecord) for sr in all_ymbd_records
                ), "All should be SalesRecord objects"
                assert all(
                    hasattr(sr, "date") and sr.date for sr in all_ymbd_records
                ), "All should have dates"
                assert all(
                    sr.quantity > 0 for sr in all_ymbd_records
                ), "All quantities should be positive"
        else:
            print("\n2️⃣  Skipping YMBD (no file provided)")

        # Step 3: Load and process FIT/CVI (if available)
        fit_coverage = 0
        if fit_file:
            print("\n3️⃣  Loading and processing FIT/CVI...")
            fit_df = read_file(fit_file, "fit_cvi", header=0)
            rooms = parse_fit_cvi_to_sales_records(rooms, fit_df)
            fit_coverage = sum(1 for r in rooms if len(r.sales_history) > 0)
            all_fit_records = [sr for r in rooms for sr in r.sales_history]
            print(
                f"   ✓ Updated {fit_coverage}/{len(rooms)} rooms with {len(all_fit_records)} sales records"
            )

            # Validate FIT/CVI data
            if all_fit_records:
                assert all(
                    isinstance(sr, SalesRecord) for sr in all_fit_records
                ), "All should be SalesRecord objects"
                assert all(
                    hasattr(sr, "date") and sr.date for sr in all_fit_records
                ), "All should have dates"
                assert all(
                    sr.quantity > 0 for sr in all_fit_records
                ), "All quantities should be positive"
        else:
            print("\n3️⃣  Skipping FIT/CVI (no file provided)")

        end_time = time.perf_counter()
        pipeline_time = (end_time - start_time) * 1000

        # Calculate totals
        total_ymbd_records = sum(len(nc.sales_history) for nc in nc12s)
        total_fit_records = sum(len(r.sales_history) for r in rooms)
        total_sales_records = total_ymbd_records + total_fit_records

        print(f"\n✅ PIPELINE COMPLETE")
        print(f"  - Total time: {pipeline_time:.2f} ms")
        print(f"  - Rooms: {len(rooms)}")
        print(f"  - 12NCs: {len(nc12s)}")
        print(f"  - YMBD sales records: {total_ymbd_records:,}")
        print(f"  - FIT/CVI sales records: {total_fit_records:,}")
        print(f"  - Total sales records: {total_sales_records:,}")

        # Final object validation
        print(f"\n🔍 Final Object Validation:")

        # Room validation
        invalid_rooms = [r for r in rooms if not r.id or not isinstance(r, Room)]
        print(
            f"  {'✓' if not invalid_rooms else '✗'} All rooms valid: {len(rooms) - len(invalid_rooms)}/{len(rooms)}"
        )
        assert not invalid_rooms, f"Found {len(invalid_rooms)} invalid rooms"

        # 12NC validation
        invalid_12ncs = [
            nc for nc in nc12s if not nc.id or len(nc.id) != 12 or not isinstance(nc, TwelveNC)
        ]
        print(
            f"  {'✓' if not invalid_12ncs else '✗'} All 12NCs valid: {len(nc12s) - len(invalid_12ncs)}/{len(nc12s)}"
        )
        assert not invalid_12ncs, f"Found {len(invalid_12ncs)} invalid 12NCs"

        # Sales data validation
        if ymbd_coverage > 0:
            print(
                f"  ✓ YMBD coverage: {ymbd_coverage}/{len(nc12s)} 12NCs ({ymbd_coverage/len(nc12s)*100:.1f}%)"
            )

            # Show uncovered 12NCs
            uncovered_12ncs = [nc for nc in nc12s if len(nc.sales_history) == 0]
            if uncovered_12ncs and len(uncovered_12ncs) <= 10:
                print(f"\n  ⚠️  Uncovered 12NCs ({len(uncovered_12ncs)}):")
                for nc in uncovered_12ncs[:10]:
                    print(f"     - {nc.id}: {nc.description[:50]}")
            elif uncovered_12ncs:
                print(f"\n  ⚠️  Uncovered 12NCs ({len(uncovered_12ncs)}):")
                for nc in uncovered_12ncs[:5]:
                    print(f"     - {nc.id}: {nc.description[:50]}")
                print(f"     ... and {len(uncovered_12ncs) - 5} more")

        if fit_coverage > 0:
            print(
                f"  ✓ FIT/CVI coverage: {fit_coverage}/{len(rooms)} rooms ({fit_coverage/len(rooms)*100:.1f}%)"
            )

            # Show uncovered rooms
            uncovered_rooms = [r for r in rooms if len(r.sales_history) == 0]
            if uncovered_rooms and len(uncovered_rooms) <= 10:
                print(f"\n  ⚠️  Uncovered Rooms ({len(uncovered_rooms)}):")
                for room in uncovered_rooms[:10]:
                    print(f"     - {room.id}: {room.description[:50]}")
            elif uncovered_rooms:
                print(f"\n  ⚠️  Uncovered Rooms ({len(uncovered_rooms)}):")
                for room in uncovered_rooms[:5]:
                    print(f"     - {room.id}: {room.description[:50]}")
                print(f"     ... and {len(uncovered_rooms) - 5} more")

        print(f"\n💡 Possible Reasons for Missing Coverage:")
        print(f"   • Different ID formats between files (normalization mismatch)")
        print(f"   • Obsolete or not-yet-released items in CBOM")
        print(f"   • Placeholder SKUs in bills of material")
        print(f"   • Historical items with no recent sales activity")

        # Object lifecycle tracking
        print(f"\n📊 OBJECT LIFECYCLE TRACKING:")
        print(f"\n  🔹 Sample 12NC Object Lifecycle:")

        # Find a 12NC with YMBD data
        sample_12nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                sample_12nc = nc
                break

        if sample_12nc:
            print(f"     ID: {sample_12nc.id}")
            print(f"     Description: {sample_12nc.description[:60]}...")
            print(
                f"     After CBOM: rooms={len(sample_12nc.rooms)}, items={sample_12nc.total_items}"
            )
            print(f"     After YMBD: sales_records={len(sample_12nc.sales_history)}")
            if sample_12nc.sales_history:
                dates = sorted(set(sr.date for sr in sample_12nc.sales_history))
                total_qty = sum(sr.quantity for sr in sample_12nc.sales_history)
                print(f"               date_range=[{dates[0]}, {dates[-1]}], total_qty={total_qty}")
        else:
            sample_12nc = nc12s[0] if nc12s else None
            if sample_12nc:
                print(f"     ID: {sample_12nc.id}")
                print(f"     Description: {sample_12nc.description[:60]}...")
                print(
                    f"     After CBOM: rooms={len(sample_12nc.rooms)}, items={sample_12nc.total_items}"
                )
                print(f"     After YMBD: sales_records=0 (no matching sales data)")

        print(f"\n  🔹 Sample Room Object Lifecycle:")

        # Find a room with FIT/CVI data
        sample_room = None
        for room in rooms:
            if len(room.sales_history) > 0:
                sample_room = room
                break

        if sample_room:
            print(f"     ID: {sample_room.id}")
            print(f"     Description: {sample_room.description[:60]}...")
            print(
                f"     After CBOM: components={len(sample_room.componenets)}, items={sample_room.total_items}"
            )
            print(f"     After FIT/CVI: sales_records={len(sample_room.sales_history)}")
            if sample_room.sales_history:
                dates = sorted(set(sr.date for sr in sample_room.sales_history))
                total_qty = sum(sr.quantity for sr in sample_room.sales_history)
                print(
                    f"                 date_range=[{dates[0]}, {dates[-1]}], total_qty={total_qty}"
                )
        else:
            sample_room = rooms[0] if rooms else None
            if sample_room:
                print(f"     ID: {sample_room.id}")
                print(f"     Description: {sample_room.description[:60]}...")
                print(
                    f"     After CBOM: components={len(sample_room.componenets)}, items={sample_room.total_items}"
                )
                print(f"     After FIT/CVI: sales_records=0 (no matching sales data)")

        print(f"\n🎉 All validation checks passed!")
        print("\n" + "=" * 80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================


if __name__ == "__main__":
    """Run tests standalone with file pickers"""
    print("\n")
    print("=" * 80)
    print("  INFRASTRUCTURE TEST SUITE - STANDALONE MODE")
    print("=" * 80)

    # Run pytest with captured output
    pytest.main(
        [
            __file__,
            "-v",  # Verbose
            "-s",  # No capture (show prints)
            "--tb=short",  # Short traceback
        ]
    )
