from __future__ import annotations

import re
from typing import Any, Dict, List

INTENTS_ALLOWED = {
    "greeting", "question", "command", "unknown",
    "tool_time", "tool_date", "tool_timer", "tool_calc",
    "tool_clarify", "tool_action", "tool_memory",
}

ACTIONS_ALLOWED = {"none", "vector_anim", "vector_move", "set_mode"}


# ------------------------------
# Intent confidence coercion (regex based)
# ------------------------------
_RE_TIMER = re.compile(r"\b(timer|set a timer)\b", re.IGNORECASE)
_RE_TIME  = re.compile(r"\b(what(?:'s| is)?\s+the\s+time|time\s+in)\b", re.IGNORECASE)
_RE_DATE  = re.compile(r"\b(what(?:'s| is)?\s+the\s+date|today'?s?\s+date|date\s+in)\b", re.IGNORECASE)
_RE_CALC  = re.compile(r"\b(calc|calculate|what\s+is)\b.*[\d\)\(][\d\+\-\*/\.\s\)\(]*", re.IGNORECASE)

# ------------------------------
# Internal state (deterministic rotation for unknown replies)
# ------------------------------
_UNKNOWN_ROTATE = 0


def _fallback_reply(user_text: str = "") -> str:
    """
    Deterministic, slightly cheeky fallback line.
    Picks a tone based on the user's text (question vs command etc),
    and varies wording using a stable hash (no randomness needed).
    """
    t = (user_text or "").strip()
    tl = t.lower()

    # stable variant (0..2) based on input
    v = (sum(ord(c) for c in tl) % 3) if tl else 0

    is_question = tl.endswith("?") or tl.startswith(("what", "why", "how", "when", "where", "who", "which"))
    is_command = any(x in tl for x in ("turn on", "turn off", "switch on", "switch off", "set ", "start ", "stop ", "open ", "close "))

    if is_command:
        opts = [
            "Alright — which one, exactly?",
            "Be specific — what do you want me to do?",
            "Okay… but you’ll need to tell me what, mate.",
        ]
        return opts[v]

    if is_question:
        opts = [
            "Say what now?",
            "What d’you mean exactly?",
            "You’ll need to rephrase that — what are you asking?",
        ]
        return opts[v]

    # general unknown
    opts = [
        "Say that again — what do you want?",
        "What now?",
        "Hold on — what are we doing here?",
    ]
    return opts[v]


def fallback(user_text: str = "") -> Dict[str, Any]:
    """
    Deterministic fallback that varies slightly based on what the user typed.
    Keeps EV from sounding robotic when the LLM/JSON fails or output is unusable.
    """
    t = (user_text or "").strip()
    tl = t.lower()

    # Very short / single-word inputs
    if len(t.split()) <= 2 and t:
        return {
            "intent": "unknown",
            "reply": f"Say that again — what d’you mean by “{t}”?",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # Looks like a question
    if "?" in t or tl.startswith(("what", "why", "how", "where", "when", "who")):
        return {
            "intent": "unknown",
            "reply": "What d’you mean exactly?",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # Looks like a command
    if any(x in tl for x in ("turn on", "turn off", "set ", "start ", "stop ", "open ", "close ", "play ")):
        return {
            "intent": "unknown",
            "reply": "Okay… but you’ll need to tell me what, mate.",
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    # Generic
    return {
        "intent": "unknown",
        "reply": "Say that again — what do you want?",
        "should_speak": True,
        "should_listen": True,
        "interruptible": True,
        "actions": [{"type": "none", "value": ""}],
    }


def _to_bool(v: Any, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off"):
            return False
    if isinstance(v, int):
        return bool(v)
    return default


def _one_sentence(text: str) -> str:
    t = (text or "").strip().replace("\n", " ")
    if not t:
        return ""

    # Normalise whitespace
    t = " ".join(t.split())

    # Special-case: keep classic 2-part joke structure as ONE reply:
    # "Why ...? Because ..."
    low = t.lower()
    why_i = low.find("why ")
    because_i = low.find(" because ")
    q_i = t.find("?")

    if why_i != -1 and q_i != -1 and because_i != -1 and because_i > q_i:
        out = t

        # Trim anything AFTER the first sentence terminator that occurs AFTER "because"
        after_because = out[because_i + 1:]
        positions = [after_because.find(p) for p in (".", "!", "?")]
        positions = [p for p in positions if p != -1]
        if positions:
            cut_at = because_i + 1 + min(positions) + 1
            out = out[:cut_at].strip()

        if len(out) > 220:
            out = out[:220].rstrip()
        return out

    # Default behaviour: take the first sentence terminator we see (earliest in text)
    positions = [(t.find(p), p) for p in (".", "!", "?")]
    positions = [pos for pos in positions if pos[0] != -1]
    if positions:
        cut = min(positions, key=lambda x: x[0])[0] + 1
        t = t[:cut].strip()

    if len(t) > 220:
        t = t[:220].rstrip()

    return t


_UNKNOWN_ROTATE = 0

def _sarcasm_unknown(reply: str) -> str:
    """
    Mild personality for unknown replies.
    Deterministic rotation (better for debugging than randomness).
    """
    global _UNKNOWN_ROTATE

    r = (reply or "").strip()
    if not r:
        return r

    rl = r.lower()

    # If it's already a good clarify-style line, keep it.
    if any(x in rl for x in ("which", "what do you mean", "do you mean")):
        return r

    robotic_markers = (
        "didn't understand",
        "did not understand",
        "not sure what you mean",
        "i'm not sure what you mean",
        "i do not know what you mean",
        "i didn't quite catch that",
        "could you please repeat",
        "please speak clearly",
        "speak clearly",
        "say that again",
        "can you repeat",
    )

    if any(m in rl for m in robotic_markers):
        options = (
            "Say what now?",
            "Go on — what d’you mean?",
            "Right… what exactly d’you want me to do?",
            "Try that again, mate.",
        )
        line = options[_UNKNOWN_ROTATE % len(options)]
        _UNKNOWN_ROTATE += 1
        return line

    return r


def coerce_intent(user_text: str, d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Confidence correction layer.
    If the LLM mislabels an obvious tool request, fix it.
    """
    t = (user_text or "").strip()
    if not t:
        return d

    tl = t.lower()

    # Only override weak intents
    if d.get("intent") in ("unknown", "question", "command"):
        if _RE_TIMER.search(tl):
            d["intent"] = "tool_timer"

        elif _RE_TIME.search(tl):
            d["intent"] = "tool_time"

        elif _RE_DATE.search(tl):
            d["intent"] = "tool_date"

        elif _RE_CALC.search(tl):
            # --- calc coercion (only if expression is real maths) ---
            # Pull the part after the keyword
            parts = re.split(r"(?:calc|calculate|what\s+is)\b", tl, maxsplit=1)
            expr = parts[1].strip() if len(parts) == 2 else ""

            # If any letters are present (kitchen/apples/etc), don't coerce
            if any(ch.isalpha() for ch in expr):
                return d

            # Must contain at least one digit
            if not any(ch.isdigit() for ch in expr):
                return d

            # Only maths characters allowed
            if re.fullmatch(r"[0-9\.\s\+\-\*\/\(\)%]+", expr):
                d["intent"] = "tool_calc"

    return d


def _normalise_actions(v: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if isinstance(v, list):
        for item in v:
            if not isinstance(item, dict):
                continue
            t = str(item.get("type", "none")).strip()
            val = str(item.get("value", "")).strip()
            if t not in ACTIONS_ALLOWED:
                t, val = "none", ""
            out.append({"type": t, "value": val})

    if not out:
        out = [{"type": "none", "value": ""}]
    return out


def _coerce_intent(raw_intent: Any) -> str:
    """
    Models sometimes output a pipe list like 'greeting|question|command|unknown'.
    We coerce it into a single allowed intent deterministically.
    """
    s = str(raw_intent if raw_intent is not None else "unknown").strip()

    # If it contains pipes, pick the first allowed token in order of appearance
    if "|" in s:
        for part in (p.strip() for p in s.split("|")):
            if part in INTENTS_ALLOWED:
                return part
        return "unknown"

    return s if s in INTENTS_ALLOWED else "unknown"


def normalise(d: Any) -> Dict[str, Any]:
    if not isinstance(d, dict):
        return fallback()

    intent = _coerce_intent(d.get("intent", "unknown"))

    raw_val = d.get("reply", "")
    raw_reply = "" if raw_val is None else str(raw_val)

    is_tool = str(d.get("intent", "")).startswith("tool_")
    intent_guess = str(d.get("intent", "")).strip()

    # Default behaviour:
    # - Tool replies are kept intact.
    # - LLM replies are trimmed to one sentence.
    if is_tool:
        reply = raw_reply.strip()
    else:
        reply = _one_sentence(raw_reply)

    # ------------------------------
    # Joke-safe override
    # ------------------------------
    rl_raw = raw_reply.lower()
    looks_like_joke = (
        "joke" in rl_raw
        or rl_raw.startswith("why ")
        or " knock knock" in rl_raw
        or "did the" in rl_raw
    )

    # If it's a normal command (not tool_) and looks like a joke,
    # keep the full cleaned reply instead of chopping to one sentence.
    if (not is_tool) and intent_guess == "command" and looks_like_joke:
        reply = " ".join(raw_reply.strip().split())
        if len(reply) > 220:
            reply = reply[:220].rstrip()

    if not reply:
        reply = fallback()["reply"]

    # Subtle sarcasm layer (unknown only)
    if intent == "unknown":
        reply = _sarcasm_unknown(reply)

    should_speak = _to_bool(d.get("should_speak", True), True)

    # Continuous loop: model cannot stop listening
    should_listen = True

    interruptible = _to_bool(d.get("interruptible", True), True)
    actions = _normalise_actions(d.get("actions", []))

    # Deterministic override: for NON-tool commands, smile on obvious joke style replies.
    # (Do not override tool actions like timers.)
    if intent == "command" and not intent.startswith("tool_"):
        rl = reply.lower()
        if "joke" in rl or rl.startswith("why "):
            actions = [{"type": "vector_anim", "value": "smile"}]

    return {
        "intent": intent,
        "reply": reply,
        "should_speak": should_speak,
        "should_listen": should_listen,
        "interruptible": interruptible,
        "actions": actions,
    }
