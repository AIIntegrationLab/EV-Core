from __future__ import annotations

from typing import Dict, Any, List

_FACTS: Dict[str, str] = {}

def remember_fact(key: str, value: str) -> None:
    if not key or not value:
        return
    _FACTS[key] = value

def get_facts() -> Dict[str, str]:
    return dict(_FACTS)

def get_memory_context() -> str:
    if not _FACTS:
        return ""
    # Compact, deterministic memory format
    lines = [f"- {k}: {v}" for k, v in sorted(_FACTS.items())]
    return "\n".join(lines)

def clear_memory() -> None:
    _FACTS.clear()
