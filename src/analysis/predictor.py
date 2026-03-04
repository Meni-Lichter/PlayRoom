from typing import List
from datetime import date, datetime
from src.models.performance import TimePeriod
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
        self,
        target_time: str,
        method: str = "avg_last_n_periods",
        buffer_percentage: float = 10.0,
        n_periods: int = 11,
    ) -> Prediction:
        """
        Predict demand for the next period

        Args:
            target_time: Target period label for prediction (e.g., '2024-03', '2024-Q1', '2024')
            method: Prediction method ("avg_same_period_previous_years", "avg_last_n_periods")
            buffer_percentage: Safety buffer percentage to add
            n_periods: Number of periods to average (only used for "avg_last_n_periods" method)

        Returns:
            Prediction object with forecasted quantity
        """
        if not self.performance_data.periods:
            raise ValueError("No historical data available for prediction")

        granularity = self.performance_data.granularity

        # Validate target_time is in the future (format depends on granularity)
        self._validate_future_target(target_time, granularity)

        # Calculate baseline prediction based on method
        if method == "avg_same_period_previous_years":
            baseline = self._predict_avg_same_period_previous_years(target_time, granularity)
        elif method == "avg_last_n_periods":
            baseline = self._predict_avg_last_n_periods(n_periods, granularity)
        else:  # default to average
            baseline = self.performance_data.average

        # Apply buffer
        predicted_quantity = baseline * (1 + buffer_percentage / 100)

        return Prediction(
            g_entity=self.performance_data.g_entity,
            period_label=target_time,
            predicted_quantity=predicted_quantity,
            baseline=baseline,
            buffer_percentage=buffer_percentage,
            method=method,
        )

    def _validate_future_target(self, target_time: str, granularity: str) -> None:
        """Validate that target_time is in the future based on granularity format"""
        today = date.today()

        try:
            if granularity == "daily" or granularity == "monthly":
                # Format: MM-DD-YYYY
                target_date = datetime.strptime(target_time, "%m-%d-%Y").date()
                if target_date < today:
                    raise ValueError("Target time must be in the future")
            elif granularity == "quarterly":
                # Format: YYYY-QN (e.g., "2026-Q2")
                year = int(target_time[:4])
                quarter = int(target_time[-1])
                current_quarter = (today.month - 1) // 3 + 1
                if year < today.year or (year == today.year and quarter <= current_quarter):
                    raise ValueError("Target time must be in the future")
            elif granularity == "yearly":
                # Format: YYYY (e.g., "2027")
                year = int(target_time)
                if year <= today.year:
                    raise ValueError("Target time must be in the future")
        except ValueError as e:
            if "Target time must be in the future" in str(e):
                raise
            # If parsing fails, skip validation (let downstream handle it)
            pass

    def _predict_avg_same_period_previous_years(self, target_time: str, granularity: str) -> float:
        """Predict based on average of the same period in previous years

        For example: predict March 2026 based on average of March 2023, 2024, 2025

        Returns:
            Predicted quantity based on historical same-period average
        """
        # Prematic check for valid inputs
        if target_time is None or len(self.performance_data.periods) == 0:
            return self.performance_data.average

        if granularity == "yearly":
            # For yearly, average the last n years
            recent = self.performance_data.periods
            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )

        elif granularity == "monthly":
            # for monthly, average the target month from previous n years
            recent = self.performance_data.periods
            target_month = target_time[:2]  # Extract month from MM-YYYY format
            matching_months = [float(p.quantity) for p in recent if p.label[:2] == target_month]
            return (
                sum(matching_months) / len(matching_months)
                if matching_months
                else self.performance_data.average
            )

        elif granularity == "quarterly":
            # for quarterly, average the target quarter from previous n years
            recent = self.performance_data.periods
            target_month = target_time[:2]  # Extract month from MM-YYYY format
            target_quarter = int((int(target_month) - 1) / 3) + 1  # Convert month to quarter
            matching_quarters = [
                float(p.quantity)
                for p in recent
                if int((int(p.label[:2]) - 1) / 3) + 1 == target_quarter
            ]
            return (
                sum(matching_quarters) / len(matching_quarters)
                if matching_quarters
                else self.performance_data.average
            )
        else:  # granularity == "daily"
            # for daily, average the target day from previous n years
            recent = self.performance_data.periods
            target_day = target_time[:5]  # Extract day from MM-DD-YYYY format
            matching_days = [float(p.quantity) for p in recent if p.label[:5] == target_day]
            return (
                sum(matching_days) / len(matching_days)
                if matching_days
                else self.performance_data.average
            )

    def _predict_avg_last_n_periods(
        self, n_periods: int = 11, granularity: str = "monthly"
    ) -> float:
        """Predict based on average of the last n periods

        For example: predict March 2026 based on average of last 11 months

        Args:
            n_periods: Number of recent periods to average
            granularity: Time granularity of the data (e.g., "monthly", "quarterly")

        Returns:
            Predicted quantity based on recent n-period average
        """
        # Prematic check for valid inputs
        if (
            len(self.performance_data.periods) == 0
            or n_periods <= 0
            or granularity not in ["yearly", "quarterly", "monthly", "daily"]
        ):
            return 0.0

        if granularity == "yearly":
            recent = self.performance_data.periods[-n_periods:]
            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )
        elif granularity == "monthly":
            recent = self.performance_data.periods[-n_periods:]
            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )
        elif granularity == "quarterly":
            recent = self.performance_data.periods[-n_periods:]
            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )
        else:  # daily
            recent = self.performance_data.periods[-n_periods:]
            return (
                sum(p.quantity for p in recent) / len(recent)
                if recent
                else self.performance_data.average
            )

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
