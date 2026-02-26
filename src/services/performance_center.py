"""Performance Center - High-level service orchestrating all features"""

from typing import List, Dict, Optional
from ..models import SalesRecord, PerformanceData, Prediction, Room, TwelveNC
from ..analysis import PerformanceAnalyzer, Predictor


class PerformanceCenter:
    """High-level API combining all features for Room-12NC Performance Analysis"""

    def __init__(self, rooms: List[Room], nc12s: List[TwelveNC]):
        """
        Initialize Performance Center with sales data and CBOM data

        Args:
            sales_data: List of historical sales records coming from ymbd and fit reports
            rooms: List of Room objects (CBOM data)
            nc12s: List of TwelveNC objects (CBOM data)
        """
        self.rooms = rooms
        self.nc12s = nc12s
        self.analyzer = PerformanceAnalyzer()

    def analyze_obj_performance(
        self,
        analyzed_obj: Room | TwelveNC,
        obj_type: str = "room",
        lookback_years: int = 3,
        granularity: str = "monthly",
    ) -> PerformanceData:
        """
        Analyze historical performance for a specific object (Room or TwelveNC)

        Args:
            analyzed_obj: Room or TwelveNC object
            obj_type: Type of the object ("room" or "12nc")
            lookback_years: Number of years of history to analyze
            granularity: Time granularity ("daily", "monthly", "quarterly", "yearly")

        Returns:
            PerformanceData object with historical performance
        """
        return self.analyzer.analyze(
            analyzed_obj, obj_type=obj_type, lookback_years=lookback_years, granularity=granularity
        )

    def predict_room_demand(
        self,
        room: Room,
        target_time: str | None,
        lookback_years: int = 3,
        method: str = "average",
        buffer_percentage: float = 10.0,
    ) -> Prediction:
        """
        Predict future demand for a room (Feature 2 + Feature 3 combined)

        Args:
            room: Room identifier
            lookback_years: Years of history to use for prediction
            method: Prediction method ("average", "last", "trend")
            buffer_percentage: Safety buffer percentage

        Returns:
            Prediction object with forecasted demand
        """
        # First analyze historical performance
        performance = self.analyze_obj_performance(
            room, obj_type="room", lookback_years=lookback_years
        )

        # Then predict based on performance
        predictor = Predictor(performance)
        return predictor.predict(
            target_time=target_time, method=method, buffer_percentage=buffer_percentage
        )

    def predict_12nc_demand(
        self,
        twelve_nc: TwelveNC,
        lookback_years: int = 3,
        method: str = "average",
        buffer_percentage: float = 10.0,
    ) -> Prediction:
        """
        Predict future demand for a 12NC (Feature 2 + Feature 3 combined)

        Args:
            twelve_nc: 12NC identifier
            lookback_years: Years of history to use for prediction
            method: Prediction method
            buffer_percentage: Safety buffer percentage

        Returns:
            Prediction object with forecasted demand
        """
        # First analyze historical performance
        performance = self.analyze_12nc_performance(twelve_nc, lookback_years)

        # Then predict based on performance
        predictor = Predictor(performance)
        return predictor.predict(method=method, buffer_percentage=buffer_percentage)

    def get_room_components(self, room: str) -> Dict[TwelveNC, int] | None:
        """
        Get the 12NC components for a specific room from CBOM data (Feature 1)

        Args:
            room: Room identifier

        Returns:
            Dictionary of 12NC components or None if not found
        """
        for room_obj in self.rooms:
            if room_obj.room == room:
                return room_obj.twelve_ncs
        return None

    def get_12nc_rooms(self, twelve_nc: str) -> Dict[Room, int] | None:
        """
        Get the rooms containing a specific 12NC from CBOM data (Feature 1)

        Args:
            twelve_nc: 12NC identifier

        Returns:
            Dictionary of rooms or None if not found
        """
        for tnc_obj in self.nc12s:
            if tnc_obj.twelve_nc == twelve_nc:
                return tnc_obj.rooms
        return None

    def analyze_multiple_rooms(
        self, rooms: List[str], lookback_years: int = 3, granularity: str = "monthly"
    ) -> dict[str, List[PerformanceData]]:
        """
        Analyze performance for multiple rooms at once

        Args:
            rooms: List of room identifiers
            lookback_years: Years of history to analyze
            granularity: Time granularity

        Returns:
            Dictionary of PerformanceData objects keyed by room identifier
        """
        return self.analyzer.multi_item_analyze(
            rooms, id_type="room", lookback_years=lookback_years, granularity=granularity
        )

    def analyze_multiple_12ncs(
        self, twelve_ncs: List[str], lookback_years: int = 3, granularity: str = "monthly"
    ) -> dict[str, List[PerformanceData]]:
        """
        Analyze performance for multiple 12NCs at once

        Args:
            twelve_ncs: List of 12NC identifiers
            lookback_years: Years of history to analyze
            granularity: Time granularity

        Returns:
            Dictionary of PerformanceData objects keyed by 12NC identifier
        """
        return self.analyzer.multi_item_analyze(
            twelve_ncs, id_type="12nc", lookback_years=lookback_years, granularity=granularity
        )

    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics about available data

        Returns:
            Dictionary with counts and summary info
        """
        return {
            "total_sales_records": len(self.sales_data),
            "total_rooms_in_cbom": len(self.room_mappings),
            "total_12ncs_in_cbom": len(self.nc12_mappings),
            "date_range": {
                "earliest": min(s.date for s in self.sales_data) if self.sales_data else None,
                "latest": max(s.date for s in self.sales_data) if self.sales_data else None,
            },
        }
