#!/usr/bin/env bash
set -euo pipefail

BASE_MODEL="gemma4:e4b-it-q4_K_M"
# BASE_MODEL="qwen2.5-coder:7b-instruct"
TARGET_MODEL="${BASE_MODEL}-ctx16k"

TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT

# note to myself 32k = 32768, 16k = 16384
cat >"$TMPFILE" <<EOF
FROM ${BASE_MODEL}
PARAMETER num_ctx 16384
EOF

echo "Creating Ollama model:"
echo "  Base:       ${BASE_MODEL}"
echo "  Target:     ${TARGET_MODEL}"
echo

ollama create "$TARGET_MODEL" -f "$TMPFILE"

echo
echo "Done."
echo
echo "Test model:"
echo "  ollama run ${TARGET_MODEL}"
echo
echo "Inspect VRAM:"
echo "  ollama ps"
echo "  nvidia-smi"
