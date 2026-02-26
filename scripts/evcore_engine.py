from __future__ import annotations

from typing import Dict, Any, Callable, Tuple

from evcore_router import route
from evcore_validate import normalise, fallback, coerce_intent
from evcore_memory import remember_fact
from evcore_facts import extract_fact
from evcore_clarify import (
    get_pending,
    try_resolve,
    set_pending,
)

# -----------------------------
# Deterministic clarification rules
# -----------------------------

_LIGHT_TARGETS = (
    "kitchen", "living room", "lounge", "bedroom", "bathroom",
    "hall", "hallway", "office",
)

_VAGUE_PHRASES = (
    "do it", "do that", "do this",
    "turn it on", "turn it off",
    "switch it on", "switch it off",
    "open it", "close it",
    "start it", "stop it",
    "that one", "the thing", "this thing", "the other one",
    "turn the thing on", "turn the thing off",
)

_SPECIFIC_TARGET_HINTS = (
    # tools / concepts
    "light", "lights",
    "timer", "alarm",
    "date", "time",
    "calc", "calculate",
    # common timer/calc words/symbols
    "minute", "minutes", "second", "seconds", "hour", "hours",
    "+", "-", "*", "/", "(", ")",
)


def _pre_clarify(user_text: str) -> Dict[str, Any] | None:
    """
    Create a clarification (set_pending) deterministically.
    Returns a raw decision dict or None.
    """
    t = (user_text or "").strip().lower()
    if not t:
        return None

    # Light clarification: user asks to turn lights on/off but doesn't say which room/light.
    wants_light = (
        ("turn on" in t or "turn off" in t or "switch on" in t or "switch off" in t)
        and ("light" in t or "lights" in t)
    )
    has_light_target = any(x in t for x in _LIGHT_TARGETS)

    if wants_light and not has_light_target:
        return set_pending(
            "light_target",
            "Which light do you mean (kitchen, living room, bedroom, bathroom, hallway, office)?",
        )

    # Vague command clarification
    looks_vague = any(p in t for p in _VAGUE_PHRASES)
    has_specific_target = any(h in t for h in _SPECIFIC_TARGET_HINTS)

    if looks_vague and not has_specific_target:
        return set_pending(
            "vague_command",
            "Say what now — what exactly d’you want me to do?",
        )

    return None


def handle_text(
    user_text: str,
    decide_fn: Callable[[str], Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    """
    Single EV Core pipeline.
    Returns: (decision, source)
    source in: "clarify", "tool", "llm", "fallback"
    """
    user_text = (user_text or "").strip()
    if not user_text:
        return normalise(fallback(user_text)), "fallback"

    # 1) Clarify resolution
    pending = get_pending()
    if pending is not None:
        resolved = try_resolve(user_text)

        # If try_resolve() cleared the pending state and returned None,
        # we must continue the pipeline (re-run tools/LLM) instead of repeating the prompt.
        if resolved is None:
            if get_pending() is None:
                # pending cleared -> fall through to normal pipeline
                pass
            else:
                d_raw = coerce_intent(user_text, pending)
                return normalise(d_raw), "clarify"
        else:
            d_raw = coerce_intent(user_text, resolved)
            return normalise(d_raw), "clarify"

    # 2) Fact capture (deterministic) → store
    fact = extract_fact(user_text)
    if fact:
        remember_fact(fact["key"], fact["value"])

    # 3) Deterministic clarification creation (only when nothing is pending)
    d_clarify = _pre_clarify(user_text)
    if d_clarify is not None:
        d_clarify = coerce_intent(user_text, d_clarify)
        return normalise(d_clarify), "clarify"

    # 4) Tool routing
    routed = route(user_text)
    if routed is not None:
        src = "clarify" if get_pending() is not None and routed.get("intent") == "tool_clarify" else "tool"
        routed = coerce_intent(user_text, routed)
        return normalise(routed), src

    # 5) LLM fallback
    try:
        d_raw = decide_fn(user_text)
        d_raw = coerce_intent(user_text, d_raw)
        return normalise(d_raw), "llm"
    except Exception:
        d_raw = fallback(user_text)
        d_raw = coerce_intent(user_text, d_raw)
        return normalise(d_raw), "fallback"
