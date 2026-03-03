# EV Core

EV Core is a deterministic-first, local AI orchestration framework designed for reliable, reboot-safe, system-level AI integration.

Built for embedded-class devices (including Jetson platforms), EV Core focuses on stability, traceability, and safe expansion — not demo scripts.

---

## Design Philosophy (Golden Rules)

- Local-first (no mandatory cloud dependency)
- No terminal-dependent processes
- Everything critical runs as a `systemd` service
- Every service produces logs
- Reboot-safe by default
- Deterministic routing before LLM fallback

EV Core is infrastructure — not a chatbot wrapper.

---

## Architecture Overview

High-level runtime flow:

User Input  
→ Router (deterministic decisions first)  
→ Engine (tool execution or LLM fallback)  
→ Run-scoped logging  
→ Output  

Planned service layout:

1. `wirepod.service` — Vector interface layer  
2. `evcore-llm.service` — Local LLM runtime  
3. `evcore-bridge.service` — Logic bridge between interface and brain  

---

## Current Status

**Phase 1 – Stable**
- Deterministic routing
- Clarification logic
- Memory foundation
- Run-scoped logging
- Version-controlled core

**Phase 2 – In Progress**
- Agent orchestration hardening
- Guardrails + validation workflow
- Patch-safe execution model

---

## Repository Structure

- `scripts/` — Core runtime logic (router, engine, loop)
- `config/` — Configuration files
- `logs/` — Run logs (git ignored)
- `agents/` — Local-only agent system (git ignored)
- `models/` — Local LLM models (git ignored)
- `llama.cpp/` — External dependency (git ignored)

---

## Roadmap

- Lightweight UI panel for run inspection
- Service health monitoring
- Autostart service hardening
- Structured agent safety constraints
- Production-ready system deployment model

---

## Licence

Apache-2.0
