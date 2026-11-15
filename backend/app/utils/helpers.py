from datetime import datetime
from typing import Optional, Tuple

def classify_density(occupancy_pct: float) -> str:
    """
    Classifies traffic density according to project specification:
    0–30%   : Low
    31–60%  : Moderate
    61–80%  : High
    81–100% : Severe
    """
    if occupancy_pct <= 30.0:
        return "Low"
    elif occupancy_pct <= 60.0:
        return "Moderate"
    elif occupancy_pct <= 80.0:
        return "High"
    else:
        return "Severe"

def format_file_size(size_bytes: int) -> str:
    """Formats bytes into human readable MB/KB."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"

def parse_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parses optional ISO / YYYY-MM-DD date strings into datetime objects."""
    dt_start = None
    dt_end = None
    if start_date:
        try:
            dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
    if end_date:
        try:
            dt_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt_end = datetime.strptime(end_date, "%Y-%m-%d")
                # Include end of day
                dt_end = dt_end.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass
    return dt_start, dt_end

