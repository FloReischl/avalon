#!/bin/bash

# cd ~/dev/avalo
# source .venv/bin/activate
# cd ~/dev

source ../.venv/bin/activate

python ./base/prompt2code.py \
  --input-script ./data/prompt2code-patch.p2c \
  --target-dir ~/dev/avalo
