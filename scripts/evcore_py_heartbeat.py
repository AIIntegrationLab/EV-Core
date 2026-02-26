import time
from datetime import datetime
from pathlib import Path

logfile = Path.home() / "evcore" / "logs" / "py-heartbeat.log"
logfile.parent.mkdir(parents=True, exist_ok=True)

with logfile.open("a", buffering=1) as f:  # line-buffered
    while True:
        f.write(f"{datetime.now().isoformat()} EV Core PY heartbeat OK (venv python)\n")
        time.sleep(10)
