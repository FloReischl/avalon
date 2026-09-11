#!/usr/bin/env bash
set -euo pipefail

BASE_MODEL="gemma4:e4b-it-q4_K_M"
# BASE_MODEL="hf.co/TrevorJS/gemma-4-E4B-it-uncensored-GGUF:Q4_K_M"
GPU_LAYERS="${1:-34}"
TARGET_MODEL="${BASE_MODEL}-test-balanced"

TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT

cat >"$TMPFILE" <<EOF
FROM ${BASE_MODEL}
PARAMETER num_gpu ${GPU_LAYERS}
EOF

echo "Creating Ollama model:"
echo "  Base:       ${BASE_MODEL}"
echo "  GPU layers: ${GPU_LAYERS}"
echo "  Target:     ${TARGET_MODEL}"
echo

ollama create "$TARGET_MODEL" -f "$TMPFILE"

echo
echo "Done."
echo
echo "Test model:"
echo "  ollama run ${TARGET_MODEL}"
echo
echo "Inspect GPU split:"
echo "  ollama ps"
echo "  nvidia-smi"
