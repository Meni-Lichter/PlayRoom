from datetime import datetime, date
from typing import List, Dict
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from pyparsing.diagram import T

from src.models.mapping import Room, TwelveNC
from ..models import SalesRecord, PerformanceData, TimePeriod
from ..utils import get_period_key


class PerformanceAnalyzer:
    """Feature 2: Analyze historical performance"""

    def __init__(self):
        self.sales_data = []  # This will be set by the PerformanceCenter when initialized

    def analyze(
        self,
        analyzed_obj: Room | TwelveNC,
        obj_type: str = "room",
        lookback_years: int = 3,
        granularity: str = "monthly",
    ) -> PerformanceData:
        """Main analysis function to analyze performance for a given 12NC or Room
        input:
            - identifier: the 12NC or Room number to analyze
            - id_type: "12nc" or "room"
            - lookback_years: number of years to look back for analysis
            - granularity: "monthly" or "yearly"
        output:
            - PerformanceData object containing historical performance data
        """
        self.sales_data = (
            analyzed_obj.sales_records
        )  # Assuming Room and TwelveNC have a sales_records attribute

        end_date = datetime.now().date()
        start_date = end_date - relativedelta(years=lookback_years)

        filtered_sales = self._filter_sales(analyzed_obj, obj_type, start_date, end_date)

        grouped = self._group_by_period(filtered_sales, granularity)

        periods = []  # List of TimePeriod objects for the performance data
        for period_key in sorted(grouped.keys()):
            sales = grouped[period_key]
            periods.append(TimePeriod(label=period_key, quantity=sum(s.quantity for s in sales)))

        total_qty = sum(p.quantity for p in periods)
        avg_qty = total_qty / len(periods) if periods else 0

        return PerformanceData(
            identifier=analyzed_obj.twelve_nc if obj_type == "12nc" else analyzed_obj.room,
            type=obj_type.upper(),
            periods=periods,
            total=total_qty,
            average=avg_qty,
        )

    def _filter_sales(
        self, analyzed_obj: Room | TwelveNC, obj_type: str, start_date: date, end_date: date
    ) -> List[SalesRecord]:
        """Private method to filter sales by identifier and date range
        input:
            - analyzed_obj: the Room or TwelveNC object to filter by
            - obj_type: "room" or "12nc"
            - start_date: the start date for filtering
            - end_date: the end date for filtering
        output:
            - List of SalesRecord that match the criteria
        """
        # DEBUG: Track filtering for specific 12NC
        target_12nc = "989606130501"
        if obj_type == "12nc" and analyzed_obj.twelve_nc == target_12nc:
            print(f"\n[ANALYZER DEBUG] Filtering sales for {analyzed_obj.twelve_nc}")
            print(f"[ANALYZER DEBUG] Total sales records: {len(self.sales_data)}")
            print(f"[ANALYZER DEBUG] Date range: {start_date} to {end_date}")
            print(f"[ANALYZER DEBUG] ID type: {obj_type}")

            # Count matches
            matching = [s for s in self.sales_data if s.twelve_nc == analyzed_obj.twelve_nc]
            print(
                f"[ANALYZER DEBUG] Records matching 12NC {analyzed_obj.twelve_nc}: {len(matching)}"
            )

            in_date_range = [s for s in matching if start_date <= s.date <= end_date]
            print(f"[ANALYZER DEBUG] Records in date range: {len(in_date_range)}")

            if len(matching) > 0:
                print(
                    f"[ANALYZER DEBUG] Sample dates for {analyzed_obj.twelve_nc}: {[s.date for s in matching[:3]]}"
                )
                print(
                    f"[ANALYZER DEBUG] Total quantity in matching records: {sum(s.quantity for s in matching)}"
                )

            if len(in_date_range) > 0:
                print(
                    f"[ANALYZER DEBUG] Total quantity in date range: {sum(s.quantity for s in in_date_range)}"
                )
                print(
                    f"[ANALYZER DEBUG] Date range of matching: {min(s.date for s in in_date_range)} to {max(s.date for s in in_date_range)}"
                )

            # Show sample of 12NCs in data
            unique_12ncs = list(set([s.twelve_nc for s in self.sales_data]))[:10]
            print(f"[ANALYZER DEBUG] Sample 12NCs in data: {unique_12ncs}")

        return [s for s in self.sales_data if (start_date <= s.date <= end_date)]

    def _group_by_period(
        self, sales: List[SalesRecord], granularity: str
    ) -> Dict[str, List[SalesRecord]]:
        """Group sales by time period based on the specified granularity,
        input:
            - sales: List of SalesRecord to group
            - granularity: "monthly" or "yearly"
        output:
            - Dictionary with period keys and corresponding sales records
        """
        groups = defaultdict(list)

        for sale in sales:
            key = get_period_key(sale.date, granularity)
            groups[key].append(sale)

        return groups

    def multi_item_analyze(
        self,
        analyzed_objs: List[Room | TwelveNC],
        objs_type: str = "12nc",
        lookback_years: int = 3,
        granularity: str = "monthly",
    ) -> Dict[str, List[PerformanceData]]:
        """Analyze multiple items:
        input:
            - analyzed_objs: List of Room or TwelveNC objects to analyze
            - objs_type: "12nc" or "room"
            - lookback_years: number of years to look back for analysis
            - granularity: "monthly" or "yearly"
        output:
            - dictionary of PerformanceData for each analyzed object
        """
        results = defaultdict(list)
        for analyzed_obj in analyzed_objs:
            try:
                performance_data = self.analyze(
                    analyzed_obj=analyzed_obj,
                    obj_type=objs_type,
                    lookback_years=lookback_years,
                    granularity=granularity,
                )
                results[analyzed_obj].append(performance_data)
            except Exception as e:
                print(f"Error analyzing {objs_type} '{analyzed_obj}': {e}")

        return results
