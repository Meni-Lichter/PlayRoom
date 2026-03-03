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
    - room_data: Dictionary {room_number: room_description, tncs['12NC (normalized)', '12NC (original)', '12NC_Description', 'Quantity']}}
    - data_12nc: Dictionary {12nc_number:  12nc_description, IGT 12NC, rooms['Room(normalized)','Room(original)', 'Room_Description', 'Quantity']}}
    """

    # Initialize dictionaries to hold data
    room_data = {}
    data_12nc = {}

    cbom_config = config["cbom"]
    # Get configuration values
    room_col_start = cbom_config["columns"].get("room_start", "G")
    room_num_row = cbom_config["rows"].get("room_numbers", 5)
    room_desc_row = cbom_config["rows"].get("room_descriptions", 4)
    nc12_col = cbom_config["columns"].get("12nc", "C")
    nc12_desc_col = cbom_config["columns"].get("12nc_description", "D")
    nc12_igt_col = cbom_config["columns"].get("IGT_12nc", "A")
    nc12_row_start = cbom_config["rows"].get("12nc_start", 9)

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

    # Extract the quantity matrix (from nc12_row_start, room columns onwards)
    quantity_matrix = df.iloc[nc12_row_start_idx:, room_col_idx:].values

    ############################
    # Process data for each room
    ############################
    valid_room_count = 0
    seen_rooms = set()
    print(f"\n[CBOM DEBUG] Processing rooms...")
    for room_idx, room_num in enumerate(room_numbers):
        if pd.isna(room_num):
            continue

        room_num_normalized = normalize_identifier(room_num)  # dict key

        room_description = (  # value to store in room_data for this room
            str(room_descriptions[room_idx]).strip()
            if not pd.isna(room_descriptions[room_idx])
            else ""
        )

        if not room_num_normalized or not re.match(
            config["validation"]["patterns"]["room_normalized"], room_num_normalized
        ):  # Validate normalized room format (e.g., "ROOM123")
            continue

        # Check for duplicates
        if room_num_normalized not in seen_rooms:
            print(f"[CBOM DEBUG] {room_num_normalized}: {room_description}")
            seen_rooms.add(room_num_normalized)
        else:
            print(f"[CBOM DEBUG] Duplicate room found: {room_num_normalized}")
            continue

        valid_room_count += 1
        # Collect all 12NCs for this room
        room_12ncs = []
        for nc12_idx, nc12_num in enumerate(nc12_numbers):
            if pd.isna(nc12_num):
                continue

            nc12_num_normalized = normalize_identifier(nc12_num)

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
                    "Quantity": quantity,
                }
            )

        # Create DataFrame for this room (use normalized room number as key)
        if room_12ncs:
            room_data[room_num_normalized] = {
                "description": room_description,
                "tnc_list": pd.DataFrame(room_12ncs),
            }

    ############################
    # Process data for each 12NC
    ############################
    valid_12nc_count = 0
    print(f"\n[CBOM DEBUG] Processing 12NCs...")
    print(f"[CBOM DEBUG] First 10 normalized 12NCs:")
    seen_12ncs = set()

    for nc12_idx, nc12_num in enumerate(nc12_numbers):
        if pd.isna(nc12_num):
            continue

        nc12_num_str = str(nc12_num).strip()

        nc12_num_normalized = normalize_identifier(nc12_num_str)  # dict key

        # Validate normalized format (12 digits)
        if not re.match(config["validation"]["patterns"]["12nc_normalized"], nc12_num_normalized):
            continue

        # Check for duplicates
        if nc12_num_normalized not in seen_12ncs:
            print(f"[CBOM DEBUG] {nc12_num_normalized}")
            seen_12ncs.add(nc12_num_normalized)
        else:
            print(f"[CBOM DEBUG] Duplicate 12NC found: {nc12_num_normalized}")
            continue

        valid_12nc_count += 1

        # Get 12NC description and IGT
        nc12_desc = (  # value to store in data_12nc for this 12NC
            str(nc12_descriptions[nc12_idx]).strip()
            if not pd.isna(nc12_descriptions[nc12_idx])
            else ""
        )
        nc12_igt = (
            str(nc12_igts[nc12_idx]).strip() if not pd.isna(nc12_igts[nc12_idx]) else ""
        )  # Store IGT 12NC if available

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
                    "Quantity": quantity,
                }
            )

        # Create DataFrame for this 12NC (use normalized 12NC as key)
        if nc12_rooms:
            data_12nc[nc12_num_normalized] = {
                "12NC_Description": nc12_desc,
                "12NC_IGT": nc12_igt,
                "room_list": pd.DataFrame(nc12_rooms),
            }

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

        # Only validate required columns if header was specified (not None)
        if header is not None:
            required_columns = config[file_type].get("columns", {}).values()

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
