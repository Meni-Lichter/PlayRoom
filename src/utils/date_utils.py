"""Date utility functions for period key generation and next period labeling"""

import calendar
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


def get_period_key(dt: date, granularity: str) -> str:
    """Generate period key based on granularity
    input:
        - dt: date object
        - granularity: "daily", "weekly", "monthly", "quarterly", "yearly"
    output:
        - String representing the period key
    """
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    elif granularity == "weekly":
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    elif granularity == "monthly":
        return dt.strftime("%Y-%m")
    elif granularity == "quarterly":
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"
    else:  # yearly
        return str(dt.year)


def get_next_period_label(granularity: str) -> str:
    """Generate label for next period"""
    now = datetime.now()

    if granularity == "monthly":
        next_month = now + relativedelta(months=1)
        return next_month.strftime("%Y-%m")
    elif granularity == "quarterly":
        next_quarter = ((now.month - 1) // 3 + 1) % 4 + 1
        year = now.year if next_quarter > 1 else now.year + 1
        return f"{year}-Q{next_quarter}"
    elif granularity == "yearly":
        return str(now.year + 1)
    elif granularity == "weekly":
        next_week = now + relativedelta(weeks=1)
        year, week, _ = next_week.isocalendar()
        return f"{year}-W{week:02d}"
    else:
        next_day = now + relativedelta(days=1)
        return next_day.strftime("%Y-%m-%d")
