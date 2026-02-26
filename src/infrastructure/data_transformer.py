# take loaded data from data_loaders and transform it into the format needed for the application
import re
from typing import Dict, List
import pandas as pd
from datetime import datetime

from src.models.mapping import Room, TwelveNC
from src.models.sales_record import SalesRecord
from src.utils.config_util import load_config
from src.utils.string_utils import normalize_identifier


def transform_cbom_data(
    room_data: dict, data_12nc: dict, config: dict
) -> tuple[List[Room], List[TwelveNC]]:
    """Transform raw CBOM data into structured Room and TwelveNC objects

    input:
    - room_data: dict with room numbers as keys and dicts containing {'description': str, '12ncs': DataFrame}
    - data_12nc: dict with 12NCs as keys and dicts containing {'description': str, 'rooms': DataFrame}
    - config: configuration dictionary for validation patterns

    output:
    - rooms: list of Room objects with attributes room, room_description, twelve_ncs (dict of 12NC: quantity)
    - nc12s: list of TwelveNC objects with attributes twelve_nc, tnc_description, rooms (dict of Room: quantity)
    """
    if not room_data or not data_12nc:
        raise ValueError("Input data cannot be empty")

    rooms: List[Room] = []
    nc12s: List[TwelveNC] = []

    # Fix: twelve_ncs should be Dict[str, int] not Dict[TwelveNC, int]
    for room, room_df in room_data.items():
        twelve_ncs_dict = {}  # Not Dict[TwelveNC, int]

        # Convert DataFrame rows to dict entries
        for idx, row in room_df.iterrows():
            twelve_ncs_dict[row["12NC"]] = int(row["Quantity"])

        rooms.append(
            Room(
                room=room,
                room_description=room_df["12NC_Description"].iloc[0],
                twelve_ncs=twelve_ncs_dict,  # Use the dict, not valid_twelve_ncs
                sales_history=[],
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

    for nc12, nc12_df in data_12nc.items():
        if not re.match(config["validation"]["patterns"]["12nc_normalized"], str(nc12)):
            print(f"Warning: 12NC '{nc12}' does not match expected format. Skipping.")
            continue

        # Extract description and rooms DataFrame
        nc12_description = nc12_df["description"]
        rooms_df = nc12_df["rooms"]

        # DEBUG: Track target through transformation
        if nc12 == target_12nc:
            print(f"[TRANSFORM DEBUG] Processing {target_12nc}...")
            print(f"[TRANSFORM DEBUG] rooms_df type: {type(rooms_df)}")
            print(f"[TRANSFORM DEBUG] rooms_df shape: {rooms_df.shape}")
            print(f"[TRANSFORM DEBUG] rooms_df columns: {rooms_df.columns.tolist()}")

        # Validate rooms and convert quantities to integers
        valid_rooms = {}
        # Convert DataFrame rows to dict entries
        for idx, row in rooms_df.iterrows():
            valid_rooms[row["Room"]] = int(row["Quantity"])

        nc12s.append(
            TwelveNC(
                twelve_nc=nc12,
                tnc_description=nc12_description,
                tnc_igt=row["12NC_IGT"],
                rooms=valid_rooms,
                sales_history=[],
            )
        )

        # DEBUG: Confirm target was added
        if nc12 == target_12nc:
            print(f"[TRANSFORM DEBUG] ✓ Added {target_12nc} to nc12s with {len(valid_rooms)} rooms")

    # DEBUG: Final check
    print(f"\n[TRANSFORM DEBUG] Transformation complete")
    print(f"[TRANSFORM DEBUG] Total nc12s created: {len(nc12s)}")
    target_in_mappings = any(m.twelve_nc == target_12nc for m in nc12s)
    print(f"[TRANSFORM DEBUG] Target {target_12nc} in final nc12s: {target_in_mappings}")

    return rooms, nc12s


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

    # Get date format from config
    config = load_config()
    date_format = config["ymbd"].get("date_format", "MM-DD-YYYY")

    # Convert format string to strptime format
    date_format_map = {
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-MMM-YYYY": "%d-%b-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
    }
    strptime_format = date_format_map.get(date_format, "%m-%d-%Y")

    matching_count = 0
    for _, row in ymbd_df.iterrows():
        try:
            date_str = str(row["Confirmed Delivery Date"]).strip()

            # Try config format first, then fallbacks (prioritize MM-DD-YYYY)
            try:
                sales_date = datetime.strptime(date_str, strptime_format).date()
            except ValueError:
                # Fallback formats
                for fmt in ["%m-%d-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%b-%Y"]:
                    try:
                        sales_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
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
            sales_record = SalesRecord(identifier=twelve_nc, quantity=quantity, date=sales_date)
            # We'll need room mapping from CBOM
            sales_records.append(sales_record)
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue

    print(f"[DEBUG] Total records found for {target_12nc}: {matching_count}")

    # Additional debug: Show summary of quantities found
    if matching_count > 0:
        target_quantities = [r.quantity for r in sales_records if r.identifier == target_12nc]
        print(f"[YMBD DEBUG] Total quantity sum for {target_12nc}: {sum(target_quantities)}")
        print(f"[YMBD DEBUG] Number of records: {len(target_quantities)}")
        print(
            f"[YMBD DEBUG] Min qty: {min(target_quantities)}, Max qty: {max(target_quantities)}, Avg: {sum(target_quantities)/len(target_quantities):.1f}"
        )

    return sales_records


def parse_fit_cvi_to_sales_records(fit_cvi_df) -> List[SalesRecord]:
    """Parse FIT_CVI DataFrame to SalesRecord objects using config date format"""
    sales_records = []

    # Get date format from config
    config = load_config()
    date_format = config["fit_cvi"].get("date_format", "MM-DD-YYYY")  # "DD-MMM-YYYY"

    date_format_map = {
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-MMM-YYYY": "%d-%b-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
    }
    strptime_format = date_format_map.get(date_format, "%m-%d-%Y")

    for _, row in fit_cvi_df.iterrows():
        try:
            date_str = str(row["SD Item\nFSD"]).strip()

            try:
                sales_date = datetime.strptime(date_str, strptime_format).date()
            except ValueError:
                # Fallback formats
                for fmt in ["%m-%d-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%b-%Y"]:
                    try:
                        sales_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    print(f"Warning: Could not parse date '{date_str}', skipping row")
                    continue

            room = str(row["Characteristic\nCharacteristic Name"]).strip()
            quantity = int(row["(Self)\nValue from"])

            sales_record = SalesRecord(identifier=room, quantity=quantity, date=sales_date)
            sales_records.append(sales_record)
        except Exception as e:
            print(f"Warning: Skipping row due to error: {e}")
            continue

    return sales_records
