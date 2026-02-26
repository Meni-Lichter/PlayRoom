from typing import List, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
from ..models import PerformanceData, Prediction
from ..utils import get_next_period_label


class Predictor:
    """Feature 3: Predict future demand based on historical performance"""

    def __init__(self, performance_data: PerformanceData):
        """
        Initialize predictor with historical performance data

        Args:
            performance_data: PerformanceData object with historical periods
        """
        self.performance_data = performance_data

    def predict(
        self, method: str = "average", buffer_percentage: float = 10.0, n_periods: int = 11
    ) -> Prediction:
        """
        Predict demand for the next period

        Args:
            method: Prediction method ("average", "last", "trend",
                    "avg_same_period_previous_years", "avg_last_n_periods", "same_period_last_year")
            buffer_percentage: Safety buffer percentage to add
            n_periods: Number of periods to average (only used for "avg_last_n_periods" method)

        Returns:
            Prediction object with forecasted quantity
        """
        if not self.performance_data.periods:
            raise ValueError("No historical data available for prediction")

        # Calculate baseline prediction based on method
        if method == "avg_same_period_previous_years":
            baseline = self._predict_avg_same_period_previous_years()
        elif method == "avg_last_n_periods":
            baseline = self._predict_avg_last_n_periods(n_periods)
        elif method == "same_period_last_year":
            baseline = self._predict_same_period_last_year()
        else:  # default to average
            baseline = self.performance_data.average

        # Apply buffer
        predicted_quantity = baseline * (1 + buffer_percentage / 100)

        # Determine next period label based on current granularity
        granularity = self._infer_granularity()
        next_period = get_next_period_label(granularity)

        return Prediction(
            identifier=self.performance_data.identifier,
            type=self.performance_data.type,
            period_label=next_period,
            predicted_quantity=predicted_quantity,
            baseline=baseline,
            buffer_percentage=buffer_percentage,
            method=method,
        )

    def _infer_granularity(self) -> str:
        """Infer time granularity from period labels"""
        if not self.performance_data.periods:
            return "monthly"

        label = self.performance_data.periods[0].label

        if "-W" in label:
            return "weekly"
        elif "-Q" in label:
            return "quarterly"
        elif len(label) == 4 and label.isdigit():
            return "yearly"
        elif len(label) == 10:  # YYYY-MM-DD
            return "daily"
        else:
            return "monthly"

    def _extract_date_parts(self, period_label: str) -> Optional[tuple[int, int]]:
        """Extract all date parts from date label - year, quarter, month, week, day as applicable
        Args:
            period_label: Period label (e.g., '2024-03', '2024-Q1', '2024')

        Returns:
            Array pf all data parts from year to day
        """
        try:
            if "-W" in period_label:
                # Weekly format: YYYY-Wnn
                parts = period_label.split("-W")
                year = int(parts[0])
                week = int(parts[1])
                # Convert week to approximate month
                approx_month = min(12, max(1, (week - 1) // 4 + 1))
                return (approx_month, year)
            elif "-Q" in period_label:
                # Quarterly format: YYYY-Qn
                parts = period_label.split("-Q")
                year = int(parts[0])
                quarter = int(parts[1])
                # Use middle month of quarter
                month = quarter * 3 - 1
                return (month, year)
            elif len(period_label) == 7 and period_label[4] == "-":
                # Monthly format: YYYY-MM
                year = int(period_label[:4])
                month = int(period_label[5:7])
                return (month, year)
            elif len(period_label) == 10:
                # Daily format: YYYY-MM-DD
                date_obj = datetime.strptime(period_label, "%Y-%m-%d")
                return (date_obj.month, date_obj.year)
            elif len(period_label) == 4 and period_label.isdigit():
                # Yearly format: YYYY - no specific month
                return None
        except (ValueError, IndexError):
            pass
        return None

    def _predict_avg_same_period_previous_years(self, n_years: int = 3) -> float:
        """Predict based on average of the same period in previous years

        For example: predict March 2026 based on average of March 2023, 2024, 2025

        Returns:
            Predicted quantity based on historical same-period average
        """
        granularity = self._infer_granularity()
        next_period = get_next_period_label(granularity)

        if granularity == "yearly":
            # For yearly, average the last n years
            recent = self.performance_data.periods[-n_years:]
            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )

        next_period_info = self._extract_date_parts(next_period)
        if next_period_info is None:
            return self.performance_data.average

        target_month, target_year = next_period_info
        matching_periods = []

        # For weekly/daily: also match the specific week/day, not just month
        for period in self.performance_data.periods:
            period_info = self._extract_date_parts(period.label)
            if not period_info:
                continue

            month, year = period_info

            # Match same month from previous n years
            if month == target_month and (target_year - n_years <= year < target_year):
                # For weekly/daily, add additional filtering here
                if granularity == "weekly":
                    # Extract and compare week numbers
                    pass
                elif granularity == "daily":
                    # Extract and compare day numbers
                    pass
                matching_periods.append(float(period.quantity))

        if not matching_periods:
            return self.performance_data.average

        return sum(matching_periods) / len(matching_periods)

    def _predict_avg_last_n_periods(self, n_periods: int = 11) -> float:
        """Predict based on average of the last n periods

        For example: predict March 2026 based on average of last 11 months

        Args:
            n_periods: Number of recent periods to average

        Returns:
            Predicted quantity based on recent n-period average
        """
        if len(self.performance_data.periods) == 0:
            return 0.0

        # Use last n periods or all available if less than n
        recent_periods = self.performance_data.periods[-n_periods:]
        total = sum(float(period.quantity) for period in recent_periods)
        return total / len(recent_periods)

    def _predict_same_period_last_year(self) -> float:
        """Predict based on the same period exactly one year ago

        For example: predict March 2026 based on March 2025

        Returns:
            Predicted quantity based on same period last year
        """
        granularity = self._infer_granularity()
        next_period = get_next_period_label(granularity)
        next_period_info = self._extract_month_year(next_period)

        if next_period_info is None:
            # For yearly granularity, just use the last year's data
            if self.performance_data.periods:
                return float(self.performance_data.periods[-1].quantity)
            return self.performance_data.average

        target_month, target_year = next_period_info
        last_year = target_year - 1

        # Find the period from last year with the same month
        for period in reversed(self.performance_data.periods):
            period_info = self._extract_month_year(period.label)
            if period_info and period_info[0] == target_month and period_info[1] == last_year:
                return float(period.quantity)

        # Fallback: if exact match not found, use average
        return self.performance_data.average

    def multi_period_predict(
        self, periods: int = 3, method: str = "average", buffer_percentage: float = 10.0
    ) -> List[Prediction]:
        """
        Predict demand for multiple future periods

        Args:
            periods: Number of future periods to predict
            method: Prediction method
            buffer_percentage: Safety buffer percentage

        Returns:
            List of Prediction objects
        """
        predictions = []

        for i in range(periods):
            prediction = self.predict(method, buffer_percentage)
            predictions.append(prediction)

            # For subsequent predictions, we could update the baseline
            # but for simplicity, we'll use the same approach

        return predictions

    def set_buffer_percentage(self, new_buffer: float):
        """Update buffer percentage for future predictions

        Args:
            new_buffer: New buffer percentage to apply
        """
        if new_buffer < 0:
            raise ValueError("Buffer percentage cannot be negative")
        self.buffer_percentage = new_buffer
