# cd ~/dev/avalo
# source .venv/bin/activate
# cd ~/dev

source ../.venv/bin/activate

python ~/scripts/dev/prompt2code.py \
  --input-script ./prompt2code-patch.yaml \
  --target-dir ~/dev/avalo

