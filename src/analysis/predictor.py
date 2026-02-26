from calendar import calendar
from logging import config
from math import inf
from typing import List, Optional
from datetime import datetime
from webbrowser import get
from dateutil.relativedelta import relativedelta
from pandas import Period

from src.models.performance import TimePeriod
from ..models import PerformanceData, Prediction
from ..utils import get_next_period_label
from ..utils.config_util import load_config


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
        self,
        target_time: str,
        method: str = "average",
        buffer_percentage: float = 10.0,
        n_periods: int = 11,
    ) -> Prediction:
        """
        Predict demand for the next period

        Args:
            target_time: Target period label for prediction (e.g., '2024-03', '2024-Q1', '2024')
            method: Prediction method ("average", "last", "trend",
                    "avg_same_period_previous_years", "avg_last_n_periods", "same_period_last_year")
            buffer_percentage: Safety buffer percentage to add
            n_periods: Number of periods to average (only used for "avg_last_n_periods" method)

        Returns:
            Prediction object with forecasted quantity
        """
        if not self.performance_data.periods:
            raise ValueError("No historical data available for prediction")
        granularity = self._infer_granularity()
        target_time = match_granularity(target_time, granularity)

        # Calculate baseline prediction based on method
        if method == "avg_same_period_previous_years":
            baseline = self._predict_avg_same_period_previous_years(
                target_time, n_years=3, granularity=granularity
            )
        elif method == "avg_last_n_periods":
            baseline = self._predict_avg_last_n_periods(n_periods, granularity=granularity)
        elif method == "same_period_last_year":
            baseline = self._predict_same_period_last_year(target_time, granularity=granularity)
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
        """Infer time granularity from period labels (MM-DD-YYYY format)"""
        if not self.performance_data.periods:
            return "monthly"

        label = self.performance_data.periods[0].label

        if "-Q" in label:
            return "quarterly"
        elif len(label) == 4 and label.isdigit():
            return "yearly"
        elif len(label) == 10 and label.count("-") == 2:  # MM-DD-YYYY
            return "daily"
        elif len(label) == 7 and label[2] == "-":  # MM-YYYY
            return "monthly"
        else:
            return "monthly"

    def _extract_date_parts(self, period_label: str) -> Optional[tuple[int, int]]:
        """Extract date parts from period label in MM-DD-YYYY format
        Args:
            period_label: Period label (e.g., '02-2025', '02-24-2025', '2025-Q1')

        Returns:
            Tuple of (month, year) or None for yearly granularity
        """
        try:
            if "-Q" in period_label:
                # Quarterly format: YYYY-Qn
                parts = period_label.split("-Q")
                year = int(parts[0])
                quarter = int(parts[1])
                # Use middle month of quarter
                month = quarter * 3 - 1
                return (month, year)
            elif len(period_label) == 7 and period_label[2] == "-":
                # Monthly format: MM-YYYY
                month = int(period_label[:2])
                year = int(period_label[3:])
                return (month, year)
            elif len(period_label) == 10 and period_label.count("-") == 2:
                # Daily format: MM-DD-YYYY
                date_obj = datetime.strptime(period_label, "%m-%d-%Y")
                return (date_obj.month, date_obj.year)
            elif len(period_label) == 4 and period_label.isdigit():
                # Yearly format: YYYY - no specific month
                return None
        except (ValueError, IndexError):
            pass
        return None

    def _predict_avg_same_period_previous_years(
        self, target_time: str, n_years: int = 3, granularity: str = "monthly"
    ) -> float:
        """Predict based on average of the same period in previous years

        For example: predict March 2026 based on average of March 2023, 2024, 2025

        Returns:
            Predicted quantity based on historical same-period average
        """
        if granularity == "yearly":
            # For yearly, average the last n years
            recent = self.performance_data.periods[-n_years:]

            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )

        elif granularity == "monthly":
            # for monthly, average the target month from previous n years
            recent = self.performance_data.periods[-n_years * 12 :]
            target_month = target_time[:2]  # Extract month from MM-YYYY format
            matching_months = [float(p.quantity) for p in recent if p.label[:2] == target_month]
            return (
                sum(matching_months) / len(matching_months)
                if matching_months
                else self.performance_data.average
            )

        elif granularity == "quarterly":
            # for quarterly, average the target quarter from previous n years
            recent = self.performance_data.periods[-n_years * 4 :]
            target_month = target_time[5:7]  # Extract quarter from target_time
            target_quarter = int((int(target_month) - 1) / 3) + 1  # Convert month to quarter
            matching_quarters = [
                float(p.quantity)
                for p in recent
                if int((int(p.label[5:7]) - 1) / 3) + 1 == target_quarter
            ]
            return (
                sum(matching_quarters) / len(matching_quarters)
                if matching_quarters
                else self.performance_data.average
            )
        elif granularity == "daily":
            # for daily, average the target day from previous n years
            recent = self.performance_data.periods[-n_years * 365 :]
            target_day = target_time[:5]  # Extract day from MM-DD-YYYY format
            matching_days = [float(p.quantity) for p in recent if p.label[:5] == target_day]
            return (
                sum(matching_days) / len(matching_days)
                if matching_days
                else self.performance_data.average
            )

        next_period_info = self._extract_date_parts(target_time)
        if next_period_info is None:
            return self.performance_data.average

        target_month, target_year = next_period_info
        matching_periods = []

        # For daily: also match the specific day, not just month
        for period in self.performance_data.periods:
            period_info = self._extract_date_parts(period.label)
            if not period_info:
                continue

            month, year = period_info

            # Match same month from previous n years
            if month == target_month and (target_year - n_years <= year < target_year):
                # For daily, add additional filtering here
                if granularity == "daily":
                    # Extract and compare day numbers
                    pass
                matching_periods.append(float(period.quantity))

        if not matching_periods:
            return self.performance_data.average

        return sum(matching_periods) / len(matching_periods)

    def _predict_avg_last_n_periods(
        self, n_periods: int = 11, granularity: str = "monthly"
    ) -> float:
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

    def _predict_same_period_last_year(
        self, target_time: str | None, granularity: str = "monthly"
    ) -> float:
        """Predict based on the same period exactly one year ago

        For example: predict March 2026 based on March 2025

        Returns:
            Predicted quantity based on same period last year
        """
        granularity = self._infer_granularity()
        next_period = get_next_period_label(granularity)
        next_period_info = self._extract_date_parts(next_period)

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
        self, periods: List[TimePeriod], method: str = "average", buffer_percentage: float = 10.0
    ) -> List[Prediction]:
        """
        Predict demand for multiple future periods

        Args:
            periods: List of future periods to predict
            method: Prediction method
            buffer_percentage: Safety buffer percentage

        Returns:
            List of Prediction objects
        """
        predictions = []

        for i in periods:
            prediction = self.predict(i.label, method, buffer_percentage)
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


def match_granularity(target_time: str, granularity: str) -> str:
    """
    Adjust target_time to match the granularity of historical performance data.

    If target is more specific than data (e.g., daily target but monthly data),
    convert target to data's granularity and notify user.

    If target is less specific than data (e.g., monthly target but daily data),
    keep target as-is (aggregation will happen during prediction).

    Args:
        target_time: User's requested target period
        granularity: Granularity of historical performance data

    Returns:
        Adjusted target_time matching data granularity
    """

    config = load_config()
    date_format = config["validation"].get("date_format", "MM-DD-YYYY")
    target_time = str(target_time)
    label_granularity = get_granularity_from_label(target_time, date_format)

    # If granularities match, no adjustment needed
    if label_granularity == granularity:
        return target_time

    # Define granularity hierarchy (least to most specific)
    granularity_order = {"yearly": 1, "quarterly": 2, "monthly": 3, "daily": 4}

    target_level = granularity_order.get(label_granularity, 0)
    data_level = granularity_order.get(granularity, 0)

    # Target is MORE specific than data - need to convert UP
    if target_level > data_level:
        print(
            f"⚠️  Warning: Target time '{target_time}' is {label_granularity}, "
            f"but data is {granularity}. Converting to {granularity} granularity."
        )

        try:
            # Parse based on label granularity using MM-DD-YYYY format
            if label_granularity == "daily":
                # Parse MM-DD-YYYY format
                date_obj = datetime.strptime(target_time, "%m-%d-%Y")
            elif label_granularity == "monthly":
                # Parse MM-YYYY format
                date_obj = datetime.strptime(target_time, "%m-%Y")
            elif label_granularity == "quarterly":
                parts = target_time.split("-Q")
                year = int(parts[0])
                quarter = int(parts[1])
                month = quarter * 3 - 2  # First month of quarter
                date_obj = datetime(year, month, 1)
            elif label_granularity == "yearly":
                date_obj = datetime(int(target_time), 1, 1)
            else:
                return target_time  # Can't parse, return as-is

            # Convert to data's granularity using MM-DD-YYYY format
            if granularity == "yearly":
                return f"{date_obj.year}"
            elif granularity == "quarterly":
                quarter = (date_obj.month - 1) // 3 + 1
                return f"{date_obj.year}-Q{quarter}"
            elif granularity == "monthly":
                # Return in MM-YYYY format
                return f"{date_obj.month:02d}-{date_obj.year}"
            elif granularity == "daily":
                # Return in MM-DD-YYYY format
                return date_obj.strftime("%m-%d-%Y")

        except (ValueError, IndexError, AttributeError) as e:
            print(f"⚠️  Error parsing target time '{target_time}': {e}. Using as-is.")
            return target_time

    # Target is LESS specific than data - keep target as-is
    # Aggregation will happen during prediction
    else:
        print(
            f"ℹ️  Target time '{target_time}' is {label_granularity}, "
            f"data is {granularity}. Will aggregate data to match target."
        )
        return target_time


def get_granularity_from_label(label: str, date_format: str) -> str:
    """Determine granularity from a period label using MM-DD-YYYY format

    Args:
        label: Period label to analyze
        date_format: Date format from config (e.g., 'MM-DD-YYYY')

    Returns:
        Granularity string: 'yearly', 'quarterly', 'monthly', or 'daily'
    """
    if "-Q" in label:
        return "quarterly"
    elif len(label) == 10 and label.count("-") == 2:  # MM-DD-YYYY (e.g., 02-24-2025)
        return "daily"
    elif len(label) == 7 and label[2] == "-":  # MM-YYYY (e.g., 02-2025)
        return "monthly"
    elif len(label) == 4 and label.isdigit():  # YYYY
        return "yearly"
    else:
        return "monthly"  # Default
