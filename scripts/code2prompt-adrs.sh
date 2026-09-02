#!/bin/bash

code2prompt ~/dev/avalo/docs/adrs \
  -O ./data/code2prompt-adrs.md \
  -F markdown \
  --exclude="**/node_modules/**" \
  --exclude="**/__pycache__/**"

