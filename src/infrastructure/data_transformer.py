# take loaded data from data_loaders and transform it into the format needed for the application
import re
from typing import Dict, List
from numpy import int_
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
    - data_12nc: dict with 12NCs as keys and dicts containing {'description': str, 'IGT_12NC': str, 'rooms': DataFrame}
    - config: configuration dictionary for validation patterns

    output:
    - rooms: list of Room objects with attributes room, room_description, twelve_ncs (dict of 12NC: quantity)
    - nc12s: list of TwelveNC objects with attributes twelve_nc, tnc_description, rooms (dict of Room: quantity)
    """
    if not room_data or not data_12nc:
        raise ValueError("Input data cannot be empty")

    rooms: List[Room] = []
    nc12s: List[TwelveNC] = []
    #####################
    # populate rooms list
    ####################
    for room in room_data.keys():
        if not re.match(config["validation"]["patterns"]["room_normalized"], str(room)):
            print(f"Warning: Room '{room}' does not match expected format. Skipping.")
            continue

        # Get description from first row if available
        description = room_data[room]["description"] if "description" in room_data[room] else ""

        twelve_ncs_dict = {}  # Not Dict[TwelveNC, int]
        # Skip rows with invalid quantities
        tnc_list = room_data[room]["tnc_list"]
        for _, row in tnc_list.iterrows():
            qty_value = str(row["Quantity"]).strip()
            if qty_value and qty_value not in ["", "nan", "None"] and not pd.isna(row["Quantity"]):
                try:
                    int__value = int(float(qty_value))
                    if int__value > 0:
                        twelve_ncs_dict[row["12NC"]] = int__value
                except (ValueError, TypeError):
                    print(
                        f"Warning: Invalid quantity '{qty_value}' for 12NC {row['12NC']} in room {room}. Skipping."
                    )
                    continue

        rooms.append(
            Room(
                id=room,
                description=description,
                components=twelve_ncs_dict,  # Use the dict, not valid_twelve_ncs
                sales_history=[],
            )
        )
    ################################
    # populate nc12s list
    ################################
    for nc12 in data_12nc.keys():

        if not re.match(config["validation"]["patterns"]["12nc_normalized"], str(nc12)):
            print(f"Warning: 12NC '{nc12}' does not match expected format. Skipping.")
            continue
        description = (
            data_12nc[nc12]["12NC_Description"] if "12NC_Description" in data_12nc[nc12] else ""
        )
        igt = data_12nc[nc12]["12NC_IGT"] if "12NC_IGT" in data_12nc[nc12] else ""

        room_dict = {}  # Not Dict[Room, int]

        room_list = data_12nc[nc12]["room_list"]

        for _, row in room_list.iterrows():
            qty_value = str(row["Quantity"]).strip()
            if qty_value and qty_value not in ["", "nan", "None"] and not pd.isna(row["Quantity"]):
                try:
                    int__value = int(float(qty_value))
                    if int__value > 0:
                        room_dict[row["Room"]] = int__value
                except (ValueError, TypeError):
                    print(
                        f"Warning: Invalid quantity '{qty_value}' for room {row['Room']} in 12NC {nc12}. Skipping."
                    )
                    continue

        nc12s.append(
            TwelveNC(
                id=nc12,
                description=description,
                igt=igt,
                components=room_dict,
                sales_history=[],
            )
        )

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
    date_format = ymbd_config.get("date_format", "YYYY-MM-DD HH:MM:SS")

    date_format_map = {
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-MMM-YYYY": "%d-%b-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "YYYY-MM-DD HH:MM:SS": "%Y-%m-%d %H:%M:%S",
    }
    strptime_format = date_format_map.get(date_format, "%Y-%m-%d %H:%M:%S")
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
                # Try fallback formats: YYYY-MM-DD HH:MM:SS first (actual format), then others
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m-%d-%Y", "%d-%b-%Y"]:
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
    date_format = fit_config.get("date_format", "YYYY-MM-DD HH:MM:SS")

    date_format_map = {
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-MMM-YYYY": "%d-%b-%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "YYYY-MM-DD HH:MM:SS": "%Y-%m-%d %H:%M:%S",
    }
    strptime_format = date_format_map.get(date_format, "%Y-%m-%d %H:%M:%S")

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

                # Try fallback formats: YYYY-MM-DD HH:MM:SS first (actual format), then others
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m-%d-%Y", "%d-%b-%Y"]:
                    try:
                        sales_date = datetime.strptime(date_str, fmt).date()
                        parsed = True
                        print(
                            f"[FIT DEBUG] Fallback success: '{date_str}' parsed with format '{fmt}'"
                        )
                        break
                    except ValueError:
                        continue
                if not parsed:
                    print(f"[FIT DEBUG] All formats failed for: '{date_str}'")
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

    return room_list
