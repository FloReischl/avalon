#!/bin/bash

code2prompt ~/dev/avalo/docs/adrs \
  -O ./data/code2prompt-adrs.md \
  -F markdown \
  --exclude="**/node_modules/**" \
  --exclude="**/__pycache__/**" \
  --exclude="**/09-prompt2code-source-pathing-frieda-instructions.md"

