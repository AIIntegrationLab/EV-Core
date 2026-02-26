from __future__ import annotations

import json
import re
from typing import Any, Dict

import requests

LLM_URL = "http://127.0.0.1:8088/v1/chat/completions"

_REPAIR_SYSTEM = (
    "You are a JSON repair tool. "
    "Return ONLY valid JSON (no markdown, no commentary). "
    "The JSON MUST start with { and end with }. "
    "Fix any syntax issues (missing commas, extra braces, bad quotes). "
)

def _basic_clean(s: str) -> str:
    clean = (s or "").strip()

    # unwrap if model returned JSON inside quotes
    if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        clean = clean[1:-1].strip()

    # unescape quotes if needed
    clean = clean.replace('\\"', '"')

    # take only the first {...} block if there's extra junk around it
    m = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    if m:
        clean = m.group(0).strip()

    return clean

def _repair_via_llm(bad_json: str) -> str:
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": _REPAIR_SYSTEM},
            {"role": "user", "content": f"Repair this into valid JSON only:\n\n{bad_json}"},
        ],
        "temperature": 0.0,
    }
    r = requests.post(LLM_URL, json=payload, timeout=60)
    r.raise_for_status()
    return (r.json()["choices"][0]["message"]["content"] or "").strip()

def extract_json(text: str) -> Dict[str, Any]:
    clean = _basic_clean(text)

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        repaired = _repair_via_llm(clean)
        repaired = _basic_clean(repaired)
        return json.loads(repaired)
