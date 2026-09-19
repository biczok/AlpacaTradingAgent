"""
Market hours utilities for validating trading hours and checking if the market is open.
"""

import datetime
import pytz
from typing import List, Tuple, Dict, Any

# US stock market holidays (simplified - in production, use a proper holidays library)
US_MARKET_HOLIDAYS_2024 = [
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # Martin Luther King Jr. Day
    "2024-02-19",  # Presidents' Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving Day
    "2024-12-25",  # Christmas Day
]

US_MARKET_HOLIDAYS_2025 = [
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # Martin Luther King Jr. Day
    "2025-02-17",  # Presidents' Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving Day
    "2025-12-25",  # Christmas Day
]

US_MARKET_HOLIDAYS_2026 = [
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # Martin Luther King Jr. Day
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day observed
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving Day
    "2026-12-25",  # Christmas Day
]

US_MARKET_HOLIDAYS_2027 = [
    "2027-01-01",  # New Year's Day
    "2027-01-18",  # Martin Luther King Jr. Day
    "2027-02-15",  # Presidents' Day
    "2027-03-26",  # Good Friday
    "2027-05-31",  # Memorial Day
    "2027-06-18",  # Juneteenth observed
    "2027-07-05",  # Independence Day observed
    "2027-09-06",  # Labor Day
    "2027-11-25",  # Thanksgiving Day
    "2027-12-24",  # Christmas Day observed
]

# Market regular hours (EST/EDT)
MARKET_OPEN_HOUR = 9   # 9:30 AM (use 9 for conservative approach)
MARKET_CLOSE_HOUR = 16  # 4:00 PM


def _get_eastern_timezone():
    return pytz.timezone("US/Eastern")


def _current_eastern_time() -> datetime.datetime:
    return datetime.datetime.now(pytz.utc).astimezone(_get_eastern_timezone())


def _coerce_to_eastern(target_datetime: datetime.datetime = None) -> datetime.datetime:
    eastern = _get_eastern_timezone()
    if target_datetime is None:
        return _current_eastern_time()
    if target_datetime.tzinfo is None:
        # Naive datetimes passed into this module are treated as Eastern wall clock time.
        return eastern.localize(target_datetime)
    return target_datetime.astimezone(eastern)

def is_market_day(target_datetime: datetime.datetime = None) -> Tuple[bool, str]:
    """
    Check if the given datetime falls on a US stock market trading day (weekday and non-holiday).
    """
    target_datetime = _coerce_to_eastern(target_datetime)
    if target_datetime.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False, "Market is closed on weekends"

    date_str = target_datetime.strftime("%Y-%m-%d")
    all_holidays = (
        US_MARKET_HOLIDAYS_2024
        + US_MARKET_HOLIDAYS_2025
        + US_MARKET_HOLIDAYS_2026
        + US_MARKET_HOLIDAYS_2027
    )
    if date_str in all_holidays:
        return False, f"Market is closed for holiday on {date_str}"
    return True, "Valid trading day"


def validate_market_hours(hours_str: str) -> Tuple[bool, List[int], str]:
    """
    Validate market hours input string.
    
    Args:
        hours_str: String like "9, 10, 11, 13" representing hours
        
    Returns:
        Tuple of (is_valid, parsed_hours_list, error_message)
    """
    if not hours_str or not hours_str.strip():
        return False, [], "Please enter at least one trading hour"
    
    try:
        # Parse comma-separated hours
        hours_parts = [h.strip() for h in hours_str.split(',') if h.strip()]
        if not hours_parts:
            return False, [], "Please enter at least one trading hour"
        
        hours = []
        for hour_str in hours_parts:
            hour = int(hour_str)
            if hour < MARKET_OPEN_HOUR or hour > MARKET_CLOSE_HOUR:
                return False, [], f"Hour {hour} is outside market hours ({MARKET_OPEN_HOUR}AM-{MARKET_CLOSE_HOUR}PM EST/EDT)"
            hours.append(hour)
        
        # Remove duplicates and sort
        hours = sorted(list(set(hours)))
        return True, hours, ""
        
    except ValueError:
        return False, [], "Please enter valid hour numbers (e.g., 9,10,11,13)"


def is_market_open(target_datetime: datetime.datetime = None, include_premarket: bool = True) -> Tuple[bool, str]:
    """
    Check if the US stock market / pre-market analysis window is open at the given datetime.
    
    Args:
        target_datetime: Datetime to check (defaults to current time)
        include_premarket: Whether to include the 20-min pre-market analysis window (starts 9:10 AM EST)
        
    Returns:
        Tuple of (is_open, reason_if_closed)
    """
    target_datetime = _coerce_to_eastern(target_datetime)
    
    is_day, reason = is_market_day(target_datetime)
    if not is_day:
        return False, reason
    
    # 20 minutes before market open (9:10 AM EST) if pre-market enabled, else 9:30 AM
    start_min = 10 if include_premarket else 30
    market_open = target_datetime.replace(hour=9, minute=start_min, second=0, microsecond=0)
    market_close = target_datetime.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if target_datetime < market_open:
        return False, f"Market opens at 9:30 AM EST/EDT (Pre-market window starts at {market_open.strftime('%I:%M %p %Z')})"
    elif target_datetime > market_close:
        return False, f"Market closed at 4:00 PM EST/EDT (currently {target_datetime.strftime('%I:%M %p %Z')})"
    
    return True, "Market is active"


def scheduled_datetime_for_hour(target_hour: int, day: datetime.datetime) -> datetime.datetime:
    """Wall-clock time on `day` when `target_hour` should fire (US/Eastern)."""
    day = _coerce_to_eastern(day)
    target_minute = 10 if int(target_hour) == 9 else 0
    naive = datetime.datetime(day.year, day.month, day.day, int(target_hour), target_minute, 0)
    eastern = _get_eastern_timezone()
    try:
        return eastern.localize(naive, is_dst=None)
    except pytz.AmbiguousTimeError:
        return eastern.localize(naive, is_dst=True)
    except pytz.NonExistentTimeError:
        return eastern.localize(naive) + datetime.timedelta(hours=1)


def slot_fire_key(slot_dt: datetime.datetime, hour: int):
    slot_dt = _coerce_to_eastern(slot_dt)
    return (slot_dt.date().isoformat(), int(hour))


def get_next_market_datetime(target_hour: int, from_datetime: datetime.datetime = None) -> datetime.datetime:
    """
    Get the next market datetime for the specified hour.
    Hour 9 is scheduled at 9:10 AM EST (20 minutes before 9:30 AM market open).
    Hours 10-16 are scheduled at the top of the hour.
    
    Args:
        target_hour: Hour to target (e.g., 9 for 9:10 AM pre-market, 11 for 11:00 AM)
        from_datetime: Starting datetime (defaults to current time)
        
    Returns:
        Next datetime when market will be open at the target hour
    """
    from_datetime = _coerce_to_eastern(from_datetime)
    candidate_day = from_datetime
    target_dt = scheduled_datetime_for_hour(target_hour, candidate_day)

    # If the target time today has already passed, start with tomorrow
    if target_dt <= from_datetime:
        candidate_day = candidate_day + datetime.timedelta(days=1)
        target_dt = scheduled_datetime_for_hour(target_hour, candidate_day)
        
    # Keep advancing until we find a valid market day
    max_attempts = 10  # Prevent infinite loops
    attempts = 0
    
    while attempts < max_attempts:
        is_day, reason = is_market_day(target_dt)
        if is_day:
            return target_dt
        
        candidate_day = candidate_day + datetime.timedelta(days=1)
        target_dt = scheduled_datetime_for_hour(target_hour, candidate_day)
        attempts += 1
    
    # Fallback - return the target datetime even if we couldn't validate
    return target_dt


CATCH_UP_GRACE = datetime.timedelta(minutes=30)


def get_due_market_slot(
    hours: List[int],
    from_datetime: datetime.datetime = None,
    fired=None,
    catch_up_while_open: bool = True,
):
    """
    Return the most recent scheduled slot that should run now, or None.

    A slot is due when its Eastern wall-clock time has been reached on a
    trading day and either the analysis window is still open or we are
    within CATCH_UP_GRACE of the slot. Already-fired (date, hour) keys are skipped.
    """
    if not hours:
        return None

    now = _coerce_to_eastern(from_datetime)
    fired = fired or set()
    is_day, _ = is_market_day(now)
    if not is_day:
        return None

    is_open, _ = is_market_open(now)
    due = []
    for hour in sorted(hours):
        slot = scheduled_datetime_for_hour(hour, now)
        if slot_fire_key(slot, hour) in fired:
            continue
        if slot > now:
            continue
        if (catch_up_while_open and is_open) or (now - slot) <= CATCH_UP_GRACE:
            due.append((hour, slot))

    if not due:
        return None
    return due[-1]


def market_hour_schedule_action(
    hours: List[int],
    from_datetime: datetime.datetime = None,
    fired=None,
):
    """
    Decide whether to run a due slot or wait for the next one.

    Returns (action, hour, slot_datetime) where action is "run" or "wait".
    """
    if not hours:
        raise ValueError("No market hours configured")

    now = _coerce_to_eastern(from_datetime)
    due = get_due_market_slot(hours, now, fired)
    if due:
        return "run", due[0], due[1]

    upcoming = [(hour, get_next_market_datetime(hour, now)) for hour in hours]
    upcoming.sort(key=lambda item: item[1])
    hour, slot = upcoming[0]
    return "wait", hour, slot


def format_market_hours_info(hours: List[int]) -> Dict[str, Any]:
    """
    Format market hours information for display.
    
    Args:
        hours: List of hours (e.g., [9, 10, 11, 13])
        
    Returns:
        Dictionary with formatted information
    """
    if not hours:
        return {"error": "No hours provided"}
    
    # Format hours for display
    formatted_hours = []
    for hour in sorted(hours):
        if hour == 9:
            formatted_hours.append("9:10 AM (Pre-Market 20m before open)")
        elif hour == 12:
            formatted_hours.append("12:00 PM")
        elif hour < 12:
            formatted_hours.append(f"{hour}:00 AM")
        else:
            formatted_hours.append(f"{hour-12}:00 PM")
    
    hours_str = "; ".join(formatted_hours)
    
    # Calculate next execution times
    next_executions = []
    sorted_hours = sorted(hours)
    for idx, hour in enumerate(sorted_hours):
        next_dt = get_next_market_datetime(hour)
        next_executions.append({
            "hour": hour,
            "formatted_hour": formatted_hours[idx],
            "next_datetime": next_dt,
            "next_formatted": next_dt.strftime("%A, %B %d at %I:%M %p %Z")
        })
    
    return {
        "hours": hours,
        "formatted_hours": hours_str,
        "next_executions": next_executions,
        "market_timezone": "US/Eastern"
    }
