from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import requests

from evcore_engine import handle_text
from evcore_contract import SYSTEM
from evcore_parse import extract_json
from evcore_memory import get_memory_context, clear_memory
from evcore_clarify import clear_pending

# ------------------------------
# Logging Setup
# ------------------------------
RUN_ID = os.environ.get("EVCORE_RUN_ID")
if not RUN_ID:
    _ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    _suid = str(uuid.uuid4())[:8]
    RUN_ID = f"{_ts}-{_suid}"

LOG_DIR = Path.home() / "evcore" / "logs" / "runs" / RUN_ID
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "evcore_loop.log"

def _log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# ------------------------------
# Configuration
# ------------------------------
LLM_URL = "http://127.0.0.1:8088/v1/chat/completions"

# Controlled chat history (small + deterministic)
HISTORY_MAX_TURNS = 6  # user+assistant pairs (12 messages max)
history: List[Dict[str, str]] = []

# Mode + temperature
mode = "auto"  # "precise" | "creative" | "auto"
TEMP_PRECISE = 0.0
TEMP_CREATIVE = 0.7


# ------------------------------
# DEBUG
# ------------------------------
DEBUG = True  # set False to hide decision tracing


def _short(s: str, n: int = 90) -> str:
    s = (s or "").replace("\n", "\\n")
    return s if len(s) <= n else s[: n - 1] + "…"


def debug_print_decision(user_text: str, d: dict, src: str) -> None:
    intent = d.get("intent", "?")
    reply = d.get("reply", "")
    should_speak = d.get("should_speak", None)
    should_listen = d.get("should_listen", None)
    interruptible = d.get("interruptible", None)
    set_mode = d.get("set_mode", None)

    actions = d.get("actions", [])
    action_lines = []
    if isinstance(actions, list):
        for i, a in enumerate(actions[:5]):  # cap to avoid spam
            if isinstance(a, dict):
                action_lines.append(
                    f"  - [{i}] type={a.get('type','?')} value={a.get('value','')}"
                )
            else:
                action_lines.append(f"  - [{i}] {repr(a)}")
    if not action_lines:
        action_lines = ["  - (none)"]

    # Console output (unchanged)
    print("\n[EV DEBUG]")

    # Log output (cleaner: mirror the same visible lines)
    _log("")          # mirrors the leading blank line from print("\n...")
    _log("[EV DEBUG]")

    l_user = f"  user:   {_short(user_text, 120)}"
    print(l_user)
    _log(l_user)

    l_route = f"  route:  {src}"
    print(l_route)
    _log(l_route)

    l_intent = f"  intent: {intent}"
    print(l_intent)
    _log(l_intent)

    l_flags = (
        f"  flags:  speak={should_speak} "
        f"listen={should_listen} "
        f"interruptible={interruptible} "
        f"set_mode={set_mode}"
    )
    print(l_flags)
    _log(l_flags)

    l_reply = f"  reply:  {_short(reply, 180)}"
    print(l_reply)
    _log(l_reply)

    print("  actions:")
    _log("  actions:")

    l_count = f"  action_count: {len(actions) if isinstance(actions, list) else 'n/a'}"
    print(l_count)
    _log(l_count)

    for line in action_lines:
        print(line)
        _log(line)

    print("[/EV DEBUG]\n")
    _log("[/EV DEBUG]")
    _log("")          # mirrors the trailing blank line from print("...\\n")


def _is_creative_prompt(t: str) -> bool:
    s = (t or "").lower()
    return any(k in s for k in (
        "joke", "funny", "story", "poem", "rap", "rhyme",
        "imagine", "creative", "write me", "make up",
    ))


def choose_temperature(user_text: str) -> float:
    if mode == "precise":
        return TEMP_PRECISE
    if mode == "creative":
        return TEMP_CREATIVE
    return TEMP_CREATIVE if _is_creative_prompt(user_text) else TEMP_PRECISE


def build_messages(user_text: str) -> List[Dict[str, str]]:
    mem = get_memory_context()

    sys_prompt = SYSTEM.strip()
    if mem:
        sys_prompt += (
            "\n\nMemory (facts learned from the user; use ONLY these if relevant):\n"
            + mem.strip()
        )

    msgs: List[Dict[str, str]] = [{"role": "system", "content": sys_prompt}]
    msgs.extend(history)
    msgs.append({"role": "user", "content": user_text})
    return msgs


def remember_turn(user_text: str, reply_text: str) -> None:
    global history
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply_text})

    max_entries = HISTORY_MAX_TURNS * 2
    if len(history) > max_entries:
        history = history[-max_entries:]


def decide(user_text: str) -> Dict[str, Any]:
    """
    LLM decision function (engine injects this).
    Returns a dict (raw decision). Engine will normalise + coerce.
    """
    payload = {
        "model": "local",
        "messages": build_messages(user_text),
        "temperature": choose_temperature(user_text),
    }

    r = requests.post(LLM_URL, json=payload, timeout=60)
    r.raise_for_status()

    text = r.json()["choices"][0]["message"]["content"]

    # Try to parse JSON decision; if plain text, wrap safely.
    try:
        d_raw = extract_json(text)
    except Exception:
        d_raw = None

    if not isinstance(d_raw, dict):
        # Let normalise() + your one-sentence/joke-preserve layer handle formatting later.
        intent_guess = "command" if _is_creative_prompt(user_text) else "unknown"
        d_raw = {
            "intent": intent_guess,
            "reply": (text or "").strip(),
            "should_speak": True,
            "should_listen": True,
            "interruptible": True,
            "actions": [{"type": "none", "value": ""}],
        }

    return d_raw


def speak(text: str) -> None:
    msg = f"EV> {text}"
    print(msg)
    _log(msg)


def _is_exit(t: str) -> bool:
    s = (t or "").strip().lower()
    return s in ("bye", "bye!", "bye mate", "bye4") or s.startswith(("exit", "quit", "bye"))


if __name__ == "__main__":
    try:
        while True:
            user_text = input("\nYou> ").strip()
            if not user_text:
                continue
            
            _log(f"YOU> {user_text}")

            if _is_exit(user_text):
                speak("Bye.")
                _log("Exit: user requested exit.")
                break

            # Local commands (loop-only)
            if user_text.lower().startswith("/mode "):
                new_mode = user_text.split(" ", 1)[1].strip().lower()
                if new_mode in ("precise", "creative", "auto"):
                    mode = new_mode
                    speak(f"Mode set to {mode}.")
                else:
                    speak("Valid modes: precise, creative, auto.")
                continue

            if user_text.lower() == "/reset":
                history.clear()
                clear_memory()
                clear_pending()
                speak("Memory cleared.")
                continue

            if user_text.lower() == "/status":
                speak(f"Mode={mode}, memory_turns={len(history)//2}.")
                continue

            # One pipeline call
            d, src = handle_text(user_text, decide)

            if DEBUG:
                debug_print_decision(user_text, d, src)

            # Speak/print
            reply = d.get("reply", "") or ""
            if d.get("should_speak", True):
                speak(reply)

            # One (and only one) history write path
            remember_turn(user_text, reply)

    except KeyboardInterrupt:
        msg = "\nEV> Bye."
        print(msg)
        _log(msg)
        _log("Exit: keyboard interrupt.")

