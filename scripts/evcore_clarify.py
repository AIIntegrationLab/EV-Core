from __future__ import annotations
from typing import Optional, Dict, Any

import re

from evcore_tools import tool_calc

# Pending clarification state (per run)
_pending_kind: Optional[str] = None
_pending_decision: Optional[Dict[str, Any]] = None

# Allowed targets for deterministic resolution
LIGHT_TARGETS = (
    "kitchen",
    "living room",
    "bedroom",
    "bathroom",
    "hall",
    "hallway",
    "office",
)


_TIMER_ONLY_RE = re.compile(
    r"^\s*(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\s*$",
    re.IGNORECASE
)

_MATH_CHARS_RE = re.compile(r"^[0-9\s\.\+\-\*\/\(\)]+$")


def get_pending() -> Optional[Dict[str, Any]]:
    """Returns the pending decision dict (what we should say to ask the user)."""
    return _pending_decision

def clear_pending() -> None:
    global _pending_kind, _pending_decision
    _pending_kind = None
    _pending_decision = None

def set_pending(kind: str, prompt: str) -> Dict[str, Any]:
    """
    Stores a pending clarification and returns the decision that asks the user.
    """
    global _pending_kind, _pending_decision

    _pending_kind = kind
    _pending_decision = {
        "intent": "tool_clarify",
        "reply": prompt,
        "should_speak": True,
        "should_listen": True,
        "interruptible": True,
        "actions": [{"type": "none", "value": ""}],
    }
    return _pending_decision

def _normalise_target(text: str) -> str:
    """Lower + trim + collapse spaces."""
    t = " ".join((text or "").strip().lower().split())
    return t

def try_resolve(user_text: str) -> Optional[Dict[str, Any]]:
    """
    If we have a pending clarification, try to resolve it using the user's new input.
    Returns a decision dict if resolved, else None.
    """
    global _pending_kind

    if not _pending_kind:
        return None

    t = (user_text or "").strip().lower()
    if not t:
        return None

    # Lights
    if _pending_kind == "light_target":
        if t in LIGHT_TARGETS:
            clear_pending()
            return {
                "intent": "tool_action",
                "reply": f"Turning on the {t} light.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "set_mode", "value": f"light_on:{t}"}],
            }

        # Invalid answer → guide user (keep pending active)
        return {
            "intent": "tool_clarify",
            "reply": "I didn't recognise that room. Please choose: kitchen, living room, bedroom, bathroom, hall, hallway, office.",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # Timer duration follow-up (after user said "timer" with no duration)
    if _pending_kind == "timer_duration":
        m = _TIMER_ONLY_RE.match(t)
        if not m:
            return {
                "intent": "tool_clarify",
                "reply": "Give me a duration like 10 minutes, 30 seconds, or 2 hours.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        n = int(m.group(1))
        unit = m.group(2).lower()

        seconds = n
        if unit.startswith(("min", "m")) and not unit.startswith("ms"):
            seconds = n * 60
        elif unit.startswith(("h", "hr")):
            seconds = n * 3600

        clear_pending()

        return {
            "intent": "tool_timer",
            "reply": f"Timer set for {n} {unit}.",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "set_mode", "value": f"timer:{seconds}"}],
        }

    # Calc expression follow-up (after user said "calc" with no expression)
    if _pending_kind == "calc_expr":
        expr = (user_text or "").strip()

        # Reject letters (keeps your "calculate kitchen + 5" deterministic)
        if any(ch.isalpha() for ch in expr):
            return {
                "intent": "tool_clarify",
                "reply": "That doesn’t look like maths — give me numbers only (e.g., 10/4*3).",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        # Validate characters
        if not expr or not _MATH_CHARS_RE.match(expr):
            return {
                "intent": "tool_clarify",
                "reply": "I can only do basic maths like 2+2 or (10/4)*3.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

        try:
            ans = tool_calc(expr)
            clear_pending()
            return {
                "intent": "tool_calc",
                "reply": f"{ans}.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }
        except Exception:
            # Keep pending active so they can try again
            return {
                "intent": "tool_clarify",
                "reply": "I can only do basic maths like 2+2 or (10/4)*3.",
                "should_speak": True,
                "should_listen": True,
                "interruptible": True,
                "actions": [{"type": "none", "value": ""}],
            }

    # Resolver for vague commands (e.g. "turn it on", "do it")
    if _pending_kind == "vague_command":
        # If the follow-up is now specific, clear pending and let the main loop re-process it
        looks_specific = any(k in t for k in ("timer", "time", "date", "calc", "calculate", "light", "lights"))
        if looks_specific:
            clear_pending()
            return None  # IMPORTANT: means "handled, now re-run normal pipeline"

        # Still vague → keep pending and ask again
        return {
            "intent": "tool_clarify",
            "reply": "Say what now — what exactly d’you want me to do?",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    return None
