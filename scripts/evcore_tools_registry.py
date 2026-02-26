from __future__ import annotations
from typing import Callable, Dict

from evcore_tools import tool_time

TOOLS: Dict[str, Callable[..., str]] = {
    "time": tool_time,
}
