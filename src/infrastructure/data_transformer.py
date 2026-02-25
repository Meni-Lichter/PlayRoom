# take loaded data from data_loaders and transform it into the format needed for the application
import re
from typing import List
import pandas as pd

from src.models.mapping import Room, TwelveNC
from src.models.sales_record import SalesRecord
from src.utils.config_util import load_config
from .data_loaders import read_file, load_cbom


def transform_cbom_data(
    room_data: dict, data_12nc: dict, config: dict
) -> tuple[List[Room], List[TwelveNC]]:
    """Transform raw CBOM data into structured mappings for rooms and 12NCs
    input:
    - room_data: dict with room numbers as keys and DataFrames containing 12NCs with quantities
    - data_12nc: dict with 12NCs as keys and DataFrames containing rooms with quantities
    - room_descriptions_dict: dict with room descriptions {room: description}
    - nc12_descriptions_dict: dict with 12NC descriptions {12nc: description}
    - config: configuration dictionary for validation patterns and other settings

    output:
    - room_mappings: list of Room objects
    - nc12_mappings: list of TwelveNC objects
    """
    if not room_data or not data_12nc:
        raise ValueError("Input data cannot be empty")

    if config is None:
        raise ValueError("Configuration cannot be None")

    room_mappings: List[Room] = []
    nc12_mappings: List[TwelveNC] = []

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

        # Get room description
        room_description = room_descriptions_dict.get(room, "")

        # Create Room object with empty sales history
        room_mappings.append(
            Room(
                room=room,
                room_description=room_description,
                twelve_ncs=valid_twelve_ncs,
                sales_history={},  # Empty for now, can be populated later
            )
        )

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

        # Get 12NC description
        nc12_description = nc12_descriptions_dict.get(str(nc12), "")

        # Create TwelveNC object with empty sales history
        nc12_mappings.append(
            TwelveNC(
                twelve_nc=str(nc12),
                tnc_description=nc12_description,
                rooms=valid_rooms,
                sales_history={},  # Empty for now, can be populated later
            )
        )

        # DEBUG: Confirm target was added
        if nc12 == target_12nc:
            print(
                f"[TRANSFORM DEBUG] ✓ Added {target_12nc} to nc12_mappings with {len(valid_rooms)} rooms"
            )

    # DEBUG: Final check
    print(f"\n[TRANSFORM DEBUG] Transformation complete")
    print(f"[TRANSFORM DEBUG] Total nc12_mappings created: {len(nc12_mappings)}")
    target_in_mappings = any(m.twelve_nc == target_12nc for m in nc12_mappings)
    print(f"[TRANSFORM DEBUG] Target {target_12nc} in final nc12_mappings: {target_in_mappings}")

    return room_mappings, nc12_mappings


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
