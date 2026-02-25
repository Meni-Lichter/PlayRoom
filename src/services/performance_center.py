"""Performance Center - High-level service orchestrating all features"""

from typing import List, Dict, Optional
from ..models import SalesRecord, PerformanceData, Prediction, Room, TwelveNC
from ..analysis import PerformanceAnalyzer, Predictor


class PerformanceCenter:
    """High-level API combining all features for Room-12NC Performance Analysis"""

    def __init__(
        self,
        sales_data: List[SalesRecord],
        room_mappings: Optional[List[Room]] = None,
        nc12_mappings: Optional[List[TwelveNC]] = None,
    ):
        """
        Initialize Performance Center with sales data and optional mappings

        Args:
            sales_data: List of historical sales records
            room_mappings: Optional list of Room objects (CBOM data)
            nc12_mappings: Optional list of TwelveNC objects (CBOM data)
        """
        self.sales_data = sales_data
        self.room_mappings = room_mappings or []
        self.nc12_mappings = nc12_mappings or []
        self.analyzer = PerformanceAnalyzer(sales_data)

    def analyze_room_performance(
        self, room: str, lookback_years: int = 3, granularity: str = "monthly"
    ) -> PerformanceData:
        """
        Analyze historical performance for a specific room

        Args:
            room: Room identifier
            lookback_years: Number of years of history to analyze
            granularity: Time granularity ("daily", "weekly", "monthly", "quarterly", "yearly")

        Returns:
            PerformanceData object with historical performance
        """
        return self.analyzer.analyze(
            room, id_type="room", lookback_years=lookback_years, granularity=granularity
        )

    def analyze_12nc_performance(
        self, twelve_nc: str, lookback_years: int = 3, granularity: str = "monthly"
    ) -> PerformanceData:
        """
        Analyze historical performance for a specific 12NC

        Args:
            twelve_nc: 12NC identifier
            lookback_years: Number of years of history to analyze
            granularity: Time granularity

        Returns:
            PerformanceData object with historical performance
        """
        return self.analyzer.analyze(
            twelve_nc, id_type="12nc", lookback_years=lookback_years, granularity=granularity
        )

    def predict_room_demand(
        self,
        room: str,
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
        performance = self.analyze_room_performance(room, lookback_years)

        # Then predict based on performance
        predictor = Predictor(performance)
        return predictor.predict(method=method, buffer_percentage=buffer_percentage)

    def predict_12nc_demand(
        self,
        twelve_nc: str,
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

    def get_room_components(self, room: str) -> Optional[Room]:
        """
        Get the 12NC components for a specific room from CBOM data (Feature 1)

        Args:
            room: Room identifier

        Returns:
            Room object or None if not found
        """
        for mapping in self.room_mappings:
            if mapping.room == room:
                return mapping
        return None

    def get_12nc_rooms(self, twelve_nc: str) -> Optional[TwelveNC]:
        """
        Get the rooms containing a specific 12NC from CBOM data (Feature 1)

        Args:
            twelve_nc: 12NC identifier

        Returns:
            TwelveNC object or None if not found
        """
        for mapping in self.nc12_mappings:
            if mapping.twelve_nc == twelve_nc:
                return mapping
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
