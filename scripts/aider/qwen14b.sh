#!/usr/bin/env bash
set -euo pipefail

#~/scripts/dev/register-gemini-api-key.sh

aider --model ollama_chat/qwen2.5-coder:14b-instruct-ctx16k --architect --map-tokens 500
