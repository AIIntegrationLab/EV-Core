from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import re


def tool_time(city: str) -> str:
    city_l = (city or "").strip().lower()
    tz_map = {
        "glasgow": "Europe/London",
        "london": "Europe/London",
        "edinburgh": "Europe/London",
        "manchester": "Europe/London",
    }
    tz = tz_map.get(city_l, "Europe/London")
    now = datetime.now(ZoneInfo(tz))
    return now.strftime("%H:%M")

def tool_date(city: str = "glasgow") -> str:
    """
    Returns today's date for the given city (UK cities map to Europe/London).
    Output format: YYYY-MM-DD
    """
    city_l = (city or "").strip().lower()
    tz_map = {
        "glasgow": "Europe/London",
        "london": "Europe/London",
        "edinburgh": "Europe/London",
        "manchester": "Europe/London",
    }
    tz = tz_map.get(city_l, "Europe/London")
    now = datetime.now(ZoneInfo(tz))
    return now.strftime("%Y-%m-%d")

def tool_timer(seconds: int) -> str:
    """
    Deterministic placeholder timer tool.
    For now it only returns a normalised duration string (no actual alarm scheduling).
    """
    if seconds < 1:
        seconds = 1
    if seconds < 60:
        return f"{seconds} seconds"
    mins = seconds // 60
    if mins < 60:
        return f"{mins} minutes"
    hrs = mins // 60
    return f"{hrs} hours"

_ALLOWED_CALC = re.compile(r"^[0-9\.\+\-\*\/\(\)\s]+$")

def tool_calc(expr: str) -> str:
    """
    Safe basic maths calculator:
    Allowed: digits, + - * / ( ) . and whitespace.
    Returns a string result (trimmed).
    """
    s = (expr or "").strip()
    if not s or not _ALLOWED_CALC.match(s):
        raise ValueError("Only basic maths is supported.")

    # Evaluate in a restricted environment
    result = eval(s, {"__builtins__": {}}, {})
    # Normalise output (avoid long floats)
    if isinstance(result, float):
        return f"{result:.10g}"
    return str(result)

