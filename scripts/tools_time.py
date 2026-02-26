from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

def time_in_glasgow() -> str:
    tz = ZoneInfo("Europe/London")
    now = datetime.now(tz)
    # Example: 19:42 (GMT) / 19:42 (BST)
    abbr = now.tzname() or "local"
    return now.strftime(f"%H:%M ({abbr})")

def maybe_handle_time_query(user_text: str) -> str | None:
    t = (user_text or "").strip().lower()

    # Very simple routing for now (we can expand later)
    triggers = (
        "time in glasgow",
        "time in glesga",
        "what time is it in glasgow",
        "what's the time in glasgow",
        "whats the time in glasgow",
    )
    if any(x in t for x in triggers):
        return f"The time in Glasgow is {time_in_glasgow()}."

    return None
