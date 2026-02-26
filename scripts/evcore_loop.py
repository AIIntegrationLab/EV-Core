from __future__ import annotations

from typing import Dict, Any, List
import requests

from evcore_engine import handle_text
from evcore_contract import SYSTEM
from evcore_parse import extract_json
from evcore_memory import get_memory_context, clear_memory
from evcore_clarify import clear_pending

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

    print("\n[EV DEBUG]")
    print(f"  user:   {_short(user_text, 120)}")
    print(f"  route:  {src}")
    print(f"  intent: {intent}")
    print(f"  flags:  speak={should_speak} listen={should_listen} interruptible={interruptible} set_mode={set_mode}")
    print(f"  reply:  {_short(reply, 180)}")
    print("  actions:")
    print(f"  action_count: {len(actions) if isinstance(actions, list) else 'n/a'}")
    for line in action_lines:
        print(line)
    print("[/EV DEBUG]\n")


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
    print(f"EV> {text}")


def _is_exit(t: str) -> bool:
    s = (t or "").strip().lower()
    return s in ("bye", "bye!", "bye mate", "bye4") or s.startswith(("exit", "quit", "bye"))


if __name__ == "__main__":
    try:
        while True:
            user_text = input("\nYou> ").strip()
            if not user_text:
                continue

            if _is_exit(user_text):
                speak("Bye.")
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
        print("\nEV> Bye.")
