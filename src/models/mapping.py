from dataclasses import dataclass
from typing import Dict, List
from src.models import SalesRecord


@dataclass
class Room:
    """room with multiple 12NCs and its sales history"""

    room: str
    room_description: str
    twelve_ncs: Dict[TwelveNC, int]  # {12NC: quantity}
    sales_history: List[SalesRecord]  # {12NC: SalesRecord}

    @property
    def total_items(self) -> int:
        """Total number of items in room"""
        return sum(self.twelve_ncs.values())

    def has_12nc(self, twelve_nc: str) -> bool:
        """Check if room contains specific 12NC"""
        return twelve_nc in self.twelve_ncs

    def show_12ncs(self) -> None:
        print(f"Room: {self.room} contains the following 12NCs:")
        for nc, qty in self.twelve_ncs.items():
            print(f"12NC: {nc}, Quantity: {qty}")

    def show_sales_history(self) -> None:
        print(f"Sales history for Room: {self.room}")
        for record in self.sales_history:
            print(
                f"12NC: {record.identifier}, Quantity Sold: {record.quantity}, Date: {record.date}"
            )

    def filter_sales_by_date(self, start_date, end_date) -> Dict[str, SalesRecord]:
        """Filter sales records by date range"""
        filtered_sales = {}
        for record in self.sales_history:
            if start_date <= record.date <= end_date:
                filtered_sales[record.identifier] = record
        return filtered_sales

    def __post_init__(self):
        """Validate data on initialization"""
        if not self.room:
            raise ValueError("Room cannot be empty")
        if not self.room_description:
            raise ValueError("Room description cannot be empty")


@dataclass
class TwelveNC:
    """Mapping between 12NCs and rooms"""

    twelve_nc: str
    tnc_description: str
    tnc_igt: str
    rooms: Dict[Room, int]  # {room: quantity}
    sales_history: List[SalesRecord]  # {room: SalesRecord}

    @property
    def total_items(self) -> int:
        """Total number of items for 12NC"""
        return sum(self.rooms.values())

    def has_room(self, room: str) -> bool:
        """Check if 12NC is in specific room"""
        return room in self.rooms

    def show_rooms(self) -> None:
        print(f"12NC: {self.twelve_nc} is found in the following rooms:")
        for room, qty in self.rooms.items():
            print(f"Room: {room}, Quantity: {qty}")

    def show_sales_history(self) -> None:
        print(f"Sales history for 12NC: {self.twelve_nc}")
        for record in self.sales_history:
            print(
                f"Room: {record.identifier}, Quantity Sold: {record.quantity}, Date: {record.date}"
            )

    def filter_sales_by_date(self, start_date, end_date) -> Dict[str, SalesRecord]:
        """Filter sales records by date range"""
        filtered_sales = {}
        for record in self.sales_history:
            if start_date <= record.date <= end_date:
                filtered_sales[record.identifier] = record
        return filtered_sales

    def __post_init__(self):
        """Validate data on initialization"""
        if not self.twelve_nc:
            raise ValueError("12NC cannot be empty")
        if not self.tnc_description:
            raise ValueError("12NC description cannot be empty")
