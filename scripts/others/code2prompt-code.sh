#!/bin/bash

code2prompt ~/dev/avalo/ \
  -O ~/dev/avalo/data/code2prompt-code.md \
  -F markdown \
  --exclude="**/node_modules/**" \
  --exclude="**/__pycache__/**" \
  --exclude="scripts/**" \
  --exclude="docs/**"
