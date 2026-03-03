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
            # Skip rows with invalid quantities
            qty_value = str(row["Quantity"]).strip()
            if qty_value and qty_value not in ["", "nan", "None"] and not pd.isna(row["Quantity"]):
                try:
                    twelve_ncs_dict[row["12NC"]] = int(float(qty_value))
                except (ValueError, TypeError):
                    print(
                        f"Warning: Invalid quantity '{qty_value}' for 12NC {row['12NC']} in room {room}. Skipping."
                    )
                    continue

        rooms.append(
            Room(
                id=room,
                description=room_df["12NC_Description"].iloc[0],
                componenets=twelve_ncs_dict,  # Use the dict, not valid_twelve_ncs
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
            # Skip rows with invalid quantities
            qty_value = str(row["Quantity"]).strip()
            if qty_value and qty_value not in ["", "nan", "None"] and not pd.isna(row["Quantity"]):
                try:
                    valid_rooms[row["Room"]] = int(float(qty_value))
                except (ValueError, TypeError):
                    print(
                        f"Warning: Invalid quantity '{qty_value}' for room {row['Room']} in 12NC {nc12}. Skipping."
                    )
                    continue

        nc12s.append(
            TwelveNC(
                id=nc12,
                description=nc12_description,
                igt=row["12NC_IGT"],
                componenets=valid_rooms,
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


def parse_ymbd_to_sales_records(tnc_list: List[TwelveNC], ymbd_df) -> List[TwelveNC]:
    """Parse YMBD DataFrame to SalesRecord objects and link to TwelveNC objects
    args:
        - tnc_list: List of TwelveNC objects
        - ymbd_df: DataFrame with columns 'Component', 'Component Quantity', 'Confirmed Delivery Date'

    returns:
        - List of twelve_ncs with sales history populated as list of SalesRecord objects
    """
    ymbd_config = load_config()["ymbd"]
    date_format = ymbd_config.get("date_format", "MM-DD-YYYY")

    date_format_map = {
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-MMM-YYYY": "%d-%b-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
    }
    strptime_format = date_format_map.get(date_format, "%m-%d-%Y")

    # Step 1: Build ymbd dictionary {12NC: [(date, qty), ...]} - O(n)
    ymbd_dict = {}
    skipped = 0

    for _, row in ymbd_df.iterrows():
        try:
            component_value = row[ymbd_config["columns"].get("12nc", "")]
            if pd.isna(component_value):
                skipped += 1
                continue

            twelve_nc = normalize_identifier(component_value)

            # Fixed validation
            if (not twelve_nc) or (not twelve_nc.isdigit()) or (len(twelve_nc) != 12):
                skipped += 1
                continue

            # Parse date
            date_str = str(row[ymbd_config["columns"].get("date", "")]).strip()
            try:
                sales_date = datetime.strptime(date_str, strptime_format).date()
            except ValueError:
                parsed = False
                for fmt in ["%m-%d-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%b-%Y"]:
                    try:
                        sales_date = datetime.strptime(date_str, fmt).date()
                        parsed = True
                        break
                    except ValueError:
                        continue
                if not parsed:
                    skipped += 1
                    continue

            quantity = int(row[ymbd_config["columns"].get("sales", "")])

            if twelve_nc not in ymbd_dict:
                ymbd_dict[twelve_nc] = []
            ymbd_dict[twelve_nc].append((sales_date, quantity))

        except Exception as e:
            skipped += 1
            continue
    matched_12ncs = 0
    matched_records = 0
    for tnc in tnc_list:
        if tnc.id in ymbd_dict.keys():
            matched_12ncs += 1
            for date, qty in ymbd_dict[tnc.id]:
                sales_record = SalesRecord(identifier=tnc.id, quantity=qty, date=date)
                tnc.sales_history.append(sales_record)
                matched_records += 1
    print(
        f"YMBD: Updated {matched_12ncs}/{len(tnc_list)} TwelveNCs with {matched_records} sales records, skipped {skipped} rows"
    )
    return tnc_list


def parse_fit_cvi_to_sales_records(room_list: List[Room], fit_cvi_df) -> List[Room]:
    """Parse FIT/CVI DataFrame and populate Room objects with sales history.

    Note: Mutates room_list by appending to sales_history of each room's components.

    args:
        - room_list: List of Room objects (will be modified in-place)
        - fit_cvi_df: DataFrame with FIT/CVI sales data (room-level)

    returns:
        - The same room_list with populated sales_history
    """
    fit_config = load_config()["fit_cvi"]
    date_format = fit_config.get("date_format", "DD-MMM-YYYY")

    date_format_map = {
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-MMM-YYYY": "%d-%b-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
    }
    strptime_format = date_format_map.get(date_format, "%d-%b-%Y")

    # Step 1: Build fit dictionary {room_id: [(date, qty), ...]} - O(n)
    fit_dict = {}
    skipped = 0

    for _, row in fit_cvi_df.iterrows():
        try:
            room_value = row[fit_config["columns"].get("room", "")]
            if pd.isna(room_value):
                skipped += 1
                continue

            room_id = normalize_identifier(room_value)

            if not room_id:
                skipped += 1
                continue

            # Parse date
            date_str = str(row[fit_config["columns"].get("date", "")]).strip()
            try:
                sales_date = datetime.strptime(date_str, strptime_format).date()
            except ValueError:
                parsed = False
                for fmt in ["%d-%b-%Y", "%m-%d-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                    try:
                        sales_date = datetime.strptime(date_str, fmt).date()
                        parsed = True
                        break
                    except ValueError:
                        continue
                if not parsed:
                    skipped += 1
                    continue

            quantity = int(row[fit_config["columns"].get("sales", "")])

            if room_id not in fit_dict:
                fit_dict[room_id] = []
            fit_dict[room_id].append((sales_date, quantity))

        except Exception as e:
            skipped += 1
            continue

    # Step 2: Update Room objects and their components - O(m)
    matched_rooms = 0
    total_records = 0

    for room in room_list:
        if room.id in fit_dict.keys():
            matched_rooms += 1
            # Add sales records to each component in the room
            for sales_date, quantity in fit_dict[room.id]:
                sales_record = SalesRecord(
                    identifier=room.id,
                    quantity=quantity,  # Room-level quantity applies to all components
                    date=sales_date,
                )
                room.sales_history.append(sales_record)
                total_records += 1

    print(
        f"FIT/CVI: Updated {matched_rooms}/{len(room_list)} rooms with {total_records} sales records, skipped {skipped} rows"
    )

    return room_list
