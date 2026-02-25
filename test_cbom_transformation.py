"""Test script for CBOM data transformation"""

from src.infrastructure import load_cbom
from src.infrastructure.data_transformer import transform_cbom_data
from src.utils import load_config
from tkinter import Tk, filedialog

def print_section(title):
    """Helper function to print section headers"""
    print("\n" + "="*80)
    print(title)
    print("="*80)

def test_raw_data(room_data, data_12nc):
    """Test and display raw loaded data"""
    print_section("RAW DATA AFTER LOADING")
    
    print(f"\nTotal Rooms: {len(room_data)}")
    print(f"Total 12NCs: {len(data_12nc)}")
    
    # Sample room data
    print("\n--- Sample Raw Room Data (first 3 rooms) ---")
    for i, (room_num, twelve_ncs) in enumerate(list(room_data.items())[:3]):
        print(f"\nRoom: {room_num}")
        print(f"  Type: {type(twelve_ncs)}")
        print(f"  12NCs in room: {len(twelve_ncs)}")
        for nc, qty in list(twelve_ncs.items())[:5]:
            print(f"    {nc}: {qty}")
        if len(twelve_ncs) > 5:
            print(f"    ... and {len(twelve_ncs) - 5} more")
    
    # Sample 12NC data
    print("\n--- Sample Raw 12NC Data (first 3 12NCs) ---")
    for i, (nc12_num, rooms) in enumerate(list(data_12nc.items())[:3]):
        print(f"\n12NC: {nc12_num}")
        print(f"  Type: {type(rooms)}")
        print(f"  Rooms containing this 12NC: {len(rooms)}")
        for room, qty in list(rooms.items())[:5]:
            print(f"    {room}: {qty}")
        if len(rooms) > 5:
            print(f"    ... and {len(rooms) - 5} more")

def test_transformed_data(room_mappings, nc12_mappings):
    """Test and display transformed data"""
    print_section("TRANSFORMED DATA (Structured Mappings)")
    
    print(f"\nTotal Room Mappings: {len(room_mappings)}")
    print(f"\nTotal 12NC Mappings: {len(nc12_mappings)}")
    
    # Test Room objects
    print("\n--- Sample Room Objects (first 3) ---")
    for i, room_map in enumerate(room_mappings[:3]):
        print(f"\n[{i+1}] Room Mapping:")
        print(f"  Room: {room_map.room}")
        print(f"  Description: {room_map.room_description}")
        print(f"  Type: {type(room_map).__name__}")
        print(f"  Number of 12NCs: {len(room_map.twelve_ncs)}")
        print(f"  Total items in room: {room_map.total_items}")
        print(f"  Sample 12NCs:")
        for nc, qty in list(room_map.twelve_ncs.items())[:5]:
            print(f"    {nc}: {qty}")
    
    # Test TwelveNC objects
    print("\n--- Sample TwelveNC Objects (first 3) ---")
    for i, nc_map in enumerate(nc12_mappings[:3]):
        print(f"\n[{i+1}] 12NC Mapping:")
        print(f"  12NC: {nc_map.twelve_nc}")
        print(f"  Description: {nc_map.tnc_description}")
        print(f"  Type: {type(nc_map).__name__}")
        print(f"  Number of rooms: {len(nc_map.rooms)}")
        print(f"  Total items: {nc_map.total_items}")
        print(f"  Sample rooms:")
        for room, qty in list(nc_map.rooms.items())[:5]:
            print(f"    {room}: {qty}")

def test_object_methods(room_mappings, nc12_mappings):
    """Test methods on mapped objects"""
    print_section("TESTING OBJECT METHODS")
    
    if room_mappings:
        room_map = room_mappings[0]
        print(f"\n--- Testing Room methods on Room: {room_map.room} ---")
        
        # Test has_12nc
        if room_map.twelve_ncs:
            test_nc = list(room_map.twelve_ncs.keys())[0]
            print(f"\nhas_12nc('{test_nc}'): {room_map.has_12nc(test_nc)}")
            print(f"has_12nc('FAKE12NC'): {room_map.has_12nc('FAKE12NC')}")
        
        # Test total_items property
        print(f"\ntotal_items property: {room_map.total_items}")
        
        # Test show_12ncs
        print("\nshow_12ncs() output:")
        room_map.show_12ncs()
    
    if nc12_mappings:
        nc_map = nc12_mappings[0]
        print(f"\n--- Testing TwelveNC methods on 12NC: {nc_map.twelve_nc} ---")
        
        # Test has_room
        if nc_map.rooms:
            test_room = list(nc_map.rooms.keys())[0]
            print(f"\nhas_room('{test_room}'): {nc_map.has_room(test_room)}")
            print(f"has_room('FAKE_ROOM'): {nc_map.has_room('FAKE_ROOM')}")
        
        # Test total_items property
        print(f"\ntotal_items property: {nc_map.total_items}")
        
        # Test show_rooms
        print("\nshow_rooms() output:")
        nc_map.show_rooms()

def test_data_consistency(room_data, data_12nc, room_mappings, nc12_mappings):
    """Test consistency between raw and transformed data"""
    print_section("DATA CONSISTENCY CHECKS")
    
    # Check if counts match (might differ due to validation filtering)
    print(f"\nRaw rooms count: {len(room_data)}")
    print(f"Mapped rooms count: {len(room_mappings)}")
    print(f"Difference: {len(room_data) - len(room_mappings)} (filtered out during validation)")
    
    print(f"\nRaw 12NCs count: {len(data_12nc)}")
    print(f"Mapped 12NCs count: {len(nc12_mappings)}")
    print(f"Difference: {len(data_12nc) - len(nc12_mappings)} (filtered out during validation)")
    
    # Check if data is preserved correctly
    print("\n--- Spot Check: Verify data preservation ---")
    if room_mappings and room_data:
        check_room = room_mappings[0].room
        if check_room in room_data:
            raw_count = len(room_data[check_room])
            mapped_count = len(room_mappings[0].twelve_ncs)
            print(f"\nRoom '{check_room}':")
            print(f"  Raw 12NCs count: {raw_count}")
            print(f"  Mapped 12NCs count: {mapped_count}")
            print(f"  [OK] Data preserved" if raw_count == mapped_count else f"  [WARNING] Data filtered")

def main():
    print("="*80)
    print("CBOM TRANSFORMATION TEST")
    print("="*80)
    
    # Load configuration
    config = load_config()
    print("\n[OK] Configuration loaded successfully")
    
    # Initialize file picker
    root = Tk()
    root.withdraw()
    
    print("\n" + "-"*80)
    print("Please select a CBOM Excel file...")
    
    cbom_path = None
    try:
        cbom_path = filedialog.askopenfilename(
            title="Select CBOM Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
    except KeyboardInterrupt:
        print("\n\nFile selection cancelled. Exiting.")
    except Exception as e:
        print(f"\n\nError opening file dialog: {e}")
    finally:
        try:
            root.destroy()
        except:
            pass
    
    if not cbom_path:
        print("No file selected. Exiting.")
        return
    
    print(f"\nReading file: {cbom_path}")
    print("-"*80)
    
    # Step 1: Load CBOM data
    print("\n[Step 1] Loading CBOM data...")
    room_data, data_12nc, room_descriptions_dict, nc12_descriptions_dict = load_cbom(cbom_path, config)
    
    if room_data is None or data_12nc is None:
        print("\n[ERROR] Failed to load CBOM file")
        return
    
    print("[OK] CBOM data loaded successfully")
    print(f"[INFO] Loaded {len(room_descriptions_dict)} room descriptions")
    print(f"[INFO] Loaded {len(nc12_descriptions_dict)} 12NC descriptions")
    
    # Test raw data
    test_raw_data(room_data, data_12nc)
    
    # Step 2: Transform data
    print("\n[Step 2] Transforming CBOM data...")
    try:
        room_mappings, nc12_mappings = transform_cbom_data(
            room_data, 
            data_12nc, 
            room_descriptions_dict,
            nc12_descriptions_dict,
            config
        )
        print("[OK] CBOM data transformed successfully")
    except Exception as e:
        print(f"\n[ERROR] Transformation failed: {e}")
        return
    
    # Test transformed data
    test_transformed_data(room_mappings, nc12_mappings)
    
    # Test object methods
    test_object_methods(room_mappings, nc12_mappings)
    
    # Test data consistency
    test_data_consistency(room_data, data_12nc, room_mappings, nc12_mappings)
    
    print("\n" + "="*80)
    print("[SUCCESS] ALL TESTS COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        raise
