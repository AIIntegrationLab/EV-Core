EV Core – Process Model (Golden Rules)

- Local-first (no cloud dependency)
- No terminal-dependent processes
- Everything important runs as a systemd service
- Logs must exist for every service
- Reboot-safe by default

Planned services:
1) wirepod.service      (Vector interface)
2) evcore-llm.service   (Local LLM brain)
3) evcore-bridge.service (Glue/logic between Wire-Pod and LLM)
