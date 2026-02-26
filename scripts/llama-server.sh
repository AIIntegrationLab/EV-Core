#!/usr/bin/env bash
set -euo pipefail

MODEL="$HOME/evcore/models/llama-3.2-3b-instruct.Q4_K_M.gguf"
PORT="8088"
LOG="$HOME/evcore/logs/llama-server.log"

mkdir -p "$(dirname "$LOG")"

exec "$HOME/evcore/llama.cpp/build/bin/llama-server" \
  -m "$MODEL" \
  --host 127.0.0.1 --port "$PORT" \
  -c 4096 \
  >> "$LOG" 2>&1
