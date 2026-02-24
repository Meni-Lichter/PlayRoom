from datetime import datetime, date
from typing import List, Dict
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from ..models import SalesRecord, PerformanceData, TimePeriod
from ..utils import get_period_key


class PerformanceAnalyzer:
    """Feature 2: Analyze historical performance"""

    def __init__(self, sales_data: List[SalesRecord]):
        self.sales_data: List[SalesRecord] = sales_data

    def analyze(
        self,
        identifier: str,
        id_type: str = "12nc",
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
        end_date = datetime.now().date()
        start_date = end_date - relativedelta(years=lookback_years)

        filtered_sales = self._filter_sales(identifier, id_type, start_date, end_date)

        grouped = self._group_by_period(filtered_sales, granularity)

        periods = []  # List of TimePeriod objects for the performance data
        for period_key in sorted(grouped.keys()):
            sales = grouped[period_key]
            periods.append(TimePeriod(label=period_key, quantity=sum(s.quantity for s in sales)))

        total_qty = sum(p.quantity for p in periods)
        avg_qty = total_qty / len(periods) if periods else 0

        return PerformanceData(
            identifier=identifier,
            type=id_type.upper(),
            periods=periods,
            total=total_qty,
            average=avg_qty,
        )

    def _filter_sales(
        self, identifier: str, id_type: str, start_date: date, end_date: date
    ) -> List[SalesRecord]:
        """Private method to filter sales by identifier and date range
        input:
            - identifier: the 12NC or Room number to filter by
            - id_type: "12nc" or "room"
            - start_date: the start date for filtering
            - end_date: the end date for filtering
        output:
            - List of SalesRecord that match the criteria
        """
        return [
            s
            for s in self.sales_data
            if (
                (start_date <= s.date <= end_date)
                and (s.twelve_nc == identifier if id_type == "12nc" else s.room == identifier)
            )
        ]

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
        identifiers: List[str],
        id_type: str = "12nc",
        lookback_years: int = 3,
        granularity: str = "monthly",
    ) -> Dict[str, List[PerformanceData]]:
        """Analyze multiple items:
        input:
            - identifiers: List of 12NCs or Room numbers to analyze
            - id_type: "12nc" or "room"
            - lookback_years: number of years to look back for analysis
            - granularity: "monthly" or "yearly"
        output:
            - dictionary of PerformanceData for each identifier
        """
        results = defaultdict(list)
        for identifier in identifiers:
            try:
                performance_data = self.analyze(
                    identifier=identifier,
                    id_type=id_type,
                    lookback_years=lookback_years,
                    granularity=granularity,
                )
                results[identifier].append(performance_data)
            except Exception as e:
                print(f"Error analyzing {id_type} '{identifier}': {e}")

        return results
