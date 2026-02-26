#!/usr/bin/env bash
set -e

MODEL="$HOME/evcore/models/llama-3.2-3b-instruct.Q4_K_M.gguf"
BIN="$HOME/evcore/llama.cpp/build/bin/llama-server"

exec "$BIN" \
  --model "$MODEL" \
  --host 127.0.0.1 \
  --port 8088 \
  --ctx-size 4096 \
  --threads 8 \
  --n-gpu-layers 99
