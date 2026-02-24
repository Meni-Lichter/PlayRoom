# take loaded data from data_loaders and transform it into the format needed for the application
import re
import pandas as pd

from src.models.mapping import Room12NCMap, TwelveNCRoomMap
from src.utils.config_util import load_config
from .data_loaders import read_file, load_cbom


def transform_cbom_data(room_data: dict, data_12nc: dict, config: dict):
    """Transform raw CBOM data into structured mappings for rooms and 12NCs
    input:
    - room_data: dict with room numbers as keys and DataFrames containing 12NCs with quantities
    - data_12nc: dict with 12NCs as keys and DataFrames containing rooms with quantities
    - config: configuration dictionary for validation patterns and other settings

    output:
    - room_mappings: list of Room12NCMap objects
    - nc12_mappings: list of TwelveNCRoomMap objects
    """
    if not room_data or not data_12nc:
        raise ValueError("Input data cannot be empty")

    if config is None:
        raise ValueError("Configuration cannot be None")

    room_mappings = []
    nc12_mappings = []

    # Validate and transform room data
    for room, twelve_ncs_df in room_data.items():
        if not re.match(config["validation"]["patterns"]["room_normalized"], room):
            print(f"Warning: Room '{room}' does not match expected format. Skipping.")
            continue

        # Convert DataFrame to dict {12NC: Quantity}
        if isinstance(twelve_ncs_df, pd.DataFrame):
            twelve_ncs_dict = dict(zip(twelve_ncs_df["12NC"], twelve_ncs_df["Quantity"]))
        else:
            twelve_ncs_dict = twelve_ncs_df

        # Validate 12NCs and convert quantities to integers
        valid_twelve_ncs = {}
        for nc, qty in twelve_ncs_dict.items():
            if re.match(config["validation"]["patterns"]["12nc_normalized"], str(nc)):
                # Handle various quantity formats
                if pd.isna(qty):
                    qty_int = 0
                elif isinstance(qty, (int, float)):
                    qty_int = int(qty)
                else:
                    qty_str = str(qty).strip()
                    qty_int = int(qty_str) if qty_str and qty_str.isdigit() else 0
                valid_twelve_ncs[str(nc)] = qty_int

        if not valid_twelve_ncs:
            print(f"Warning: No valid 12NCs found for room '{room}'. Skipping.")
            continue

        room_mappings.append(Room12NCMap(room=room, twelve_ncs=valid_twelve_ncs))

    # Validate and transform 12NC data
    target_12nc = "989606130501"
    print(f"\n[TRANSFORM DEBUG] Transforming 12NC data...")
    print(f"[TRANSFORM DEBUG] Looking for {target_12nc} in data_12nc...")
    print(f"[TRANSFORM DEBUG] Total 12NCs in data_12nc: {len(data_12nc)}")
    
    if target_12nc in data_12nc:
        print(f"[TRANSFORM DEBUG] ✓ Found {target_12nc} in data_12nc")
    else:
        print(f"[TRANSFORM DEBUG] ✗ {target_12nc} NOT in data_12nc")
        print(f"[TRANSFORM DEBUG] Sample keys (first 10): {list(data_12nc.keys())[:10]}")
    
    for nc12, rooms_df in data_12nc.items():
        if not re.match(config["validation"]["patterns"]["12nc_normalized"], str(nc12)):
            print(f"Warning: 12NC '{nc12}' does not match expected format. Skipping.")
            continue

        # DEBUG: Track target through transformation
        if nc12 == target_12nc:
            print(f"[TRANSFORM DEBUG] Processing {target_12nc}...")
            print(f"[TRANSFORM DEBUG] rooms_df type: {type(rooms_df)}")
            if isinstance(rooms_df, pd.DataFrame):
                print(f"[TRANSFORM DEBUG] rooms_df shape: {rooms_df.shape}")
                print(f"[TRANSFORM DEBUG] rooms_df columns: {rooms_df.columns.tolist()}")

        # Convert DataFrame to dict {Room: Quantity}
        if isinstance(rooms_df, pd.DataFrame):
            rooms_dict = dict(zip(rooms_df["Room"], rooms_df["Quantity"]))
        else:
            rooms_dict = rooms_df

        # Validate rooms and convert quantities to integers
        valid_rooms = {}
        for room, qty in rooms_dict.items():
            if re.match(config["validation"]["patterns"]["room_normalized"], str(room)):
                # Handle various quantity formats
                if pd.isna(qty):
                    qty_int = 0
                elif isinstance(qty, (int, float)):
                    qty_int = int(qty)
                else:
                    qty_str = str(qty).strip()
                    qty_int = int(qty_str) if qty_str and qty_str.isdigit() else 0
                valid_rooms[str(room)] = qty_int

        if not valid_rooms:
            print(f"Warning: No valid rooms found for 12NC '{nc12}'. Skipping.")
            continue

        nc12_mappings.append(TwelveNCRoomMap(twelve_nc=str(nc12), rooms=valid_rooms))
        
        # DEBUG: Confirm target was added
        if nc12 == target_12nc:
            print(f"[TRANSFORM DEBUG] ✓ Added {target_12nc} to nc12_mappings with {len(valid_rooms)} rooms")

    # DEBUG: Final check
    print(f"\n[TRANSFORM DEBUG] Transformation complete")
    print(f"[TRANSFORM DEBUG] Total nc12_mappings created: {len(nc12_mappings)}")
    target_in_mappings = any(m.twelve_nc == target_12nc for m in nc12_mappings)
    print(f"[TRANSFORM DEBUG] Target {target_12nc} in final nc12_mappings: {target_in_mappings}")

    return room_mappings, nc12_mappings
