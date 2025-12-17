"""
Formatting utilities for E-Com67 platform
"""

from datetime import datetime
from typing import Union


def format_currency(amount: Union[int, float], currency: str = "USD") -> str:
    """Format currency amount for display"""
    if currency == "USD":
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def format_timestamp(timestamp: Union[int, float, datetime]) -> str:
    """Format timestamp for consistent display"""
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = timestamp
    
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")