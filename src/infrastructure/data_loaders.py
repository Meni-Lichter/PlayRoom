# Standard library imports
import re
import os
import pandas as pd
import logging
from pathlib import Path
from tkinter import messagebox

# Use relative imports for utility functions
from ..utils import (
    col_letter_to_index,
    file_in_use,
    normalize_identifier,
    find_column_by_canon,
    load_config,
    pick_sheet,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_cbom(cbom_path, config) -> tuple[dict, dict]:
    """
    Reads the CBOM Excel file and extracts room-12NC relationships.

    Input:
    - cbom_path: Path to the CBOM Excel file
    - config: Configuration dictionary with CBOM structure settings

    Output:
    - room_data: Dictionary {room_number:  tncs['12NC (normalized)', '12NC (original)', '12NC_Description', 'Quantity']}}
    - data_12nc: Dictionary {12nc_number:  rooms['Room(normalized)','Room(original)', 'Room_Description', 'Quantity']}}
    """

    # Initialize dictionaries to hold data
    room_data = {}
    data_12nc = {}

    # Get configuration values
    room_col_start = config["cbom"]["columns"].get("room_start", "G")
    room_num_row = config["cbom"]["rows"].get("room_numbers", 5)
    room_desc_row = config["cbom"]["rows"].get("room_descriptions", 4)
    nc12_col = config["cbom"]["columns"].get("12nc", "C")
    nc12_desc_col = config["cbom"]["columns"].get("12nc_description", "D")
    nc12_igt_col = config["cbom"]["columns"].get("12nc_igt", "A")
    nc12_row_start = config["cbom"]["rows"].get("12nc_start", 9)

    df = read_file(cbom_path, "cbom", header=None)
    if df is None:
        return room_data, data_12nc

    room_col_idx = col_letter_to_index(room_col_start)
    nc12_col_idx = col_letter_to_index(nc12_col)
    nc12_desc_col_idx = col_letter_to_index(nc12_desc_col)
    nc12_igt_col_idx = col_letter_to_index(nc12_igt_col)
    # Convert 1-indexed rows to 0-indexed
    room_num_row_idx = room_num_row - 1
    room_desc_row_idx = room_desc_row - 1
    nc12_row_start_idx = nc12_row_start - 1

    # Extract room information (starting from room_col_start)
    room_numbers = df.iloc[room_num_row_idx, room_col_idx:].values
    room_descriptions = df.iloc[room_desc_row_idx, room_col_idx:].values

    # Extract 12NC information (starting from nc12_row_start)
    nc12_numbers = df.iloc[nc12_row_start_idx:, nc12_col_idx].values
    nc12_descriptions = df.iloc[nc12_row_start_idx:, nc12_desc_col_idx].values
    nc12_igts = df.iloc[nc12_row_start_idx:, nc12_igt_col_idx].values
    # DEBUG: Check for target 12NC in raw CBOM data
    target_12nc = "989606130501"
    print(f"\n[CBOM DEBUG] Looking for 12NC {target_12nc} in CBOM file...")
    print(f"[CBOM DEBUG] Total 12NCs in CBOM: {len(nc12_numbers)}")
    print(f"[CBOM DEBUG] First 5 raw 12NC values: {nc12_numbers[:5]}")
    print(
        f"[CBOM DEBUG] First 5 values types: {[type(nc12_numbers[i]) for i in range(min(5, len(nc12_numbers)))]}"
    )

    # Check for target considering it might have hyphens (9896-061-30501)
    target_with_hyphens = (
        f"{target_12nc[:4]}-{target_12nc[4:7]}-{target_12nc[7:]}"  # "9896-061-30501"
    )
    print(f"[CBOM DEBUG] Also looking for hyphenated format: {target_with_hyphens}")

    found_raw = False
    for idx, nc in enumerate(nc12_numbers):
        if pd.isna(nc):
            continue
        nc_str = str(nc).strip()
        # Check both formats
        if target_12nc in nc_str or target_with_hyphens in nc_str:
            print(
                f"[CBOM DEBUG] Found target in raw data at index {idx}: '{nc}' (type: {type(nc)})"
            )
            found_raw = True
            break

    if not found_raw:
        print(
            f"[CBOM DEBUG] Target {target_12nc} (or {target_with_hyphens}) NOT found in raw 12NC data"
        )

    # Extract the quantity matrix (from nc12_row_start, room columns onwards)
    quantity_matrix = df.iloc[nc12_row_start_idx:, room_col_idx:].values

    ############################
    # Process data for each room
    ############################
    valid_room_count = 0
    for room_idx, room_num in enumerate(room_numbers):
        if pd.isna(room_num):
            continue

        room_num_normalized = normalize_identifier(room_num)

        if not room_num_normalized or not re.match(
            config["validation"]["patterns"]["room_normalized"], room_num_normalized
        ):  # Validate normalized room format (e.g., "ROOM123")
            continue

        valid_room_count += 1
        # Collect all 12NCs for this room
        room_12ncs = []
        for nc12_idx, nc12_num in enumerate(nc12_numbers):
            if pd.isna(nc12_num):
                continue

            nc12_num_normalized = normalize_identifier(nc12_num)

            # DEBUG: Track normalization of target 12NC
            if target_12nc in str(nc12_num) or nc12_num_normalized == target_12nc:
                print(f"[CBOM DEBUG] Normalizing 12NC: '{nc12_num}' -> '{nc12_num_normalized}'")

            # Validate normalized format (12 digits)
            if (
                not re.match(
                    config["validation"]["patterns"]["12nc_normalized"], nc12_num_normalized
                )
            ) or (not nc12_num_normalized):
                continue

            quantity = quantity_matrix[nc12_idx, room_idx]

            # Only include if quantity exists and is not zero
            if pd.isna(quantity):
                quantity = 0
            nc12_igt = str(nc12_igts[nc12_idx]).strip() if not pd.isna(nc12_igts[nc12_idx]) else ""
            nc12_desc = (
                str(nc12_descriptions[nc12_idx]).strip()
                if not pd.isna(nc12_descriptions[nc12_idx])
                else ""
            )

            room_12ncs.append(
                {
                    "12NC": nc12_num_normalized,  # Store normalized version
                    "12NC_IGT": nc12_igt,  # Store IGT 12NC if available
                    "12NC_Original": str(nc12_num).strip(),  # Keep original for reference
                    "12NC_Description": nc12_desc,
                    "Quantity": quantity,
                }
            )

        # Create DataFrame for this room (use normalized room number as key)
        if room_12ncs:
            room_data[room_num_normalized] = pd.DataFrame(room_12ncs)

    ############################
    # Process data for each 12NC
    ############################
    valid_12nc_count = 0
    target_found_in_processing = False
    print(f"\n[CBOM DEBUG] Processing 12NCs...")
    print(f"[CBOM DEBUG] First 10 normalized 12NCs:")

    for nc12_idx, nc12_num in enumerate(nc12_numbers):
        if pd.isna(nc12_num):
            continue

        nc12_num_str = str(nc12_num).strip()

        nc12_num_normalized = normalize_identifier(nc12_num_str)

        # DEBUG: Show first 10 normalizations
        if nc12_idx < 10:
            print(f"  [{nc12_idx}] '{nc12_num}' -> '{nc12_num_normalized}'")

        # DEBUG: Track target 12NC through processing
        if nc12_num_normalized == target_12nc:
            target_found_in_processing = True
            print(
                f"[CBOM DEBUG] ✓✓✓ Processing target 12NC: raw='{nc12_num}' normalized='{nc12_num_normalized}'"
            )

        # Validate normalized format (12 digits)
        if not re.match(config["validation"]["patterns"]["12nc_normalized"], nc12_num_normalized):
            continue

        valid_12nc_count += 1

        # Collect all rooms for this 12NC
        nc12_rooms = []
        for room_idx, room_num in enumerate(room_numbers):
            if pd.isna(room_num):
                continue
            room_num_normalized = normalize_identifier(room_num)

            if not room_num_normalized:  # Skip empty normalized values
                continue

            quantity = quantity_matrix[nc12_idx, room_idx]

            if pd.isna(quantity):
                quantity = 0

            room_desc = (
                str(room_descriptions[room_idx]).strip()
                if not pd.isna(room_descriptions[room_idx])
                else ""
            )

            nc12_rooms.append(
                {
                    "Room": room_num_normalized,  # Store normalized version
                    "Room_Original": str(room_num).strip(),  # Keep original for reference
                    "Room_Description": room_desc,
                    "Quantity": quantity,
                }
            )

        # Create DataFrame for this 12NC (use normalized 12NC as key)
        if nc12_rooms:
            data_12nc[nc12_num_normalized] = pd.DataFrame(nc12_rooms)

    # DEBUG: Final check for target 12NC in mappings
    print(
        f"\n[CBOM DEBUG] Target {target_12nc} found during processing: {target_found_in_processing}"
    )
    print(f"[CBOM DEBUG] Total valid 12NCs processed: {valid_12nc_count}")
    print(f"[CBOM DEBUG] Total 12NCs in data_12nc dict: {len(data_12nc)}")

    if target_12nc in data_12nc:
        print(f"[CBOM DEBUG] ✓ Target {target_12nc} IS in data_12nc!")
        rooms_for_target = data_12nc[target_12nc]
        print(f"[CBOM DEBUG] Rooms for {target_12nc}: {list(rooms_for_target['Room'].values)}")
    else:
        print(f"[CBOM DEBUG] ✗ Target {target_12nc} NOT in data_12nc")
        print(f"[CBOM DEBUG] Sample keys in data_12nc (first 10): {list(data_12nc.keys())[:10]}")

    return room_data, data_12nc


def read_file(path: Path, file_type: str, header=None, converters=None) -> pd.DataFrame | None:
    """
    Reads an Excel or CSV file into a DataFrame, handling different formats and errors.
    Meant primarily to be used for reading FIT_CVI files but can be used for other file types as well with appropriate configuration.

    Args:
        path (Path): The path to the file to read.
        file_type (str): The type of the file ('excel' or 'csv').
        header (int, list of int, None): Row(s) to use as the column names. Defaults to None.
        converters (dict, optional): Dict of functions for converting values in certain columns. Keys can be integers or column labels.
    Returns:
        pd.DataFrame: The contents of the file as a DataFrame, or None if an error occurred.
    """
    df = None
    try:
        if not os.path.exists(path):
            messagebox.showerror(
                "File Not Found",
                f"The specified file does not exist:\n{path}\n\nPlease check the file path and try again.",
            )
            return None
        if file_in_use(path):
            messagebox.showerror(
                "File In Use",
                f"The specified file is currently open in another program:\n{path}\n\nPlease close the file and try again.",
            )
            return None

        # Load configuration for required fields and sheet names
        config = load_config(config_path="config/config.json")

        if isinstance(path, str):
            path = Path(path)
        ext = path.suffix.lower()

        relevant_sheet = pick_sheet(path, file_type, config)
        print(f"Using sheet: {relevant_sheet} from file: {path.name}")

        # Prepare converters for specific file types to prevent unwanted type conversions
        converters_dict = converters.copy() if converters else {}

        if file_type == "ymbd":
            # Force Component column to be read as string to prevent float conversion
            # which can cause issues like 989606130501 becoming 989606130501.0
            converters_dict["Component"] = lambda x: str(x).strip()

        # Read file based on extension
        if ext == ".csv":
            df = pd.read_csv(
                path, header=header, converters=converters_dict if converters_dict else None
            )
        elif ext in [".xlsx", ".xlsm"]:
            df = pd.read_excel(
                path,
                sheet_name=relevant_sheet,
                header=header,
                engine="openpyxl",
                converters=converters_dict if converters_dict else None,
            )
        elif ext in [".xls"]:
            df = pd.read_excel(
                path,
                sheet_name=relevant_sheet,
                header=header,
                engine="xlrd",
                converters=converters_dict if converters_dict else None,
            )
            print("read .xls file with pandas")
        else:
            raise ValueError(
                f"Unsupported file format: {ext}. Only .xlsx, .xlsm, and .csv files are supported."
            )

        print(f"#######DataFrame shape: {df.shape}#########")
        required_columns = config[file_type].get("required_fields", [])

        if not set(required_columns).issubset(set(df.columns)):
            messagebox.showerror(
                "Error", f"Sheet '{relevant_sheet}' must contain columns: {required_columns}"
            )
            return None

        return df

    except Exception as e:
        print(f"Error reading file: {e}")
        messagebox.showerror("Error", f"Could not read file:\n{e}")
        return None
