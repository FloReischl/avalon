#!/bin/bash

# cd ~/dev/avalo
# source .venv/bin/activate
# cd ~/dev

source ~/dev/avalo/.venv/bin/activate

python ~/dev/avalo/scripts/base/prompt2code.py \
  --input-script ~/dev/avalo/data/prompt2code-patch.p2c \
  --target-dir ~/dev/avalo
