#!/usr/bin/env bash
set -euo pipefail

~/scripts/dev/register-gemini-api-key.sh

aider --model gemini/gemini-flash-lite-latest --edit-format diff

