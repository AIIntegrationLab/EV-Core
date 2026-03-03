# Contributing to EV Core

Thanks for your interest in contributing.

EV Core is built with a strong bias towards reliability and traceability. Contributions that improve determinism, safety, and maintainability are especially welcome.

## Ground rules

- Keep changes small and reviewable (one improvement per PR where possible).
- Preserve the deterministic-first design (tools/routing before LLM fallback).
- Do not commit secrets, keys, tokens, or private configuration.
- Do not add large binaries or model files to the repo.

## Development workflow

1. Fork the repo (or create a branch if you have access).
2. Create a feature branch:
   - `feature/<short-description>`
3. Make changes with clear commits.
4. Open a PR into `dev` with:
   - what changed
   - why it changed
   - how to test it manually (brief)

## What belongs in this repo

- Core runtime logic (`scripts/`)
- Configuration templates (`config/`)
- Documentation

## What does NOT belong in this repo

- `models/` (local model weights)
- `llama.cpp/` (external dependency)
- `logs/` (run artefacts)
- `agents/` (local-only agent system, intentionally isolated)
- `.env` files or credentials

## Reporting issues

Please include:
- device/OS info
- relevant log snippets (redact secrets)
- steps to reproduce
- expected vs actual behaviour
