"""Utility functions."""
from datetime import date, timedelta
from typing import Optional


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def days_ago(days: int) -> date:
    """Get date N days ago."""
    return date.today() - timedelta(days=days)

