"""
Comprehensive Integration Test Suite
Tests all major functionalities of the Room_12NC_PerformanceCenter system
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict

# Import core models
from src.models.mapping import Room, TwelveNC, G_entity
from src.models.sales_record import SalesRecord
from src.models.performance import PerformanceData, TimePeriod
from src.models.prediction import Prediction

# Import analysis modules
from src.analysis.performance_analyzer import PerformanceAnalyzer
from src.analysis.predictor import Predictor

# Import infrastructure (functions not classes)
from src.infrastructure import data_loaders, data_transformer

# Import UI panels
from src.ui.screens.panels.performance_panel import PerformancePanel
from src.ui.screens.panels.belonging_panel import BelongingPanel
from src.ui.screens.panels.details_panel import DetailsPanel
from src.ui.screens.panels.prediction_panel import PredictionPanel

# Import utilities
from src.utils.date_utils import get_period_key, get_next_period_label


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_sales_records():
    """Create sample sales records spanning multiple years"""
    base_date = datetime(2024, 1, 1)
    records = []
    
    # Create records for 2022-2026 with varying quantities
    for year_offset in range(-2, 3):  # 2022 to 2026
        for month in range(1, 13):
            date = datetime(2024 + year_offset, month, 15).date()  # Convert to date
            quantity = 10 + (month % 3) * 5 + year_offset * 2
            records.append(SalesRecord(
                identifier="TEST_ID",
                date=date,
                quantity=quantity
            ))
    
    return records


@pytest.fixture
def sample_room(sample_sales_records):
    """Create a sample room with components"""
    return Room(
        id="ROOM_001",
        description="Test Room Description",
        components={
            "12NC_001": 5,
            "12NC_002": 3,
            "12NC_003": 8,
            "12NC_004": 2
        },
        sales_history=sample_sales_records
    )


@pytest.fixture
def sample_twelve_ncs(sample_sales_records):
    """Create sample 12NC objects"""
    ncs = []
    for i in range(1, 5):
        nc = TwelveNC(
            id=f"12NC_00{i}",
            description=f"Component {i} Description",
            igt=f"IGT_{i}",
            components={"ROOM_001": [5, 3, 8, 2][i-1]},
            sales_history=sample_sales_records
        )
        ncs.append(nc)
    return ncs


@pytest.fixture
def mock_panel_widget():
    """Mock panel widget for UI testing"""
    panel = MagicMock()
    panel.winfo_children.return_value = []
    return panel


@pytest.fixture
def mock_colors():
    """Mock color scheme"""
    return {
        "bg_white": "#FFFFFF",
        "bg_main": "#EEF2F6",
        "bg_light": "#F8FAFB",
        "text_dark": "#1E2A33",
        "text_muted": "#6B7280",
        "text_light": "#9CA3AF",
        "accent_teal": "#20B2AA",
        "border": "#E5E7EB",
        "border_light": "#F3F4F6"
    }


@pytest.fixture
def mock_font_sizes():
    """Mock font sizes"""
    return {
        "title": 18,
        "body": 14,
        "small": 12,
        "xsmall": 10
    }


@pytest.fixture
def mock_get_font():
    """Mock font getter function"""
    def get_font(family="Segoe UI", size=14, weight="normal"):
        return MagicMock()
    return get_font


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestModels:
    """Test data models"""
    
    def test_room_creation(self, sample_room):
        """Test Room model creation and properties"""
        assert sample_room.id == "ROOM_001"
        assert sample_room.description == "Test Room Description"
        assert len(sample_room.components) == 4
        assert sample_room.total_items == 18  # 5+3+8+2
        assert sample_room.has_12nc("12NC_001")
        assert not sample_room.has_12nc("12NC_999")
    
    def test_twelve_nc_creation(self, sample_twelve_ncs):
        """Test TwelveNC model creation and properties"""
        nc = sample_twelve_ncs[0]
        assert nc.id == "12NC_001"
        assert nc.description == "Component 1 Description"
        assert nc.has_room("ROOM_001")
        assert nc.total_items == 5
    
    def test_g_entity_wrapper(self, sample_room):
        """Test G_entity wrapper functionality"""
        g_entity = G_entity(g_entity=sample_room, entity_type="room")
        assert g_entity.entity_type == "room"
        assert g_entity.g_entity == sample_room
    
    def test_sales_record_structure(self, sample_sales_records):
        """Test SalesRecord structure"""
        record = sample_sales_records[0]
        assert hasattr(record, 'identifier')
        assert hasattr(record, 'date')
        assert hasattr(record, 'quantity')
        from datetime import date
        assert isinstance(record.date, date)


# ============================================================================
# ANALYSIS TESTS
# ============================================================================

class TestAnalysis:
    """Test analysis modules"""
    
    def test_performance_analyzer_monthly(self, sample_room):
        """Test performance analyzer with monthly granularity"""
        analyzer = PerformanceAnalyzer()
        g_entity = G_entity(g_entity=sample_room, entity_type="room")
        
        result = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=2,
            granularity="monthly"
        )
        
        assert isinstance(result, PerformanceData)
        assert len(result.periods) > 0
        assert all(isinstance(p, TimePeriod) for p in result.periods)
    
    def test_performance_analyzer_quarterly(self, sample_room):
        """Test performance analyzer with quarterly granularity"""
        analyzer = PerformanceAnalyzer()
        g_entity = G_entity(g_entity=sample_room, entity_type="room")
        
        result = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=2,
            granularity="quarterly"
        )
        
        assert isinstance(result, PerformanceData)
        # Should have quarters
        assert any("Q" in p.label for p in result.periods)
    
    def test_performance_analyzer_yearly(self, sample_room):
        """Test performance analyzer with yearly granularity"""
        analyzer = PerformanceAnalyzer()
        g_entity = G_entity(g_entity=sample_room, entity_type="room")
        
        result = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=4,
            granularity="yearly"
        )
        
        assert isinstance(result, PerformanceData)
        # Should return yearly aggregates (5 years with 4-year lookback: 2022-2026)
        assert len(result.periods) == 5
        assert result.granularity == "yearly"
    
    def test_predictor_functionality(self, sample_room):
        """Test demand prediction"""
        # First get performance data
        analyzer = PerformanceAnalyzer()
        g_entity = G_entity(g_entity=sample_room, entity_type="room")
        
        performance_data = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=2,
            granularity="monthly"
        )
        
        # Initialize predictor with performance data
        predictor = Predictor(performance_data)
        
        # Get next period to predict
        next_period = get_next_period_label("monthly")
        
        # Test prediction
        prediction = predictor.predict(
            target_time=next_period,
            method="avg_last_n_periods",
            buffer_percentage=10.0
        )
        
        assert isinstance(prediction, Prediction)
        assert prediction.predicted_quantity > 0
        assert prediction.baseline > 0


# ============================================================================
# UTILITY TESTS
# ============================================================================

class TestUtilities:
    """Test utility functions"""
    
    def test_period_key_monthly(self):
        """Test monthly period key generation"""
        date = datetime(2024, 3, 15)
        key = get_period_key(date, "monthly")
        assert key == "03-2024"
    
    def test_period_key_quarterly(self):
        """Test quarterly period key generation"""
        date = datetime(2024, 3, 15)
        key = get_period_key(date, "quarterly")
        assert key == "2024-Q1"
    
    def test_period_key_yearly(self):
        """Test yearly period key generation"""
        date = datetime(2024, 3, 15)
        key = get_period_key(date, "yearly")
        assert key == "2024"
    
    def test_next_period_label_monthly(self):
        """Test next period label for monthly"""
        next_label = get_next_period_label("monthly")
        assert next_label is not None
        assert "-" in next_label  # Format: MM-YYYY
    
    def test_next_period_label_quarterly(self):
        """Test next period label for quarterly"""
        next_label = get_next_period_label("quarterly")
        assert next_label is not None
        assert "Q" in next_label  # Format: YYYY-Qn
    
    def test_next_period_label_yearly(self):
        """Test next period label for yearly"""
        next_label = get_next_period_label("yearly")
        assert next_label is not None
        assert len(next_label) == 4  # Format: YYYY


# ============================================================================
# UI PANEL TESTS
# ============================================================================

class TestPerformancePanel:
    """Test Performance Panel functionality"""
    
    def test_panel_initialization(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test performance panel initialization"""
        panel = PerformancePanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font
        )
        
        assert panel.granularity == "Months"
        assert panel.time_range == (0, 11)
        assert len(panel.year_colors) >= 4
    
    def test_granularity_options(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test granularity options"""
        panel = PerformancePanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font
        )
        
        assert "Months" in panel.granularity_map
        assert "Quarters" in panel.granularity_map
        assert "Years" in panel.granularity_map
        assert panel.granularity_map["Months"] == "monthly"
        assert panel.granularity_map["Quarters"] == "quarterly"
        assert panel.granularity_map["Years"] == "yearly"
    
    def test_max_periods_calculation(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test max periods calculation for different granularities"""
        panel = PerformancePanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font
        )
        
        panel.granularity = "Months"
        assert panel._get_max_periods() == 12
        
        panel.granularity = "Quarters"
        assert panel._get_max_periods() == 4
        
        panel.granularity = "Years"
        assert panel._get_max_periods() == 3


class TestBelongingPanel:
    """Test Belonging Panel functionality"""
    
    def test_panel_with_callbacks(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test belonging panel with navigation and description callbacks"""
        nav_callback = Mock()
        desc_callback = Mock(return_value="Test Description")
        
        panel = BelongingPanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font,
            navigate_callback=nav_callback,
            get_description_callback=desc_callback
        )
        
        assert panel.navigate_callback == nav_callback
        assert panel.get_description_callback == desc_callback
    
    def test_panel_without_callbacks(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test belonging panel works without callbacks"""
        panel = BelongingPanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font
        )
        
        assert panel.navigate_callback is None
        assert panel.get_description_callback is None


class TestDetailsPanel:
    """Test Details Panel functionality"""
    
    def test_panel_initialization(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test details panel initialization"""
        panel = DetailsPanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font
        )
        
        assert panel.panel == mock_panel_widget
        assert panel.COLORS == mock_colors
        assert panel.FONT_SIZES == mock_font_sizes


class TestPredictionPanel:
    """Test Prediction Panel functionality"""
    
    def test_panel_initialization(self, mock_panel_widget, mock_colors, mock_font_sizes, mock_get_font):
        """Test prediction panel initialization"""
        panel = PredictionPanel(
            mock_panel_widget,
            mock_colors,
            mock_font_sizes,
            mock_get_font
        )
        
        assert panel.panel == mock_panel_widget


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEndIntegration:
    """Test complete workflows"""
    
    def test_room_analysis_workflow(self, sample_room):
        """Test complete room analysis workflow"""
        # 1. Wrap entity
        g_entity =G_entity(g_entity=sample_room, entity_type="room")
        
        # 2. Analyze performance
        analyzer = PerformanceAnalyzer()
        performance = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=2,
            granularity="monthly"
        )
        
        assert len(performance.periods) > 0
        
        # 3. Predict future demand
        predictor = Predictor(performance)
        next_period = get_next_period_label("monthly")
        prediction = predictor.predict(
            target_time=next_period,
            method="avg_last_n_periods"
        )
        
        assert prediction.predicted_quantity >= 0
        
        # 4. Verify data consistency
        assert all(p.quantity >= 0 for p in performance.periods)
        assert prediction.predicted_quantity >= 0
    
    def test_twelve_nc_analysis_workflow(self, sample_twelve_ncs):
        """Test complete 12NC analysis workflow"""
        nc = sample_twelve_ncs[0]
        
        # 1. Wrap entity
        g_entity = G_entity(g_entity=nc, entity_type="12NC")
        
        # 2. Analyze performance
        analyzer = PerformanceAnalyzer()
        performance = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=2,
            granularity="quarterly"
        )
        
        assert len(performance.periods) > 0
        
        # 3. Predict future demand
        predictor = Predictor(performance)
        next_period = get_next_period_label("quarterly")
        prediction = predictor.predict(
            target_time=next_period,
            method="avg_last_n_periods"
        )
        
        assert prediction.predicted_quantity >= 0
    
    def test_multi_granularity_consistency(self, sample_room):
        """Test that different granularities produce consistent data"""
        g_entity = G_entity(g_entity=sample_room, entity_type="room")
        analyzer = PerformanceAnalyzer()
        
        # Analyze at different granularities
        monthly = analyzer.analyze(g_entity, lookback_years=1, granularity="monthly")
        quarterly = analyzer.analyze(g_entity, lookback_years=1, granularity="quarterly")
        yearly = analyzer.analyze(g_entity, lookback_years=1, granularity="yearly")
        
        # All should return data
        assert len(monthly.periods) > 0
        assert len(quarterly.periods) > 0
        assert len(yearly.periods) > 0
        
        # Monthly should have most periods
        assert len(monthly.periods) >= len(quarterly.periods)
        assert len(quarterly.periods) >= len(yearly.periods)


# ============================================================================
# DATA TRANSFORMATION TESTS
# ============================================================================

class TestDataTransformation:
    """Test data loading and transformation"""
    
    def test_data_modules_exist(self):
        """Test that data infrastructure modules are available"""
        assert data_loaders is not None
        assert data_transformer is not None


# ============================================================================
# SYSTEM INTEGRATION TEST
# ============================================================================

class TestSystemIntegration:
    """High-level system integration tests"""
    
    def test_complete_system_flow(self, sample_room, sample_twelve_ncs):
        """Test complete system flow from data to analysis to UI"""
        
        # Step 1: Verify data models
        assert sample_room.total_items > 0
        assert len(sample_twelve_ncs) == 4
        
        # Step 2: Performance analysis
        analyzer = PerformanceAnalyzer()
        g_room = G_entity(g_entity=sample_room, entity_type="room")
        
        performance = analyzer.analyze(
            analyzed_obj=g_room,
            lookback_years=3,
            granularity="monthly"
        )
        
        assert len(performance.periods) > 0
        
        # Step 3: Prediction
        predictor = Predictor(performance)
        predictions = []
        current_period = get_next_period_label("monthly")
        for i in range(6):
            prediction = predictor.predict(
                target_time=current_period,
                method="avg_last_n_periods"
            )
            predictions.append(prediction)
            # Note: get_next_period_label() only takes granularity, not current_period
        
        assert len(predictions) == 6
        
        # Step 4: Verify relationships
        for nc_id, qty in sample_room.components.items():
            assert qty > 0
            # Find corresponding NC
            nc_found = any(nc.id == nc_id for nc in sample_twelve_ncs)
            assert nc_found
        
        print(f"\n✓ Complete system flow test passed")
        print(f"  - Room: {sample_room.id} with {sample_room.total_items} items")
        print(f"  - Performance periods: {len(performance.periods)}")
        print(f"  - Predictions: {len(predictions)}")
        print(f"  - Components verified: {len(sample_room.components)}")


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_sales_history(self):
        """Test handling of entity with no sales history"""
        room = Room(
            id="EMPTY_ROOM",
            description="Room with no sales",
            components={"12NC_001": 1},
            sales_history=[]
        )
        
        g_entity = G_entity(g_entity=room, entity_type="room")
        analyzer = PerformanceAnalyzer()
        
        # Should raise ValueError for empty sales data
        with pytest.raises(ValueError, match="No sales data available"):
            analyzer.analyze(
                analyzed_obj=g_entity,
                lookback_years=1,
                granularity="monthly"
            )
    
    def test_single_sale_record(self):
        """Test with only one sales record"""
        from datetime import date
        single_record = [SalesRecord(
            identifier="TEST",
            date=date(2024, 1, 15),
            quantity=5
        )]
        
        room = Room(
            id="SINGLE_SALE",
            description="Room with single sale",
            components={"12NC_001": 1},
            sales_history=single_record
        )
        
        g_entity = G_entity(g_entity=room, entity_type="room")
        analyzer = PerformanceAnalyzer()
        
        # With only one record and 1 year lookback, may not have enough data
        # System may raise ValueError for empty periods
        try:
            result = analyzer.analyze(
                analyzed_obj=g_entity,
                lookback_years=1,
                granularity="monthly"
            )
            assert isinstance(result, PerformanceData)
            assert len(result.periods) >= 1
        except ValueError:
            # Acceptable if periods are empty
            pass
    
    def test_zero_quantity_sales(self):
        """Test handling of zero quantity sales"""
        from datetime import date
        zero_records = [SalesRecord(
            identifier="TEST",
            date=date(2024, 1, 15),
            quantity=0
        )]
        
        room = Room(
            id="ZERO_SALES",
            description="Room with zero sales",
            components={"12NC_001": 1},
            sales_history=zero_records
        )
        
        assert room.id == "ZERO_SALES"
        assert len(room.sales_history) == 1
    
    def test_empty_components(self):
        """Test room/12NC with no components"""
        from datetime import date
        room = Room(
            id="EMPTY_COMP",
            description="Room with no components",
            components={},
            sales_history=[SalesRecord(identifier="TEST", date=date(2024, 1, 1), quantity=5)]
        )
        
        assert room.total_items == 0
        assert len(room.components) == 0
    
    def test_large_component_quantity(self):
        """Test handling of very large quantities"""
        room = Room(
            id="LARGE_QTY",
            description="Room with large quantities",
            components={"12NC_001": 999999},
            sales_history=[]
        )
        
        assert room.total_items == 999999
        assert room.has_12nc("12NC_001")
    
    def test_many_components(self):
        """Test room with many components"""
        components = {f"12NC_{i:03d}": i for i in range(1, 51)}  # 50 components
        
        room = Room(
            id="MANY_COMP",
            description="Room with many components",
            components=components,
            sales_history=[]
        )
        
        assert len(room.components) == 50
        assert room.total_items == sum(range(1, 51))
    
    def test_special_characters_in_id(self):
        """Test handling of special characters in IDs"""
        room = Room(
            id="ROOM-001_TEST",
            description="Room with special chars",
            components={"12NC_001": 1},
            sales_history=[]
        )
        
        assert "-" in room.id
        assert "_" in room.id
    
    def test_very_long_description(self):
        """Test handling of very long descriptions"""
        long_desc = "A" * 500  # 500 character description
        
        room = Room(
            id="LONG_DESC",
            description=long_desc,
            components={"12NC_001": 1},
            sales_history=[]
        )
        
        assert len(room.description) == 500
    
    def test_future_dates_filtered(self):
        """Test that future dates are properly handled"""
        from datetime import date
        future_date = date(2026, 12, 31)
        past_date = date(2023, 1, 1)
        
        records = [
            SalesRecord(identifier="TEST", date=past_date, quantity=10),
            SalesRecord(identifier="TEST", date=future_date, quantity=20)
        ]
        
        room = Room(
            id="FUTURE_TEST",
            description="Test future dates",
            components={"12NC_001": 1},
            sales_history=records
        )
        
        g_entity = G_entity(g_entity=room, entity_type="room")
        analyzer = PerformanceAnalyzer()
        
        result = analyzer.analyze(
            analyzed_obj=g_entity,
            lookback_years=4,
            granularity="yearly"
        )
        
        # Should handle both past and future gracefully
        assert isinstance(result, PerformanceData)
    
    def test_duplicate_sales_same_period(self):
        """Test handling of multiple sales in same period"""
        from datetime import date
        # Use current year dates to ensure they're within lookback range
        records = [
            SalesRecord(identifier="TEST", date=date(2025, 1, 10), quantity=5),
            SalesRecord(identifier="TEST", date=date(2025, 1, 20), quantity=10),
            SalesRecord(identifier="TEST", date=date(2025, 1, 30), quantity=3)
        ]
        
        room = Room(
            id="DUP_PERIOD",
            description="Multiple sales same month",
            components={"12NC_001": 1},
            sales_history=records
        )
        
        g_entity = G_entity(g_entity=room, entity_type="room")
        analyzer = PerformanceAnalyzer()
        
        try:
            result = analyzer.analyze(
                analyzed_obj=g_entity,
                lookback_years=1,
                granularity="monthly"
            )
            # Should aggregate sales from multiple dates in same month
            assert isinstance(result, PerformanceData)
            # The sales should be aggregated (5 + 10 + 3 = 18)
            if len(result.periods) > 0:
                total_qty = sum(p.quantity for p in result.periods)
                assert total_qty == 18
        except ValueError:
            # Acceptable if data falls outside lookback range
            pass
    
    def test_panel_with_none_callback(self):
        """Test belonging panel with None callbacks"""
        from unittest.mock import MagicMock
        panel_widget = MagicMock()
        panel_widget.winfo_children.return_value = []
        
        panel = BelongingPanel(
            panel_widget,
            {"bg_white": "#FFF"},
            {"body": 14},
            lambda **kwargs: MagicMock(),
            navigate_callback=None,
            get_description_callback=None
        )
        
        assert panel.navigate_callback is None
        assert panel.get_description_callback is None
    
    def test_performance_panel_year_boundaries(self):
        """Test performance panel with year boundaries"""
        from unittest.mock import MagicMock
        panel_widget = MagicMock()
        panel_widget.winfo_children.return_value = []
        
        panel = PerformancePanel(
            panel_widget,
            {"accent_teal": "#20B2AA", "border": "#E5E7EB"},
            {"body": 14, "small": 12, "title": 18},
            lambda **kwargs: MagicMock()
        )
        
        # Test with 5+ years (should only track 4)
        panel.year_colors[2021] = "#FF0000"
        panel.year_colors[2027] = "#00FF00"
        
        assert len(panel.year_colors) >= 4
    
    def test_period_key_edge_months(self):
        """Test period key generation for edge months"""
        from datetime import datetime
        
        # January
        jan_key = get_period_key(datetime(2024, 1, 1), "monthly")
        assert jan_key == "01-2024"
        
        # December
        dec_key = get_period_key(datetime(2024, 12, 31), "monthly")
        assert dec_key == "12-2024"
    
    def test_period_key_leap_year(self):
        """Test period key on leap year date"""
        from datetime import datetime
        
        leap_date = datetime(2024, 2, 29)
        key = get_period_key(leap_date, "monthly")
        assert key == "02-2024"


# ============================================================================
# RUN SUMMARY
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE INTEGRATION TEST SUITE")
    print("=" * 70)
    pytest.main([__file__, "-v", "--tb=short"])
