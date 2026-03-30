"""Performance Center - High-level service orchestrating all features"""

from typing import List, Dict

from src.utils.date_utils import _infer_granularity
from ..models import PerformanceData, Prediction, Room, TwelveNC, G_entity
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

    def analyze_entity_performance(
        self,
        analyzed_obj: G_entity,
        lookback_years: int = 3,
        granularity: str = "monthly",
    ) -> PerformanceData:
        """
        Analyze historical performance for a specific entity (Room or TwelveNC)

        Args:
            analyzed_obj: Room or TwelveNC object
            lookback_years: Number of years of history to analyze
            granularity: Time granularity ("daily", "monthly", "quarterly", "yearly")

        Returns:
            PerformanceData object with historical performance
        """
        return self.analyzer.analyze(
            analyzed_obj, lookback_years=lookback_years, granularity=granularity
        )

    def predict_entity_demand(
        self,
        entity: G_entity,
        target_time: str,
        lookback_years: int = 3,
        method: str = "average",
        buffer_percentage: float = 10.0,
    ) -> Prediction:
        """
        Predict future demand for an entity (Room or TwelveNC) (Feature 2 + Feature 3 combined)

        Args:
            entity: Room or TwelveNC object
            lookback_years: Years of history to use for prediction
            method: Prediction method ("average", "last", "trend")
            buffer_percentage: Safety buffer percentage

        Returns:
            Prediction object with forecasted demand
        """
        granularity = _infer_granularity(target_time)
        # First analyze historical performance
        performance = self.analyze_entity_performance(
            entity, lookback_years=lookback_years, granularity=granularity
        )

        # Then predict based on performance
        predictor = Predictor(performance)
        return predictor.predict(
            target_time=target_time, method=method, buffer_percentage=buffer_percentage
        )

    def get_entity_components(self, entity: G_entity) -> Dict[str, int] | None:
        """
        Get the 12NC components for a specific room from CBOM data (Feature 1)

        Args:
            room: Room identifier

        Returns:
            Dictionary of 12NC components or None if not found
        """
        if isinstance(entity.g_entity, Room):
            for room_obj in self.rooms:
                if room_obj.id == entity.g_entity.id:
                    return room_obj.components
        elif isinstance(entity.g_entity, TwelveNC):
            for tnc_obj in self.nc12s:
                if tnc_obj.id == entity.g_entity.id:
                    return tnc_obj.components
        else:
            raise ValueError("Entity must be of type Room or TwelveNC")

    def analyze_multiple_entities(
        self, entities: List[G_entity], lookback_years: int = 3, granularity: str = "monthly"
    ) -> dict[str, List[PerformanceData]]:
        """
        Analyze performance for multiple entities (Room or TwelveNC) at once

        Args:
            entities: List of G_entity objects to analyze
            lookback_years: Years of history to analyze
            granularity: Time granularity

        Returns:
            Dictionary of PerformanceData objects keyed by entity identifier
        """
        return self.analyzer.multi_item_analyze(
            entities, lookback_years=lookback_years, granularity=granularity
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
