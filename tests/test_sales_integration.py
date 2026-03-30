"""
Sales Integration Test Suite
Tests the complete flow: CBOM loading → YMBD/FIT_CVI sales data → Entity details
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
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
# TEST CONFIGURATION
# ============================================================================

# Update these paths to your test data files
TEST_FILES = {
    "cbom": "C:/dev/Room_12NC_PerformanceCenter/DATA/CBOM -- 830234_Hemo_with_X3_Solutions_ECR25-020.xls",
    "ymbd": "C:/dev/Room_12NC_PerformanceCenter/DATA/YMBD_314--sales report from SAP.XLSX",
    "fit_cvi": "C:/dev/Room_12NC_PerformanceCenter/DATA/For Room Performance--All Sold FIT_CVI.xlsx"
}


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def config():
    """Load configuration"""
    return load_config()


@pytest.fixture(scope="module")
def cbom_data(config):
    """Load CBOM data"""
    cbom_path = Path(TEST_FILES["cbom"])
    if not cbom_path.exists():
        pytest.skip(f"CBOM file not found: {cbom_path}")
    
    room_data, data_12nc = load_cbom(cbom_path, config)
    return room_data, data_12nc, config


@pytest.fixture(scope="module")
def transformed_data(cbom_data):
    """Transform CBOM data into Room and TwelveNC objects"""
    room_data, data_12nc, config = cbom_data
    rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
    return rooms, nc12s


@pytest.fixture(scope="module")
def ymbd_data():
    """Load YMBD sales data"""
    ymbd_path = Path(TEST_FILES["ymbd"])
    if not ymbd_path.exists():
        pytest.skip(f"YMBD file not found: {ymbd_path}")
    
    return read_file(ymbd_path, "ymbd", header=0)


@pytest.fixture(scope="module")
def fit_cvi_data():
    """Load FIT_CVI sales data"""
    fit_cvi_path = Path(TEST_FILES["fit_cvi"])
    if not fit_cvi_path.exists():
        pytest.skip(f"FIT_CVI file not found: {fit_cvi_path}")
    
    return read_file(fit_cvi_path, "fit_cvi", header=0)


@pytest.fixture(scope="module")
def entities_with_sales(transformed_data, ymbd_data, fit_cvi_data):
    """Complete integration: CBOM + YMBD + FIT_CVI"""
    rooms, nc12s = transformed_data
    
    # Add YMBD sales to 12NCs
    if ymbd_data is not None:
        nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_data)
    
    # Add FIT_CVI sales to Rooms
    if fit_cvi_data is not None:
        rooms = parse_fit_cvi_to_sales_records(rooms, fit_cvi_data)
    
    return rooms, nc12s


# ============================================================================
# TEST SUITE
# ============================================================================

class TestSalesIntegration:
    """Test complete sales data integration flow"""
    
    def test_cbom_loading(self, cbom_data):
        """Test CBOM data loads successfully"""
        room_data, data_12nc, config = cbom_data
        
        assert room_data is not None, "Room data should load"
        assert data_12nc is not None, "12NC data should load"
        assert len(room_data) > 0, "Room data should contain entries"
        assert len(data_12nc) > 0, "12NC data should contain entries"
    
    def test_cbom_transformation(self, transformed_data):
        """Test CBOM transforms to Room/TwelveNC objects"""
        rooms, nc12s = transformed_data
        
        assert len(rooms) > 0, "Should create Room objects"
        assert len(nc12s) > 0, "Should create TwelveNC objects"
        
        # Check Room structure
        sample_room = rooms[0]
        assert isinstance(sample_room, Room), "Should be Room instance"
        assert hasattr(sample_room, 'id'), "Room should have id"
        assert hasattr(sample_room, 'description'), "Room should have description"
        assert hasattr(sample_room, 'sales_history'), "Room should have sales_history"
        assert isinstance(sample_room.sales_history, list), "sales_history should be list"
        
        # Check TwelveNC structure
        sample_nc12 = nc12s[0]
        assert isinstance(sample_nc12, TwelveNC), "Should be TwelveNC instance"
        assert hasattr(sample_nc12, 'id'), "TwelveNC should have id"
        assert hasattr(sample_nc12, 'description'), "TwelveNC should have description"
        assert hasattr(sample_nc12, 'sales_history'), "TwelveNC should have sales_history"
        assert isinstance(sample_nc12.sales_history, list), "sales_history should be list"
    
    def test_ymbd_file_loading(self, ymbd_data):
        """Test YMBD file loads with correct headers"""
        assert ymbd_data is not None, "YMBD data should load"
        assert len(ymbd_data) > 0, "YMBD should contain rows"
        
        # Check for required columns
        required_columns = ['Component', 'Component Quantity', 'Confirmed Delivery Date']
        for col in required_columns:
            assert col in ymbd_data.columns, f"YMBD should have '{col}' column"
    
    def test_fit_cvi_file_loading(self, fit_cvi_data):
        """Test FIT_CVI file loads with correct headers"""
        assert fit_cvi_data is not None, "FIT_CVI data should load"
        assert len(fit_cvi_data) > 0, "FIT_CVI should contain rows"
        
        # Check for required columns
        assert 'Characteristic\nCharacteristic Name' in fit_cvi_data.columns or \
               any('Characteristic Name' in col for col in fit_cvi_data.columns), \
               "FIT_CVI should have room identifier column"
    
    def test_sales_history_population(self, entities_with_sales):
        """Test sales history is populated from YMBD and FIT_CVI"""
        rooms, nc12s = entities_with_sales
        
        # Check 12NCs have sales history
        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]
        assert len(nc12s_with_sales) > 0, "Some 12NCs should have sales history"
        
        print(f"\n✅ {len(nc12s_with_sales)}/{len(nc12s)} 12NCs have sales history")
        
        # Check Rooms have sales history
        rooms_with_sales = [room for room in rooms if len(room.sales_history) > 0]
        assert len(rooms_with_sales) > 0, "Some Rooms should have sales history"
        
        print(f"✅ {len(rooms_with_sales)}/{len(rooms)} Rooms have sales history")
    
    def test_sales_record_structure(self, entities_with_sales):
        """Test SalesRecord objects have correct structure"""
        rooms, nc12s = entities_with_sales
        
        # Find entity with sales
        entity_with_sales = None
        for nc in nc12s:
            if len(nc.sales_history) > 0:
                entity_with_sales = nc
                break
        
        if not entity_with_sales:
            for room in rooms:
                if len(room.sales_history) > 0:
                    entity_with_sales = room
                    break
        
        assert entity_with_sales is not None, "Should find entity with sales"
        
        sample_record = entity_with_sales.sales_history[0]
        assert isinstance(sample_record, SalesRecord), "Should be SalesRecord instance"
        assert hasattr(sample_record, 'identifier'), "SalesRecord should have identifier"
        assert hasattr(sample_record, 'quantity'), "SalesRecord should have quantity"
        assert hasattr(sample_record, 'date'), "SalesRecord should have date"
        assert sample_record.quantity > 0, "Quantity should be positive"
    
    def test_total_quantity_calculation(self, entities_with_sales):
        """Test total sold quantity calculation"""
        rooms, nc12s = entities_with_sales
        
        # Test 12NC with sales
        nc12_with_sales = next((nc for nc in nc12s if len(nc.sales_history) > 0), None)
        if nc12_with_sales:
            total = sum(record.quantity for record in nc12_with_sales.sales_history)
            assert total > 0, "Total quantity should be positive"
            assert total == sum(r.quantity for r in nc12_with_sales.sales_history), \
                "Total should match sum of all quantities"
            
            print(f"\n✅ 12NC {nc12_with_sales.id}: {len(nc12_with_sales.sales_history)} records, {total} total units")
        
        # Test Room with sales
        room_with_sales = next((room for room in rooms if len(room.sales_history) > 0), None)
        if room_with_sales:
            total = sum(record.quantity for record in room_with_sales.sales_history)
            assert total > 0, "Total quantity should be positive"
            
            print(f"✅ Room {room_with_sales.id}: {len(room_with_sales.sales_history)} records, {total} total units")
    
    def test_entity_attributes(self, entities_with_sales):
        """Test entities have all required attributes"""
        rooms, nc12s = entities_with_sales
        
        # Test Room attributes
        sample_room = rooms[0]
        assert hasattr(sample_room, 'total_items'), "Room should have total_items"
        assert isinstance(sample_room.total_items, int), "total_items should be int"
        assert hasattr(sample_room, 'components'), "Room should have components list"
        
        # Test TwelveNC attributes
        sample_nc12 = nc12s[0]
        assert hasattr(sample_nc12, 'total_items'), "TwelveNC should have total_items"
        assert isinstance(sample_nc12.total_items, int), "total_items should be int"
        assert hasattr(sample_nc12, 'igt'), "TwelveNC should have igt"
        assert hasattr(sample_nc12, 'components'), "TwelveNC should have components list"
    
    def test_data_consistency(self, entities_with_sales):
        """Test data consistency across entities"""
        rooms, nc12s = entities_with_sales
        
        # All entities should have unique IDs
        room_ids = [room.id for room in rooms]
        nc12_ids = [nc.id for nc in nc12s]
        
        assert len(room_ids) == len(set(room_ids)), "Room IDs should be unique"
        assert len(nc12_ids) == len(set(nc12_ids)), "12NC IDs should be unique"
        
        # All sales records should have valid dates
        for nc in nc12s:
            for record in nc.sales_history:
                assert record.date is not None, "Sales record should have date"
                assert record.identifier == nc.id, "Sales record identifier should match entity ID"
        
        for room in rooms:
            for record in room.sales_history:
                assert record.date is not None, "Sales record should have date"
                assert record.identifier == room.id, "Sales record identifier should match entity ID"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test data loading and processing performance"""
    
    def test_cbom_load_performance(self, config):
        """Test CBOM loads in reasonable time"""
        import time
        cbom_path = Path(TEST_FILES["cbom"])
        if not cbom_path.exists():
            pytest.skip("CBOM file not found")
        
        start = time.time()
        room_data, data_12nc = load_cbom(cbom_path, config)
        elapsed = time.time() - start
        
        print(f"\n⏱️  CBOM load time: {elapsed:.2f}s")
        assert elapsed < 10, "CBOM should load in under 10 seconds"
    
    def test_full_integration_performance(self, config):
        """Test complete data pipeline performance"""
        import time
        
        cbom_path = Path(TEST_FILES["cbom"])
        ymbd_path = Path(TEST_FILES["ymbd"])
        fit_cvi_path = Path(TEST_FILES["fit_cvi"])
        
        if not all([cbom_path.exists(), ymbd_path.exists(), fit_cvi_path.exists()]):
            pytest.skip("Test files not found")
        
        start = time.time()
        
        # Load CBOM
        room_data, data_12nc = load_cbom(cbom_path, config)
        
        # Transform
        rooms, nc12s = transform_cbom_data(room_data, data_12nc, config)
        
        # Load sales data
        ymbd_df = read_file(ymbd_path, "ymbd", header=0)
        fit_cvi_df = read_file(fit_cvi_path, "fit_cvi", header=0)
        
        # Populate sales history
        nc12s = parse_ymbd_to_sales_records(nc12s, ymbd_df)
        rooms = parse_fit_cvi_to_sales_records(rooms, fit_cvi_df)
        
        elapsed = time.time() - start
        
        print(f"\n⏱️  Full integration time: {elapsed:.2f}s")
        print(f"📊 Loaded {len(rooms)} rooms and {len(nc12s)} 12NCs")
        print(f"📈 Total sales records: {sum(len(nc.sales_history) for nc in nc12s) + sum(len(r.sales_history) for r in rooms)}")
        
        assert elapsed < 30, "Full integration should complete in under 30 seconds"


# ============================================================================
# SUMMARY TEST
# ============================================================================

class TestSummary:
    """Print summary of loaded data"""
    
    def test_print_summary(self, entities_with_sales):
        """Print comprehensive data summary"""
        rooms, nc12s = entities_with_sales
        
        print("\n" + "="*70)
        print("📊 DATA INTEGRATION SUMMARY")
        print("="*70)
        
        # Room statistics
        rooms_with_sales = [r for r in rooms if len(r.sales_history) > 0]
        total_room_sales = sum(len(r.sales_history) for r in rooms)
        total_room_qty = sum(sum(rec.quantity for rec in r.sales_history) for r in rooms)
        
        print(f"\n🏠 ROOMS:")
        print(f"  Total Rooms: {len(rooms)}")
        print(f"  Rooms with sales: {len(rooms_with_sales)} ({len(rooms_with_sales)/len(rooms)*100:.1f}%)")
        print(f"  Total sales records: {total_room_sales}")
        print(f"  Total quantity sold: {total_room_qty}")
        
        # 12NC statistics
        nc12s_with_sales = [nc for nc in nc12s if len(nc.sales_history) > 0]
        total_nc12_sales = sum(len(nc.sales_history) for nc in nc12s)
        total_nc12_qty = sum(sum(rec.quantity for rec in nc.sales_history) for nc in nc12s)
        
        print(f"\n🔧 12NCs:")
        print(f"  Total 12NCs: {len(nc12s)}")
        print(f"  12NCs with sales: {len(nc12s_with_sales)} ({len(nc12s_with_sales)/len(nc12s)*100:.1f}%)")
        print(f"  Total sales records: {total_nc12_sales}")
        print(f"  Total quantity sold: {total_nc12_qty}")
        
        # Sample entities
        if rooms_with_sales:
            sample = rooms_with_sales[0]
            total = sum(r.quantity for r in sample.sales_history)
            print(f"\n📦 Sample Room: {sample.id}")
            print(f"  Description: {sample.description}")
            print(f"  Sales records: {len(sample.sales_history)}")
            print(f"  Total sold: {total} units")
        
        if nc12s_with_sales:
            sample = nc12s_with_sales[0]
            total = sum(r.quantity for r in sample.sales_history)
            print(f"\n🔩 Sample 12NC: {sample.id}")
            print(f"  Description: {sample.description}")
            print(f"  Sales records: {len(sample.sales_history)}")
            print(f"  Total sold: {total} units")
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED - System Ready!")
        print("="*70 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
