# Data class for individual sales records in the Room-12NC Performance Center application
from dataclasses import dataclass
from datetime import date


@dataclass
class SalesRecord:
    """Individual sales transaction"""

    identifier: str  # Could be room or 12NC depending on context
    quantity: int
    date: date

    def __post_init__(self):
        """Validate data on initialization"""
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if not self.identifier:
            raise ValueError("Identifier cannot be empty")

    def recognize_type(self) -> str:
        """Determine if identifier is a 12NC or Room based on format"""
        if self.identifier.isdigit() and len(self.identifier) == 12:
            return "12NC"
        else:
            return "Room"
