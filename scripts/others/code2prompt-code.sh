#!/bin/bash

code2prompt ~/dev/avalon/ \
  -O ~/dev/avalon/data/code2prompt-code.md \
  -F markdown \
  --exclude="**/node_modules/**" \
  --exclude="**/__pycache__/**" \
  --exclude="scripts/**" \
  --exclude="docs/**"
