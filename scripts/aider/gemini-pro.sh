#!/usr/bin/env bash
set -euo pipefail

~/scripts/dev/register-gemini-api-key.sh

# stable
aider --model gemini/gemini-2.5-pro
#aider --model gemini/gemini-2.5-pro --architect

# experimental!
#aider --model gemini/gemini-3.1-pro-preview
#aider --model gemini/gemini-3.1-pro-preview --architect
