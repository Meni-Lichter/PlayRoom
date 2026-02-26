"""Date utility functions for period key generation and next period labeling"""

import calendar
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


def get_period_key(dt: date, granularity: str) -> str:
    """Generate period key based on granularity using MM-DD-YYYY format from config
    input:
        - dt: date object
        - granularity: "daily", "monthly", "quarterly", "yearly"
    output:
        - String representing the period key in MM-DD-YYYY compatible format
    """
    if granularity == "daily":
        return dt.strftime("%m-%d-%Y")  # MM-DD-YYYY
    elif granularity == "monthly":
        return f"{dt.month:02d}-{dt.year}"  # MM-YYYY
    elif granularity == "quarterly":
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{quarter}"
    else:  # yearly
        return str(dt.year)


def get_next_period_label(granularity: str) -> str:
    """Generate the next period label based on granularity

    Returns labels in MM-DD-YYYY compatible format from config
    """
    now = datetime.now()

    if granularity == "yearly":
        return str(now.year + 1)
    elif granularity == "quarterly":
        current_quarter = (now.month - 1) // 3 + 1
        next_quarter = current_quarter + 1
        next_year = now.year
        if next_quarter > 4:
            next_quarter = 1
            next_year += 1
        return f"{next_year}-Q{next_quarter}"
    elif granularity == "monthly":
        next_month = now.month + 1
        next_year = now.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        # Return MM-YYYY format
        return f"{next_month:02d}-{next_year}"  # "03-2025"
    elif granularity == "daily":
        next_day = now + timedelta(days=1)
        # Format: MM-DD-YYYY
        return next_day.strftime("%m-%d-%Y")  # "02-24-2025"
    else:
        return str(now.year + 1)
