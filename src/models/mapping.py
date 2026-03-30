from dataclasses import dataclass
from typing import Dict, List
from src.models.sales_record import SalesRecord


@dataclass
class Room:
    """room with multiple 12NCs and its sales history"""

    id: str
    description: str
    components: Dict[str, int]  # {12NC: quantity}
    sales_history: List[SalesRecord]  # {12NC: SalesRecord}

    @property
    def twelve_ncs(self) -> Dict[str, int]:
        """Alias for components field"""
        return self.components

    @property
    def total_items(self) -> int:
        """Total number of items in room"""
        return sum(self.components.values())

    def has_12nc(self, twelve_nc: str) -> bool:
        """Check if room contains specific 12NC"""
        return twelve_nc in self.components

    def show_12ncs(self) -> None:
        print(f"Room: {self.id} contains the following 12NCs:")
        for nc, qty in self.components.items():
            print(f"12NC: {nc}, Quantity: {qty}")

    def show_sales_history(self) -> None:
        print(f"Sales history for Room: {self.id}")
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
        if not self.id:
            raise ValueError("Room cannot be empty")
        if not self.description:
            raise ValueError("Room description cannot be empty")


@dataclass
class TwelveNC:
    """Mapping between 12NCs and rooms"""

    id: str
    description: str
    igt: str
    components: Dict[str, int]  # {room: quantity}
    sales_history: List[SalesRecord]  # {room: SalesRecord}

    @property
    def rooms(self) -> Dict[str, int]:
        """Alias for components field"""
        return self.components

    @property
    def total_items(self) -> int:
        """Total number of items for 12NC"""
        return sum(self.components.values())

    def has_room(self, room: str) -> bool:
        """Check if 12NC is in specific room"""
        return room in self.components

    def show_rooms(self) -> None:
        print(f"12NC: {self.id} is found in the following rooms:")
        for room, qty in self.components.items():
            print(f"Room: {room}, Quantity: {qty}")

    def show_sales_history(self) -> None:
        print(f"Sales history for 12NC: {self.id}")
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
        if not self.id:
            raise ValueError("12NC cannot be empty")
        if not self.description:
            raise ValueError("12NC description cannot be empty")


@dataclass
class G_entity:
    """Base class for Room and 12NC entities"""

    g_entity: Room | TwelveNC
    entity_type: str  # "room" or "12NC"


def __init__(self, g_entity: Room | TwelveNC, entity_type: str):
    if entity_type not in ["room", "12NC"]:
        raise ValueError("entity_type must be 'room' or '12NC'")
    self.g_entity = g_entity
    self.entity_type = entity_type
