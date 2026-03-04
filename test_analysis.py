"""
Analysis Test Suite for Room_12NC_PerformanceCenter
Tests the performance analysis functionality including data loading, transformation, and analysis.
"""

import pytest
import pandas as pd
import time
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Optional, Tuple, List
from datetime import datetime

# Import infrastructure modules
from src.infrastructure.data_loaders import load_cbom, read_file
from src.infrastructure.data_transformer import (
    transform_cbom_data,
    parse_ymbd_to_sales_records,
    parse_fit_cvi_to_sales_records,
)
from src.models.mapping import G_entity, Room, TwelveNC
from src.models.sales_record import SalesRecord
from src.models.performance import PerformanceData, TimePeriod
from src.models.prediction import Prediction
from src.analysis.performance_analyzer import PerformanceAnalyzer
from src.analysis.predictor import Predictor
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
    cbom_file = pick_file(
        "Select CBOM File", [("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
    )
    ymbd_file = pick_file(
        "Select YMBD File (Sales)", [("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
    )
    fit_file = pick_file(
        "Select FIT/CVI File (Room Sales)",
        [("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")],
    )
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


@pytest.fixture
def prepared_data(cbom_file, ymbd_file, fit_file, config):
    """Prepare all data: load, transform, and parse sales"""
    if not cbom_file:
        pytest.skip("No CBOM file provided")

    # Load and transform CBOM
    room_data, data_12nc = load_cbom(cbom_file, config)
    rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)

    # Parse YMBD if available
    if ymbd_file:
        ymbd_df = read_file(ymbd_file, "ymbd", header=0)
        nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)

    # Parse FIT/CVI if available
    if fit_file:
        fit_df = read_file(fit_file, "fit_cvi", header=0)
        rooms = parse_fit_cvi_to_sales_records(rooms, fit_df)

    return rooms, nc12s


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def wrap_entity(entity: Room | TwelveNC) -> G_entity:
    """Wrap Room or TwelveNC in G_entity wrapper"""
    if isinstance(entity, Room):
        return G_entity(g_entity=entity, entity_type="room")
    elif isinstance(entity, TwelveNC):
        return G_entity(g_entity=entity, entity_type="12NC")
    else:
        raise TypeError(f"Unknown entity type: {type(entity)}")


# ============================================================================
# DATA PREPARATION TESTS
# ============================================================================


class TestDataPreparation:
    """Test data loading and preparation for analysis"""

    def test_load_and_transform_cbom(self, cbom_file, config):
        """Test CBOM loading and transformation"""
        if not cbom_file:
            pytest.skip("No CBOM file provided")

        start_time = time.perf_counter()
        room_data, data_12nc = load_cbom(cbom_file, config)
        load_time = (time.perf_counter() - start_time) * 1000

        assert room_data is not None and len(room_data) > 0
        assert data_12nc is not None and len(data_12nc) > 0

        start_time = time.perf_counter()
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        transform_time = (time.perf_counter() - start_time) * 1000

        assert all(isinstance(r, Room) for r in rooms)
        assert all(isinstance(nc, TwelveNC) for nc in nc12s)

        print(f"\nCBOM Data Preparation:")
        print(f"  Load time: {load_time:.2f} ms")
        print(f"  Transform time: {transform_time:.2f} ms")
        print(f"  Rooms: {len(rooms)}")
        print(f"  12NCs: {len(nc12s)}")

    def test_parse_sales_data(self, cbom_file, ymbd_file, fit_file, config):
        """Test sales data parsing and linking"""
        if not cbom_file:
            pytest.skip("No CBOM file provided")

        # Prepare base data
        room_data, data_12nc = load_cbom(cbom_file, config)
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)

        results = {"YMBD": {}, "FIT/CVI": {}}

        # Parse YMBD
        if ymbd_file:
            start_time = time.perf_counter()
            ymbd_df = read_file(ymbd_file, "ymbd", header=0)
            nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)
            ymbd_time = (time.perf_counter() - start_time) * 1000

            nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]
            total_records = sum(len(nc.sales_history) for nc in nc12s)

            results["YMBD"] = {
                "time": ymbd_time,
                "matched": len(nc12s_with_sales),
                "total": len(nc12s),
                "records": total_records,
                "avg_per_item": total_records / len(nc12s_with_sales) if nc12s_with_sales else 0,
            }

        # Parse FIT/CVI
        if fit_file:
            start_time = time.perf_counter()
            fit_df = read_file(fit_file, "fit_cvi", header=0)
            rooms = parse_fit_cvi_to_sales_records(rooms, fit_df)
            fit_time = (time.perf_counter() - start_time) * 1000

            rooms_with_sales = [r for r in rooms if len(r.sales_history) > 0]
            total_records = sum(len(r.sales_history) for r in rooms)

            results["FIT/CVI"] = {
                "time": fit_time,
                "matched": len(rooms_with_sales),
                "total": len(rooms),
                "records": total_records,
                "avg_per_item": total_records / len(rooms_with_sales) if rooms_with_sales else 0,
            }

        print(f"\nSales Data Parsing:")
        for source, data in results.items():
            if data:
                print(f"  {source}:")
                print(f"    Time: {data['time']:.2f} ms")
                print(
                    f"    Matched: {data['matched']}/{data['total']} ({data['matched']/data['total']*100:.1f}%)"
                )
                print(f"    Records: {data['records']:,}")
                print(f"    Avg per item: {data['avg_per_item']:.1f}")


# ============================================================================
# ANALYSIS TESTS
# ============================================================================


class TestAnalysis:
    """Test the performance analysis functionality"""

    def test_single_item_analysis_12nc(self, prepared_data):
        """Test analyzing a single 12NC"""
        rooms, nc12s = prepared_data

        # Find a 12NC with sales data
        target_nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                target_nc = nc
                break

        if not target_nc:
            pytest.skip("No 12NC with sales data found")

        analyzer = PerformanceAnalyzer()
        start_time = time.perf_counter()
        result = analyzer.analyze(wrap_entity(target_nc), lookback_years=3, granularity="monthly")
        analysis_time = (time.perf_counter() - start_time) * 1000

        assert isinstance(result, PerformanceData)
        assert result.g_entity is not None
        assert len(result.periods) > 0
        assert result.total > 0

        print(f"\n12NC Single Item Analysis:")
        print(f"  12NC ID: {target_nc.id}")
        print(f"  Overall Sales records: {len(target_nc.sales_history)}")
        print(f"  Analysis time: {analysis_time:.2f} ms")
        print(f"  Periods analyzed: {result.period_count}")
        print(f"  Total quantity: {result.total:,}")
        print(f"  Average per period: {result.average:.2f}")
        print(f"  Granularity: {result.granularity}")

        # Show period breakdown
        print(f"  Period breakdown (first 5):")
        unsotrted_periods = result.periods[:5]
        sorted_periods = sorted(unsotrted_periods, key=lambda p: p.quantity, reverse=True)
        for idx, period in enumerate(sorted_periods):
            print(f"    {period.label}: {period.quantity:,}")
        if len(result.periods) > 5:
            print(f"    ... and {len(result.periods) - 5} more periods")

    def test_single_item_analysis_room(self, prepared_data):
        """Test analyzing a single Room"""
        rooms, nc12s = prepared_data

        # Find a Room with sales data
        target_room = None
        for room in rooms:
            if len(room.sales_history) > 0:
                target_room = room
                break

        if not target_room:
            pytest.skip("No Room with sales data found")

        analyzer = PerformanceAnalyzer()
        start_time = time.perf_counter()

        result = analyzer.analyze(wrap_entity(target_room), lookback_years=3, granularity="monthly")
        analysis_time = (time.perf_counter() - start_time) * 1000

        assert isinstance(result, PerformanceData)
        assert result.g_entity is not None
        assert len(result.periods) > 0
        assert result.total > 0

        print(f"\nRoom Single Item Analysis:")
        print(f"  Room ID: {target_room.id}")
        print(f"  Sales records: {len(target_room.sales_history)}")
        print(f"  Analysis time: {analysis_time:.2f} ms")
        print(f"  Periods analyzed: {result.period_count}")
        print(f"  Total quantity: {result.total:,}")
        print(f"  Average per period: {result.average:.2f}")
        print(f"  Granularity: {result.granularity}")

        # Show period breakdown
        print(f"  Period breakdown (first 5):")
        for idx, period in enumerate(result.periods[:5]):
            print(f"    {period.label}: {period.quantity:,}")
        if len(result.periods) > 5:
            print(f"    ... and {len(result.periods) - 5} more periods")

    def test_batch_analysis_12ncs(self, prepared_data):
        """Test analyzing multiple 12NCs"""
        rooms, nc12s = prepared_data

        # Get 12NCs with sales data
        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]

        if not nc12s_with_sales:
            pytest.skip("No 12NCs with sales data found")

        # Limit to 10 for testing
        test_items = nc12s_with_sales[:10]

        analyzer = PerformanceAnalyzer()
        start_time = time.perf_counter()

        results = []
        for nc in test_items:
            try:
                result = analyzer.analyze(wrap_entity(nc), lookback_years=3, granularity="monthly")
                results.append(result)
            except Exception as e:
                print(f"Error analyzing 12NC {nc.id}: {e}")

        batch_time = (time.perf_counter() - start_time) * 1000

        assert len(results) > 0

        # Calculate statistics
        total_qty = sum(r.total for r in results)
        avg_qty = total_qty / len(results) if results else 0
        avg_periods = sum(r.period_count for r in results) / len(results) if results else 0
        avg_time_per_item = batch_time / len(results)

        print(f"\nBatch 12NC Analysis:")
        print(f"  Items analyzed: {len(results)}/{len(test_items)}")
        print(f"  Total batch time: {batch_time:.2f} ms")
        print(f"  Avg time per item: {avg_time_per_item:.2f} ms")
        print(f"  Total quantity (all items): {total_qty:,}")
        print(f"  Avg quantity per item: {avg_qty:.2f}")
        print(f"  Avg periods per item: {avg_periods:.1f}")

        # Show performance distribution
        print(f"\n  Top 5 by quantity:")
        sorted_results = sorted(results, key=lambda x: x.total, reverse=True)
        for idx, result in enumerate(sorted_results[:5]):
            print(f"    {idx+1}. {result.get_entity_id()}: {result.total:,}")

    def test_batch_analysis_rooms(self, prepared_data):
        """Test analyzing multiple Rooms"""
        rooms, nc12s = prepared_data

        # Get rooms with sales data
        rooms_with_sales = [r for r in rooms if len(r.sales_history) > 0]

        if not rooms_with_sales:
            pytest.skip("No Rooms with sales data found")

        # Limit to 10 for testing
        test_items = rooms_with_sales[:10]

        analyzer = PerformanceAnalyzer()
        start_time = time.perf_counter()

        results = []
        for room in test_items:
            try:
                result = analyzer.analyze(
                    wrap_entity(room), lookback_years=3, granularity="monthly"
                )
                results.append(result)
            except Exception as e:
                print(f"Error analyzing Room {room.id}: {e}")

        batch_time = (time.perf_counter() - start_time) * 1000

        assert len(results) > 0

        # Calculate statistics
        total_qty = sum(r.total for r in results)
        avg_qty = total_qty / len(results) if results else 0
        avg_periods = sum(r.period_count for r in results) / len(results) if results else 0
        avg_time_per_item = batch_time / len(results)

        print(f"\nBatch Room Analysis:")
        print(f"  Items analyzed: {len(results)}/{len(test_items)}")
        print(f"  Total batch time: {batch_time:.2f} ms")
        print(f"  Avg time per item: {avg_time_per_item:.2f} ms")
        print(f"  Total quantity (all items): {total_qty:,}")
        print(f"  Avg quantity per item: {avg_qty:.2f}")
        print(f"  Avg periods per item: {avg_periods:.1f}")

        # Show performance distribution
        print(f"\n  Top 5 by quantity:")
        sorted_results = sorted(results, key=lambda x: x.total, reverse=True)
        for idx, result in enumerate(sorted_results[:5]):
            try:
                print(f"    {idx+1}. {result.get_entity_id()}: {result.total:,}")
                print(
                    f"       Periods: {result.period_count}, Avg per period: {result.average:.2f}"
                )
                if len(result.periods) > 0:
                    # Sort periods chronologically by parsing MM-YYYY format
                    def parse_period_key(label):
                        try:
                            if "-Q" in label:  # Quarterly: YYYY-Qn
                                parts = label.split("-Q")
                                year = int(parts[0])
                                quarter = int(parts[1])
                                return (year, quarter * 3)
                            elif len(label) == 7 and label[2] == "-":  # Monthly: MM-YYYY
                                month, year = label.split("-")
                                return (int(year), int(month))
                            elif len(label) == 4 and label.isdigit():  # Yearly: YYYY
                                return (int(label), 0)
                            elif len(label) == 10 and label.count("-") == 2:  # Daily: MM-DD-YYYY
                                parts = label.split("-")
                                return (int(parts[2]), int(parts[0]), int(parts[1]))
                            else:
                                return (0, 0)
                        except:
                            return (0, 0)

                    sorted_periods = sorted(result.periods, key=lambda p: parse_period_key(p.label))
                    min_period = sorted_periods[0].label
                    max_period = sorted_periods[-1].label
                    print(f"       Time range: {min_period} to {max_period}")
            except (AttributeError, IndexError) as e:
                print(f"    {idx+1}. Error displaying details: {e}")


# ============================================================================
# PERFORMANCE ANALYSIS TESTS
# ============================================================================


class TestAnalysisPerformance:
    """Test the performance characteristics of the analysis system"""

    def test_analysis_speed_12nc(self, prepared_data):
        """Measure analysis speed for 12NCs at different scales"""
        rooms, nc12s = prepared_data

        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]

        if not nc12s_with_sales:
            pytest.skip("No 12NCs with sales data found")

        test_scales = [1, 5, 10, min(50, len(nc12s_with_sales))]
        results = {}

        analyzer = PerformanceAnalyzer()

        print(f"\n12NC Analysis Speed Test:")
        for scale in test_scales:
            test_items = nc12s_with_sales[:scale]
            start_time = time.perf_counter()

            count = 0
            for nc in test_items:
                try:
                    analyzer.analyze(wrap_entity(nc), lookback_years=3, granularity="monthly")
                    count += 1
                except Exception:
                    pass

            elapsed = (time.perf_counter() - start_time) * 1000
            per_item = elapsed / scale if scale > 0 else 0
            throughput = (scale / elapsed * 1000) if elapsed > 0 else 0

            results[scale] = {
                "time": elapsed,
                "count": count,
                "per_item": per_item,
                "throughput": throughput,
            }

            print(
                f"  {scale} items: {elapsed:.2f} ms ({per_item:.2f} ms/item, {throughput:.2f} items/sec)"
            )

    def test_analysis_speed_rooms(self, prepared_data):
        """Measure analysis speed for Rooms at different scales"""
        rooms, nc12s = prepared_data

        rooms_with_sales = [r for r in rooms if len(r.sales_history) > 0]

        if not rooms_with_sales:
            pytest.skip("No Rooms with sales data found")

        test_scales = [1, 5, 10, min(50, len(rooms_with_sales))]
        results = {}

        analyzer = PerformanceAnalyzer()

        print(f"\nRoom Analysis Speed Test:")
        for scale in test_scales:
            test_items = rooms_with_sales[:scale]
            start_time = time.perf_counter()

            count = 0
            for room in test_items:
                try:
                    analyzer.analyze(wrap_entity(room), lookback_years=3, granularity="monthly")
                    count += 1
                except Exception:
                    pass

            elapsed = (time.perf_counter() - start_time) * 1000
            per_item = elapsed / scale if scale > 0 else 0
            throughput = (scale / elapsed * 1000) if elapsed > 0 else 0

            results[scale] = {
                "time": elapsed,
                "count": count,
                "per_item": per_item,
                "throughput": throughput,
            }

            print(
                f"  {scale} items: {elapsed:.2f} ms ({per_item:.2f} ms/item, {throughput:.2f} items/sec)"
            )

    def test_granularity_impact(self, prepared_data):
        """Test impact of different granularities on analysis"""
        rooms, nc12s = prepared_data

        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]

        if not nc12s_with_sales:
            pytest.skip("No 12NCs with sales data found")

        target_nc = nc12s_with_sales[0]
        granularities = ["monthly", "quarterly", "yearly"]
        results = {}

        analyzer = PerformanceAnalyzer()

        print(f"\nGranularity Impact Test (12NC: {target_nc.id}):")
        for granularity in granularities:
            start_time = time.perf_counter()
            result = analyzer.analyze(
                wrap_entity(target_nc), lookback_years=3, granularity=granularity
            )
            elapsed = (time.perf_counter() - start_time) * 1000

            results[granularity] = {
                "time": elapsed,
                "periods": result.period_count,
                "total": result.total,
            }

            print(
                f"  {granularity}: {elapsed:.2f} ms, {result.period_count} periods, total {result.total:,}"
            )

    def test_lookback_period_impact(self, prepared_data):
        """Test impact of different lookback periods on analysis"""
        rooms, nc12s = prepared_data

        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]

        if not nc12s_with_sales:
            pytest.skip("No 12NCs with sales data found")

        target_nc = nc12s_with_sales[0]
        lookback_years = [1, 3, 5]
        results = {}

        analyzer = PerformanceAnalyzer()

        print(f"\nLookback Period Impact Test (12NC: {target_nc.id}):")
        for years in lookback_years:
            start_time = time.perf_counter()
            result = analyzer.analyze(
                wrap_entity(target_nc), lookback_years=years, granularity="monthly"
            )
            elapsed = (time.perf_counter() - start_time) * 1000

            results[years] = {
                "time": elapsed,
                "periods": result.period_count,
                "total": result.total,
            }

            print(
                f"  {years} years: {elapsed:.2f} ms, {result.period_count} periods, total {result.total:,}"
            )


# ============================================================================
# COMPREHENSIVE INTEGRATION TEST
# ============================================================================


class TestAnalysisIntegration:
    """End-to-end integration test of the entire analysis pipeline"""

    def test_complete_analysis_pipeline(self, cbom_file, ymbd_file, fit_file, config):
        """Test the complete pipeline from data loading to analysis"""
        if not cbom_file:
            pytest.skip("Need CBOM file for integration test")

        pipeline_start = time.perf_counter()

        # Step 1: Load and transform CBOM
        print(f"\nComplete Analysis Pipeline:")
        print(f"  Step 1: Load and transform CBOM...")
        start = time.perf_counter()
        room_data, data_12nc = load_cbom(cbom_file, config)
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        step1_time = (time.perf_counter() - start) * 1000
        print(f"    Time: {step1_time:.2f} ms | Rooms: {len(rooms)} | 12NCs: {len(nc12s)}")

        # Step 2: Parse sales data
        print(f"  Step 2: Parse sales data...")
        ymbd_records = 0
        fit_records = 0

        if ymbd_file:
            start = time.perf_counter()
            ymbd_df = read_file(ymbd_file, "ymbd", header=0)
            nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)
            step2a_time = (time.perf_counter() - start) * 1000
            ymbd_records = sum(len(nc.sales_history) for nc in nc12s)
            print(f"    YMBD: {step2a_time:.2f} ms | Records: {ymbd_records:,}")

        if fit_file:
            start = time.perf_counter()
            fit_df = read_file(fit_file, "fit_cvi", header=0)
            rooms = parse_fit_cvi_to_sales_records(rooms, fit_df)
            step2b_time = (time.perf_counter() - start) * 1000
            fit_records = sum(len(r.sales_history) for r in rooms)
            print(f"    FIT/CVI: {step2b_time:.2f} ms | Records: {fit_records:,}")

        # Step 3: Analyze items
        print(f"  Step 3: Analyze items...")
        analyzer = PerformanceAnalyzer()

        # Analyze 12NCs
        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]
        nc_analysis_count = min(10, len(nc12s_with_sales))
        start = time.perf_counter()
        nc_results = []
        for nc in nc12s_with_sales[:nc_analysis_count]:
            try:
                result = analyzer.analyze(wrap_entity(nc), lookback_years=3, granularity="monthly")
                nc_results.append(result)
            except Exception:
                pass
        step3a_time = (time.perf_counter() - start) * 1000

        # Analyze Rooms
        rooms_with_sales = [r for r in rooms if len(r.sales_history) > 0]
        room_analysis_count = min(10, len(rooms_with_sales))
        start = time.perf_counter()
        room_results = []
        for room in rooms_with_sales[:room_analysis_count]:
            try:

                result = analyzer.analyze(
                    wrap_entity(room), lookback_years=3, granularity="monthly"
                )
                room_results.append(result)
            except Exception:
                pass
        step3b_time = (time.perf_counter() - start) * 1000

        print(f"    12NCs: {step3a_time:.2f} ms | Analyzed: {len(nc_results)}")
        print(f"    Rooms: {step3b_time:.2f} ms | Analyzed: {len(room_results)}")

        # Summary
        pipeline_time = (time.perf_counter() - pipeline_start) * 1000
        total_analyzed = len(nc_results) + len(room_results)

        print(f"\n  Pipeline Summary:")
        print(f"    Total time: {pipeline_time:.2f} ms")
        print(f"    Total items analyzed: {total_analyzed}")
        print(f"    Time per item: {pipeline_time / total_analyzed:.2f} ms (avg)")

        if nc_results:
            nc_total_qty = sum(r.total for r in nc_results)
            print(f"    12NC total quantity: {nc_total_qty:,}")

        if room_results:
            room_total_qty = sum(r.total for r in room_results)
            print(f"    Room total quantity: {room_total_qty:,}")


# ============================================================================
# PREDICTION TESTS
# ============================================================================


class TestPrediction:
    """Test the prediction functionality"""

    def test_prediction_last_n_periods_method(self, prepared_data):
        """Test single period prediction using average method"""
        rooms, nc12s = prepared_data

        # Find a 12NC with sales data
        target_nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                target_nc = nc
                break

        if not target_nc:
            pytest.skip("No 12NC with sales data found")

        analyzer = PerformanceAnalyzer()
        performance_data = analyzer.analyze(
            wrap_entity(target_nc), lookback_years=3, granularity="monthly"
        )

        if len(performance_data.periods) == 0:
            pytest.skip("No periods in performance data")

        predictor = Predictor(performance_data)

        # Get next period label
        from src.utils import get_next_period_label

        next_period = get_next_period_label("monthly")

        start_time = time.perf_counter()
        prediction = predictor.predict(
            target_time=next_period, method="avg_last_n_periods", buffer_percentage=10.0
        )
        pred_time = (time.perf_counter() - start_time) * 1000

        assert isinstance(prediction, Prediction)
        assert prediction.predicted_quantity > 0
        assert prediction.baseline > 0
        assert prediction.buffer_percentage == 10.0

        print(f"\n12NC Single Prediction (Average Method):")
        print(f"  12NC ID: {target_nc.id}")
        print(f"  Period: {prediction.period_label}")
        print(f"  Baseline: {prediction.baseline:.2f}")
        print(f"  Buffer: {prediction.buffer_percentage}%")
        print(f"  Predicted: {prediction.predicted_quantity:.2f}")
        print(f"  Prediction time: {pred_time:.2f} ms")

    def test_prediction_same_period_method(self, prepared_data):
        """Test prediction using same-period-previous-years method"""
        rooms, nc12s = prepared_data

        target_nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0 and len(nc.sales_history) > 2:  # Need multiple records
                target_nc = nc
                break

        if not target_nc:
            pytest.skip("No 12NC with sufficient sales data")

        analyzer = PerformanceAnalyzer()
        performance_data = analyzer.analyze(
            wrap_entity(target_nc), lookback_years=3, granularity="monthly"
        )

        if len(performance_data.periods) < 3:
            pytest.skip("Insufficient periods for same-period comparison")

        predictor = Predictor(performance_data)
        from src.utils import get_next_period_label

        next_period = get_next_period_label("monthly")

        start_time = time.perf_counter()
        prediction = predictor.predict(
            target_time=next_period, method="avg_same_period_previous_years", buffer_percentage=15.0
        )
        pred_time = (time.perf_counter() - start_time) * 1000

        assert isinstance(prediction, Prediction)
        assert prediction.predicted_quantity > 0
        assert prediction.method == "avg_same_period_previous_years"

        print(f"\n12NC Prediction (Same-Period Method):")
        print(f"  12NC ID: {target_nc.id}")
        print(f"  Period: {prediction.period_label}")
        print(f"  Baseline: {prediction.baseline:.2f}")
        print(f"  Method: {prediction.method}")
        print(f"  Predicted: {prediction.predicted_quantity:.2f}")
        print(f"  Prediction time: {pred_time:.2f} ms")

    def test_prediction_buffer_impact(self, prepared_data):
        """Test impact of different buffer percentages"""
        rooms, nc12s = prepared_data

        target_nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                target_nc = nc
                break

        if not target_nc:
            pytest.skip("No 12NC with sales data found")

        analyzer = PerformanceAnalyzer()
        performance_data = analyzer.analyze(
            wrap_entity(target_nc), lookback_years=3, granularity="monthly"
        )

        if len(performance_data.periods) == 0:
            pytest.skip("No periods in performance data")

        predictor = Predictor(performance_data)
        from src.utils import get_next_period_label

        next_period = get_next_period_label("monthly")

        buffers = [0, 5, 10, 20, 30]
        results = {}

        print(f"\nBuffer Impact Test (12NC: {target_nc.id}):")
        for buffer in buffers:
            prediction = predictor.predict(
                target_time=next_period, method="avg_last_n_periods", buffer_percentage=buffer
            )
            results[buffer] = prediction.predicted_quantity
            print(f"  Buffer {buffer}%: {prediction.predicted_quantity:.2f}")

        # Verify buffer scaling
        assert results[10] > results[0]
        assert results[20] > results[10]
        assert results[30] > results[20]

    def test_prediction_different_granularities(self, prepared_data):
        """Test prediction with different time granularities"""
        rooms, nc12s = prepared_data

        target_nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                target_nc = nc
                break

        if not target_nc:
            pytest.skip("No 12NC with sales data found")

        analyzer = PerformanceAnalyzer()
        granularities = ["monthly", "quarterly", "yearly", "daily"]
        results = {}

        print(f"\nGranularity Prediction Test (12NC: {target_nc.id}):")
        for granularity in granularities:
            performance_data = analyzer.analyze(
                wrap_entity(target_nc), lookback_years=3, granularity=granularity
            )

            if len(performance_data.periods) == 0:
                continue

            predictor = Predictor(performance_data)
            from src.utils import get_next_period_label

            next_period = get_next_period_label(granularity)

            prediction = predictor.predict(
                target_time=next_period, method="avg_last_n_periods", buffer_percentage=10.0
            )
            results[granularity] = {
                "prediction_time": prediction.period_label,
                "predicted": prediction.predicted_quantity,
                "periods": len(performance_data.periods),
                "average": performance_data.average,
            }
            print(
                f"  {granularity}: {prediction.predicted_quantity:.2f} (avg: {performance_data.average:.2f}, periods: {len(performance_data.periods)})"
            )

    def test_room_prediction_same_period_previous_years(self, prepared_data):
        """Test prediction for Room objects"""
        rooms, nc12s = prepared_data

        target_room = None
        for room in rooms:
            if len(room.sales_history) > 0:
                target_room = room
                break

        if not target_room:
            pytest.skip("No Room with sales data found")

        analyzer = PerformanceAnalyzer()
        performance_data = analyzer.analyze(
            wrap_entity(target_room), lookback_years=3, granularity="monthly"
        )

        if len(performance_data.periods) == 0:
            pytest.skip("No periods in performance data")

        predictor = Predictor(performance_data)
        from src.utils import get_next_period_label

        next_period = get_next_period_label("monthly")

        start_time = time.perf_counter()
        prediction = predictor.predict(
            target_time=next_period, method="avg_same_period_previous_years", buffer_percentage=10.0
        )
        pred_time = (time.perf_counter() - start_time) * 1000

        assert isinstance(prediction, Prediction)
        assert prediction.predicted_quantity > 0

        print(f"\nRoom Prediction:")
        print(f"  Room ID: {target_room.id}")
        print(f"  Period: {prediction.period_label}")
        print(f"  Baseline: {prediction.baseline:.2f}")
        print(f"  Buffer: {prediction.buffer_percentage}%")
        print(f"  Predicted: {prediction.predicted_quantity:.2f}")
        print(f"  Prediction time: {pred_time:.2f} ms")

    def test_room_prediction_last_n_periods(self, prepared_data):
        """Test prediction for Room objects"""
        rooms, nc12s = prepared_data

        target_room = None
        for room in rooms:
            if len(room.sales_history) > 0:
                target_room = room
                break

        if not target_room:
            pytest.skip("No Room with sales data found")

        analyzer = PerformanceAnalyzer()
        performance_data = analyzer.analyze(
            wrap_entity(target_room), lookback_years=3, granularity="monthly"
        )

        if len(performance_data.periods) == 0:
            pytest.skip("No periods in performance data")

        predictor = Predictor(performance_data)
        from src.utils import get_next_period_label

        next_period = get_next_period_label("monthly")

        start_time = time.perf_counter()
        prediction = predictor.predict(
            target_time=next_period, method="avg_last_n_periods", buffer_percentage=10.0
        )
        pred_time = (time.perf_counter() - start_time) * 1000

        assert isinstance(prediction, Prediction)
        assert prediction.predicted_quantity > 0

        print(f"\nRoom Prediction:")
        print(f"  Room ID: {target_room.id}")
        print(f"  Period: {prediction.period_label}")
        print(f"  Baseline: {prediction.baseline:.2f}")
        print(f"  Buffer: {prediction.buffer_percentage}%")
        print(f"  Predicted: {prediction.predicted_quantity:.2f}")
        print(f"  Prediction time: {pred_time:.2f} ms")

    def test_batch_predictions(self, prepared_data):
        """Test predicting for multiple items"""
        rooms, nc12s = prepared_data

        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]

        if not nc12s_with_sales:
            pytest.skip("No 12NCs with sales data found")

        test_items = nc12s_with_sales[:5]
        analyzer = PerformanceAnalyzer()
        from src.utils import get_next_period_label

        predictions = []
        start_time = time.perf_counter()

        for nc in test_items:
            performance_data = analyzer.analyze(
                wrap_entity(nc), lookback_years=3, granularity="monthly"
            )
            if len(performance_data.periods) == 0:
                continue

            predictor = Predictor(performance_data)
            next_period = get_next_period_label("monthly")
            prediction = predictor.predict(
                target_time=next_period,
                method="avg_same_period_previous_years",
                buffer_percentage=10.0,
            )
            predictions.append(prediction)

        batch_time = (time.perf_counter() - start_time) * 1000

        if predictions:
            avg_predicted = sum(p.predicted_quantity for p in predictions) / len(predictions)
            total_predicted = sum(p.predicted_quantity for p in predictions)

            print(f"\nBatch Predictions:")
            print(f"  Items predicted: {len(predictions)}")
            print(f"  Total time: {batch_time:.2f} ms")
            print(f"  Avg time per item: {batch_time / len(predictions):.2f} ms")
            print(f"  Total predicted quantity: {total_predicted:,.2f}")
            print(f"  Avg predicted quantity: {avg_predicted:.2f}")

            print(f"\n  Top 3 predictions:")
            sorted_preds = sorted(predictions, key=lambda p: p.predicted_quantity, reverse=True)
            for idx, pred in enumerate(sorted_preds[:3]):
                print(f"    {idx+1}. {pred.predicted_quantity:.2f}")

    def test_prediction_validation(self, prepared_data):
        """Test prediction validation and error handling"""
        rooms, nc12s = prepared_data

        target_nc = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                target_nc = nc
                break

        if not target_nc:
            pytest.skip("No 12NC with sales data found")

        analyzer = PerformanceAnalyzer()
        performance_data = analyzer.analyze(
            wrap_entity(target_nc), lookback_years=3, granularity="monthly"
        )

        if len(performance_data.periods) == 0:
            pytest.skip("No periods in performance data")

        predictor = Predictor(performance_data)
        from src.utils import get_next_period_label

        next_period = get_next_period_label("monthly")

        # Test invalid buffer percentage
        try:
            prediction = predictor.predict(
                target_time=next_period, method="avg_last_n_periods", buffer_percentage=-10.0
            )
            # If no error, that's fine - implementation may not validate
            print(f"\nPrediction Validation:")
            print(f"  Negative buffer handled: {prediction.buffer_percentage}")
        except ValueError as e:
            print(f"\nPrediction Validation:")
            print(f"  Negative buffer rejected: {str(e)}")

        # Test valid prediction
        prediction = predictor.predict(
            target_time=next_period, method="avg_last_n_periods", buffer_percentage=10.0
        )
        assert prediction.predicted_quantity > 0
        print(f"  Valid prediction: {prediction.predicted_quantity:.2f}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================


if __name__ == "__main__":
    """Run tests standalone with file pickers"""
    pytest.main(
        [
            __file__,
            "-v",
            "-s",
            "--tb=short",
        ]
    )
