from datetime import datetime, timedelta

def minutes_between(start, end):
    return int((end - start).total_seconds() // 60)

def add_minutes(start, minutes):
    return start + timedelta(minutes=minutes)

def format_dt(value):
    return value.strftime("%Y-%m-%d %H:%M")

def format_minutes(minutes):
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    if hours > 0:
        return f"{hours}h"
    return f"{mins}m"

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end
