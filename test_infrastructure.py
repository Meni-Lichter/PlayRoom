"""
Comprehensive Test Suite for Infrastructure Components
Tests data loading and transformation performance for CBOM, YMBD, and FIT_CVI files
"""

import pytest
import pandas as pd
import time
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Optional

from src.infrastructure.data_loaders import load_cbom, read_file
from src.infrastructure.data_transformer import (
    transform_cbom_data,
    parse_ymbd_to_sales_records,
    parse_fit_cvi_to_sales_records,
)
from src.utils.config_util import load_config
from src.models.mapping import Room, TwelveNC
from src.models.sales_record import SalesRecord


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def print_section(title: str, char: str = "="):
    """Print formatted section header"""
    print(f"\n{char * 80}")
    print(f"{title:^80}")
    print(f"{char * 80}\n")


def format_time(seconds: float) -> str:
    """Format seconds into readable time string"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def pick_file(file_type: str) -> Optional[Path]:
    """Open file picker dialog for selecting test files"""
    root = Tk()
    root.withdraw()  # Hide the main window
    root.attributes("-topmost", True)  # Bring dialog to front

    file_extensions = {
        "CBOM": [("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
        "YMBD": [("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
        "FIT_CVI": [("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
    }

    file_path = filedialog.askopenfilename(
        title=f"Select {file_type} file for testing",
        filetypes=file_extensions.get(file_type, [("All files", "*.*")]),
    )

    root.destroy()

    return Path(file_path) if file_path else None


# ============================================================================
# TEST DATA LOADING PERFORMANCE
# ============================================================================


class TestDataLoading:
    """Test suite for data loading functions"""

    @pytest.fixture(scope="class")
    def config(self):
        """Load configuration once for all tests"""
        return load_config()

    @pytest.fixture(scope="class")
    def cbom_file(self):
        """Get CBOM file path from user"""
        print_section("Select CBOM File", "-")
        file_path = pick_file("CBOM")
        if not file_path:
            pytest.skip("No CBOM file selected")
        return file_path

    @pytest.fixture(scope="class")
    def ymbd_file(self):
        """Get YMBD file path from user"""
        print_section("Select YMBD File", "-")
        file_path = pick_file("YMBD")
        if not file_path:
            pytest.skip("No YMBD file selected")
        return file_path

    @pytest.fixture(scope="class")
    def fit_cvi_file(self):
        """Get FIT_CVI file path from user"""
        print_section("Select FIT_CVI File", "-")
        file_path = pick_file("FIT_CVI")
        if not file_path:
            pytest.skip("No FIT_CVI file selected")
        return file_path

    def test_load_cbom_performance(self, cbom_file, config):
        """Test CBOM loading performance and data integrity"""
        print_section("Testing CBOM Data Loading")

        # Measure loading time
        start_time = time.perf_counter()
        room_data, data_12nc = load_cbom(cbom_file, config)
        load_time = time.perf_counter() - start_time

        # Assertions
        assert room_data is not None, "room_data should not be None"
        assert data_12nc is not None, "data_12nc should not be None"
        assert isinstance(room_data, dict), "room_data should be a dictionary"
        assert isinstance(data_12nc, dict), "data_12nc should be a dictionary"
        assert len(room_data) > 0, "room_data should contain at least one room"
        assert len(data_12nc) > 0, "data_12nc should contain at least one 12NC"

        # Performance report
        print(f"✓ CBOM file loaded successfully")
        print(f"  - File: {cbom_file.name}")
        print(f"  - Load time: {format_time(load_time)}")
        print(f"  - Rooms found: {len(room_data)}")
        print(f"  - 12NCs found: {len(data_12nc)}")
        print(
            f"  - Performance: {len(room_data) + len(data_12nc)}/sec = {(len(room_data) + len(data_12nc))/load_time:.2f} items/sec"
        )

        # Data structure validation
        sample_room = next(iter(room_data.values()))
        assert isinstance(sample_room, pd.DataFrame), "Room data should be DataFrame"
        assert "12NC" in sample_room.columns, "Room data should have '12NC' column"
        assert "Quantity" in sample_room.columns, "Room data should have 'Quantity' column"

        sample_12nc = next(iter(data_12nc.values()))
        assert isinstance(sample_12nc, pd.DataFrame), "12NC data should be DataFrame"
        assert "Room" in sample_12nc.columns, "12NC data should have 'Room' column"
        assert "Quantity" in sample_12nc.columns, "12NC data should have 'Quantity' column"

        # Sample data display
        print(f"\n  Sample Room Data (first 3):")
        for i, (room, df) in enumerate(list(room_data.items())[:3]):
            print(f"    Room {room}: {len(df)} components")

        print(f"\n  Sample 12NC Data (first 3):")
        for i, (nc, df) in enumerate(list(data_12nc.items())[:3]):
            print(f"    12NC {nc}: {len(df)} rooms")

        return room_data, data_12nc

    def test_read_ymbd_performance(self, ymbd_file, config):
        """Test YMBD file reading performance"""
        print_section("Testing YMBD Data Loading")

        start_time = time.perf_counter()
        ymbd_df = read_file(ymbd_file, "ymbd", header=0)
        load_time = time.perf_counter() - start_time

        # Assertions
        assert ymbd_df is not None, "YMBD DataFrame should not be None"
        assert isinstance(ymbd_df, pd.DataFrame), "Should return a DataFrame"
        assert len(ymbd_df) > 0, "DataFrame should contain data"

        # Validate required columns
        required_columns = config["ymbd"]["columns"].values()
        for col in required_columns:
            assert col in ymbd_df.columns, f"Missing required column: {col}"

        print(f"✓ YMBD file loaded successfully")
        print(f"  - File: {ymbd_file.name}")
        print(f"  - Load time: {format_time(load_time)}")
        print(f"  - Rows: {len(ymbd_df)}")
        print(f"  - Columns: {len(ymbd_df.columns)}")
        print(f"  - Performance: {len(ymbd_df)/load_time:.2f} rows/sec")
        print(f"  - Memory usage: {ymbd_df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

        return ymbd_df

    def test_read_fit_cvi_performance(self, fit_cvi_file, config):
        """Test FIT_CVI file reading performance"""
        print_section("Testing FIT_CVI Data Loading")

        start_time = time.perf_counter()
        fit_cvi_df = read_file(fit_cvi_file, "fit_cvi", header=0)
        load_time = time.perf_counter() - start_time

        # Assertions
        assert fit_cvi_df is not None, "FIT_CVI DataFrame should not be None"
        assert isinstance(fit_cvi_df, pd.DataFrame), "Should return a DataFrame"
        assert len(fit_cvi_df) > 0, "DataFrame should contain data"

        # Validate required columns
        required_columns = config["fit_cvi"]["columns"].values()
        for col in required_columns:
            assert col in fit_cvi_df.columns, f"Missing required column: {col}"

        print(f"✓ FIT_CVI file loaded successfully")
        print(f"  - File: {fit_cvi_file.name}")
        print(f"  - Load time: {format_time(load_time)}")
        print(f"  - Rows: {len(fit_cvi_df)}")
        print(f"  - Columns: {len(fit_cvi_df.columns)}")
        print(f"  - Performance: {len(fit_cvi_df)/load_time:.2f} rows/sec")
        print(f"  - Memory usage: {fit_cvi_df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

        return fit_cvi_df


# ============================================================================
# TEST DATA TRANSFORMATION PERFORMANCE
# ============================================================================


class TestDataTransformation:
    """Test suite for data transformation functions"""

    @pytest.fixture(scope="class")
    def config(self):
        """Load configuration once for all tests"""
        return load_config()

    @pytest.fixture(scope="class")
    def cbom_data(self, config):
        """Load CBOM data for transformation tests"""
        print_section("Load CBOM for Transformation Tests", "-")
        file_path = pick_file("CBOM")
        if not file_path:
            pytest.skip("No CBOM file selected")
        return load_cbom(file_path, config)

    @pytest.fixture(scope="class")
    def ymbd_data(self, config):
        """Load YMBD data for transformation tests"""
        print_section("Load YMBD for Transformation Tests", "-")
        file_path = pick_file("YMBD")
        if not file_path:
            pytest.skip("No YMBD file selected")
        return read_file(file_path, "ymbd", header=0)

    @pytest.fixture(scope="class")
    def fit_cvi_data(self, config):
        """Load FIT_CVI data for transformation tests"""
        print_section("Load FIT_CVI for Transformation Tests", "-")
        file_path = pick_file("FIT_CVI")
        if not file_path:
            pytest.skip("No FIT_CVI file selected")
        return read_file(file_path, "fit_cvi", header=0)

    def test_transform_cbom_performance(self, cbom_data, config):
        """Test CBOM data transformation performance"""
        print_section("Testing CBOM Data Transformation")

        room_data, data_12nc = cbom_data

        start_time = time.perf_counter()
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        transform_time = time.perf_counter() - start_time

        # Assertions
        assert rooms is not None, "rooms should not be None"
        assert nc12s is not None, "nc12s should not be None"
        assert isinstance(rooms, list), "rooms should be a list"
        assert isinstance(nc12s, list), "nc12s should be a list"
        assert len(rooms) > 0, "Should have at least one room"
        assert len(nc12s) > 0, "Should have at least one 12NC"
        assert all(isinstance(r, Room) for r in rooms), "All items should be Room objects"
        assert all(isinstance(nc, TwelveNC) for nc in nc12s), "All items should be TwelveNC objects"

        print(f"✓ CBOM data transformed successfully")
        print(f"  - Transform time: {format_time(transform_time)}")
        print(f"  - Rooms created: {len(rooms)}")
        print(f"  - 12NCs created: {len(nc12s)}")
        print(f"  - Performance: {(len(rooms) + len(nc12s))/transform_time:.2f} objects/sec")

        # Validate data structure
        sample_room = rooms[0]
        print(f"\n  Sample Room Object:")
        print(f"    - Room ID: {sample_room.room}")
        print(f"    - Description: {sample_room.room_description[:50]}...")
        print(f"    - Component count: {len(sample_room.twelve_ncs)}")
        print(f"    - Total items: {sample_room.total_items}")

        sample_12nc = nc12s[0]
        print(f"\n  Sample 12NC Object:")
        print(f"    - 12NC ID: {sample_12nc.twelve_nc}")
        print(f"    - Description: {sample_12nc.tnc_description[:50]}...")
        print(f"    - Room count: {len(sample_12nc.rooms)}")
        print(f"    - Total items: {sample_12nc.total_items}")

        return rooms, nc12s

    def test_parse_ymbd_performance(self, ymbd_data, config):
        """Test YMBD parsing to SalesRecord objects"""
        print_section("Testing YMBD Sales Record Parsing")

        start_time = time.perf_counter()
        sales_records = parse_ymbd_to_sales_records(ymbd_data)
        parse_time = time.perf_counter() - start_time

        # Assertions
        assert sales_records is not None, "sales_records should not be None"
        assert isinstance(sales_records, list), "Should return a list"
        assert len(sales_records) > 0, "Should have at least one sales record"
        assert all(
            isinstance(sr, SalesRecord) for sr in sales_records
        ), "All items should be SalesRecord objects"

        print(f"✓ YMBD data parsed successfully")
        print(f"  - Parse time: {format_time(parse_time)}")
        print(f"  - Sales records created: {len(sales_records)}")
        print(f"  - Performance: {len(sales_records)/parse_time:.2f} records/sec")

        # Data quality checks
        total_quantity = sum(sr.quantity for sr in sales_records)
        unique_12ncs = len(set(sr.identifier for sr in sales_records))
        unique_dates = len(set(sr.date for sr in sales_records))

        print(f"\n  Data Summary:")
        print(f"    - Total quantity: {total_quantity:,}")
        print(f"    - Unique 12NCs: {unique_12ncs}")
        print(f"    - Unique dates: {unique_dates}")
        print(f"    - Avg quantity per record: {total_quantity/len(sales_records):.2f}")

        # Sample records
        print(f"\n  Sample Records (first 3):")
        for i, sr in enumerate(sales_records[:3]):
            print(f"    [{i+1}] 12NC: {sr.identifier}, Qty: {sr.quantity}, Date: {sr.date}")

        return sales_records

    def test_parse_fit_cvi_performance(self, fit_cvi_data, config):
        """Test FIT_CVI parsing to SalesRecord objects"""
        print_section("Testing FIT_CVI Sales Record Parsing")

        start_time = time.perf_counter()
        sales_records = parse_fit_cvi_to_sales_records(fit_cvi_data)
        parse_time = time.perf_counter() - start_time

        # Assertions
        assert sales_records is not None, "sales_records should not be None"
        assert isinstance(sales_records, list), "Should return a list"
        assert len(sales_records) > 0, "Should have at least one sales record"
        assert all(
            isinstance(sr, SalesRecord) for sr in sales_records
        ), "All items should be SalesRecord objects"

        print(f"✓ FIT_CVI data parsed successfully")
        print(f"  - Parse time: {format_time(parse_time)}")
        print(f"  - Sales records created: {len(sales_records)}")
        print(f"  - Performance: {len(sales_records)/parse_time:.2f} records/sec")

        # Data quality checks
        total_quantity = sum(sr.quantity for sr in sales_records)
        unique_rooms = len(set(sr.identifier for sr in sales_records))
        unique_dates = len(set(sr.date for sr in sales_records))

        print(f"\n  Data Summary:")
        print(f"    - Total quantity: {total_quantity:,}")
        print(f"    - Unique rooms: {unique_rooms}")
        print(f"    - Unique dates: {unique_dates}")
        print(f"    - Avg quantity per record: {total_quantity/len(sales_records):.2f}")

        # Sample records
        print(f"\n  Sample Records (first 3):")
        for i, sr in enumerate(sales_records[:3]):
            print(f"    [{i+1}] Room: {sr.identifier}, Qty: {sr.quantity}, Date: {sr.date}")

        return sales_records


# ============================================================================
# TEST INTEGRATION & DATA CONSISTENCY
# ============================================================================


class TestDataIntegration:
    """Test suite for data integration and consistency checks"""

    @pytest.fixture(scope="class")
    def config(self):
        """Load configuration once for all tests"""
        return load_config()

    @pytest.fixture(scope="class")
    def full_dataset(self, config):
        """Load all files for integration testing"""
        print_section("Load All Files for Integration Tests", "-")

        cbom_file = pick_file("CBOM")
        if not cbom_file:
            pytest.skip("No CBOM file selected")

        ymbd_file = pick_file("YMBD")
        fit_cvi_file = pick_file("FIT_CVI")

        # Load and transform data
        room_data, data_12nc = load_cbom(cbom_file, config)
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)

        ymbd_records = None
        if ymbd_file:
            ymbd_df = read_file(ymbd_file, "ymbd", header=0)
            ymbd_records = parse_ymbd_to_sales_records(ymbd_df)

        fit_cvi_records = None
        if fit_cvi_file:
            fit_cvi_df = read_file(fit_cvi_file, "fit_cvi", header=0)
            fit_cvi_records = parse_fit_cvi_to_sales_records(fit_cvi_df)

        return {
            "rooms": rooms,
            "nc12s": nc12s,
            "ymbd_records": ymbd_records,
            "fit_cvi_records": fit_cvi_records,
        }

    def test_data_consistency(self, full_dataset):
        """Test consistency between rooms and 12NCs"""
        print_section("Testing Data Consistency")

        rooms = full_dataset["rooms"]
        nc12s = full_dataset["nc12s"]

        print(f"Checking bidirectional relationship consistency...")

        # Build lookup dictionaries
        room_dict = {r.room: r for r in rooms}
        nc12_dict = {nc.twelve_nc: nc for nc in nc12s}

        # Check if every 12NC in rooms exists in nc12s
        inconsistencies = 0
        for room in rooms:
            for nc12_id in room.twelve_ncs.keys():
                if nc12_id not in nc12_dict:
                    print(f"  ⚠ Warning: 12NC {nc12_id} in room {room.room} not found in 12NC list")
                    inconsistencies += 1

        # Check if every room in 12NCs exists in rooms
        for nc12 in nc12s:
            for room_id in nc12.rooms.keys():
                if room_id not in room_dict:
                    print(
                        f"  ⚠ Warning: Room {room_id} in 12NC {nc12.twelve_nc} not found in room list"
                    )
                    inconsistencies += 1

        if inconsistencies == 0:
            print(f"✓ All relationships are consistent")
        else:
            print(f"⚠ Found {inconsistencies} inconsistencies")

        assert inconsistencies == 0, f"Data has {inconsistencies} inconsistencies"

    def test_sales_data_coverage(self, full_dataset):
        """Test sales data coverage against CBOM components"""
        print_section("Testing Sales Data Coverage")

        nc12s = full_dataset["nc12s"]
        ymbd_records = full_dataset.get("ymbd_records")
        fit_cvi_records = full_dataset.get("fit_cvi_records")

        if ymbd_records:
            nc12_ids = set(nc.twelve_nc for nc in nc12s)
            ymbd_12ncs = set(sr.identifier for sr in ymbd_records)
            coverage = len(ymbd_12ncs.intersection(nc12_ids))
            coverage_percent = (coverage / len(nc12_ids) * 100) if nc12_ids else 0

            print(f"YMBD Sales Coverage:")
            print(f"  - 12NCs in CBOM: {len(nc12_ids)}")
            print(f"  - 12NCs with sales data: {coverage}")
            print(f"  - Coverage: {coverage_percent:.2f}%")

            # Find 12NCs without sales data
            missing = nc12_ids - ymbd_12ncs
            if missing and len(missing) <= 10:
                print(f"  - 12NCs without sales data: {', '.join(list(missing)[:10])}")

        if fit_cvi_records:
            rooms = full_dataset["rooms"]
            room_ids = set(r.room for r in rooms)
            fit_cvi_rooms = set(sr.identifier for sr in fit_cvi_records)
            coverage = len(fit_cvi_rooms.intersection(room_ids))
            coverage_percent = (coverage / len(room_ids) * 100) if room_ids else 0

            print(f"\nFIT_CVI Sales Coverage:")
            print(f"  - Rooms in CBOM: {len(room_ids)}")
            print(f"  - Rooms with sales data: {coverage}")
            print(f"  - Coverage: {coverage_percent:.2f}%")

    def test_end_to_end_performance(self, config):
        """Test complete end-to-end loading and transformation performance"""
        print_section("Testing End-to-End Performance")

        cbom_file = pick_file("CBOM")
        if not cbom_file:
            pytest.skip("No CBOM file selected")

        print(f"Running complete pipeline on: {cbom_file.name}\n")

        # Full pipeline timing
        total_start = time.perf_counter()

        # Step 1: Load CBOM
        load_start = time.perf_counter()
        room_data, data_12nc = load_cbom(cbom_file, config)
        load_time = time.perf_counter() - load_start

        # Step 2: Transform CBOM
        transform_start = time.perf_counter()
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        transform_time = time.perf_counter() - transform_start

        total_time = time.perf_counter() - total_start

        # Performance report
        print(f"Performance Summary:")
        print(
            f"  1. CBOM Loading:        {format_time(load_time):>12}  ({load_time/total_time*100:>5.1f}%)"
        )
        print(
            f"  2. CBOM Transformation: {format_time(transform_time):>12}  ({transform_time/total_time*100:>5.1f}%)"
        )
        print(f"  {'─' * 50}")
        print(f"  Total Pipeline Time:    {format_time(total_time):>12}  (100.0%)")
        print(f"\n  Throughput:")
        print(
            f"    - Rooms processed:  {len(rooms):>6} rooms  ({len(rooms)/total_time:>8.2f} rooms/sec)"
        )
        print(
            f"    - 12NCs processed:  {len(nc12s):>6} 12NCs  ({len(nc12s)/total_time:>8.2f} 12NCs/sec)"
        )

        # Memory efficiency
        import sys

        memory_estimate = (sys.getsizeof(rooms) + sys.getsizeof(nc12s)) / 1024 / 1024
        print(f"\n  Memory Efficiency:")
        print(f"    - Objects memory: ~{memory_estimate:.2f} MB")

        print(f"\n✓ End-to-end pipeline completed successfully")


# ============================================================================
# MAIN EXECUTION
# ============================================================================


if __name__ == "__main__":
    """
    Run tests with: python test_infrastructure.py
    Or use pytest: pytest test_infrastructure.py -v -s
    """
    print_section("Infrastructure Performance Test Suite", "=")
    print("This test suite will prompt you to select files for testing.")
    print("You can run individual test classes or all tests.")
    print("\nPress Enter to continue...")
    input()

    # Run pytest programmatically with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
