from __future__ import annotations

import re
from typing import Any, Dict, Optional

from evcore_tools import tool_time, tool_date, tool_timer, tool_calc
from evcore_memory import get_facts
from evcore_clarify import set_pending


# ------------------------------
# Patterns
# ------------------------------

# Memory question routing (deterministic)
_NAME_Q_RE = re.compile(r"\b(what\s+is\s+my\s+name|who\s+am\s+i)\b", re.IGNORECASE)
_KNOW_Q_RE = re.compile(r"\b(what\s+do\s+you\s+know\s+about\s+me)\b", re.IGNORECASE)

# Time / date routing
_TIME_RE = re.compile(
    r"\b(time)\b|"
    r"\bwhat\s+time\s+is\s+it\b|"
    r"\bwhat\s*'?s\s+the\s+time\b|"
    r"\bwhats\s+the\s+time\b",
    re.IGNORECASE,
)

_DATE_RE = re.compile(
    r"\b(date)\b|"
    r"\bwhat\s*'?s\s+the\s+date\b|"
    r"\bwhats\s+the\s+date\b|"
    r"\bwhat\s+date\s+is\s+it\b|"
    r"\btoday'?s\s+date\b",
    re.IGNORECASE,
)

_CITY_RE = re.compile(r"\b(glasgow|london|edinburgh|manchester)\b", re.IGNORECASE)

UK_ONLY_REPLY = (
    "I can only give the time/date for UK cities right now (Glasgow, London, Edinburgh, Manchester)."
)

# Timer examples: "timer 5 minutes", "set a timer for 10 min", "timer 30s"
_TIMER_RE = re.compile(
    r"\b(timer)\b.*?\b(\d+)\s*(seconds?|secs?|s|minutes?|mins?|min|m|hours?|hrs?|h)\b",
    re.IGNORECASE,
)

# Calc examples: "calc 2+2", "calculate (10/4)*3", "what is 7*8"
_CALC_RE = re.compile(
    r"^(?:calc|calculate)\s+(.+)$|^what\s+is\s+(.+)$",
    re.IGNORECASE,
)

# Strict-ish: only allow maths characters, so we don't catch "what is my name?"
_MATH_CHARS_RE = re.compile(r"^[0-9\.\s\+\-\*\/\(\)%]+$")


def _city_or_default(text: str) -> str:
    m = _CITY_RE.search(text)
    return m.group(1).lower() if m else "glasgow"


def route(user_text: str) -> Optional[Dict[str, Any]]:
    t_raw = (user_text or "").strip()
    if not t_raw:
        return None

    # ---- Memory question routing ----
    tl = t_raw.lower()

    asks_name = ("what is my name" in tl) or ("what's my name" in tl) or ("whats my name" in tl)
    asks_about_me = "what do you know about me" in tl

    if asks_name or asks_about_me:
        facts = get_facts()
        name = facts.get("name")
        home = facts.get("home_city")

        if asks_name:
            if name:
                return {
                    "intent": "tool_memory",
                    "reply": f"Your name is {name}.",
                    "should_speak": True,
                    "should_listen": True,
                    "interruptible": True,
                    "actions": [{"type": "none", "value": ""}],
                }
            return {
                "intent": "tool_memory",
                "reply": "I don’t know your name yet.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        # asks_about_me
        bits = []
        if name:
            bits.append(f"your name is {name}")
        if home:
            bits.append(f"you live in {home}")

        if bits:
            joined = " and ".join(bits) if len(bits) == 2 else bits[0]
            return {
                "intent": "tool_memory",
                "reply": f"I know {joined}.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        return {
            "intent": "tool_memory",
            "reply": "I don’t know anything about you yet.",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # ------------------------------
    # Time tool
    # ------------------------------
    if _TIME_RE.search(t_raw):
        # If user explicitly says "in X" but X is not a supported UK city, block guessing.
        if re.search(r"\b(in)\b", t_raw, re.IGNORECASE) and not _CITY_RE.search(t_raw):
            return {
                "intent": "tool_time",
                "reply": UK_ONLY_REPLY,
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        city = _city_or_default(t_raw)
        hhmm = tool_time(city)
        return {
            "intent": "tool_time",
            "reply": f"The time in {city.title()} is {hhmm} (GMT).",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # ------------------------------
    # Date tool
    # ------------------------------
    if _DATE_RE.search(t_raw):
        if re.search(r"\b(in)\b", t_raw, re.IGNORECASE) and not _CITY_RE.search(t_raw):
            return {
                "intent": "tool_date",
                "reply": UK_ONLY_REPLY,
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        city = _city_or_default(t_raw)
        ymd = tool_date(city)
        return {
            "intent": "tool_date",
            "reply": f"Today’s date in {city.title()} is {ymd}.",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # ------------------------------
    # Timer tool
    # ------------------------------
    t = t_raw.strip().lower()
    if t in ("timer", "set a timer", "start a timer"):
        return set_pending("timer_duration", "How long should I set the timer for?")

    m_timer = _TIMER_RE.search(t_raw)
    if m_timer:
        n = int(m_timer.group(2))
        unit = m_timer.group(3).lower()

        seconds = n
        if unit.startswith(("min", "m")) and not unit.startswith("ms"):
            seconds = n * 60
        elif unit.startswith(("h", "hr")):
            seconds = n * 3600

        duration = tool_timer(seconds)
        return {
            "intent": "tool_timer",
            "reply": f"Timer set for {duration}.",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "set_mode", "value": f"timer:{seconds}"}],
        }

    # ------------------------------
    # ---- Light routing (deterministic stub) ----
    # ------------------------------
    if "light" in tl and ("turn on" in tl or "switch on" in tl):
        for room in (
            "kitchen",
            "living room",
            "bedroom",
            "bathroom",
            "hall",
            "hallway",
            "office",
        ):
            if room in tl:
                return {
                    "intent": "tool_action",
                    "reply": f"Turning on the {room} light.",
                    "should_speak": True,
                    "should_listen": True,
                    "interruptible": True,
                    "actions": [
                        {"type": "set_mode", "value": f"light_on:{room}"}
                    ],
                }

    if "light" in tl and ("turn off" in tl or "switch off" in tl):
        for room in (
            "kitchen",
            "living room",
            "bedroom",
            "bathroom",
            "hall",
            "hallway",
            "office",
        ):
            if room in tl:
                return {
                    "intent": "tool_action",
                    "reply": f"Turning off the {room} light.",
                    "should_speak": True,
                    "should_listen": True,
                    "interruptible": True,
                    "actions": [
                        {"type": "set_mode", "value": f"light_off:{room}"}
                    ],
                }

    # ---- Light routing (extra: allow missing word "light") ----
    rooms = ("kitchen", "living room", "bedroom", "bathroom", "hall", "hallway", "office")

    has_room = None
    for r in rooms:
        if r in tl:
            has_room = r
            break

    if has_room:
        # Turn ON patterns
        if ("turn on" in tl or "switch on" in tl) and "light" not in tl:
            return {
                "intent": "tool_action",
                "reply": f"Turning on the {has_room} light.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "set_mode", "value": f"light_on:{has_room}"}],
            }

        # Turn OFF patterns
        if ("turn off" in tl or "switch off" in tl) and "light" not in tl:
            return {
                "intent": "tool_action",
                "reply": f"Turning off the {has_room} light.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "set_mode", "value": f"light_off:{has_room}"}],
            }

        # Short forms: "kitchen on", "bedroom off"
        if tl.strip().endswith(" on") and "light" not in tl:
            return {
                "intent": "tool_action",
                "reply": f"Turning on the {has_room} light.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "set_mode", "value": f"light_on:{has_room}"}],
            }

        if tl.strip().endswith(" off") and "light" not in tl:
            return {
                "intent": "tool_action",
                "reply": f"Turning off the {has_room} light.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "set_mode", "value": f"light_off:{has_room}"}],
            }

    # ------------------------------
    # Calc with no expression → deterministic clarification
    # ------------------------------
    tl = t_raw.strip().lower()
    if tl in ("calc", "calculate", "calculator"):
        return set_pending("calc_expr", "What should I calculate? (e.g., 10/4*3)")

    # ------------------------------
    # Reject non-maths "calculate ..." (letters present)
    # ------------------------------
    if tl.startswith(("calc ", "calculate ")):
        expr = t_raw.split(" ", 1)[1].strip() if " " in t_raw else ""
        if any(ch.isalpha() for ch in expr):
            return {
                "intent": "tool_calc",
                "reply": "That doesn’t look like maths — give me numbers only (e.g., 10/4*3).",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

    # ------------------------------
    # Calc tool (guarded so it doesn't catch normal questions)
    # ------------------------------
    m_calc = _CALC_RE.match(t_raw)
    if m_calc:
        expr = (m_calc.group(1) or m_calc.group(2) or "").strip()

        # NEW: if there are letters, it's not a pure maths expression
        if any(ch.isalpha() for ch in expr):
            return None

        if expr and _MATH_CHARS_RE.match(expr):
            try:
                ans = tool_calc(expr)
                return {
                    "intent": "tool_calc",
                    "reply": f"{ans}.",
                    "should_speak": True,
                    "should_listen": True,
                    "interruptible": True,
                    "actions": [{"type": "none", "value": ""}],
                }
            except Exception:
                return {
                    "intent": "tool_calc",
                    "reply": "I can only do basic maths like 2+2 or (10/4)*3.",
                    "should_speak": True,
                    "should_listen": True,
                    "interruptible": True,
                    "actions": [{"type": "none", "value": ""}],
                }

    return None
