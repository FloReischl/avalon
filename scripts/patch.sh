#!/bin/bash

# cd ~/dev/avalon
# source .venv/bin/activate
# cd ~/dev

source ~/dev/avalon/.venv/bin/activate

python ~/dev/avalon/scripts/base/prompt2code.py \
  --input-script ~/dev/avalon/data/patch.p2c \
  --target-dir ~/dev/avalon
