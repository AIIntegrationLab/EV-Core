from __future__ import annotations

import re
from typing import Dict, Optional

# Very small, deterministic fact set (expand later)
_NAME_RE = re.compile(r"\b(my name is|i am|i'm)\s+([A-Za-z][A-Za-z\-']{1,30})\b", re.IGNORECASE)
_LIVE_RE = re.compile(r"\b(i live in|i'm in|im in)\s+([A-Za-z][A-Za-z\-\s']{1,40})\b", re.IGNORECASE)

def extract_fact(user_text: str) -> Optional[Dict[str, str]]:
    t = (user_text or "").strip()

    m = _NAME_RE.search(t)
    if m:
        name = m.group(2).strip()
        # Normalise name: Julian -> Julian
        name = name[:1].upper() + name[1:].lower()
        return {"key": "name", "value": name}

    m = _LIVE_RE.search(t)
    if m:
        city = m.group(2).strip()
        # Keep city reasonably tidy
        city = " ".join(w[:1].upper() + w[1:].lower() for w in city.split())
        return {"key": "home_city", "value": city}

    return None
