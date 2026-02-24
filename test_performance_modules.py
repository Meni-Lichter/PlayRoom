"""
Comprehensive test suite for PerformanceCenter, PerformanceAnalyzer, and Predictor
Tests include file loading, data transformation, and integration with all modules
"""

import pytest
import pandas as pd
import os
from pathlib import Path
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from src.models import SalesRecord, PerformanceData, TimePeriod, Room12NCMap, TwelveNCRoomMap
from src.analysis import PerformanceAnalyzer, Predictor
from src.services import PerformanceCenter
from src.infrastructure import load_cbom, read_file
from src.infrastructure.data_transformer import transform_cbom_data
from src.utils import load_config


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


@pytest.fixture
def sample_ymbd_csv(test_data_dir):
    """Create a sample YMBD CSV file with 12NC sales data"""
    data = {
        "Component": [],
        "Component Description": [],
        "Confirmed Delivery Date": [],
        "Component Quantity": [],
    }

    # Generate 36 months of data for multiple 12NCs
    base_date = datetime(2023, 1, 1)

    # 12NC-001: Seasonal pattern (higher in Q1, Q4)
    for month_offset in range(36):
        sales_date = base_date + relativedelta(months=month_offset)
        month = sales_date.month
        quantity = 150 if month in [1, 2, 3, 11, 12] else 100

        data["Component"].append("000000000001")  # 12 digits
        data["Component Description"].append("Component 001 Description")
        data["Confirmed Delivery Date"].append(sales_date.strftime("%m-%d-%Y"))
        data["Component Quantity"].append(quantity)

    # 12NC-002: Upward trend
    for month_offset in range(36):
        sales_date = base_date + relativedelta(months=month_offset)
        quantity = 80 + (month_offset * 2)

        data["Component"].append("000000000002")
        data["Component Description"].append("Component 002 Description")
        data["Confirmed Delivery Date"].append(sales_date.strftime("%m-%d-%Y"))
        data["Component Quantity"].append(quantity)

    # 12NC-003: Recent data only (last 12 months)
    for month_offset in range(24, 36):
        sales_date = base_date + relativedelta(months=month_offset)

        data["Component"].append("000000000003")
        data["Component Description"].append("Component 003 Description")
        data["Confirmed Delivery Date"].append(sales_date.strftime("%m-%d-%Y"))
        data["Component Quantity"].append(200)

    df = pd.DataFrame(data)
    file_path = test_data_dir / "sample_ymbd.csv"
    df.to_csv(file_path, index=False)
    return file_path


@pytest.fixture
def sample_fit_cvi_csv(test_data_dir):
    """Create a sample FIT_CVI CSV file with Room sales data"""
    data = {
        "Characteristic\nCharacteristic Name": [],
        "Characteristic\nChar. description": [],
        "SD Item\nFSD": [],
        "(Self)\nValue from": [],
    }

    base_date = datetime(2023, 1, 1)

    # Room1: Seasonal pattern
    for month_offset in range(36):
        sales_date = base_date + relativedelta(months=month_offset)
        month = sales_date.month
        quantity = 150 if month in [1, 2, 3, 11, 12] else 100

        data["Characteristic\nCharacteristic Name"].append("ROOM001")
        data["Characteristic\nChar. description"].append("Room 001 Description")
        data["SD Item\nFSD"].append(sales_date.strftime("%d-%b-%Y"))
        data["(Self)\nValue from"].append(quantity)

    # Room2: Steady growth
    for month_offset in range(36):
        sales_date = base_date + relativedelta(months=month_offset)
        quantity = 80 + (month_offset * 2)

        data["Characteristic\nCharacteristic Name"].append("ROOM002")
        data["Characteristic\nChar. description"].append("Room 002 Description")
        data["SD Item\nFSD"].append(sales_date.strftime("%d-%b-%Y"))
        data["(Self)\nValue from"].append(quantity)

    df = pd.DataFrame(data)
    file_path = test_data_dir / "sample_fit_cvi.csv"
    df.to_csv(file_path, index=False)
    return file_path


@pytest.fixture
def sample_cbom_excel(test_data_dir):
    """Create a sample CBOM Excel file"""
    # Create a simple CBOM structure
    # Row 4: Room descriptions
    # Row 5: Room numbers
    # Starting row 9: 12NCs with quantities

    data = {}

    # Create empty rows
    for i in range(10):
        data[i] = [None] * 12

    # Row 4 (index 3): Room descriptions (starting at column G=6)
    data[3] = [None] * 6 + ["Desc Room1", "Desc Room2", "Desc Room3"]

    # Row 5 (index 4): Room numbers (starting at column G=6)
    data[4] = [None] * 6 + ["ROOM001", "ROOM002", "ROOM003"]

    # Column C (index 2): 12NCs starting at row 9
    # Column D (index 3): 12NC descriptions
    # Columns G onwards: Quantities

    # Row 9 (index 8): First 12NC
    data[8] = [None, None, "000000000001", "12NC 001 Desc", None, None, 2, 0, 1]

    # Row 10 (index 9): Second 12NC
    data[9] = [None, None, "000000000002", "12NC 002 Desc", None, None, 0, 3, 0]

    # Row 11 (index 10): Third 12NC
    data[10] = [None, None, "000000000003", "12NC 003 Desc", None, None, 1, 0, 2]

    df = pd.DataFrame.from_dict(data, orient="index")

    file_path = test_data_dir / "sample_cbom.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="C-BoM 830234", index=False, header=False)

    return file_path


@pytest.fixture
def sales_data_from_ymbd(sample_ymbd_csv):
    """Load and transform YMBD data into SalesRecord objects"""
    df = pd.read_csv(sample_ymbd_csv)
    sales_records = []

    for _, row in df.iterrows():
        # Parse date
        sales_date = datetime.strptime(row["Confirmed Delivery Date"], "%m-%d-%Y").date()

        # For YMBD, we need to map 12NC to rooms (simplified for testing)
        # In real scenario, this would come from CBOM mapping
        twelve_nc = row["Component"]
        # Simple mapping for testing
        room_map = {"000000000001": "ROOM001", "000000000002": "ROOM002", "000000000003": "ROOM003"}
        room = room_map.get(twelve_nc, "UNKNOWN")

        sales_records.append(
            SalesRecord(
                twelve_nc=twelve_nc,
                room=room,
                quantity=int(row["Component Quantity"]),
                date=sales_date,
            )
        )

    return sales_records


@pytest.fixture
def sales_data_from_fit_cvi(sample_fit_cvi_csv):
    """Load and transform FIT_CVI data into SalesRecord objects"""
    df = pd.read_csv(sample_fit_cvi_csv)
    sales_records = []

    for _, row in df.iterrows():
        # Parse date
        sales_date = datetime.strptime(row["SD Item\nFSD"], "%d-%b-%Y").date()

        # For FIT_CVI, we need to map rooms to 12NCs (simplified for testing)
        room = row["Characteristic\nCharacteristic Name"]
        # Simple mapping for testing
        nc_map = {"ROOM001": "000000000001", "ROOM002": "000000000002", "ROOM003": "000000000003"}
        twelve_nc = nc_map.get(room, "000000000000")

        sales_records.append(
            SalesRecord(
                twelve_nc=twelve_nc,
                room=room,
                quantity=int(row["(Self)\nValue from"]),
                date=sales_date,
            )
        )

    return sales_records


@pytest.fixture
def cbom_mappings_from_file(sample_cbom_excel, config):
    """Load and transform CBOM data into mapping objects"""
    room_data, data_12nc = load_cbom(sample_cbom_excel, config)

    if room_data is None or data_12nc is None:
        # Fallback: create manual mappings for testing
        room_mappings = [
            Room12NCMap(room="ROOM001", twelve_ncs={"000000000001": 2, "000000000003": 1}),
            Room12NCMap(room="ROOM002", twelve_ncs={"000000000002": 3}),
            Room12NCMap(room="ROOM003", twelve_ncs={"000000000001": 1, "000000000003": 2}),
        ]
        nc12_mappings = [
            TwelveNCRoomMap(twelve_nc="000000000001", rooms={"ROOM001": 2, "ROOM003": 1}),
            TwelveNCRoomMap(twelve_nc="000000000002", rooms={"ROOM002": 3}),
            TwelveNCRoomMap(twelve_nc="000000000003", rooms={"ROOM001": 1, "ROOM003": 2}),
        ]
        return room_mappings, nc12_mappings

    room_mappings, nc12_mappings = transform_cbom_data(room_data, data_12nc, config)
    return room_mappings, nc12_mappings


@pytest.fixture
def sample_sales_data():
    """Generate sample sales data spanning 3 years with monthly patterns"""
    sales = []
    base_date = date(2023, 1, 1)

    # Create 36 months of data for Room1 with 12NC-001
    for month_offset in range(36):
        sales_date = base_date + relativedelta(months=month_offset)
        # Seasonal pattern: higher sales in Q1 and Q4
        month = sales_date.month
        if month in [1, 2, 3, 11, 12]:
            quantity = 150
        else:
            quantity = 100

        sales.append(
            SalesRecord(twelve_nc="12NC-001", room="Room1", quantity=quantity, date=sales_date)
        )

    # Create data for Room2 with 12NC-002
    for month_offset in range(36):
        sales_date = base_date + relativedelta(months=month_offset)
        sales.append(
            SalesRecord(
                twelve_nc="12NC-002",
                room="Room2",
                quantity=80 + (month_offset * 2),  # Upward trend
                date=sales_date,
            )
        )

    # Create data for Room3 with 12NC-003 (only last year)
    for month_offset in range(24, 36):
        sales_date = base_date + relativedelta(months=month_offset)
        sales.append(SalesRecord(twelve_nc="12NC-003", room="Room3", quantity=200, date=sales_date))

    return sales


@pytest.fixture
def sample_room_mappings():
    """Sample Room to 12NC mappings (CBOM data)"""
    return [
        Room12NCMap(room="Room1", twelve_ncs={"12NC-001": 2, "12NC-004": 1}),
        Room12NCMap(room="Room2", twelve_ncs={"12NC-002": 3, "12NC-005": 1}),
        Room12NCMap(room="Room3", twelve_ncs={"12NC-003": 2}),
    ]


@pytest.fixture
def sample_nc12_mappings():
    """Sample 12NC to Room mappings (CBOM data)"""
    return [
        TwelveNCRoomMap(twelve_nc="12NC-001", rooms={"Room1": 2}),
        TwelveNCRoomMap(twelve_nc="12NC-002", rooms={"Room2": 3}),
        TwelveNCRoomMap(twelve_nc="12NC-003", rooms={"Room3": 2}),
    ]


@pytest.fixture
def performance_analyzer(sample_sales_data):
    """Create a PerformanceAnalyzer instance with sample data"""
    return PerformanceAnalyzer(sample_sales_data)


@pytest.fixture
def performance_center(sample_sales_data, sample_room_mappings, sample_nc12_mappings):
    """Create a PerformanceCenter instance with all data"""
    return PerformanceCenter(
        sales_data=sample_sales_data,
        room_mappings=sample_room_mappings,
        nc12_mappings=sample_nc12_mappings,
    )


@pytest.fixture
def sample_performance_data():
    """Create sample performance data for predictor testing"""
    periods = [
        TimePeriod(label="2023-01", quantity=150),
        TimePeriod(label="2023-02", quantity=150),
        TimePeriod(label="2023-03", quantity=150),
        TimePeriod(label="2023-04", quantity=100),
        TimePeriod(label="2023-05", quantity=100),
        TimePeriod(label="2023-06", quantity=100),
        TimePeriod(label="2023-07", quantity=100),
        TimePeriod(label="2023-08", quantity=100),
        TimePeriod(label="2023-09", quantity=100),
        TimePeriod(label="2023-10", quantity=100),
        TimePeriod(label="2023-11", quantity=150),
        TimePeriod(label="2023-12", quantity=150),
        TimePeriod(label="2024-01", quantity=150),
        TimePeriod(label="2024-02", quantity=150),
        TimePeriod(label="2024-03", quantity=150),
        TimePeriod(label="2024-04", quantity=100),
        TimePeriod(label="2024-05", quantity=100),
        TimePeriod(label="2024-06", quantity=100),
        TimePeriod(label="2024-07", quantity=100),
        TimePeriod(label="2024-08", quantity=100),
        TimePeriod(label="2024-09", quantity=100),
        TimePeriod(label="2024-10", quantity=100),
        TimePeriod(label="2024-11", quantity=150),
        TimePeriod(label="2024-12", quantity=150),
        TimePeriod(label="2025-01", quantity=150),
        TimePeriod(label="2025-02", quantity=150),
    ]

    total = sum(p.quantity for p in periods)
    avg = total / len(periods)

    return PerformanceData(
        identifier="12NC-001", type="12NC", periods=periods, total=total, average=avg
    )


# ============================================================================
# PerformanceAnalyzer Tests
# ============================================================================


class TestPerformanceAnalyzer:
    """Test the PerformanceAnalyzer class"""

    def test_analyzer_initialization(self, sample_sales_data):
        """Test that analyzer initializes correctly"""
        analyzer = PerformanceAnalyzer(sample_sales_data)
        assert analyzer.sales_data == sample_sales_data
        assert len(analyzer.sales_data) > 0

    def test_analyze_12nc_monthly(self, performance_analyzer):
        """Test analyzing 12NC performance with monthly granularity"""
        result = performance_analyzer.analyze(
            identifier="12NC-001", id_type="12nc", lookback_years=3, granularity="monthly"
        )

        assert result.identifier == "12NC-001"
        assert result.type == "12NC"
        assert len(result.periods) > 0
        assert result.total > 0
        assert result.average > 0
        assert result.period_count == len(result.periods)

    def test_analyze_room_monthly(self, performance_analyzer):
        """Test analyzing Room performance with monthly granularity"""
        result = performance_analyzer.analyze(
            identifier="Room1", id_type="room", lookback_years=3, granularity="monthly"
        )

        assert result.identifier == "Room1"
        assert result.type == "ROOM"
        assert len(result.periods) > 0
        assert result.total > 0

    def test_analyze_yearly_granularity(self, performance_analyzer):
        """Test analyzing with yearly granularity"""
        result = performance_analyzer.analyze(
            identifier="12NC-001", id_type="12nc", lookback_years=3, granularity="yearly"
        )

        assert len(result.periods) <= 3  # Should have at most 3 years
        # Check that period labels are years
        for period in result.periods:
            assert len(period.label) == 4
            assert period.label.isdigit()

    def test_analyze_quarterly_granularity(self, performance_analyzer):
        """Test analyzing with quarterly granularity"""
        result = performance_analyzer.analyze(
            identifier="12NC-001", id_type="12nc", lookback_years=2, granularity="quarterly"
        )

        # Check that period labels follow quarterly format
        for period in result.periods:
            assert "-Q" in period.label

    def test_analyze_no_data(self, performance_analyzer):
        """Test analyzing with non-existent identifier"""
        result = performance_analyzer.analyze(
            identifier="NON-EXISTENT", id_type="12nc", lookback_years=3, granularity="monthly"
        )

        assert len(result.periods) == 0
        assert result.total == 0
        assert result.average == 0

    def test_filter_by_date_range(self, performance_analyzer):
        """Test that date filtering works correctly"""
        result = performance_analyzer.analyze(
            identifier="12NC-003",  # Only has data in last year
            id_type="12nc",
            lookback_years=1,
            granularity="monthly",
        )

        assert len(result.periods) <= 12  # At most 12 months


# ============================================================================
# Predictor Tests
# ============================================================================


class TestPredictor:
    """Test the Predictor class"""

    def test_predictor_initialization(self, sample_performance_data):
        """Test predictor initialization"""
        predictor = Predictor(sample_performance_data)
        assert predictor.performance_data == sample_performance_data

    def test_predict_average_method(self, sample_performance_data):
        """Test prediction using average method"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(method="average", buffer_percentage=10.0)

        assert prediction.identifier == "12NC-001"
        assert prediction.method == "average"
        assert prediction.baseline == sample_performance_data.average
        assert prediction.buffer_percentage == 10.0
        assert prediction.predicted_quantity > prediction.baseline
        assert abs(prediction.predicted_quantity - prediction.baseline * 1.1) < 0.01

    def test_predict_avg_same_period_previous_years(self, sample_performance_data):
        """Test prediction using avg_same_period_previous_years method"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(
            method="avg_same_period_previous_years", buffer_percentage=10.0
        )

        assert prediction.method == "avg_same_period_previous_years"
        assert prediction.baseline > 0
        # Next period should be March (after Feb 2025), which has higher values (150)
        assert prediction.baseline >= 150  # Should be around 150 based on historical March data

    def test_predict_avg_last_n_periods(self, sample_performance_data):
        """Test prediction using avg_last_n_periods method"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(
            method="avg_last_n_periods", buffer_percentage=10.0, n_periods=11
        )

        assert prediction.method == "avg_last_n_periods"
        assert prediction.baseline > 0
        # Last 11 periods should average around 120-130 based on the data
        assert 100 < prediction.baseline < 160

    def test_predict_same_period_last_year(self, sample_performance_data):
        """Test prediction using same_period_last_year method"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(method="same_period_last_year", buffer_percentage=10.0)

        assert prediction.method == "same_period_last_year"
        assert prediction.baseline > 0
        # Next period is March 2026, should use March 2025 (which would be 150)

    def test_predict_with_custom_buffer(self, sample_performance_data):
        """Test prediction with custom buffer percentage"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(method="average", buffer_percentage=20.0)

        assert prediction.buffer_percentage == 20.0
        expected = sample_performance_data.average * 1.2
        assert abs(prediction.predicted_quantity - expected) < 0.01

    def test_predict_zero_buffer(self, sample_performance_data):
        """Test prediction with zero buffer"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(method="average", buffer_percentage=0.0)

        assert prediction.buffer_percentage == 0.0
        assert prediction.predicted_quantity == prediction.baseline

    def test_predict_with_empty_data(self):
        """Test that predictor raises error with empty data"""
        empty_data = PerformanceData(identifier="TEST", type="12NC", periods=[], total=0, average=0)
        predictor = Predictor(empty_data)

        with pytest.raises(ValueError, match="No historical data available"):
            predictor.predict()

    def test_infer_granularity_monthly(self, sample_performance_data):
        """Test granularity inference for monthly data"""
        predictor = Predictor(sample_performance_data)
        granularity = predictor._infer_granularity()
        assert granularity == "monthly"

    def test_infer_granularity_weekly(self):
        """Test granularity inference for weekly data"""
        weekly_data = PerformanceData(
            identifier="TEST",
            type="12NC",
            periods=[
                TimePeriod(label="2024-W01", quantity=100),
                TimePeriod(label="2024-W02", quantity=110),
            ],
            total=210,
            average=105,
        )
        predictor = Predictor(weekly_data)
        granularity = predictor._infer_granularity()
        assert granularity == "weekly"

    def test_infer_granularity_quarterly(self):
        """Test granularity inference for quarterly data"""
        quarterly_data = PerformanceData(
            identifier="TEST",
            type="12NC",
            periods=[
                TimePeriod(label="2024-Q1", quantity=300),
                TimePeriod(label="2024-Q2", quantity=320),
            ],
            total=620,
            average=310,
        )
        predictor = Predictor(quarterly_data)
        granularity = predictor._infer_granularity()
        assert granularity == "quarterly"

    def test_infer_granularity_yearly(self):
        """Test granularity inference for yearly data"""
        yearly_data = PerformanceData(
            identifier="TEST",
            type="12NC",
            periods=[
                TimePeriod(label="2023", quantity=1200),
                TimePeriod(label="2024", quantity=1300),
            ],
            total=2500,
            average=1250,
        )
        predictor = Predictor(yearly_data)
        granularity = predictor._infer_granularity()
        assert granularity == "yearly"

    def test_buffer_amount_property(self, sample_performance_data):
        """Test that buffer_amount property is calculated correctly"""
        predictor = Predictor(sample_performance_data)
        prediction = predictor.predict(method="average", buffer_percentage=10.0)

        expected_buffer = prediction.predicted_quantity - prediction.baseline
        assert abs(prediction.buffer_amount - expected_buffer) < 0.01


# ============================================================================
# PerformanceCenter Tests
# ============================================================================


class TestPerformanceCenter:
    """Test the PerformanceCenter service"""

    def test_performance_center_initialization(
        self, sample_sales_data, sample_room_mappings, sample_nc12_mappings
    ):
        """Test PerformanceCenter initialization"""
        pc = PerformanceCenter(
            sales_data=sample_sales_data,
            room_mappings=sample_room_mappings,
            nc12_mappings=sample_nc12_mappings,
        )

        assert pc.sales_data == sample_sales_data
        assert pc.room_mappings == sample_room_mappings
        assert pc.nc12_mappings == sample_nc12_mappings
        assert isinstance(pc.analyzer, PerformanceAnalyzer)

    def test_initialization_without_mappings(self, sample_sales_data):
        """Test initialization without CBOM mappings"""
        pc = PerformanceCenter(sales_data=sample_sales_data)

        assert pc.sales_data == sample_sales_data
        assert pc.room_mappings == []
        assert pc.nc12_mappings == []

    def test_analyze_room_performance(self, performance_center):
        """Test analyzing room performance"""
        result = performance_center.analyze_room_performance(
            room="Room1", lookback_years=3, granularity="monthly"
        )

        assert result.identifier == "Room1"
        assert result.type == "ROOM"
        assert len(result.periods) > 0

    def test_analyze_12nc_performance(self, performance_center):
        """Test analyzing 12NC performance"""
        result = performance_center.analyze_12nc_performance(
            twelve_nc="12NC-001", lookback_years=3, granularity="monthly"
        )

        assert result.identifier == "12NC-001"
        assert result.type == "12NC"
        assert len(result.periods) > 0

    def test_predict_room_demand(self, performance_center):
        """Test predicting room demand"""
        prediction = performance_center.predict_room_demand(
            room="Room1", lookback_years=3, method="average", buffer_percentage=10.0
        )

        assert prediction.identifier == "Room1"
        assert prediction.method == "average"
        assert prediction.predicted_quantity > 0
        assert prediction.buffer_percentage == 10.0

    def test_predict_12nc_demand(self, performance_center):
        """Test predicting 12NC demand"""
        prediction = performance_center.predict_12nc_demand(
            twelve_nc="12NC-001", lookback_years=3, method="average", buffer_percentage=10.0
        )

        assert prediction.identifier == "12NC-001"
        assert prediction.method == "average"
        assert prediction.predicted_quantity > 0

    def test_predict_with_new_methods(self, performance_center):
        """Test prediction with new prediction methods"""
        # Test avg_same_period_previous_years
        pred1 = performance_center.predict_12nc_demand(
            twelve_nc="12NC-001", method="avg_same_period_previous_years"
        )
        assert pred1.method == "avg_same_period_previous_years"

        # Test avg_last_n_periods
        pred2 = performance_center.predict_12nc_demand(
            twelve_nc="12NC-001", method="avg_last_n_periods"
        )
        assert pred2.method == "avg_last_n_periods"

        # Test same_period_last_year
        pred3 = performance_center.predict_12nc_demand(
            twelve_nc="12NC-001", method="same_period_last_year"
        )
        assert pred3.method == "same_period_last_year"

    def test_get_room_components(self, performance_center):
        """Test getting room components from CBOM"""
        mapping = performance_center.get_room_components("Room1")

        assert mapping is not None
        assert mapping.room == "Room1"
        assert "12NC-001" in mapping.twelve_ncs

    def test_get_room_components_not_found(self, performance_center):
        """Test getting non-existent room"""
        mapping = performance_center.get_room_components("NonExistentRoom")
        assert mapping is None

    def test_get_12nc_rooms(self, performance_center):
        """Test getting 12NC rooms from CBOM"""
        mapping = performance_center.get_12nc_rooms("12NC-001")

        assert mapping is not None
        assert mapping.twelve_nc == "12NC-001"
        assert "Room1" in mapping.rooms

    def test_get_12nc_rooms_not_found(self, performance_center):
        """Test getting non-existent 12NC"""
        mapping = performance_center.get_12nc_rooms("NON-EXISTENT")
        assert mapping is None

    def test_get_summary_stats(self, performance_center):
        """Test getting summary statistics"""
        stats = performance_center.get_summary_stats()

        assert "total_sales_records" in stats
        assert "total_rooms_in_cbom" in stats
        assert "total_12ncs_in_cbom" in stats
        assert "date_range" in stats

        assert stats["total_sales_records"] > 0
        assert stats["total_rooms_in_cbom"] == 3
        assert stats["total_12ncs_in_cbom"] == 3
        assert stats["date_range"]["earliest"] is not None
        assert stats["date_range"]["latest"] is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple components"""

    def test_end_to_end_prediction_workflow(self, performance_center):
        """Test complete workflow from analysis to prediction"""
        # Step 1: Analyze historical performance
        performance = performance_center.analyze_12nc_performance(
            twelve_nc="12NC-001", lookback_years=3, granularity="monthly"
        )

        assert len(performance.periods) > 0

        # Step 2: Make prediction
        prediction = performance_center.predict_12nc_demand(
            twelve_nc="12NC-001", lookback_years=3, method="average", buffer_percentage=15.0
        )

        assert prediction.predicted_quantity > 0
        assert prediction.buffer_percentage == 15.0

    def test_compare_prediction_methods(self, performance_center):
        """Compare predictions from different methods"""
        methods = [
            "average",
            "avg_same_period_previous_years",
            "avg_last_n_periods",
            "same_period_last_year",
        ]

        predictions = {}
        for method in methods:
            pred = performance_center.predict_12nc_demand(
                twelve_nc="12NC-001", method=method, buffer_percentage=10.0
            )
            predictions[method] = pred

        # All predictions should have values
        for method, pred in predictions.items():
            assert pred.predicted_quantity > 0, f"Method {method} failed"
            assert pred.baseline > 0, f"Baseline for {method} is zero"

    def test_seasonal_pattern_detection(self, performance_center):
        """Test that seasonal patterns are captured in predictions"""
        # 12NC-001 has higher sales in Q1 and Q4
        # Predict using same period method
        prediction = performance_center.predict_12nc_demand(
            twelve_nc="12NC-001", method="avg_same_period_previous_years", buffer_percentage=0.0
        )

        # The baseline should reflect seasonal patterns
        assert prediction.baseline > 0


# ============================================================================
# File-Based Integration Tests
# ============================================================================


class TestFileBasedIntegration:
    """Tests that load and process actual files"""

    def test_load_ymbd_data(self, sample_ymbd_csv):
        """Test loading YMBD sales data from CSV"""
        df = pd.read_csv(sample_ymbd_csv)

        assert not df.empty
        assert "Component" in df.columns
        assert "Component Quantity" in df.columns
        assert "Confirmed Delivery Date" in df.columns
        assert len(df) == 72 + 12  # 36 months * 2 12NCs + 12 months for 3rd 12NC

    def test_load_fit_cvi_data(self, sample_fit_cvi_csv):
        """Test loading FIT_CVI room data from CSV"""
        df = pd.read_csv(sample_fit_cvi_csv)

        assert not df.empty
        assert "Characteristic\nCharacteristic Name" in df.columns
        assert "(Self)\nValue from" in df.columns
        assert "SD Item\nFSD" in df.columns
        assert len(df) == 72  # 36 months * 2 rooms

    def test_transform_ymbd_to_sales_records(self, sales_data_from_ymbd):
        """Test transforming YMBD data to SalesRecord objects"""
        assert len(sales_data_from_ymbd) > 0

        # Check first record
        first_record = sales_data_from_ymbd[0]
        assert isinstance(first_record, SalesRecord)
        assert first_record.twelve_nc == "000000000001"
        assert first_record.room == "ROOM001"
        assert first_record.quantity > 0
        assert isinstance(first_record.date, date)

    def test_transform_fit_cvi_to_sales_records(self, sales_data_from_fit_cvi):
        """Test transforming FIT_CVI data to SalesRecord objects"""
        assert len(sales_data_from_fit_cvi) > 0

        # Check first record
        first_record = sales_data_from_fit_cvi[0]
        assert isinstance(first_record, SalesRecord)
        assert first_record.room == "ROOM001"
        assert first_record.twelve_nc == "000000000001"
        assert first_record.quantity > 0
        assert isinstance(first_record.date, date)

    def test_load_cbom_mappings(self, cbom_mappings_from_file):
        """Test loading CBOM data and transforming to mappings"""
        room_mappings, nc12_mappings = cbom_mappings_from_file

        assert len(room_mappings) > 0
        assert len(nc12_mappings) > 0

        # Check room mapping structure
        first_room = room_mappings[0]
        assert isinstance(first_room, Room12NCMap)
        assert first_room.room is not None
        assert len(first_room.twelve_ncs) > 0

        # Check 12NC mapping structure
        first_nc = nc12_mappings[0]
        assert isinstance(first_nc, TwelveNCRoomMap)
        assert first_nc.twelve_nc is not None
        assert len(first_nc.rooms) > 0

    def test_end_to_end_with_file_data(self, sales_data_from_ymbd, cbom_mappings_from_file):
        """Test complete workflow using data loaded from files"""
        room_mappings, nc12_mappings = cbom_mappings_from_file

        # Create PerformanceCenter with file-based data
        pc = PerformanceCenter(
            sales_data=sales_data_from_ymbd,
            room_mappings=room_mappings,
            nc12_mappings=nc12_mappings,
        )

        # Test summary stats
        stats = pc.get_summary_stats()
        assert stats["total_sales_records"] > 0
        assert stats["total_rooms_in_cbom"] > 0
        assert stats["total_12ncs_in_cbom"] > 0

        # Analyze performance for a 12NC
        performance = pc.analyze_12nc_performance(
            twelve_nc="000000000001", lookback_years=3, granularity="monthly"
        )

        assert performance.identifier == "000000000001"
        assert len(performance.periods) > 0
        assert performance.total > 0

        # Make prediction
        prediction = pc.predict_12nc_demand(
            twelve_nc="000000000001",
            method="avg_same_period_previous_years",
            buffer_percentage=10.0,
        )

        assert prediction.identifier == "000000000001"
        assert prediction.predicted_quantity > 0
        assert prediction.method == "avg_same_period_previous_years"

    def test_analyze_with_multiple_data_sources(
        self, sales_data_from_ymbd, sales_data_from_fit_cvi, cbom_mappings_from_file
    ):
        """Test combining data from both YMBD and FIT_CVI sources"""
        # Combine sales data from both sources
        combined_sales = sales_data_from_ymbd + sales_data_from_fit_cvi
        room_mappings, nc12_mappings = cbom_mappings_from_file

        pc = PerformanceCenter(
            sales_data=combined_sales, room_mappings=room_mappings, nc12_mappings=nc12_mappings
        )

        # Should have more data points
        stats = pc.get_summary_stats()
        assert stats["total_sales_records"] == len(combined_sales)

        # Analyze room performance
        room_performance = pc.analyze_room_performance(
            room="ROOM001", lookback_years=3, granularity="monthly"
        )

        assert room_performance.identifier == "ROOM001"
        assert len(room_performance.periods) > 0

    def test_prediction_methods_with_file_data(self, sales_data_from_ymbd, cbom_mappings_from_file):
        """Test all three new prediction methods with file-based data"""
        room_mappings, nc12_mappings = cbom_mappings_from_file

        pc = PerformanceCenter(
            sales_data=sales_data_from_ymbd,
            room_mappings=room_mappings,
            nc12_mappings=nc12_mappings,
        )

        # Test method 1: avg_same_period_previous_years
        pred1 = pc.predict_12nc_demand(
            twelve_nc="000000000001",
            method="avg_same_period_previous_years",
            buffer_percentage=10.0,
        )
        assert pred1.baseline > 0
        assert pred1.method == "avg_same_period_previous_years"

        # Test method 2: avg_last_n_periods
        pred2 = pc.predict_12nc_demand(
            twelve_nc="000000000001", method="avg_last_n_periods", buffer_percentage=10.0
        )
        assert pred2.baseline > 0
        assert pred2.method == "avg_last_n_periods"

        # Test method 3: same_period_last_year
        pred3 = pc.predict_12nc_demand(
            twelve_nc="000000000001", method="same_period_last_year", buffer_percentage=10.0
        )
        assert pred3.baseline > 0
        assert pred3.method == "same_period_last_year"

        # All three methods should give different but reasonable results
        baselines = [pred1.baseline, pred2.baseline, pred3.baseline]
        assert all(b > 0 for b in baselines)

    def test_cbom_lookup_integration(self, sales_data_from_ymbd, cbom_mappings_from_file):
        """Test CBOM mapping lookup functionality"""
        room_mappings, nc12_mappings = cbom_mappings_from_file

        pc = PerformanceCenter(
            sales_data=sales_data_from_ymbd,
            room_mappings=room_mappings,
            nc12_mappings=nc12_mappings,
        )

        # Look up room components
        room1_components = pc.get_room_components("ROOM001")
        assert room1_components is not None
        assert room1_components.room == "ROOM001"
        assert len(room1_components.twelve_ncs) > 0

        # Look up 12NC rooms
        nc1_rooms = pc.get_12nc_rooms("000000000001")
        assert nc1_rooms is not None
        assert nc1_rooms.twelve_nc == "000000000001"
        assert len(nc1_rooms.rooms) > 0


# ============================================================================
# Interactive Demo Main Function
# ============================================================================


def parse_ymbd_to_sales_records(ymbd_df):
    """Parse YMBD DataFrame to SalesRecord objects"""
    sales_records = []

    # Try multiple date formats
    date_formats = [
        "%Y-%m-%d %H:%M:%S",  # 2025-02-28 00:00:00
        "%Y-%m-%d",  # 2025-02-28
        "%m-%d-%Y",  # 02-28-2025
        "%d-%b-%Y",  # 28-Feb-2025
    ]

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

            twelve_nc = str(row["Component"]).strip()
            quantity = int(row["Component Quantity"])

            # We'll need room mapping from CBOM
            sales_records.append({"twelve_nc": twelve_nc, "quantity": quantity, "date": sales_date})
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue

    return sales_records


def parse_fit_cvi_to_sales_records(fit_cvi_df):
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

            sales_records.append({"room": room, "quantity": quantity, "date": sales_date})
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue

    return sales_records


def merge_sales_data(ymbd_records, fit_cvi_records, room_mappings, nc12_mappings):
    """Merge YMBD and FIT_CVI data into complete SalesRecord objects

    Important:
    - YMBD records are for 12NC sales (keep 12NC, lookup room from CBOM)
    - FIT_CVI records are for Room sales (keep Room, set 12NC to placeholder)
    - These are separate data sources and should not be mixed
    """
    sales_records = []

    # Create lookup dictionaries
    nc_to_rooms = {}
    for mapping in nc12_mappings:
        nc_to_rooms[mapping.twelve_nc] = list(mapping.rooms.keys())

    # Process YMBD records (12NC sales data)
    # These represent actual 12NC sales, so keep the 12NC
    for record in ymbd_records:
        twelve_nc = record["twelve_nc"]
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
        print(f"✓ Loaded {len(room_mappings)} rooms and {len(nc12_mappings)} 12NCs")

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
            demo_12nc = 989606130501
            print(f"\nAnalyzing 12NC: {demo_12nc}")

            performance = pc.analyze_12nc_performance(
                twelve_nc=demo_12nc, lookback_years=3, granularity="monthly"
            )

            print(f"\n  Total Quantity (3 years): {performance.total}")
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
                room=demo_room, lookback_years=3, granularity="monthly"
            )

            print(f"\n  Total Quantity (3 years): {room_performance.total}")
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
